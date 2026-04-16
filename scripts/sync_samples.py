"""assets/samples/ 를 Google Drive 와 양방향 동기화 (rclone 기반).

assets/samples/ 는 .gitignore (개인 사진 보호) — 새 환경에 클론한 뒤
본인 Drive 에서 당겨오면 기존 실험 YAML 이 그대로 동작한다.

Drive 경로: gdrive:<root>/assets/samples/  (기본 root = i2v-experiments)

사전 준비
---------
rclone 설치 + 'gdrive' remote 등록 (scripts/sync_to_drive.py 상단 docstring 참고).
확인: `rclone lsd gdrive:`.

Usage
-----
    # Drive 로 업로드 (로컬 → 리모트)
    python scripts/sync_samples.py push
    python scripts/sync_samples.py push --dry-run

    # Drive 에서 복원 (리모트 → 로컬, 클론 직후)
    python scripts/sync_samples.py pull

    # 상태 확인
    python scripts/sync_samples.py list
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def _require_rclone() -> None:
    if shutil.which("rclone") is None:
        raise SystemExit(
            "rclone not found. install: curl https://rclone.org/install.sh | sudo bash"
        )


def _remote_path(remote: str, drive_root: str) -> str:
    return f"{remote}:{drive_root}/assets/samples"


def push(local: Path, remote: str, drive_root: str, dry_run: bool) -> int:
    if not local.exists():
        raise SystemExit(f"local dir not found: {local}")
    rp = _remote_path(remote, drive_root)
    cmd = ["rclone", "copy", str(local), rp, "--progress",
           "--exclude", ".gitkeep", "--exclude", ".DS_Store"]
    if dry_run:
        cmd.append("--dry-run")
    print(f"[push] {local} -> {rp}")
    print(f"       {' '.join(cmd)}")
    return subprocess.run(cmd).returncode


def pull(local: Path, remote: str, drive_root: str, dry_run: bool) -> int:
    rp = _remote_path(remote, drive_root)
    local.mkdir(parents=True, exist_ok=True)
    cmd = ["rclone", "copy", rp, str(local), "--progress"]
    if dry_run:
        cmd.append("--dry-run")
    print(f"[pull] {rp} -> {local}")
    print(f"       {' '.join(cmd)}")
    return subprocess.run(cmd).returncode


def list_remote(remote: str, drive_root: str) -> int:
    rp = _remote_path(remote, drive_root)
    print(f"[list] {rp}")
    return subprocess.run(["rclone", "ls", rp]).returncode


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["push", "pull", "list"])
    ap.add_argument("--local", type=Path, default=Path("assets/samples"))
    ap.add_argument("--remote", default="gdrive")
    ap.add_argument("--drive-root", default="i2v-experiments")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    _require_rclone()

    if args.action == "push":
        rc = push(args.local, args.remote, args.drive_root, args.dry_run)
    elif args.action == "pull":
        rc = pull(args.local, args.remote, args.drive_root, args.dry_run)
    else:
        rc = list_remote(args.remote, args.drive_root)

    sys.exit(rc)


if __name__ == "__main__":
    main()
