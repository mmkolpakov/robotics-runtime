#!/usr/bin/env bash
set -Eeuo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd -P)"
cd "$root"
engine="${API_FIXTURE_ENGINE:-docker}"
[[ "$engine" == docker ]] || { printf "The stock checksum-bound composition requires Docker BuildKit\n" >&2; exit 69; }
build=(docker buildx build --builder default --load --platform linux/amd64)
scope="rr-api-ci-$(date +%s)-$$"
cleanupTimeout=15
if [[ "${1:-}" == --cleanup-only ]]; then
  scope="${API_FIXTURE_SUITE:?owned suite required}"
  cleanupTimeout="${API_FIXTURE_CLEANUP_TIMEOUT:-15}"
fi
[[ "$scope" =~ ^[a-z0-9-]{1,80}$ && "$cleanupTimeout" =~ ^[0-9]+$ ]]
((cleanupTimeout >= 1 && cleanupTimeout <= 30))
export API_FIXTURE_ENGINE="$engine" API_FIXTURE_SUITE="$scope"
mkdir -p artifacts api/.tools/bin
inputs="$root/artifacts/api-ci-inputs"
mkdir -p "$inputs"
cleanup() {
  local status=$? failed=0 id label
  trap - EXIT
  set +e
  local listing
  if listing="$(timeout "$cleanupTimeout" "$engine" ps --all --quiet --no-trunc --filter "label=org.robotics.runtime.fixture-suite=$scope")"; then
    for id in $listing; do
      [[ "$id" =~ ^[0-9a-f]{64}$ ]] || { failed=1; continue; }
      if ! label="$(timeout "$cleanupTimeout" "$engine" inspect --format '{{.Id}} {{index .Config.Labels "org.robotics.runtime.fixture-suite"}}' "$id")"; then failed=1; continue; fi
      if [[ "$label" == "$id $scope" ]]; then timeout "$cleanupTimeout" "$engine" rm --force "$id" >/dev/null || failed=1; else failed=1; fi
    done
  else failed=1; fi
  if listing="$(timeout "$cleanupTimeout" "$engine" volume ls --quiet --filter "label=org.robotics.runtime.fixture-suite=$scope")"; then
    for id in $listing; do
      [[ "$id" =~ ^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}$ ]] || { failed=1; continue; }
      if ! label="$(timeout "$cleanupTimeout" "$engine" volume inspect --format '{{.Name}} {{index .Labels "org.robotics.runtime.fixture-suite"}}' "$id")"; then failed=1; continue; fi
      if [[ "$label" == "$id $scope" ]]; then timeout "$cleanupTimeout" "$engine" volume rm "$id" >/dev/null || failed=1; else failed=1; fi
    done
  else failed=1; fi
  if listing="$(timeout "$cleanupTimeout" "$engine" network ls --quiet --no-trunc --filter "label=org.robotics.runtime.fixture-suite=$scope")"; then
    for id in $listing; do
      [[ "$id" =~ ^[0-9a-f]{64}$ ]] || { failed=1; continue; }
      if ! label="$(timeout "$cleanupTimeout" "$engine" network inspect --format '{{.Id}} {{index .Labels "org.robotics.runtime.fixture-suite"}}' "$id")"; then failed=1; continue; fi
      if [[ "$label" == "$id $scope" ]]; then timeout "$cleanupTimeout" "$engine" network rm "$id" >/dev/null || failed=1; else failed=1; fi
    done
  else failed=1; fi
  python3 - "$root/artifacts" "$scope" "$status" "$failed" <<'PY'
import json,shutil,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve()
for marker in root.glob('rr-*/fixture-owner.json'):
    value=json.loads(marker.read_bytes())
    if value['suite']!=sys.argv[2]:continue
    assert marker.parent.name==value['owner'] and marker.parent.resolve().parent==root
    secrets=marker.parent/'secrets'
    if secrets.exists():
        assert secrets.resolve().parent==marker.parent.resolve()
        shutil.rmtree(secrets)
