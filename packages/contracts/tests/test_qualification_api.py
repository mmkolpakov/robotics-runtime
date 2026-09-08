from __future__ import annotations

import io
import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from robotics_runtime_contracts.cli import main
from robotics_runtime_contracts.qualification import (
    QualificationError,
    inspect_qualification_artifacts,
    inspect_qualification_documents,
    load_qualification_artifact,
    validate_qualification_artifacts,
    validate_qualification_documents,
)
from tests.support import qualification_specifications
from tests.test_qualification import artifacts, document


def test_reports_independent_run_and_domain_failures() -> None:
    items = artifacts("transport")
    document(items, "acceptance-aggregate.json")["run_id"] = (
        "run-00000000-0000-4000-8000-000000000099"
    )
    for domain in ("control", "worker"):
        document(items, f"results/{domain}.json")["runtime_manifest_sha256"] = "0" * 64
    report = inspect_qualification_documents(items)
    assert not report.valid
    assert not report.blocked_checks
    assert [(item.check, item.subject_name) for item in report.diagnostics] == [
        ("run.identity", None),
        ("domain.identity", "results/control.json"),
        ("domain.identity", "results/worker.json"),
    ]
    with pytest.raises(QualificationError, match="aggregate run_id") as caught:
        report.metadata()
    assert caught.value.diagnostics == report.diagnostics


def test_invalid_documents_are_collected_before_dependent_links() -> None:
    items = artifacts("transport")
    for domain in ("control", "worker"):
        del document(items, f"results/{domain}.json")["runtime_manifest_sha256"]
    report = inspect_qualification_documents(items)
    assert not report.valid
    assert report.blocked_checks == ("links",)
    assert len(report.diagnostics) == 2
    assert {item.subject_name for item in report.diagnostics} == {
        "results/control.json",
        "results/worker.json",
    }
    assert {item.check for item in report.diagnostics} == {"document"}
    with pytest.raises(QualificationError) as caught:
        validate_qualification_documents(items)
    assert caught.value.blocked_checks == ("links",)


def test_empty_set_reports_all_required_subjects() -> None:
    report = inspect_qualification_documents([])
    assert not report.valid
    assert report.blocked_checks == ("links",)
    assert [item.subject_name for item in report.diagnostics] == [
        "scenario.json",
        "acceptance-run.json",
        "acceptance-aggregate.json",
    ]


def test_duplicate_subject_blocks_ambiguous_link_lookup() -> None:
    items = artifacts("transport")
    report = inspect_qualification_documents([*items, items[0]])
    assert not report.valid
    assert report.diagnostics[0].check == "subjects.unique"
    assert report.blocked_checks == ("links",)


def test_missing_domain_prevents_dependent_keyed_lookups() -> None:
    items = [
        item
        for item in artifacts("transport")
        if item.subject_name != "runtime-manifests/worker.json"
    ]
    report = inspect_qualification_documents(items)
    assert [item.check for item in report.diagnostics] == ["domains"]
    assert "domain.links" in report.blocked_checks
    assert "transport" in report.blocked_checks
    assert "aggregate.results" not in report.blocked_checks
    assert not report.valid


@pytest.mark.parametrize("case", ["transport", "inference", "physical"])
def test_public_file_and_descriptor_apis_agree_on_existing_fixtures(case: str) -> None:
    specifications = qualification_specifications(case)
    report = inspect_qualification_artifacts(specifications)
    assert report.valid
    assert not report.diagnostics and not report.blocked_checks
    assert validate_qualification_documents(report.artifacts) == (
        report.run_id,
        report.generated_at,
    )
    assert report.metadata() == validate_qualification_artifacts(specifications)
    paths = {
        value.partition(":")[2].partition("=")[0]: Path(value.partition("=")[2])
        for value in specifications
    }
    for artifact in report.artifacts:
        raw = paths[artifact.subject_name].read_bytes()
        assert artifact.sha256 == sha256(raw).hexdigest()
        assert artifact.size_bytes == len(raw)


