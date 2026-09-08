"""Preserve published valid documents through the public schema + semantics API."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from scripts.schema_compatibility.structure import ReviewRequired, token

FIXTURES = Path(__file__).resolve().parents[2] / "tests/schema_compatibility/fixtures"
PROBE = Path(__file__).with_name("probe.py")


def regressions() -> dict[str, Any]:
    manifest = json.loads((FIXTURES / "provenance.json").read_bytes())
    if not manifest:
        raise ReviewRequired("Frozen semantic regression manifest is empty")
    documents = {}
    for name, provenance in manifest.items():
        raw = (FIXTURES / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != provenance["sha256"]:
            raise ReviewRequired(f"Frozen semantic regression bytes changed: {name}")
        documents[f"regression/{name}"] = json.loads(raw)
    return documents


def probe(source: Path, request: dict[str, Any]) -> dict[str, Any]:
    # -I ignores PYTHONPATH, cwd and user site. Only this probe prepends the
    # explicitly selected source; no editable workspace package can mask it.
    result = subprocess.run(
        [sys.executable, "-I", "-B", str(PROBE), str(source)],
        input=json.dumps(request, allow_nan=False),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=60,
    )
    if result.returncode:
        raise ReviewRequired(result.stderr.strip())
    response: dict[str, Any] = json.loads(result.stdout)
    return response


def check_semantics(published: Path, candidate: Path) -> int:
    files = {
        path.relative_to(published).as_posix(): str(path)
        for path in sorted((published / "tests/fixtures").rglob("*"))
        if path.parent.name == "valid" and path.suffix in {".json", ".yaml", ".yml"}
    }
    if not files:
        raise ReviewRequired("Published /valid/ regression corpus is empty")
    old = probe(published / "src", {"files": files, "documents": regressions()})
    new = probe(candidate / "src", {"documents": old["documents"]})
    if token(old["documents"]) != token(new["documents"]):
        raise ReviewRequired("Candidate changed the semantic regression corpus")
    return len(old["documents"])
