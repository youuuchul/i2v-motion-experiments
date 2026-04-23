"""Run one experiment YAML end-to-end.

Usage:
    python scripts/run_inference.py --config configs/experiments/smoke_wan2_1_vace_14b.yaml

각 실행은 outputs/<exp>/<exp>_<ts>_seed<N>/ 디렉토리에 video/config/run.log/meta.json을 남기고
outputs/index.jsonl 에 요약 한 줄을 append 한다.
"""
from __future__ import annotations

import argparse
import importlib
import time
import traceback
from pathlib import Path

from PIL import Image, ImageOps

import i2v.models  # noqa: F401  (trigger registry)
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--outputs-root", type=Path, default=Path("outputs"))
    args = ap.parse_args()

    cfg = load_yaml(args.config)
    model_cfg = load_yaml(cfg["model_config"])
    preset = load_yaml(cfg["preset"])
    run = cfg["run"]
    inp = cfg["input"]

    experiment = cfg.get("experiment") or args.config.stem
    seed = run.get("seed")
    run_dir = make_run_dir(args.outputs_root, experiment, seed)
    snapshot_config(run_dir, cfg, preset, model_cfg)
    started_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    run_id = build_run_id(experiment, started_at, seed)

    status = "ok"
    error: str | None = None
    video_path: Path | None = None
    wall_sec: float | None = None
    vram_peak: float | None = None
    load_sec: float | None = None
    inference_sec: float | None = None

    with Tee(run_dir / "run.log"):
        t0 = time.time()
        try:
            if seed is not None:
                seed_everything(seed)

            spec = VideoSpec(**preset)
            image = ImageOps.exif_transpose(Image.open(inp["image"])).convert("RGB")
            image = center_crop_to_aspect(image, spec.width, spec.height)

            mode = inp.get("mode", "i2v")
            reference_images = [
                center_crop_to_aspect(
                    ImageOps.exif_transpose(Image.open(p)).convert("RGB"),
                    spec.width, spec.height,
                )
                for p in inp.get("reference_images", [])
            ]

            _ = registry  # keeps import used
            pipe, load_sec = _build_pipeline(model_cfg)

            request = GenerationRequest(
                image=image,
                prompt=inp.get("prompt", ""),
                negative_prompt=inp.get("negative_prompt", ""),
                mode=mode,
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
            vram_peak = _vram_peak_mib()

    finished_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    meta = build_meta_v2(
        run_id=run_id,
        run_dir=run_dir,
        config_path=args.config,
        cfg=cfg,
        preset=preset,
        model_cfg=model_cfg,
        started_at=started_at,
        finished_at=finished_at,
        status=status,
        error=error,
        video_path=video_path,
        wall_sec=wall_sec,
        vram_peak_mib=round(vram_peak, 1) if vram_peak is not None else None,
        load_sec=load_sec,
        inference_sec=inference_sec,
    )
    write_meta(run_dir, meta)
    append_index(args.outputs_root, to_index_entry(meta))

    if status != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
