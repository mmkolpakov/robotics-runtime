"""Embed upstream-generated C4 Mermaid views in the repository README."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VIEWS = ("Container", "Context")


def render_readme() -> str:
    readme = (ROOT / "README.md").read_text()
    directory = ROOT / "docs/architecture"
    configuration = json.loads((directory / "mermaid-config.json").read_text())
    initialization = "%%{init: " + json.dumps(configuration, separators=(",", ":")) + "}%%"
    fence = chr(96) * 3
    for view in VIEWS:
        start = f"<!-- architecture:{view}:start -->"
        end = f"<!-- architecture:{view}:end -->"
        if readme.count(start) != 1 or readme.count(end) != 1:
            raise ValueError(f"README needs one ordered marker pair for {view}")
        first, last = readme.index(start), readme.index(end)
        if last <= first:
            raise ValueError(f"README markers are reversed for {view}")
        source = (directory / f"generated/structurizr-{view}.mmd").read_text().strip()
        block = f"{start}\n\n{fence}mermaid\n{initialization}\n{source}\n{fence}\n\n{end}"
        readme = readme[:first] + block + readme[last + len(end) :]
    return readme


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = ROOT / "README.md"
    expected = render_readme()
    if args.check:
        if path.read_text() != expected:
            parser.exit(1, "README diagrams differ; run docs/architecture/render.sh\n")
    else:
        path.write_text(expected)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
