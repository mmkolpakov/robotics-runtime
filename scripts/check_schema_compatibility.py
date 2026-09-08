"""Fail closed on incompatible published schema or semantic regression changes."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

# Also support `python scripts/check_schema_compatibility.py` from any cwd.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.bundle_schemas import read_schemas  # noqa: E402
from scripts.schema_compatibility.history import baseline, extract  # noqa: E402
from scripts.schema_compatibility.semantic import check_semantics  # noqa: E402
from scripts.schema_compatibility.structure import check_structure  # noqa: E402


def check(root: Path) -> str:
    release = baseline(root)
    with TemporaryDirectory(prefix="contracts-compatibility-") as temporary:
        published = extract(root, release, Path(temporary))
        candidate = root / "packages/contracts"
        old_path = published / "src/robotics_runtime_contracts/schemas"
        new_path = candidate / "src/robotics_runtime_contracts/schemas"
        count = check_structure(
            read_schemas(old_path),
            read_schemas(new_path),
            json.loads((old_path / "catalog.v1.json").read_bytes()),
            json.loads((new_path / "catalog.v1.json").read_bytes()),
        )
        cases = check_semantics(published, candidate)
    return f"{release.tag} ({release.commit}): {count} retained schemas; {cases} semantic cases"


def main() -> int:
    try:
        print(f"Schema compatibility passed: {check(ROOT)}")
        return 0
    except Exception as error:
        # Tooling/import/history errors must also fail the CI/pre-commit gate.
        print(f"Schema compatibility review_required: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
