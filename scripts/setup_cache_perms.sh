#!/usr/bin/env bash
# 도커 cache 볼륨의 소유권을 호스트 UID/GID 로 맞춤.
# 새 환경 / 다른 팀원 / volume prune 후 1회 실행.
#
# 배경: compose 가 user UID 매핑으로 컨테이너를 띄우는데, named volume 의 초기 권한은
# root:root 이라 hf_hub_download/from_pretrained 가 디렉토리 만들 때 PermissionError.
#
# Usage: bash scripts/setup_cache_perms.sh
set -euo pipefail

UID_VAL="${UID:-$(id -u)}"
GID_VAL="${GID:-$(id -g)}"

VOLUMES=(
  "docker_hf_cache"
  "docker_torch_cache"
)

for v in "${VOLUMES[@]}"; do
  path="/var/lib/docker/volumes/${v}/_data"
  if [ -d "$path" ]; then
    echo "[chown] ${path} -> ${UID_VAL}:${GID_VAL}"
    sudo chown -R "${UID_VAL}:${GID_VAL}" "$path"
  else
    echo "[skip] ${path} (not found — volume not yet created)"
  fi
done

echo "[done] cache perms aligned to host UID/GID"
