"""Exercise the product template, including a real isolated typed-wheel installation."""

from __future__ import annotations

import ast
import configparser
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import dataclass, replace
from email.parser import BytesParser
from hashlib import sha256
from importlib import import_module
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal, TypedDict, cast
from zipfile import ZipFile

import pytest
from mcap.reader import NonSeekingReader
from mcap.records import Chunk
from mcap.stream_reader import StreamReader
from mcap.writer import CompressionType, Writer
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from robotics_runtime_contracts import load_mapping
from zstandard import ZstdError

from robotics_acceptance_harness.documents import load_bundle
from robotics_acceptance_harness.evidence import load_evidence_index
from robotics_acceptance_harness.sdk import EvaluationContext, HarnessError, ProductEvaluator
from tests.support import local_evidence_artifact, write_evidence_index, write_verified_receipt

HARNESS = Path(__file__).resolve().parents[1]
ROOT = HARNESS.parents[1]
TEMPLATE = HARNESS / "examples/evaluator-template"
FIXTURES = HARNESS / "tests/fixtures/simulation"
RUN_ID = "run-01234567-89ab-4def-8123-456789abcdef"
NAMESPACE = "org.example.recording"
PACKAGE = "example-recording-evaluator"
CLI = "from robotics_acceptance_harness.cli import main; raise SystemExit(main())"


def mcap_bytes(messages: int = 2, *, compression: CompressionType = CompressionType.NONE) -> bytes:
    stream = io.BytesIO()
    writer = Writer(stream, compression=compression, enable_data_crcs=True)
    writer.start()
    channel = writer.register_channel(topic="/example", message_encoding="json", schema_id=0)
    for index in range(messages):
        writer.add_message(channel, index + 1, b'{"value": 1}', index + 1)
    writer.finish()
    return stream.getvalue()


def corrupt_compressed_chunk(content: bytes) -> bytes:
    (chunk,) = [
        record
        for record in StreamReader(io.BytesIO(content), emit_chunks=True).records
        if isinstance(record, Chunk)
    ]
    assert chunk.compression in {"zstd", "lz4"}
    assert len(chunk.data) >= 4 and content.count(chunk.data) == 1
    # Damage the real compressor's frame magic without changing MCAP record lengths.
    corrupted = bytes(value ^ 0xFF for value in chunk.data[:4]) + chunk.data[4:]
    return content.replace(chunk.data, corrupted, 1)


def write_index(directory: Path, content: bytes) -> tuple[Path, Path, str]:
    directory.mkdir(parents=True, exist_ok=True)
    payload = directory / "recording.mcap"
    payload.write_bytes(content)
    artifact = local_evidence_artifact(payload, media_type="application/mcap")
    index = write_evidence_index(
        directory / "evidence-index.json", run_id=RUN_ID, artifacts=[artifact]
    )
    return index, payload, str(artifact["sha256"])


def context(directory: Path, content: bytes) -> tuple[EvaluationContext, Path, str]:
    index, payload, digest = write_index(directory, content)
    bundle = load_bundle(FIXTURES / "scenario.yaml", runtime_path=FIXTURES / "runtime.yaml")
    evidence = load_evidence_index(index, expected_run_id=RUN_ID)
    return EvaluationContext(RUN_ID, "primary", bundle, evidence, (), 0, 10), payload, digest


@pytest.fixture
def evaluator(monkeypatch: pytest.MonkeyPatch) -> ProductEvaluator:
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    monkeypatch.syspath_prepend(str(TEMPLATE / "src"))
    return cast(ProductEvaluator, import_module("recording_evaluator").evaluate)


@pytest.mark.parametrize("messages", [0, 1, 3])
def test_template_counts_verified_messages(
    tmp_path: Path, evaluator: ProductEvaluator, messages: int
) -> None:
    inputs, _payload, digest = context(tmp_path, mcap_bytes(messages))
    (result,) = evaluator(inputs)
    assert result.status == ("passed" if messages else "failed")
    assert result.observed_value == messages
    assert result.source == "product"
    assert result.namespace == NAMESPACE
    assert result.assertion_id == f"{NAMESPACE}.nonempty.{digest}"
    assert result.evidence_sha256 == (digest,)


