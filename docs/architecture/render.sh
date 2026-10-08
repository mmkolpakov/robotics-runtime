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
"$engine" run --rm --platform linux/amd64 --network none "${mapping[@]}" --user "$owner" \
  -v "$PWD:/usr/local/structurizr" "$structurizr" \
  export -workspace workspace.dsl -format mermaid -output generated
for view in Context Container ContainerDetail ExternalTestAPI NativeInterfaces ConsumerInterfaces DevelopmentDeployment ExecutionDeployment; do
  configuration="generated/mermaid-$view.json"
  python3 -c 'import json,sys; from pathlib import Path; c=json.loads(Path("mermaid-config.json").read_text()); c["themeCSS"]="path.flowchart-link { fill: none !important; }"; Path(sys.argv[1]).write_text(json.dumps(c,indent=2)+"\n")' "$configuration"
  if [[ "$view" == ExternalTestAPI || "$view" == Container || "$view" == Context ]]; then
    configuration="generated/mermaid-$view.json"
    python3 -c 'import json,sys; from pathlib import Path; c=json.loads(Path("mermaid-config.json").read_text()); c["themeVariables"]["fontSize"]="26px"; c["layout"]="elk"; c["flowchart"].update(nodeSpacing=16,rankSpacing=20,inheritDir=True); c["themeCSS"]="path.flowchart-link { fill: none !important; }"; c["flowchart"].update(wrappingWidth=240 if "-Context." in sys.argv[1] else 140) if "ExternalTestAPI" not in sys.argv[1] else c.update(themeCSS=c["themeCSS"]+" g.cluster:not([id$=-diagram]) > rect, g.cluster:not([id$=-diagram]) > g.cluster-label { visibility: hidden; }"); Path(sys.argv[1]).write_text(json.dumps(c,indent=2)+"\n")' "$configuration"
  fi
  if [[ "$view" == ContainerDetail ]]; then
    configuration="generated/mermaid-ContainerDetail.json"
    python3 -c 'import json,sys; from pathlib import Path; c=json.loads(Path("mermaid-config.json").read_text()); c["layout"]="elk"; c["themeCSS"]="path.flowchart-link { fill: none !important; }"; Path(sys.argv[1]).write_text(json.dumps(c,indent=2)+"\n")' "$configuration"
  fi
  "$engine" run --rm --platform linux/amd64 --network none "${mapping[@]}" --user "$owner" \
    -v "$PWD:/data" "$mermaid" -c "$configuration" \
    -i "generated/structurizr-$view.mmd" -o "generated/$view.svg"
done
for diagram in run-sequence run-state; do
  "$engine" run --rm --platform linux/amd64 --network none "${mapping[@]}" --user "$owner" \
    -v "$PWD:/data" "$mermaid" -c mermaid-config.json -i "$diagram.mmd" -o "generated/$diagram.svg"
done
python3 publish_readme.py
