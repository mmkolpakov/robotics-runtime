"""Fail closed on incompatible published schema or semantic regression changes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

# Also support `python scripts/check_schema_compatibility.py` from any cwd.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.bundle_schemas import read_schemas  # noqa: E402
from scripts.schema_compatibility.dataset_migration import dataset_migration  # noqa: E402
from scripts.schema_compatibility.history import baseline, extract, published_baseline  # noqa: E402
from scripts.schema_compatibility.semantic import check_semantics  # noqa: E402
from scripts.schema_compatibility.structure import check_structure  # noqa: E402


def check(root: Path, *, repository: str | None = None) -> str:
    release = published_baseline(root, repository) if repository is not None else baseline(root)
    with TemporaryDirectory(prefix="contracts-compatibility-") as temporary:
        published = extract(root, release, Path(temporary))
        candidate = root / "packages/contracts"
        old_path = published / "src/robotics_runtime_contracts/schemas"
        new_path = candidate / "src/robotics_runtime_contracts/schemas"
        transition = dataset_migration(root, release, published, candidate)
        count = check_structure(
            read_schemas(old_path),
            read_schemas(new_path),
            json.loads((old_path / "catalog.v1.json").read_bytes()),
            json.loads((new_path / "catalog.v1.json").read_bytes()),
            dataset_transition=transition,
        )
        cases = check_semantics(
            published, candidate, legacy=not release.prefix, dataset_transition=transition
        )
    migration = (
        "; reviewed dataset-manifest.v1 -> dataset-manifest.v2 break"
        if transition is not None
        else ""
    )
    return (
        f"{release.tag} ({release.commit}): {count} retained schemas; "
        f"{cases} semantic cases{migration}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--published-repository")
    args = parser.parse_args(argv or [])
    try:
        print(f"Schema compatibility passed: {check(ROOT, repository=args.published_repository)}")
        return 0
    except Exception as error:
        # Tooling/import/history errors must also fail the CI/pre-commit gate.
        print(f"Schema compatibility review_required: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
