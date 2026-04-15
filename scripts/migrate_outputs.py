"""기존 outputs/ 아래의 비정형 결과(.mp4)를 신규 run_dir 규약으로 흡수.

탐지 규칙:
  - outputs/<exp>/ 아래에 있는 .mp4 중, 부모 디렉토리에 meta.json이 없는 것.
  - 이미 run_dir 규약에 편입된 건 건너뜀.

각 대상에 대해:
  - run_dir = outputs/<exp>/<exp>_<file_mtime_ts>_seedunknown/
  - 기존 mp4를 run_dir 로 옮김 (원본 삭제, 디스크 절약)
  - 최소 meta.json 생성 (legacy=true)
  - outputs/index.jsonl 에 append

Usage:
    python scripts/migrate_outputs.py --outputs-root outputs
    python scripts/migrate_outputs.py --outputs-root outputs --dry-run
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path


def _is_in_run_dir(mp4: Path) -> bool:
    return (mp4.parent / "meta.json").exists()


def _load_existing_index(idx: Path) -> set[str]:
    """이미 인덱스에 등록된 video_path 집합."""
    if not idx.exists():
        return set()
    seen = set()
    for line in idx.read_text().splitlines():
        if not line.strip():
            continue
        try:
            e = json.loads(line)
            if e.get("video_path"):
                seen.add(e["video_path"])
        except json.JSONDecodeError:
            continue
    return seen


def migrate(outputs_root: Path, dry_run: bool = False) -> None:
    if not outputs_root.exists():
        print(f"no outputs dir: {outputs_root}")
        return

    index_path = outputs_root / "index.jsonl"
    indexed = _load_existing_index(index_path)

    mp4s = [p for p in outputs_root.rglob("*.mp4") if not _is_in_run_dir(p)]
    if not mp4s:
        print("nothing to migrate")
        return

    for mp4 in mp4s:
        if str(mp4) in indexed:
            continue
        exp_dir = mp4.parent
        experiment = exp_dir.name
        ts = datetime.fromtimestamp(mp4.stat().st_mtime).strftime("%Y%m%d-%H%M%S")
        run_dir = exp_dir / f"{experiment}_{ts}_seedunknown"
        new_video = run_dir / mp4.name

        entry = {
            "experiment": experiment,
            "run_dir": str(run_dir),
            "video_path": str(new_video),
            "model": None,
            "mode": None,
            "prompt": None,
            "seed": None,
            "num_inference_steps": None,
            "guidance_scale": None,
            "status": "ok",
            "wall_sec": None,
            "vram_peak_mib": None,
            "started_at": ts,
            "finished_at": ts,
            "legacy": True,
        }

        print(f"{'[dry]' if dry_run else '[mv] '} {mp4} -> {new_video}")
        if dry_run:
            continue

        run_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(mp4), str(new_video))
        (run_dir / "meta.json").write_text(json.dumps(entry, indent=2, ensure_ascii=False))
        with open(index_path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outputs-root", type=Path, default=Path("outputs"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    migrate(args.outputs_root, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