@pytest.mark.parametrize("content", [b"not an MCAP", mcap_bytes()[:-9]])
def test_template_invalid_mcap_is_an_input_error(
    tmp_path: Path, evaluator: ProductEvaluator, content: bytes
) -> None:
    inputs, _payload, digest = context(tmp_path, content)
    (result,) = evaluator(inputs)
    assert result.status == "error"
    assert result.observed_value is None
    assert result.message.startswith("InputError:")
    assert result.evidence_sha256 == (digest,)


@pytest.mark.parametrize(
    ("compression", "error_type"),
    [(CompressionType.ZSTD, ZstdError), (CompressionType.LZ4, RuntimeError)],
    ids=["zstd", "lz4"],
)
def test_template_corrupt_compressed_chunk_is_an_input_error(
    tmp_path: Path,
    evaluator: ProductEvaluator,
    compression: CompressionType,
    error_type: type[Exception],
) -> None:
    original = mcap_bytes(compression=compression)
    valid_inputs, _valid_payload, _valid_digest = context(tmp_path / "valid", original)
    (valid_result,) = evaluator(valid_inputs)
    assert valid_result.status == "passed" and valid_result.observed_value == 2

    content = corrupt_compressed_chunk(original)
    # This must reach the actual decompressor, rather than a generic MCAP/CRC failure.
    with pytest.raises(error_type):
        list(
            NonSeekingReader(io.BytesIO(content), validate_crcs=True).iter_messages(
                log_time_order=False
            )
        )
    inputs, _payload, digest = context(tmp_path / "corrupt", content)
    with inputs.evidence(digest) as snapshot:
        assert snapshot.read() == content  # The index authenticates the corrupted payload.
    (result,) = evaluator(inputs)
    assert result.status == "error"
    assert result.observed_value is None
    assert result.message.startswith("InputError:") and digest in result.message
    assert result.source == "product" and result.namespace == NAMESPACE
    assert result.assertion_id == f"{NAMESPACE}.nonempty.{digest}"
    assert result.evidence_sha256 == (digest,)


@pytest.mark.parametrize("unavailable", ["deleted", "modified", "retained-only"])
def test_template_file_failures_are_input_errors(
    tmp_path: Path, evaluator: ProductEvaluator, unavailable: str
) -> None:
    inputs, payload, digest = context(tmp_path, mcap_bytes())
    if unavailable == "deleted":
        payload.unlink()
    elif unavailable == "modified":
        payload.write_bytes(b"changed after index verification")
    else:
        inputs = replace(
            inputs, evidence=replace(inputs.evidence, local_files=MappingProxyType({}))
        )
    (result,) = evaluator(inputs)
    assert result.status == "error"
    assert result.message.startswith("InputError:")
    assert result.evidence_sha256 == (digest,)


def test_template_requires_mcap_evidence(tmp_path: Path, evaluator: ProductEvaluator) -> None:
    inputs, _payload, _digest = context(tmp_path, mcap_bytes())
    inputs = replace(inputs, evidence=replace(inputs.evidence, links=()))
    with pytest.raises(HarnessError, match="no application/mcap"):
        tuple(evaluator(inputs))


def test_template_imports_only_the_public_harness_sdk() -> None:
    source = TEMPLATE / "src/recording_evaluator/__init__.py"
    imports = [
        node for node in ast.walk(ast.parse(source.read_text())) if isinstance(node, ast.ImportFrom)
    ]
    harness_imports = [
        node.module for node in imports if (node.module or "").startswith("robotics_")
    ]
    assert harness_imports == ["robotics_acceptance_harness.sdk"]


class WheelProof(TypedDict):
    format: Literal["evaluator-template-wheel-proof.v1"]
    status: Literal["pending", "blocked", "failed", "passed"]
    reason: str
    wheels: dict[str, str]
    versions: dict[str, str]
    checks: list[str]


