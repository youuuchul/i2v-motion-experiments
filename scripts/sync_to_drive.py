"""실험 결과물을 Google Drive에 백업 (rclone 사용).

사전 준비
---------
1) 로컬 PC에서 rclone 설치 후 `rclone config`로 'gdrive' remote 생성 (Drive OAuth).
2) 로컬의 `~/.config/rclone/rclone.conf` 를 VM의 `~/.config/rclone/rclone.conf` 로 복사.
3) VM 내부에서도 rclone 설치: `curl https://rclone.org/install.sh | sudo bash`
4) `rclone lsd gdrive:` 로 연결 확인.

정책
----
- 이 스크립트는 outputs/index.jsonl 을 읽어 아직 archive 되지 않은 run_dir 중
  --older-than-days / --experiment 필터를 만족하는 것만 업로드한다.
- 업로드 성공 시 인덱스의 해당 항목에 `archived: true`, `drive_path`가 기록된다.
- `--delete-local-video` 를 주면 업로드 완료 후 로컬의 video 파일만 삭제(작은 meta/config/log은 유지).
- Drive 경로: gdrive:<root>/<experiment>/<run_dir_basename>/

Usage
-----
    # 드라이런으로 대상 확인
    python scripts/sync_to_drive.py --dry-run

    # 7일 이상 된 것만 업로드 (video도 로컬 삭제)
    python scripts/sync_to_drive.py --older-than-days 7 --delete-local-video

    # 특정 실험만
    python scripts/sync_to_drive.py --experiment smoke_wan2_1_vace_14b
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path


def _require_rclone() -> None:
    if shutil.which("rclone") is None:
        raise SystemExit(
            "rclone not found. install: curl https://rclone.org/install.sh | sudo bash"
        )


def _read_index(idx: Path) -> list[dict]:
    if not idx.exists():
        return []
    entries = []
    for line in idx.read_text().splitlines():
        if line.strip():
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return entries


def _write_index(idx: Path, entries: list[dict]) -> None:
    tmp = idx.with_suffix(".jsonl.tmp")
    with open(tmp, "w") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    tmp.replace(idx)


def _parse_ts(s: str | None) -> datetime | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y%m%d-%H%M%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outputs-root", type=Path, default=Path("outputs"))
    ap.add_argument("--remote", default="gdrive")
    ap.add_argument("--drive-root", default="i2v-experiments")
    ap.add_argument("--older-than-days", type=int, default=0,
                    help="이 값(일) 이상 경과한 run_dir만 대상 (0=전부)")
    ap.add_argument("--experiment", default=None, help="특정 실험명만")
    ap.add_argument("--delete-local-video", action="store_true",
                    help="업로드 성공 시 로컬 video 파일 삭제 (meta/config/log는 유지)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    _require_rclone()

    idx_path = args.outputs_root / "index.jsonl"
    entries = _read_index(idx_path)
    if not entries:
        print("empty index")
        return

    cutoff = datetime.now() - timedelta(days=args.older_than_days)
    targets: list[tuple[int, dict]] = []
    for i, e in enumerate(entries):
        if e.get("archived"):
            continue
        if args.experiment and e.get("experiment") != args.experiment:
            continue
        started = _parse_ts(e.get("started_at"))
        if args.older_than_days and (started is None or started > cutoff):
            continue
        if not e.get("run_dir"):
            continue
        if not Path(e["run_dir"]).exists():
            continue
        targets.append((i, e))

    if not targets:
        print("nothing to upload")
        return

    print(f"{len(targets)} run(s) to upload")
    for i, e in targets:
        run_dir = Path(e["run_dir"])
        remote_path = f"{args.remote}:{args.drive_root}/{e['experiment']}/{run_dir.name}"
        print(f"[{'dry' if args.dry_run else 'upload'}] {run_dir} -> {remote_path}")
        if args.dry_run:
            continue

        cmd = ["rclone", "copy", str(run_dir), remote_path, "--progress"]
        res = subprocess.run(cmd)
        if res.returncode != 0:
            print(f"  FAILED rclone copy rc={res.returncode}; skipping index update")
            continue

        e["archived"] = True
        e["drive_path"] = remote_path
        e["archived_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        if args.delete_local_video and e.get("video_path"):
            vp = Path(e["video_path"])
            if vp.exists():
                try:
                    vp.unlink()
                    e["video_local_deleted"] = True
                    print(f"  removed local video: {vp}")
                except PermissionError as ex:
                    print(f"  WARN 로컬 삭제 실패 (drive 업로드는 성공): {ex}")
                    print(f"       수동 삭제: sudo rm {vp}")

        entries[i] = e

    if not args.dry_run:
        _write_index(idx_path, entries)
        print(f"index updated: {idx_path}")


if __name__ == "__main__":
    main()
