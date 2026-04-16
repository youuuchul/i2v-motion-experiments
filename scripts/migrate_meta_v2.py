"""legacy meta.json (v1) → v2 마이그레이션.

규칙: docs/SCHEMA.md

- outputs/ 트리에서 모든 meta.json 스캔
- schema_version 없거나 < 2 이면 변환
- 원본은 meta.json.v1.bak 으로 보관
- index.jsonl 재생성 (기존 백업 → index.jsonl.v1.bak)

휴리스틱:
- experiment 명에서 category/subcategory 추론 (실패 시 null)
- image_hash 는 파일 존재 시 계산
- legacy=True 마킹

Usage:
    python scripts/migrate_meta_v2.py --outputs-root outputs --dry-run
    python scripts/migrate_meta_v2.py --outputs-root outputs
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from i2v.utils.meta_v2 import (
    SCHEMA_VERSION,
    _file_sha256,
    _infer_offload,
    _infer_quantization,
    _resolution_tier,
    _video_size_mb,
    compute_config_hash,
    to_index_entry,
)

# 실험명 키워드 → (category, subcategory) 휴리스틱
CATEGORY_HEURISTICS: list[tuple[str, str, str]] = [
    ("offer_drink",   "person_action", "offer_drink"),
    ("rim_light",     "camera_move",   "rim_light"),
    ("golden_hour",   "camera_move",   "golden_hour"),
    ("silhouette",    "camera_move",   "silhouette"),
    ("dolly_pan",     "camera_move",   "dolly_pan"),
    ("dolly_in",      "camera_move",   "dolly_in"),
    ("focus_shift",   "camera_move",   "face_to_bg"),
    ("rack_focus",    "camera_move",   "rack_focus"),
    ("food_steam",    "food_motion",   "steam_rise"),
    ("steam",         "food_motion",   "steam_rise"),
    ("drink_ripple",  "drink_motion",  "ripple"),
    ("foam",          "drink_motion",  "foam_settle"),
    ("ripple",        "drink_motion",  "ripple"),
    ("smoke_",        None,            None),  # 명시적으로 null
]


def infer_template(experiment: str) -> tuple[str | None, str | None]:
    name = experiment.lower()
    for kw, cat, sub in CATEGORY_HEURISTICS:
        if kw in name:
            return cat, sub
    return None, None


def convert_v1_to_v2(v1: dict, meta_path: Path) -> dict:
    experiment = v1.get("experiment") or meta_path.parent.name
    seed = v1.get("seed")
    started_at = v1.get("started_at") or ""
    finished_at = v1.get("finished_at") or ""

    ts = (started_at or "").replace("-", "").replace(":", "")
    seed_part = f"seed{seed}" if seed is not None else "seedrand"
    run_id = f"{experiment}_{ts}_{seed_part}" if ts else f"{experiment}_legacy_{seed_part}"

    preset = v1.get("preset") or {}
    width = int(preset.get("width") or 0)
    height = int(preset.get("height") or 0)
    fps = int(preset.get("fps") or 0)
    duration_s = float(preset.get("duration_s") or 0.0)
    num_frames = int(round(fps * duration_s)) if fps and duration_s else None

    model_init = v1.get("model_init") or {}
    model_cfg_proxy = {
        "name": v1.get("model"),
        "class": v1.get("model_class"),
        "init": model_init,
    }

    cat, sub = infer_template(experiment)
    image_path = v1.get("image_path")
    video_path = v1.get("video_path")

    out = {
        "schema_version": SCHEMA_VERSION,
        "legacy": True,
        "run": {
            "run_id": run_id,
            "run_dir": v1.get("run_dir") or str(meta_path.parent),
            "config_path": v1.get("config_path"),
            "started_at": started_at or None,
            "finished_at": finished_at or None,
            "status": v1.get("status") or "ok",
            "error": v1.get("error"),
        },
        "experiment": {
            "name": experiment,
            "notes": None,
            "tags": ["legacy"],
        },
        "template": {
            "template_id": None,
            "category": cat,
            "subcategory": sub,
            "intent": None,
            "secondary": [],
            "promoted_at": None,
        },
        "input": {
            "mode": v1.get("mode", "i2v"),
            "image_path": image_path,
            "image_hash": _file_sha256(image_path) if image_path else None,
            "reference_images": [],
            "prompt": v1.get("prompt", ""),
            "negative_prompt": v1.get("negative_prompt", ""),
        },
        "model": {
            "name": v1.get("model"),
            "class": v1.get("model_class"),
            "version": None,
            "quantization": _infer_quantization(model_cfg_proxy),
            "offload": _infer_offload(model_cfg_proxy),
            "lora": [],
        },
        "generation": {
            "seed": seed,
            "num_inference_steps": v1.get("num_inference_steps"),
            "guidance_scale": v1.get("guidance_scale"),
            "width": width,
            "height": height,
            "fps": fps,
            "num_frames": num_frames,
            "duration_s": duration_s,
            "aspect": preset.get("aspect"),
            "resolution_tier": _resolution_tier(width, height) if width and height else None,
        },
        "output": {
            "video_path": video_path,
            "video_size_mb": _video_size_mb(video_path),
            "archived": bool(v1.get("archived", False)),
            "drive_path": v1.get("drive_path"),
            "archived_at": v1.get("archived_at"),
        },
        "metrics": {
            "wall_sec": v1.get("wall_sec"),
            "load_sec": None,
            "inference_sec": None,
            "vram_peak_mib": v1.get("vram_peak_mib"),
            "ram_peak_mib": None,
            "steps_per_sec": None,
        },
        "environment": {
            "gpu": None,
            "vram_total_gib": None,
            "host": None,
            "driver": None,
            "torch": None,
            "diffusers": None,
        },
    }
    out["run"]["config_hash"] = compute_config_hash(out)
    return out


def backfill_v2(meta: dict) -> bool:
    """이미 v2 인 meta 에 누락된 필드 채움. True 반환 시 변경됨."""
    changed = False
    run = meta.setdefault("run", {})
    if not run.get("config_hash"):
        run["config_hash"] = compute_config_hash(meta)
        changed = True
    tmpl = meta.setdefault("template", {})
    if "secondary" not in tmpl:
        tmpl["secondary"] = []
        changed = True
    return changed


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outputs-root", type=Path, default=Path("outputs"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root: Path = args.outputs_root
    if not root.exists():
        raise SystemExit(f"outputs root not found: {root}")

    meta_files = sorted(root.glob("**/meta.json"))
    print(f"[migrate] found {len(meta_files)} meta.json files under {root}")

    converted = 0
    skipped_v2 = 0
    failed: list[tuple[Path, str]] = []
    new_metas: list[dict] = []

    for mp in meta_files:
        try:
            data = json.loads(mp.read_text())
        except Exception as e:
            failed.append((mp, f"read error: {e}"))
            continue

        sv = data.get("schema_version")
        if sv and sv >= SCHEMA_VERSION:
            # 이미 v2 — 누락 필드 (config_hash, secondary 등) backfill
            if backfill_v2(data):
                if not args.dry_run:
                    mp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str))
            skipped_v2 += 1
            new_metas.append(data)
            continue

        try:
            v2 = convert_v1_to_v2(data, mp)
        except Exception as e:
            failed.append((mp, f"convert error: {e}"))
            continue

        new_metas.append(v2)
        if args.dry_run:
            converted += 1
            print(f"  [dry] would convert: {mp}")
            continue

        backup = mp.with_suffix(".json.v1.bak")
        if not backup.exists():
            mp.replace(backup)
        mp.write_text(json.dumps(v2, indent=2, ensure_ascii=False, default=str))
        converted += 1
        print(f"  converted: {mp}")

    # index.jsonl 재생성
    idx = root / "index.jsonl"
    if not args.dry_run:
        if idx.exists():
            bak = root / "index.jsonl.v1.bak"
            if not bak.exists():
                idx.replace(bak)
            else:
                idx.unlink()
        with open(idx, "w") as f:
            for m in new_metas:
                f.write(json.dumps(to_index_entry(m), ensure_ascii=False, default=str) + "\n")
        print(f"[migrate] rebuilt {idx} ({len(new_metas)} entries)")
    else:
        print(f"[migrate] [dry] would rebuild index.jsonl with {len(new_metas)} entries")

    print(f"[migrate] done. converted={converted} skipped_v2={skipped_v2} failed={len(failed)}")
    for p, why in failed:
        print(f"  FAIL {p}: {why}")


if __name__ == "__main__":
    main()