(root/('api-ci-'+sys.argv[2]+'.json')).write_text(json.dumps({
    'suite':sys.argv[2],'originalExitCode':int(sys.argv[3]),'cleanupFailed':bool(int(sys.argv[4]))
},indent=2)+'\n')
PY
  if [[ $? != 0 ]]; then failed=1; fi
  node api/test/publish-safe-reports.mjs "$scope" || failed=1
  if [[ "$status" == 0 && "$failed" != 0 ]]; then status=1; fi
  exit "$status"
}
trap cleanup EXIT
if [[ "${1:-}" == --cleanup-only ]]; then [[ $# == 1 ]]; exit 0; fi
[[ $# == 0 ]]
"$engine" version >"artifacts/api-ci-$scope-engine.log"
"$engine" buildx version >"artifacts/api-ci-$scope-buildx.log"
"$engine" buildx inspect default --bootstrap >"artifacts/api-ci-$scope-builder.log"
grep -Eq "^Driver:[[:space:]]+docker$" "artifacts/api-ci-$scope-builder.log"
readarray -t pins < <(python3 - <<'PY'
import json
v=json.load(open('api/test/upstream-lock.json'))
for value in [v['fixtureSource']['revision'],v['fixtureSource']['workspaceRevision'],v['node']]:print(value)
PY
)
checkout() {
  local destination="$1" url="$2" revision="$3"
  if [[ ! -e "$destination/.git" ]]; then
    mkdir -p "$destination"
    git -C "$destination" init --quiet
    git -C "$destination" remote add origin "$url"
    GIT_TERMINAL_PROMPT=0 timeout 180 git -C "$destination" fetch --quiet --depth=1 origin "$revision"
    git -C "$destination" checkout --quiet --detach FETCH_HEAD
  fi
  [[ "$(git -C "$destination" rev-parse HEAD)" == "$revision" ]]
  git -C "$destination" diff --quiet HEAD --
}
infra="$inputs/infra";foundation="$inputs/foundation"
checkout "$infra" https://github.com/mmkolpakov/robotics-runtime-infra.git "${pins[0]}"
checkout "$foundation" https://github.com/mmkolpakov/robotics-runtime.git "${pins[1]}"
python3 - "$infra" <<'PY'
import json,sys
from pathlib import Path
expected=json.load(open('api/test/upstream-lock.json'))['fixtureSource']
actual=json.loads((Path(sys.argv[1])/'config/foundation-lock.json').read_bytes())
assert actual['workspace']['revision']==expected['workspaceRevision']
assert actual['packages']['contracts']['version']==expected['contracts']
assert actual['packages']['harness']['version']==expected['harness']
PY
nodeCopy="$scope-node"
"$engine" create --name "$nodeCopy" --label "org.robotics.runtime.fixture-suite=$scope" "${pins[2]}" >/dev/null
"$engine" cp "$nodeCopy:/usr/local/bin/node" api/.tools/node
if [[ ! -d api/.tools/npm ]]; then "$engine" cp "$nodeCopy:/usr/local/lib/node_modules/npm" api/.tools/npm; fi
"$engine" rm "$nodeCopy" >/dev/null
ln -sfn ../npm/bin/npm-cli.js api/.tools/bin/npm
export PATH="$root/api/.tools/bin:$root/api/.tools:$PATH"
[[ "$(node --version)" == v24.21.0 && "$(npm --version)" == 11.19.0 ]]
(cd api && timeout 180 npm ci --ignore-scripts --no-fund && timeout 120 npm audit --audit-level=high && timeout 120 npm test) >"artifacts/api-ci-$scope-node.log" 2>&1
cosign="cgr.dev/chainguard/cosign:latest@sha256:e7ef547a42e52b877a9069ee49e2caa6287c30bcb97d27df3ec5d22c0afdbb6f"
wheels="localhost/rr-api-fixture-wheels:$scope"
evidence="localhost/rr-api-fixture-evidence:$scope"
bridge="localhost/rr-api-fixture-bridge:$scope"
contracts="localhost/rr-api-fixture-contracts:$scope"
init="localhost/rr-api-fixture-init:$scope"
export API_FIXTURE_IMAGE="localhost/rr-api-fixture-api:$scope"
export API_FIXTURE_SDK_IMAGE="localhost/rr-api-fixture-sdk:$scope"
timeout 600 "${build[@]}" --target foundation-wheels --build-context "foundation-source=$foundation" \
  -f "$infra/Dockerfile" -t "$wheels" "$infra" >"artifacts/api-ci-$scope-wheels.log" 2>&1
timeout 600 "${build[@]}" --target evidence-sink --build-context "foundation-source=$foundation" \
  --build-arg "COSIGN_IMAGE=$cosign" --build-arg COSIGN_VERSION=3.1.3 \
  -f "$infra/Dockerfile" -t "$evidence" "$infra" >"artifacts/api-ci-$scope-evidence.log" 2>&1
timeout 120 "${build[@]}" --build-arg "EVIDENCE_IMAGE=$evidence" \
  -f api/test/Dockerfile.bridge -t "$bridge" . >"artifacts/api-ci-$scope-bridge.log" 2>&1
timeout 300 "${build[@]}" --build-arg "FOUNDATION_WHEELS_IMAGE=$wheels" --build-arg "LEGACY_BASE_IMAGE=$bridge" \
  -f "$infra/docker/foundation-coordinator.Dockerfile" -t "$contracts" "$infra" >"artifacts/api-ci-$scope-contracts.log" 2>&1
timeout 300 "${build[@]}" -f "$infra/docker/host/init.Dockerfile" \
  -t "$init" "$infra" >"artifacts/api-ci-$scope-init.log" 2>&1
initCopy="$scope-init"
"$engine" create --name "$initCopy" --label "org.robotics.runtime.fixture-suite=$scope" "$init" >/dev/null
"$engine" cp "$initCopy:/out/catatonit" "artifacts/$scope-catatonit"
"$engine" rm "$initCopy" >/dev/null
timeout 60 node api/test/prepare-worker-assets.mjs "$root/artifacts/$scope-catatonit"
timeout 180 "${build[@]}" --build-arg "CONTRACTS_BASE=$contracts" --build-arg "EVIDENCE_TOOLS_BASE=$evidence" \
  -f api/test/Dockerfile -t "$API_FIXTURE_IMAGE" . >"artifacts/api-ci-$scope-api.log" 2>&1
timeout 180 "${build[@]}" --build-arg "API_IMAGE=$API_FIXTURE_IMAGE" \
  -f api/test/Dockerfile.consumer -t "$API_FIXTURE_SDK_IMAGE" . >"artifacts/api-ci-$scope-sdk.log" 2>&1
timeout 90 node api/test/role-fixture.mjs >"artifacts/api-ci-$scope-role.log" 2>&1
timeout 420 node api/test/gateway-fixture.mjs >"artifacts/api-ci-$scope-gateway.log" 2>&1
