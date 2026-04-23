"""여러 실험 YAML을 순차 실행. 동일 model_config는 로드 한 번만.

각 실행은 run_inference.py 와 동일한 로깅 규약 (run_dir + meta + index) 을 따른다.

Usage:
    python scripts/run_batch.py --configs configs/experiments/a.yaml configs/experiments/b.yaml
    python scripts/run_batch.py --glob "configs/experiments/wan_vace_*.yaml"
"""
from __future__ import annotations

import argparse
import glob as _glob
import importlib
import subprocess
import sys
import time
import traceback
from pathlib import Path

from PIL import Image, ImageOps

import i2v.models  # noqa: F401
from i2v.core.registry import registry
from i2v.core.types import GenerationRequest, VideoSpec
from i2v.utils.config import load_yaml
from i2v.utils.meta_v2 import build_meta_v2, build_run_id, to_index_entry
from i2v.utils.run_logging import (
    Tee,
    append_index,
    make_run_dir,
    snapshot_config,
    write_meta,
)
from i2v.utils.seed import seed_everything
from i2v.utils.video import center_crop_to_aspect


def _build_pipeline(model_cfg: dict) -> tuple:
    """Returns (pipe, load_sec)."""
    cls_path = model_cfg["class"]
    module_name, cls_name = cls_path.rsplit(".", 1)
    cls = getattr(importlib.import_module(module_name), cls_name)
    pipe = cls(**model_cfg.get("init", {}))
    t = time.time()
    pipe.load()
    return pipe, round(time.time() - t, 2)


def _vram_peak_mib() -> float | None:
    try:
        import torch

        if torch.cuda.is_available():
            return torch.cuda.max_memory_allocated() / (1024 * 1024)
    except Exception:
        pass
    return None


