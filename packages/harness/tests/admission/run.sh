#!/usr/bin/env bash
set -euo pipefail
runtime="${CONTAINER_RUNTIME:-docker}"
root="$(realpath "${1:-artifacts/evaluator-admission}")"
image="${2:-evaluator-admission:ci}"
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
  --cidfile "$cid" --user "$(id -u):$(id -g)" --read-only \
  --network none --cap-drop ALL --security-opt no-new-privileges \
  --memory 512m --cpus 1 --pids-limit 32 \
  --tmpfs /tmp:rw,mode=1777,size=256m \
  --mount "type=bind,source=$root/archive,target=$root/archive,readonly" \
  --mount "type=bind,source=$root/inputs.json,target=/inputs.json,readonly" \
  --mount "type=bind,source=$root/expectations.json,target=/expectations.json,readonly" \
  --mount "type=bind,source=$root/assessment,target=/assessment" \
  --entrypoint python "$image" /opt/admission/witness.py
