#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
engine="${CONTAINER_ENGINE:-docker}"
mapping=()
case "$engine" in
  podman) mapping=(--userns keep-id) ;;
  docker) ;;
  *) printf 'CONTAINER_ENGINE must be docker or podman\n' >&2; exit 2 ;;
esac

structurizr='docker.io/structurizr/structurizr@sha256:1c77e5e4c012dbf509d98f6020f3fdf643c0d25593982092be6cd9518ebfb941'
mermaid='docker.io/minlag/mermaid-cli@sha256:8b88ad79bc541632afd94e392b59fdcec7da7b544e118b3a85aa8bc036ef5b71'
owner="$(id -u):$(id -g)"
mkdir -p generated

"$engine" run --rm --platform linux/amd64 --network none "${mapping[@]}" --user "$owner" \
  -v "$PWD:/usr/local/structurizr" "$structurizr" validate -workspace workspace.dsl
for format in svg mermaid; do
  "$engine" run --rm --platform linux/amd64 --network none "${mapping[@]}" --user "$owner" \
    -v "$PWD:/usr/local/structurizr" "$structurizr" \
    export -workspace workspace.dsl -format "$format" -output generated
done
for diagram in run-sequence run-state; do
  "$engine" run --rm --platform linux/amd64 --network none "${mapping[@]}" --user "$owner" \
    -v "$PWD:/data" "$mermaid" -i "$diagram.mmd" -o "generated/$diagram.svg"
done