def run_one(
    pipe, cfg_path: Path, cfg: dict, model_cfg: dict, outputs_root: Path,
    *, load_sec: float | None = None,
) -> dict:
    import torch

    preset = load_yaml(cfg["preset"])
    run = cfg["run"]
    inp = cfg["input"]
    experiment = cfg.get("experiment") or cfg_path.stem
    seed = run.get("seed")

    run_dir = make_run_dir(outputs_root, experiment, seed)
    snapshot_config(run_dir, cfg, preset, model_cfg)
    started_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    run_id = build_run_id(experiment, started_at, seed)

    status = "ok"
    error: str | None = None
    video_path: Path | None = None
    wall_sec: float | None = None
    inference_sec: float | None = None

    # 실행별 VRAM 피크 별도 측정 위해 리셋
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()

    with Tee(run_dir / "run.log"):
        t0 = time.time()
        try:
            if seed is not None:
                seed_everything(seed)
            spec = VideoSpec(**preset)
            image = ImageOps.exif_transpose(Image.open(inp["image"])).convert("RGB")
            image = center_crop_to_aspect(image, spec.width, spec.height)
            reference_images = [
                center_crop_to_aspect(
                    ImageOps.exif_transpose(Image.open(p)).convert("RGB"),
                    spec.width, spec.height,
                )
                for p in inp.get("reference_images", [])
            ]
            request = GenerationRequest(
                image=image,
                prompt=inp.get("prompt", ""),
                negative_prompt=inp.get("negative_prompt", ""),
                mode=inp.get("mode", "i2v"),
                reference_images=reference_images,
                spec=spec,
                seed=seed,
                guidance_scale=run.get("guidance_scale"),
                num_inference_steps=run.get("num_inference_steps"),
                extra={"out_dir": str(run_dir)},
            )
            t_gen = time.time()
            result = pipe.generate(request)
            inference_sec = round(time.time() - t_gen, 2)
            video_path = Path(result.video_path)
            print(f"saved -> {video_path}")
        except Exception as e:
            status = "error"
            error = f"{type(e).__name__}: {e}"
            traceback.print_exc()
        finally:
            wall_sec = round(time.time() - t0, 2)

    finished_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    vram_peak = _vram_peak_mib()
    meta = build_meta_v2(
        run_id=run_id,
        run_dir=run_dir,
        config_path=cfg_path,
        cfg=cfg,
        preset=preset,
        model_cfg=model_cfg,
        started_at=started_at,
        finished_at=finished_at,
        status=status,
        error=error,
        video_path=video_path,
        wall_sec=wall_sec,
        vram_peak_mib=round(vram_peak, 1) if vram_peak else None,
        load_sec=load_sec,
        inference_sec=inference_sec,
    )
    write_meta(run_dir, meta)
    entry = to_index_entry(meta)
    append_index(outputs_root, entry)
    return entry


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", nargs="*", type=Path, default=[])
    ap.add_argument("--glob", default=None, help="glob 패턴으로 configs 선택")
    ap.add_argument("--outputs-root", type=Path, default=Path("outputs"))
    ap.add_argument("--sync-after-each", action="store_true",
                    help="각 실행 성공 직후 해당 run_dir을 Drive로 sync (sync_to_drive.py 호출)")
    ap.add_argument("--sync-after-batch", action="store_true",
                    help="전체 배치 종료 후 아직 archive 안 된 run을 한꺼번에 sync")
    ap.add_argument("--sync-delete-local-video", action="store_true",
                    help="sync 시 --delete-local-video 전달")
    args = ap.parse_args()

    paths: list[Path] = list(args.configs)
    if args.glob:
        paths.extend(Path(p) for p in sorted(_glob.glob(args.glob)))
    paths = [p for p in paths if p.exists()]
    if not paths:
        raise SystemExit("no configs to run")

    # model_config 단위로 그룹핑 (동일 모델 연속 실행 시 로드 재사용)
    groups: dict[str, list[tuple[Path, dict, dict]]] = {}
    for p in paths:
        cfg = load_yaml(p)
        mcfg_path = cfg["model_config"]
        model_cfg = load_yaml(mcfg_path)
        groups.setdefault(mcfg_path, []).append((p, cfg, model_cfg))

    _ = registry
    print(f"[batch] {len(paths)} experiments across {len(groups)} model group(s)")

    ok, err = 0, 0
    for mcfg_path, items in groups.items():
        print(f"[batch] loading model: {mcfg_path}  ({len(items)} runs)")
        pipe, load_sec = _build_pipeline(items[0][2])
        print(f"[batch] model loaded in {load_sec}s")
        try:
            for i, (cfg_path, cfg, model_cfg) in enumerate(items, 1):
                print(f"[batch] ({i}/{len(items)}) {cfg_path.name}")
                # load_sec는 그룹의 첫 실행만 실측치, 이후 실행은 0 (로드 재사용)
                this_load = load_sec if i == 1 else 0.0
                entry = run_one(pipe, cfg_path, cfg, model_cfg, args.outputs_root, load_sec=this_load)
                if entry["status"] == "ok":
                    ok += 1
                    print(f"  OK wall={entry['wall_sec']}s")
                    if args.sync_after_each:
                        _sync(args.outputs_root, entry["experiment"],
                              delete_local_video=args.sync_delete_local_video)
                else:
                    err += 1
                    print(f"  ERR {entry['error']}")
        finally:
            try:
                pipe.unload()
            except Exception:
                pass

    print(f"[batch] done. ok={ok} err={err}")

    if args.sync_after_batch:
        print("[batch] syncing all unarchived runs to drive...")
        _sync(args.outputs_root, experiment=None,
              delete_local_video=args.sync_delete_local_video)


def _sync(outputs_root: Path, experiment: str | None, delete_local_video: bool) -> None:
    """sync_to_drive.py 를 서브프로세스로 호출. rclone 실패해도 배치는 계속 진행."""
    cmd = [sys.executable, "scripts/sync_to_drive.py", "--outputs-root", str(outputs_root)]
    if experiment:
        cmd += ["--experiment", experiment]
    if delete_local_video:
        cmd.append("--delete-local-video")
    print(f"  [sync] {' '.join(cmd)}")
    res = subprocess.run(cmd)
    if res.returncode != 0:
        print(f"  [sync] WARN returncode={res.returncode} (배치 계속 진행)")


if __name__ == "__main__":
    main()
