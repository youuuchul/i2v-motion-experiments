"""실험 실행 디렉토리·로그·인덱스 기록 헬퍼.

디렉토리 규약:
    outputs/<exp>/<exp>_<YYYYMMDD-HHMMSS>_seed<N>/
        ├─ video.mp4            # 어댑터가 저장한 결과 (실제 파일명은 어댑터가 결정)
        ├─ config.snapshot.yaml # 실험/프리셋/모델 설정을 머지한 스냅샷
        ├─ run.log              # stdout+stderr 복제
        └─ meta.json            # 모델·양자화·시간·vram 피크 등

인덱스: outputs/index.jsonl 에 한 줄씩 append.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


def make_run_dir(outputs_root: Path, experiment: str, seed: int | None) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    seed_str = f"seed{seed}" if seed is not None else "seedrand"
    run_dir = outputs_root / experiment / f"{experiment}_{ts}_{seed_str}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def snapshot_config(run_dir: Path, experiment_cfg: dict[str, Any], preset: dict[str, Any],
                    model_cfg: dict[str, Any]) -> Path:
    snap = {
        "experiment": experiment_cfg,
        "preset": preset,
        "model": model_cfg,
    }
    path = run_dir / "config.snapshot.yaml"
    with open(path, "w") as f:
        yaml.safe_dump(snap, f, sort_keys=False, allow_unicode=True)
    return path


class Tee:
    """sys.stdout/stderr 에 연결해 콘솔과 파일에 동시 기록."""

    def __init__(self, file_path: Path):
        self._f = open(file_path, "w", buffering=1)  # line-buffered
        self._orig_out = sys.stdout
        self._orig_err = sys.stderr

    def __enter__(self) -> "Tee":
        sys.stdout = _Splitter(self._orig_out, self._f)
        sys.stderr = _Splitter(self._orig_err, self._f)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        sys.stdout = self._orig_out
        sys.stderr = self._orig_err
        self._f.close()


class _Splitter:
    def __init__(self, *streams):
        self._streams = streams

    def write(self, data: str) -> int:
        for s in self._streams:
            try:
                s.write(data)
            except Exception:
                pass
        return len(data)

    def flush(self) -> None:
        for s in self._streams:
            try:
                s.flush()
            except Exception:
                pass


def write_meta(run_dir: Path, meta: dict[str, Any]) -> Path:
    path = run_dir / "meta.json"
    with open(path, "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False, default=str)
    return path


def append_index(outputs_root: Path, entry: dict[str, Any]) -> None:
    idx = outputs_root / "index.jsonl"
    idx.parent.mkdir(parents=True, exist_ok=True)
    with open(idx, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
