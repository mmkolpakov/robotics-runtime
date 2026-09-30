"""Preserve published valid documents through the public schema + semantics API."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from scripts.schema_compatibility.probe import fixture_document
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


def published_documents(published: Path) -> dict[str, str]:
    """Return released valid fixtures, qualification sets and consumer examples."""
    files = {}
    for corpus in ("tests/fixtures", "consumer-examples"):
        for path in sorted((published / corpus).rglob("*")):
            relative = path.relative_to(published)
            if path.suffix not in {".json", ".yaml", ".yml"} or "invalid" in relative.parts:
                continue
            if path.parent.name != "valid":
                # Qualification sets and examples also hold raw evidence; replay documents only.
                document = fixture_document(path)
                if not isinstance(document, dict) or "schema_version" not in document:
                    continue
            files[relative.as_posix()] = str(path)
    return files


def check_semantics(published: Path, candidate: Path) -> int:
    files = published_documents(published)
    if not any(Path(name).parent.name == "valid" for name in files):
        raise ReviewRequired("Published /valid/ regression corpus is empty")
    old = probe(published / "src", {"files": files, "documents": regressions()})
    new = probe(candidate / "src", {"documents": old["documents"]})
    if token(old["documents"]) != token(new["documents"]):
        raise ReviewRequired("Candidate changed the semantic regression corpus")
    return len(old["documents"])
