"""Embed pinned-renderer C4 SVG views and their canonical source in README."""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VIEWS = ("Container", "Context")


def render_readme() -> str:
    readme = (ROOT / "README.md").read_text()
    labels = {"Container": "Execution and external Test boundaries", "Context": "Platform context"}
    for view in VIEWS:
        start = f"<!-- architecture:{view}:start -->"
        end = f"<!-- architecture:{view}:end -->"
        if readme.count(start) != 1 or readme.count(end) != 1:
            raise ValueError(f"README needs one ordered marker pair for {view}")
        first, last = readme.index(start), readme.index(end)
        if last <= first:
            raise ValueError(f"README markers are reversed for {view}")
        block = (
            f"{start}\n\n"
            f"![{labels[view]}](docs/architecture/generated/{view}.svg)\n\n"
            "[Canonical C4 source](docs/architecture/workspace.dsl) · "
            f"[Generated Mermaid](docs/architecture/generated/structurizr-{view}.mmd)\n\n{end}"
        )
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
