from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import textwrap
from collections.abc import Mapping
from pathlib import Path
from zipfile import ZipFile

import pytest
import robotics_runtime_contracts

import robotics_acceptance_harness

MODULE = "spec33_evaluator"
DIST_INFO = "spec33_evaluator-1.0.dist-info"
SOURCE = """\
import math
from robotics_acceptance_harness import AssertionEvaluation

def evaluate(context):
    return (AssertionEvaluation(
        'org.spec33.observed', 'passed', math.fsum([20, 22]), '1',
        source='product', namespace='org.spec33',
        evidence_sha256=(next(iter(context.evidence_sha256)),),
    ),)
"""
EVALUATE = """\
record = _verify_installed_record(entry_point)
evaluator = _load_evaluator(entry_point, record)
print(json.dumps([item.observed_value for item in evaluator(context())]))
"""


def _wheel_files(
    sources: Mapping[str, str], target: str, distribution_name: str, namespace: str
) -> dict[str, bytes]:
    dist_info = f"{distribution_name}-1.0.dist-info"
    files = {name: source.encode() for name, source in sources.items()}
    files[f"{dist_info}/METADATA"] = (
        f"Metadata-Version: 2.1\nName: {distribution_name.replace('_', '-')}\nVersion: 1.0\n"
    ).encode()
    files[f"{dist_info}/WHEEL"] = (
        b"Wheel-Version: 1.0\nGenerator: spec33-test\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
    )
    files[f"{dist_info}/entry_points.txt"] = (
        f"[robotics_acceptance.evaluators]\n{namespace} = {target}\n".encode()
    )
    record = io.StringIO(newline="")
    writer = csv.writer(record)
    for name, payload in files.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).rstrip(b"=").decode()
        writer.writerow((name, f"sha256={digest}", len(payload)))
    writer.writerow((f"{dist_info}/RECORD", "", ""))
    files[f"{dist_info}/RECORD"] = record.getvalue().encode()
    return files


