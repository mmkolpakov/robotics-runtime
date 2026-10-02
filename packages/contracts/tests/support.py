import json
from pathlib import Path
from typing import Any

from robotics_runtime_contracts import load_mapping


def load_fixture(path: Path) -> dict[str, Any]:
    return load_mapping(path)


def qualification_specifications(case: str) -> list[str]:
    root = Path(__file__).parent / "fixtures" / "qualification" / case
    manifest: list[dict[str, str]] = json.loads(
        (root / "artifacts.json").read_text(encoding="utf-8")
    )
    return [f"{item['kind']}:{item['subject_name']}={root / item['file']}" for item in manifest]