@dataclass
class BuiltTemplate:
    root: Path
    wheel: Path
    proof: WheelProof

    def save(self) -> None:
        (self.root / "wheel-proof.json").write_text(
            json.dumps(self.proof, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


def run_check(
    root: Path, label: str, command: list[str], *, expected: int = 0
) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    for name in ("PYTHONPATH", "PYTHONHOME", "PYTHONPYCACHEPREFIX", "MYPYPATH", "VIRTUAL_ENV"):
        environment.pop(name, None)
    environment.update(PYTHONDONTWRITEBYTECODE="1", UV_COMPILE_BYTECODE="0")
    result = subprocess.run(
        command,
        cwd=root / "working",
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=240,
        check=False,
    )
    (root / f"{label}.json").write_text(
        json.dumps(
            {
                "command": command,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    assert result.returncode == expected, (
        f"{label} failed; proof: {root}\n{result.stdout}\n{result.stderr}"
    )
    return result


def build_wheel(root: Path, source: Path, name: str) -> Path:
    copied = root / name
    copied.mkdir()
    for filename in ("pyproject.toml", "README.md", "LICENSE"):
        if (source / filename).is_file():
            shutil.copy2(source / filename, copied / filename)
    shutil.copytree(
        source / "src", copied / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )
    destination = root / "wheels" / name
    run_check(
        root,
        f"build-{name}",
        [
            "uv",
            "build",
            "--wheel",
            "--no-sources",
            "--python",
            sys.executable,
            "--out-dir",
            str(destination),
            str(copied),
        ],
    )
    wheels = list(destination.glob("*.whl"))
    assert len(wheels) == 1
    return wheels[0]


@pytest.fixture(scope="module")
def template_wheel() -> BuiltTemplate:
    assert shutil.which("uv"), "uv is required for the real template wheel proof"
    output = os.environ.get("EVALUATOR_TEMPLATE_PROOF_DIR")
    if output:
        Path(output).mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="evaluator-template-", dir=output)).resolve()
    assert not root.is_relative_to(ROOT), "the wheel proof must run outside the workspace"
    (root / "working").mkdir()
    wheel = build_wheel(root, TEMPLATE, "template")
    built = BuiltTemplate(
        root,
        wheel,
        {
            "format": "evaluator-template-wheel-proof.v1",
            "status": "pending",
            "reason": "Only the template wheel has been built; installation is not yet verified",
            "wheels": {wheel.name: sha256(wheel.read_bytes()).hexdigest()},
            "versions": {},
            "checks": ["build-template-wheel"],
        },
    )
    built.save()
    print(f"\nTemplate wheel proof: {root}")
    return built


def test_template_wheel_has_typed_entrypoint(template_wheel: BuiltTemplate) -> None:
    with ZipFile(template_wheel.wheel) as wheel:
        assert "recording_evaluator/py.typed" in wheel.namelist()
        (metadata_path,) = [name for name in wheel.namelist() if name.endswith("/METADATA")]
        metadata = BytesParser().parsebytes(wheel.read(metadata_path))
        requirements = {
            item.name: item.specifier
            for item in map(Requirement, metadata.get_all("Requires-Dist", []))
        }
        assert requirements["robotics-acceptance-harness"] == SpecifierSet(">=0.20.0,<0.21")
        assert requirements["mcap"] == SpecifierSet(">=1.4,<2")
        assert requirements["zstandard"] == SpecifierSet(">=0.25.0,<1")
        (entry_path,) = [name for name in wheel.namelist() if name.endswith("/entry_points.txt")]
        entries = configparser.ConfigParser()
        entries.read_string(wheel.read(entry_path).decode())
        assert entries["robotics_acceptance.evaluators"][NAMESPACE] == (
            "recording_evaluator:evaluate"
        )


# This is host-side test setup, not product code. It runs from installed wheels
# in a fresh interpreter and leaves qualified loading to the harness.
INSTALLED_EVALUATION = """\
import json
import sys
from dataclasses import asdict
from importlib.metadata import distribution
from pathlib import Path
from robotics_acceptance_harness.sdk import EvaluationContext
from robotics_acceptance_harness.documents import load_bundle
from robotics_acceptance_harness.evidence import load_evidence_index
from robotics_acceptance_harness.evaluation import evaluate_acceptance
from robotics_acceptance_harness.receipts import load_verified_receipts

request = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
bundle = load_bundle(request['scenario'], runtime_path=request['runtime'])
evidence = load_evidence_index(request['index'], expected_run_id=request['run_id'])
context = EvaluationContext(request['run_id'], 'primary', bundle, evidence, (), 0, 10)
receipts = load_verified_receipts(receipt_paths=[request['receipt']],
    verification_paths=[request['verification']], dependency_paths=request['dependencies'])
evaluations = evaluate_acceptance(context, evaluator_receipts=receipts)
for name in ('recording_evaluator', 'robotics_acceptance_harness', 'robotics_runtime_contracts'):
    assert Path(sys.modules[name].__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
installed = distribution('example-recording-evaluator')
assert any(str(path).endswith('/py.typed') for path in installed.files)
print(json.dumps([asdict(item) for item in evaluations if item.source == 'product']))
"""


def qualification_files(root: Path, wheel: Path) -> tuple[Path, Path, dict[str, Any]]:
    digest = sha256(wheel.read_bytes()).hexdigest()
    chain = write_verified_receipt(
        root,
        {
            "uri": wheel.as_uri(),
            "sha256": digest,
            "size_bytes": wheel.stat().st_size,
            "media_type": "application/vnd.python.wheel",
            "immutable_revision": f"sha256:{digest}",
        },
        stem="evaluator",
    )
    requirement = {
        "namespace": NAMESPACE,
        "entry_point": "recording_evaluator:evaluate",
        "distribution": PACKAGE,
        "version": "0.1.0",
        "artifact_sha256": digest,
        "receipt_sha256": chain["receipt_sha256"],
    }
    scenario, runtime = root / "scenario.json", root / "runtime.json"
    scenario.write_text(
        json.dumps(
            {**load_mapping(FIXTURES / "scenario.yaml"), "evaluator_requirements": [requirement]}
        ),
        encoding="utf-8",
    )
    runtime.write_text(
        json.dumps(
            {**load_mapping(FIXTURES / "runtime.yaml"), "evaluator_bindings": [requirement]}
        ),
        encoding="utf-8",
    )
    return scenario, runtime, chain


def test_template_wheel_clean_install_and_doctor(template_wheel: BuiltTemplate) -> None:
    built, root = template_wheel, template_wheel.root
    projects = {
        name: tomllib.loads((path / "pyproject.toml").read_text())["project"]
        for name, path in {"harness": HARNESS, "contracts": ROOT / "packages/contracts"}.items()
    }
    built.proof["versions"] = {name: str(project["version"]) for name, project in projects.items()}
    ready = SpecifierSet(">=0.20.0,<0.21").contains(
        projects["harness"]["version"]
    ) and SpecifierSet(">=0.18").contains(projects["contracts"]["version"])
    if not ready:
        reason = f"requires harness >=0.20.0,<0.21 and contracts >=0.18: {built.proof['versions']}"
        built.proof["status"] = "blocked"
        built.proof["reason"] = reason
        built.save()
        if os.environ.get("EVALUATOR_TEMPLATE_REQUIRE_INTEGRATION") == "1":
            pytest.fail(reason)
        pytest.skip(reason)
    built.proof["status"] = "failed"
    built.proof["reason"] = "Integration started; not all checks have passed"
    built.save()
    harness = build_wheel(root, HARNESS, "harness")
    contracts = build_wheel(root, ROOT / "packages/contracts", "contracts")
    for wheel in (harness, contracts):
        built.proof["wheels"][wheel.name] = sha256(wheel.read_bytes()).hexdigest()
    built.save()
    environment = root / "venv"
    run_check(root, "create-venv", ["uv", "venv", "--python", sys.executable, str(environment)])
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    run_check(
        root,
        "install-wheels",
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            "--link-mode",
            "copy",
            str(contracts),
            str(harness),
            str(built.wheel),
            "mypy==2.3.0",
        ],
    )
    run_check(root, "pip-check", ["uv", "pip", "check", "--python", str(python)])
    dependencies = run_check(
        root,
        "compression-dependencies",
        [
            str(python),
            "-I",
            "-B",
            "-c",
            "import json; from importlib.metadata import version; "
            "print(json.dumps({name: version(name) for name in ('mcap', 'zstandard', 'lz4')}))",
        ],
    )
    built.proof["versions"].update(json.loads(dependencies.stdout))
    built.save()
    run_check(root, "doctor-discovery", [str(python), "-I", "-B", "-c", CLI, "doctor"])
    scenario, runtime, chain = qualification_files(root, built.wheel)
    doctor = [
        str(python),
        "-I",
        "-B",
        "-c",
        CLI,
        "doctor",
        "--scenario",
        str(scenario),
        "--evaluator-receipt",
        str(chain["receipt"]),
        "--evaluator-verification",
        str(chain["verification"]),
    ]
    for dependency in chain["dependencies"]:
        doctor.extend(["--evaluator-receipt-dependency", str(dependency)])
    report = json.loads(run_check(root, "doctor-qualified", doctor).stdout)
    assert report["status"] == "passed"
    assert report["evaluators"][0]["namespace"] == NAMESPACE
    bad_scenario = json.loads(scenario.read_text())
    bad_scenario["evaluator_requirements"][0]["artifact_sha256"] = "0" * 64
    invalid = root / "invalid-qualification.json"
    invalid.write_text(json.dumps(bad_scenario), encoding="utf-8")
    negative_doctor = [
        str(invalid) if argument == str(scenario) else argument for argument in doctor
    ]
    assert (
        json.loads(run_check(root, "doctor-negative", negative_doctor, expected=1).stdout)["status"]
        == "failed"
    )
    for case, payload, expected in (
        ("nonempty", mcap_bytes(2), "passed"),
        ("empty", mcap_bytes(0), "failed"),
        ("invalid", b"not an MCAP", "error"),
        ("nonempty-zstd", mcap_bytes(compression=CompressionType.ZSTD), "passed"),
        ("nonempty-lz4", mcap_bytes(compression=CompressionType.LZ4), "passed"),
        (
            "corrupt-zstd",
            corrupt_compressed_chunk(mcap_bytes(compression=CompressionType.ZSTD)),
            "error",
        ),
        (
            "corrupt-lz4",
            corrupt_compressed_chunk(mcap_bytes(compression=CompressionType.LZ4)),
            "error",
        ),
    ):
        index, _payload, digest = write_index(root / case, payload)
        request = root / f"{case}-request.json"
        request.write_text(
            json.dumps(
                {
                    "scenario": str(scenario),
                    "runtime": str(runtime),
                    "index": str(index),
                    "run_id": RUN_ID,
                    "receipt": str(chain["receipt"]),
                    "verification": str(chain["verification"]),
                    "dependencies": [str(path) for path in chain["dependencies"]],
                }
            ),
            encoding="utf-8",
        )
        response = run_check(
            root,
            f"evaluate-{case}",
            [str(python), "-I", "-B", "-c", INSTALLED_EVALUATION, str(request)],
        )
        (evaluation,) = json.loads(response.stdout)
        assert evaluation["status"] == expected
        assert evaluation["evidence_sha256"] == [digest]
        assert evaluation["assertion_id"] == f"{NAMESPACE}.nonempty.{digest}"
        assert evaluation["source"] == "product" and evaluation["namespace"] == NAMESPACE
        if expected == "error":
            assert evaluation["observed_value"] is None
            assert (
                evaluation["message"].startswith("InputError:") and digest in evaluation["message"]
            )
    typing_probe = root / "working/typing_probe.py"
    shutil.copy2(TEMPLATE / "proof/typing_probe.py", typing_probe)
    config = root / "mypy.ini"
    config.write_text("[mypy]\n", encoding="utf-8")
    mypy = [
        str(python),
        "-I",
        "-B",
        "-m",
        "mypy",
        "--strict",
        "--disallow-any-expr",
        "--config-file",
        str(config),
        "--cache-dir",
        str(root / "mypy-cache"),
    ]
    run_check(root, "typed-consumer", [*mypy, str(typing_probe)])
    negative = root / "working/negative_consumer.py"
    negative.write_text(
        "from recording_evaluator import evaluate\nevaluate(object())\n", encoding="utf-8"
    )
    failure = run_check(root, "typed-consumer-negative", [*mypy, str(negative)], expected=1)
    assert "arg-type" in failure.stdout
    built.proof["checks"].extend(
        [
            "install-real-wheels",
            "uv-pip-check",
            "compression-dependencies",
            "doctor-discovery",
            "doctor-qualified",
            "doctor-negative",
            "qualified-nonempty",
            "qualified-empty",
            "qualified-invalid",
            "qualified-nonempty-zstd",
            "qualified-nonempty-lz4",
            "qualified-corrupt-zstd",
            "qualified-corrupt-lz4",
            "installed-typed-consumer",
            "rejected-untyped-argument",
        ]
    )
    built.proof["status"] = "passed"
    built.proof["reason"] = "All isolated wheel checks passed"
    built.save()
