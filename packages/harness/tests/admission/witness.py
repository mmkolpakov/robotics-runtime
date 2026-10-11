"""Exercise public installed CLI admission under the fixture's OCI limits."""

from __future__ import annotations

import errno
import hashlib
import json
import subprocess
from pathlib import Path

from robotics_runtime_contracts import validate_role

INPUTS = Path("/inputs.json")
EXPECTATIONS = Path("/expectations.json")
OUTPUT = Path("/assessment")


def run(
    inputs: dict[str, object], output: Path, profile: Path | None
) -> subprocess.CompletedProcess[str]:
    arguments = ["robotics-acceptance", "evaluate"]
    for name, value in inputs.items():
        arguments.extend(("--" + name.replace("_", "-"), str(value)))
    arguments.extend(("--output", str(output)))
    for name in ("receipt", "verification"):
        option = "--evaluator-receipt" if name == "receipt" else "--evaluator-verification"
        arguments.extend((option, f"/opt/admission/receipts/{name}.json"))
    for name in ("statement.json", "publisher.json", "verified-report.txt"):
        arguments.extend(("--evaluator-receipt-dependency", f"/opt/admission/receipts/{name}"))
    if profile is not None:
        arguments.extend(("--evaluator-trust-profile", str(profile)))
    return subprocess.run(arguments, capture_output=True, text=True, timeout=90, check=False)


def readonly(path: Path) -> None:
    try:
        with path.open("ab") as stream:
            stream.write(b"mutation must be refused")
    except OSError as error:
        assert error.errno in {errno.EROFS, errno.EACCES, errno.EPERM}, error
    else:
        raise AssertionError(f"input was writable: {path}")


def main() -> None:
    inputs = json.loads(INPUTS.read_bytes())
    expectations = json.loads(EXPECTATIONS.read_bytes())
    archive = Path(inputs["evidence_index"]).parent
    originals = {path: path.read_bytes() for path in archive.iterdir() if path.is_file()}
    raw = archive / "native-state.json"
    readonly(raw)
    readonly(Path("/opt/admission/profile.json"))
    completed = run(inputs, OUTPUT / "valid", Path("/opt/admission/profile.json"))
    assert completed.returncode == 0, completed.stderr
    result = json.loads((OUTPUT / "valid/acceptance-result.json").read_bytes())
    validate_role(result, "acceptance_result")
    assertion = next(
        item
        for item in result["assertion_results"]
        if item["assertion_id"] == expectations["assertion_id"]
    )
    assert assertion["status"] == "passed"
    assert assertion["observed_value"] == expectations["raw_size_bytes"]
    assert expectations["raw_sha256"] in assertion["evidence_sha256"]
    refused = run(inputs, OUTPUT / "receipt-only", None)
    assert refused.returncode == 2, refused.stdout
    assert "authenticated wheel/source admission" in refused.stderr
    assert not (OUTPUT / "receipt-only/acceptance-result.json").exists()
    wrong = json.loads(Path("/opt/admission/profile.json").read_bytes())
    if wrong["verifier"]["kind"] == "github":
        wrong["evaluators"][0]["publisher"]["certificate_identity"] += "-wrong-publisher"
    else:
        wrong["verifier"]["public_key"] = "/opt/admission/auxiliary/other.pub"
        wrong["verifier"]["public_key_sha256"] = expectations["other_key_sha256"]
        wrong["evaluators"][0]["publisher"]["public_key_sha256"] = expectations["other_key_sha256"]
    wrong_path = Path("/tmp/wrong-profile.json")
    wrong_path.write_text(json.dumps(wrong))
    wrong_path.chmod(0o600)
    refused = run(inputs, OUTPUT / "wrong-publisher", wrong_path)
    assert refused.returncode == 2, refused.stdout
    assert "verification refused" in refused.stderr
    assert not (OUTPUT / "wrong-publisher/acceptance-result.json").exists()
    assert {path: path.read_bytes() for path in originals} == originals
    report = {
        **expectations,
        "installed_public_cli": True,
        "authenticated_original_source": True,
        "read_only_evidence_and_profile": True,
        "receipt_only_refused": True,
        "wrong_publisher_refused": True,
        "input_inventory": {
            path.name: hashlib.sha256(value).hexdigest() for path, value in originals.items()
        },
    }
    (OUTPUT / "witness.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "passed", "assertion": assertion["assertion_id"]}))


if __name__ == "__main__":
    main()
