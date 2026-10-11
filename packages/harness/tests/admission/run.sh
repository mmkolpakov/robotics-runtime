#!/usr/bin/env bash
set -euo pipefail
runtime="${CONTAINER_RUNTIME:-docker}"
root="$(realpath "${1:-artifacts/evaluator-admission}")"
image="${2:-evaluator-admission:ci}"
archive_target="${3:-$root/archive}"
user_namespace=()
if [[ "${runtime##*/}" == podman ]]; then
  init_path="$(realpath "${CONTAINER_INIT:?set the existing pinned stock catatonit path}")"
  observed="$(sha256sum -- "$init_path")"
  if [[ "${observed%% *}" != 43e9b836ca7631672f12d0610cd574875b62d236dfd62e3b86751f35862e5eba ]]; then
    echo "stock init binary differs from the approved fixture pin" >&2
    exit 1
  fi
  user_namespace=(--userns keep-id --init-path "$init_path")
fi
cid="$root/container.cid"
rm -f "$cid"
cleanup() {
  if [[ -s "$cid" ]]; then
    "$runtime" rm --force "$(cat "$cid")" >/dev/null 2>&1 || true
    rm -f "$cid"
  fi
}
trap cleanup EXIT
mkdir -p "$root/assessment"
timeout --signal=TERM --kill-after=10s 180s "$runtime" run --rm --init \
  "${user_namespace[@]}" --cidfile "$cid" --user "$(id -u):$(id -g)" --read-only \
  --network none --cap-drop ALL --security-opt no-new-privileges \
  --memory 512m --cpus 1 --pids-limit 32 \
  --tmpfs /tmp:rw,exec,nosuid,nodev,mode=1777,size=256m \
  --mount "type=bind,source=$root/archive,target=$archive_target,readonly" \
  --mount "type=bind,source=$root/inputs.json,target=/inputs.json,readonly" \
  --mount "type=bind,source=$root/expectations.json,target=/expectations.json,readonly" \
  --mount "type=bind,source=$root/assessment,target=/assessment" \
  --entrypoint python "$image" /opt/admission/witness.py