def test_file_inspection_collects_load_failures_and_retains_successes(tmp_path: Path) -> None:
    good = tmp_path / "raw.bin"
    good.write_bytes(b"retained raw evidence")
    report = inspect_qualification_artifacts(
        [
            f"recording:evidence/missing.mcap={tmp_path / 'missing.mcap'}",
            "not-a-specification",
            f"recording:evidence/raw.bin={good}",
        ]
    )
    assert [item.error_id for item in report.diagnostics] == [
        "input.io_error",
        "cli.arguments_invalid",
    ]
    assert [item.subject_name for item in report.artifacts] == ["evidence/raw.bin"]
    assert not report.valid
    assert report.blocked_checks == ("links",)


def test_cli_json_preserves_diagnostics_argument_exit_and_existing_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    destination = tmp_path / "metadata.json"
    destination.write_bytes(b"previous result")
    code = main(
        [
            "--format",
            "json",
            "validate-qualification",
            "--artifact",
            "bad-first",
            "--artifact",
            "bad-second",
            "--output",
            str(destination),
        ]
    )
    assert code == 2
    payload = json.loads(capsys.readouterr().err)["error"]
    assert payload["error_id"] == "cli.arguments_invalid"
    assert len(payload["diagnostics"]) == 2
    assert payload["blocked_checks"] == ["links"]
    assert destination.read_bytes() == b"previous result"


def test_raw_file_is_streamed_once_without_the_document_size_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = b"0123456789abcdef" * (1024 * 1024)
    source = tmp_path / "large.mcap"
    source.write_bytes(raw)
    original_open = Path.open
    reads: list[int] = []
    opens: list[Path] = []

    class BoundedReader(io.BytesIO):
        def read(self, size: int | None = -1) -> bytes:
            assert size is not None and 0 < size <= 1024 * 1024
            reads.append(size)
            return super().read(size)

    def tracked_open(path: Path, *args: Any, **kwargs: Any) -> Any:
        if path == source:
            opens.append(path)
            return BoundedReader(raw)
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", tracked_open)
    artifact = load_qualification_artifact(f"recording:evidence/large.mcap={source}")
    assert opens == [source]
    assert len(reads) == 17
    assert artifact.size_bytes == len(raw) and artifact.sha256 == sha256(raw).hexdigest()


def test_supplied_descriptors_do_not_claim_to_verify_file_bytes() -> None:
    items = artifacts("transport")
    raw = next(item for item in items if item.document is None)
    # Descriptor validity is checked, even though the functional API has no file path.
    invalid = replace(raw, sha256="z" * 64)
    report = inspect_qualification_documents(
        [invalid, *(item for item in items if item is not raw)]
    )
    assert not report.valid
    assert report.diagnostics[0].subject_name == raw.subject_name
    assert "hexadecimal" in report.diagnostics[0].message


def test_programming_errors_are_not_relabelled_as_expected_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken_open(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("unexpected storage adapter failure")

    monkeypatch.setattr(Path, "open", broken_open)
    with pytest.raises(RuntimeError, match="unexpected storage adapter"):
        inspect_qualification_artifacts(["recording:evidence/example.mcap=example.mcap"])


def test_metadata_output_cannot_replace_a_validated_input(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    arguments = ["--format", "json", "validate-qualification"]
    originals: dict[Path, bytes] = {}
    for index, specification in enumerate(qualification_specifications("physical")):
        prefix, _, source = specification.partition("=")
        destination = tmp_path / f"{index}-{Path(source).name}"
        original = Path(source).read_bytes()
        destination.write_bytes(original)
        originals[destination] = original
        arguments.extend(("--artifact", f"{prefix}={destination}"))
    arguments.extend(("--output", str(next(iter(originals)))))
    assert main(arguments) == 1
    assert (
        "output must not replace input" in json.loads(capsys.readouterr().err)["error"]["message"]
    )
    assert all(path.read_bytes() == data for path, data in originals.items())