def _install_wheel(
    tmp_path: Path,
    sources: Mapping[str, str],
    target: str = f"{MODULE}:evaluate",
    *,
    distribution_name: str = "spec33_evaluator",
    namespace: str = "org.spec33",
) -> Path:
    uv = shutil.which("uv")
    if uv is None:
        pytest.fail("these installed-wheel regressions require the workspace's uv tool")
    wheel = tmp_path / f"{distribution_name}-1.0-py3-none-any.whl"
    with ZipFile(wheel, "w") as archive:
        for name, payload in _wheel_files(sources, target, distribution_name, namespace).items():
            archive.writestr(name, payload)
    site = tmp_path / "site"
    result = subprocess.run(
        [
            uv,
            "pip",
            "install",
            "--no-config",
            "--no-cache",
            "--no-deps",
            "--python",
            sys.executable,
            "--target",
            str(site),
            str(wheel),
        ],
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return site


@pytest.fixture
def installed(tmp_path: Path) -> Path:
    return _install_wheel(tmp_path, {f"{MODULE}.py": SOURCE})


def _run(site: Path, body: str, prefix: Path | None = None) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.pop("PYTHONPYCACHEPREFIX", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONPATH"] = os.pathsep.join(
        [
            str(Path(robotics_acceptance_harness.__file__).parent.parent),
            str(Path(robotics_runtime_contracts.__file__).parent.parent),
        ]
    )
    if prefix is not None:
        environment["PYTHONPYCACHEPREFIX"] = str(prefix)
    setup = """\
import importlib
import json
import sys
from pathlib import Path
from importlib.metadata import distribution
from robotics_acceptance_harness.evaluation import (
    EvaluationError, _load_evaluator, _verify_installed_record,
)
from tests.test_evaluation import context
site = Path(sys.argv[1])
sys.path.insert(0, str(site))
entry_point = distribution('spec33-evaluator').entry_points['org.spec33']
"""
    return subprocess.run(
        [sys.executable, "-c", setup + textwrap.dedent(body), str(site)],
        cwd=Path(__file__).parent.parent,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )


def _assert_rejected(result: subprocess.CompletedProcess[str], reason: str) -> None:
    assert result.returncode != 0, result.stdout
    assert f"EvaluationError: {reason}" in result.stderr, result.stderr


def test_installed_wheel_loads_and_repeats_without_writing_cache(installed: Path) -> None:
    result = _run(
        installed,
        "context()\nsys.dont_write_bytecode = False\n"
        + EVALUATE
        + EVALUATE
        + """\
assert sys.dont_write_bytecode is False
assert not list(site.rglob('*.pyc'))
""",
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["[42.0]", "[42.0]"]


def test_prefix_cache_control_executes_forged_code_but_verifier_rejects(
    installed: Path, tmp_path: Path
) -> None:
    prefix = tmp_path / "external-cache"
    prepare = _run(
        installed,
        f"""\
import py_compile
source = site / '{MODULE}.py'
forged = site.parent / 'forged.py'
forged.write_text(source.read_text().replace('[20, 22]', '[90, 9]'))
cache = importlib.util.cache_from_source(str(source))
assert Path(cache).is_relative_to(Path(sys.pycache_prefix))
py_compile.compile(str(forged), cfile=cache, doraise=True,
                   invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH)
print(json.dumps([item.observed_value for item in entry_point.load()(context())]))
""",
        prefix,
    )
    assert prepare.returncode == 0, prepare.stderr
    assert json.loads(prepare.stdout) == [99.0]
    _assert_rejected(
        _run(installed, EVALUATE, prefix),
        "evaluator loading does not support sys.pycache_prefix",
    )
    control = _run(installed, EVALUATE)
    assert control.returncode == 0, control.stderr
    assert json.loads(control.stdout) == [42.0]


def test_prefix_enabled_after_verification_is_rejected(installed: Path, tmp_path: Path) -> None:
    result = _run(
        installed,
        f"""\
record = _verify_installed_record(entry_point)
sys.pycache_prefix = {str(tmp_path / "late-cache")!r}
_load_evaluator(entry_point, record)
""",
    )
    assert result.returncode != 0
    assert "does not support sys.pycache_prefix" in result.stderr


@pytest.mark.parametrize("location", ["adjacent", "legacy"])
def test_unrecorded_bytecode_is_rejected(installed: Path, location: str) -> None:
    result = _run(
        installed,
        f"""\
import py_compile
source = site / '{MODULE}.py'
cache = (importlib.util.cache_from_source(str(source)) if {location!r} == 'adjacent'
         else str(source.with_suffix('.pyc')))
py_compile.compile(str(source), cfile=cache, doraise=True)
"""
        + EVALUATE,
    )
    _assert_rejected(result, "installed evaluator has unverified bytecode cache")


@pytest.mark.parametrize("mutation", ["source", "cache"])
def test_import_uses_verified_bytes_despite_late_file_changes(
    installed: Path, mutation: str
) -> None:
    result = _run(
        installed,
        f"""\
record = _verify_installed_record(entry_point)
source = site / '{MODULE}.py'
forged = source.read_text().replace('[20, 22]', '[90, 9]')
if {mutation!r} == 'source':
    source.write_text(forged)
else:
    import py_compile
    other = site.parent / 'forged.py'
    other.write_text(forged)
    py_compile.compile(str(other), cfile=importlib.util.cache_from_source(str(source)),
                       doraise=True,
                       invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH)
evaluator = _load_evaluator(entry_point, record)
print(json.dumps([item.observed_value for item in evaluator(context())]))
""",
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == [42.0]


def test_preimported_module_is_not_authenticated_by_its_file_attribute(installed: Path) -> None:
    result = _run(installed, f"import {MODULE}\n" + EVALUATE)
    assert result.returncode != 0
    assert "was already imported without verification" in result.stderr


def test_normalized_record_paths_remain_loadable(installed: Path) -> None:
    record_path = installed / DIST_INFO / "RECORD"
    with record_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    for row in rows:
        if row[0] == f"{MODULE}.py":
            row[0] = f"../site/{MODULE}.py"
    with record_path.open("w", newline="", encoding="utf-8") as stream:
        csv.writer(stream).writerows(rows)
    result = _run(installed, EVALUATE)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == [42.0]


def test_shadow_module_is_rejected_even_after_record_verification(installed: Path) -> None:
    result = _run(
        installed,
        f"""\
record = _verify_installed_record(entry_point)
shadow = site.parent / 'shadow'
shadow.mkdir()
(shadow / '{MODULE}.py').write_text('raise RuntimeError("unverified code executed")')
sys.path.insert(0, str(shadow))
_load_evaluator(entry_point, record)
""",
    )
    assert result.returncode != 0
    assert "outside its verified RECORD" in result.stderr
    assert "RuntimeError: unverified code executed" not in result.stderr


@pytest.mark.parametrize("namespace", [False, True])
def test_package_relative_lazy_circular_and_dotted_attribute_imports(
    tmp_path: Path, namespace: bool
) -> None:
    sources = {
        f"{MODULE}/api.py": """\
from . import support
class Product:
    @staticmethod
    def evaluate(context):
        from .lazy import evaluate
        yield from evaluate(context)
""",
        f"{MODULE}/support.py": "from . import api\n",
        f"{MODULE}/lazy.py": SOURCE,
    }
    if not namespace:
        sources[f"{MODULE}/__init__.py"] = "from . import api\n"
    site = _install_wheel(tmp_path, sources, f"{MODULE}.api:Product.evaluate [feature]")
    result = _run(site, EVALUATE + EVALUATE)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["[42.0]", "[42.0]"]


@pytest.mark.parametrize("import_at", ["parent", "lazy"])
def test_unrecorded_package_code_does_not_execute(tmp_path: Path, import_at: str) -> None:
    sources = {f"{MODULE}/api.py": SOURCE}
    if import_at == "lazy":
        sources[f"{MODULE}/__init__.py"] = ""
        sources[f"{MODULE}/api.py"] = SOURCE.replace(
            "def evaluate(context):", "def evaluate(context):\n    from . import injected"
        )
    site = _install_wheel(tmp_path, sources, f"{MODULE}.api:evaluate")
    name = "__init__" if import_at == "parent" else "injected"
    (site / MODULE / f"{name}.py").write_text('raise RuntimeError("unverified code executed")')
    result = _run(site, EVALUATE)
    assert result.returncode != 0
    assert "outside its verified RECORD" in result.stderr
    assert "RuntimeError: unverified code executed" not in result.stderr


@pytest.mark.parametrize("link_kind", ["file", "directory"])
def test_record_paths_cannot_follow_symlinks(tmp_path: Path, link_kind: str) -> None:
    site = _install_wheel(tmp_path, {f"{MODULE}/__init__.py": SOURCE})
    original = site / MODULE
    if link_kind == "file":
        original /= "__init__.py"
    external = tmp_path / original.name
    original.rename(external)
    try:
        original.symlink_to(external, target_is_directory=link_kind == "directory")
    except OSError as error:
        pytest.skip(f"symlink creation unavailable: {error}")
    _assert_rejected(_run(site, EVALUATE), "installed evaluator path contains a symlink")


def test_failed_import_restores_import_state(tmp_path: Path) -> None:
    installed = _install_wheel(tmp_path, {f"{MODULE}.py": "raise RuntimeError('fixture failure')"})
    result = _run(
        installed,
        """\
record = _verify_installed_record(entry_point)
finders = tuple(sys.meta_path)
sys.dont_write_bytecode = False
try:
    _load_evaluator(entry_point, record)
except EvaluationError as error:
    assert isinstance(error.__cause__, RuntimeError)
    assert str(error.__cause__) == 'fixture failure'
else:
    raise AssertionError('failed import was accepted')
assert tuple(sys.meta_path) == finders
assert sys.dont_write_bytecode is False
assert 'spec33_evaluator' not in sys.modules
print('restored')
""",
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "restored"


def _namespace_wheels(
    tmp_path: Path,
    *,
    split_sites: bool = False,
    primary_source: str = "from .lazy_alpha import evaluate\n",
    primary_target: str = "spec33_shared.alpha:evaluate",
) -> tuple[Path, Path]:
    site = _install_wheel(
        tmp_path,
        {"spec33_shared/alpha.py": primary_source, "spec33_shared/lazy_alpha.py": SOURCE},
        primary_target,
    )
    peer_root = tmp_path / "peer" if split_sites else tmp_path
    peer_root.mkdir(exist_ok=True)
    peer_site = _install_wheel(
        peer_root,
        {
            "spec33_shared/beta.py": (
                "def evaluate(context):\n"
                "    from .lazy_beta import evaluate\n"
                "    yield from evaluate(context)\n"
            ),
            "spec33_shared/lazy_beta.py": SOURCE.replace("org.spec33", "org.spec33.peer").replace(
                "[20, 22]", "[20, 23]"
            ),
        },
        "spec33_shared.beta:evaluate",
        distribution_name="spec33_peer",
        namespace="org.spec33.peer",
    )
    return site, peer_site


def _namespace_run(
    site: Path,
    peer_site: Path,
    body: str,
    *,
    include_peer: bool = True,
    before_qualification: str = "",
) -> subprocess.CompletedProcess[str]:
    setup = f"""\
import hashlib
from robotics_acceptance_harness.evaluation import (
    _installed_evaluators, evaluate_acceptance, evaluator_inventory,
)
from robotics_acceptance_harness.receipts import load_verified_receipts
from tests.support import write_verified_receipt
peer_site = Path({str(peer_site)!r})
if peer_site != site:
    sys.path.insert(0, str(peer_site))
peer = distribution('spec33-peer').entry_points['org.spec33.peer']
points = [entry_point, peer] if {include_peer!r} else [entry_point]
chains, requirements = [], []
for point in points:
    wheel_root = Path(point.dist.locate_file('')).parent
    wheel = wheel_root / (point.dist.name.replace('-', '_') + '-1.0-py3-none-any.whl')
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    chain = write_verified_receipt(site.parent, {{
        'uri': wheel.as_uri(), 'sha256': digest, 'size_bytes': wheel.stat().st_size,
        'media_type': 'application/vnd.python.wheel', 'immutable_revision': 'sha256:' + digest,
    }}, stem=point.dist.name)
    chains.append(chain)
    requirements.append({{
        'namespace': point.name, 'entry_point': point.value,
        'distribution': point.dist.name, 'version': point.dist.version,
        'artifact_sha256': digest, 'receipt_sha256': chain['receipt_sha256'],
    }})
# Receipt chains may refer to the same external-verification bytes.
dependencies = {{
    hashlib.sha256(path.read_bytes()).hexdigest(): path
    for chain in chains for path in chain['dependencies']
}}
receipts = load_verified_receipts(
    receipt_paths=[chain['receipt'] for chain in chains],
    verification_paths=[chain['verification'] for chain in chains],
    dependency_paths=list(dependencies.values()),
)
"""
    return _run(site, setup + textwrap.dedent(before_qualification) + textwrap.dedent(body))


@pytest.mark.parametrize("split_sites", [False, True])
@pytest.mark.parametrize("reverse", [False, True])
def test_qualified_namespace_wheels_load_in_either_order_and_repeat(
    tmp_path: Path, split_sites: bool, reverse: bool
) -> None:
    site, peer_site = _namespace_wheels(tmp_path, split_sites=split_sites)
    result = _namespace_run(
        site,
        peer_site,
        """\
inventory = evaluator_inventory(requirements, receipts)
assert len(inventory) == 2 and all(item['status'] == 'qualified' for item in inventory)
for _ in range(2):
    evaluators = _installed_evaluators(requirements, receipts)
    for _ in range(2):
        results = evaluate_acceptance(context(), evaluators=evaluators)
        values = sorted(item.observed_value for item in results if item.source == 'product')
        assert values == [42.0, 43.0]
assert not list(site.parent.rglob('*.pyc'))
print('both qualified')
""",
        before_qualification="requirements.reverse()\n" if reverse else "",
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "both qualified"


def test_namespace_peer_record_is_checked_before_any_evaluator_executes(tmp_path: Path) -> None:
    site, peer_site = _namespace_wheels(
        tmp_path, primary_source="raise RuntimeError('primary executed before qualification')\n"
    )
    (peer_site / "spec33_shared/lazy_beta.py").write_text("raise RuntimeError('tampered peer')")
    result = _namespace_run(site, peer_site, "_installed_evaluators(requirements, receipts)\n")
    _assert_rejected(result, "installed evaluator file differs from RECORD")
    assert "primary executed before qualification" not in result.stderr
    assert "RuntimeError: tampered peer" not in result.stderr


def test_namespace_entry_point_must_belong_to_its_own_wheel(tmp_path: Path) -> None:
    site, peer_site = _namespace_wheels(tmp_path, primary_target="spec33_shared.beta:evaluate")
    result = _namespace_run(site, peer_site, "_installed_evaluators(requirements, receipts)\n")
    _assert_rejected(result, "evaluator module 'spec33_shared.beta' resolves outside")


@pytest.mark.parametrize("peer_preverified", [False, True])
def test_namespace_does_not_authorize_an_unqualified_peer(
    tmp_path: Path, peer_preverified: bool
) -> None:
    site, peer_site = _namespace_wheels(
        tmp_path,
        primary_source=(
            "def evaluate(context):\n"
            "    from .beta import evaluate\n"
            "    yield from evaluate(context)\n"
        ),
    )
    result = _namespace_run(
        site,
        peer_site,
        "evaluators = _installed_evaluators(requirements, receipts)\n"
        "evaluate_acceptance(context(), evaluators=evaluators)\n",
        include_peer=False,
        before_qualification=(
            "_load_evaluator(peer, _verify_installed_record(peer))\n" if peer_preverified else ""
        ),
    )
    assert result.returncode != 0
    assert (
        "already imported without verification"
        if peer_preverified
        else "outside its verified RECORD"
    ) in result.stderr


def test_qualified_namespace_rejects_a_normally_preimported_peer(tmp_path: Path) -> None:
    site, peer_site = _namespace_wheels(tmp_path)
    result = _namespace_run(
        site,
        peer_site,
        "_installed_evaluators(requirements, receipts)\n",
        before_qualification="import spec33_shared.beta\n",
    )
    _assert_rejected(result, "evaluator module 'spec33_shared.beta' was already imported")


def test_qualified_namespace_rejects_an_unowned_search_location(tmp_path: Path) -> None:
    site, peer_site = _namespace_wheels(tmp_path, split_sites=True)
    result = _namespace_run(
        site,
        peer_site,
        "_installed_evaluators(requirements, receipts)\n",
        before_qualification="""\
foreign = site.parent / 'foreign'
(foreign / 'spec33_shared').mkdir(parents=True)
sys.path.insert(0, str(foreign))
""",
    )
    _assert_rejected(result, "evaluator namespace 'spec33_shared' is outside its verified RECORD")


@pytest.mark.parametrize("failure", ["type", "namespace", "evidence", "finalizer"])
def test_consumer_rejection_closes_verified_generator_with_retained_traceback(
    tmp_path: Path, failure: str
) -> None:
    value = {
        "type": "'invalid result'",
        "namespace": (
            "AssertionEvaluation('org.other.result', 'passed', 1, '1', source='product', "
            "namespace='org.other', evidence_sha256=('a' * 64,))"
        ),
        "evidence": (
            "AssertionEvaluation('org.spec33.result', 'passed', 1, '1', source='product', "
            "namespace='org.spec33', evidence_sha256=('b' * 64,))"
        ),
        "finalizer": "'invalid result'",
    }[failure]
    source = (
        "from robotics_acceptance_harness import AssertionEvaluation\n"
        "closed = []\n"
        "def evaluate(context):\n"
        "    try:\n"
        f"        yield {value}\n"
        "        raise RuntimeError('consumer advanced after invalid result')\n"
        "    finally:\n"
        "        closed.append(True)\n"
    )
    if failure == "finalizer":
        source += "        raise RuntimeError('fixture finalizer failed')\n"
    site = _install_wheel(tmp_path, {f"{MODULE}.py": source})
    result = _run(
        site,
        f"""\
from robotics_acceptance_harness.evaluation import evaluate_acceptance
evaluation_context = context()
evaluator = _load_evaluator(entry_point, _verify_installed_record(entry_point))
finders = tuple(sys.meta_path)
sys.dont_write_bytecode = False
retained_errors = []
try:
    evaluate_acceptance(evaluation_context, evaluators=((entry_point.name, evaluator),))
except EvaluationError as error:
    retained_errors.append(error)
    assert tuple(sys.meta_path) == finders
    assert sys.dont_write_bytecode is False
else:
    raise AssertionError('consumer accepted invalid product result')
assert retained_errors[0].__traceback__ is not None
assert sys.modules[{MODULE!r}].closed == [True]
assert 'consumer advanced' not in str(retained_errors[0])
if {failure!r} == 'finalizer':
    assert 'fixture finalizer failed' in str(retained_errors[0])
assert tuple(sys.meta_path) == finders
assert sys.dont_write_bytecode is False
print('restored with retained traceback')
""",
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "restored with retained traceback"
