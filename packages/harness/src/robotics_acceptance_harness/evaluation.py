from __future__ import annotations

import os
import sys
from collections.abc import Callable, Generator, Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from importlib import import_module
from importlib.abc import MetaPathFinder
from importlib.machinery import ModuleSpec, PathFinder, SourceFileLoader
from importlib.metadata import EntryPoint, entry_points
from pathlib import Path
from types import CodeType, MappingProxyType, ModuleType
from typing import Any, cast

from packaging.utils import canonicalize_name

from robotics_acceptance_harness.archive import AssessmentControls
from robotics_acceptance_harness.documents import DocumentBundle, LoadedDocument
from robotics_acceptance_harness.errors import HarnessError
from robotics_acceptance_harness.evaluator_trust import (
    AuthenticatedInstallation,
    require_authenticated_installation,
)
from robotics_acceptance_harness.evidence import VerifiedEvidence
from robotics_acceptance_harness.metrics import (
    AssertionEvaluation,
    MetricPoint,
    evaluate_metric_assertions,
    validate_metric_definitions,
)
from robotics_acceptance_harness.policy import (
    evaluate_data_plane_policy,
    evaluate_evidence_policy,
    evaluate_native_evidence_policy,
)
from robotics_acceptance_harness.receipts import VerifiedReceiptSet

EVALUATOR_ENTRY_POINT_GROUP = "robotics_acceptance.evaluators"


class EvaluationError(HarnessError, ValueError):
    """Raised when an evaluator violates the public extension contract."""

    error_id = "evaluation.invalid"


@dataclass(frozen=True, slots=True)
class EvaluationContext:
    """Immutable inputs shared by live and offline acceptance evaluation."""

    run_id: str
    domain_id: str
    bundle: DocumentBundle
    evidence: VerifiedEvidence
    metric_samples: tuple[MetricPoint, ...]
    window_start_ns: int
    window_end_ns: int
    max_raw_evidence_bytes: int | None = None
    assessment_controls: AssessmentControls | None = None
    metric_evidence_sha256: str | None = None
    original_result: LoadedDocument | None = None

    @property
    def method_controls(self) -> Mapping[str, Any]:
        return (
            self.assessment_controls.data if self.assessment_controls is not None else self.scenario
        )

    @property
    def scenario(self) -> Mapping[str, Any]:
        return self.bundle.scenario.data

    @property
    def runtime(self) -> Mapping[str, Any]:
        return self.bundle.runtime.data

    @property
    def original_evidence_sha256(self) -> frozenset[str]:
        return frozenset(str(item["sha256"]) for item in self.evidence.links)

    @property
    def evidence_sha256(self) -> frozenset[str]:
        method_inputs = (
            self.assessment_controls.inputs if self.assessment_controls is not None else {}
        )
        return self.original_evidence_sha256 | frozenset(method_inputs)


type ProductEvaluator = Callable[[EvaluationContext], Iterable[AssertionEvaluation]]


@dataclass(frozen=True)
class _VerifiedRecord:
    paths: frozenset[Path]
    sources: Mapping[Path, bytes]


def _check_bytecode_prefix() -> None:
    if sys.pycache_prefix is not None:
        raise EvaluationError("evaluator loading does not support sys.pycache_prefix")


def _installed_path(path: Path) -> Path:
    absolute = Path(os.path.abspath(path))
    if path.resolve() != absolute:
        raise EvaluationError(f"installed evaluator path contains a symlink: {path}")
    return absolute


class _VerifiedSourceLoader(SourceFileLoader):
    """Compile captured source bytes; never consult or write a cache."""

    def __init__(self, name: str, path: Path, source: bytes) -> None:
        super().__init__(name, str(path))
        self.source = source

    def get_code(self, fullname: str) -> CodeType:
        return self.source_to_code(self.source, self.path)


def _check_namespace(name: str, locations: Sequence[str], paths: frozenset[Path]) -> None:
    for location in locations:
        directory = _installed_path(Path(location))
        if not any(path.is_relative_to(directory) for path in paths):
            raise EvaluationError(f"evaluator namespace {name!r} is outside its verified RECORD")


def _record_spec(
    name: str,
    search_path: Sequence[str] | None,
    paths: frozenset[Path],
    *,
    namespace_paths: frozenset[Path] | None = None,
) -> ModuleSpec:
    spec = PathFinder.find_spec(name, search_path)
    if spec is None:
        raise EvaluationError(f"cannot resolve evaluator module {name!r}")
    if spec.origin is None and spec.submodule_search_locations:
        # Namespace packages execute no code, but every search location must be owned.
        _check_namespace(
            name,
            spec.submodule_search_locations,
            paths if namespace_paths is None else namespace_paths,
        )
    elif spec.origin is None or _installed_path(Path(spec.origin)) not in paths:
        raise EvaluationError(f"evaluator module {name!r} resolves outside its verified RECORD")
    return spec


class _VerifiedImports(MetaPathFinder):
    """Admit only source verified for the current set of qualified distributions."""

    def __init__(self, qualified: Sequence[tuple[EntryPoint, _VerifiedRecord]]) -> None:
        self.roots: set[str] = set()
        paths: set[Path] = set()
        sources: dict[Path, bytes] = {}
        for entry_point, record in qualified:
            assert entry_point.dist is not None
            root = _installed_path(Path(str(entry_point.dist.locate_file(""))))
            self.roots.add(entry_point.module.split(".")[0])
            self.roots.update(
                path.relative_to(root).parts[0].split(".")[0]
                for path in record.paths
                if path.is_relative_to(root)
            )
            paths.update(record.paths)
            for path, source in record.sources.items():
                if path in sources and sources[path] != source:
                    raise EvaluationError(f"qualified evaluators disagree on source bytes: {path}")
                sources[path] = source
        self.paths = frozenset(paths)
        self.sources = MappingProxyType(sources)

    def owns(self, name: str) -> bool:
        return name.split(".")[0] in self.roots

    def find_spec(
        self, fullname: str, path: Sequence[str] | None, target: ModuleType | None = None
    ) -> ModuleSpec | None:
        if not self.owns(fullname):
            return None
        spec = _record_spec(fullname, path, self.paths)
        if spec.origin is not None:
            source_path = _installed_path(Path(spec.origin))
            if source_path not in self.sources:
                raise EvaluationError(
                    f"evaluator module {fullname!r} requires RECORD-hashed source"
                )
            spec.loader = _VerifiedSourceLoader(fullname, source_path, self.sources[source_path])
        return spec

    def check_loaded(self, name: str, module: ModuleType) -> None:
        spec = module.__spec__
        if spec is not None and spec.origin is None and spec.submodule_search_locations:
            _check_namespace(name, module.__path__, self.paths)
            return
        loader = getattr(spec, "loader", None)
        if (
            not isinstance(loader, _VerifiedSourceLoader)
            or self.sources.get(Path(loader.path)) != loader.source
        ):
            raise EvaluationError(
                f"evaluator module {name!r} was already imported without verification"
            )


@contextmanager
def _verified_imports(finder: _VerifiedImports) -> Iterator[None]:
    _check_bytecode_prefix()
    for name, module in tuple(sys.modules.items()):
        if module is not None and finder.owns(name):
            finder.check_loaded(name, module)
    sys.meta_path.insert(0, finder)
    try:
        yield
    finally:
        sys.meta_path.remove(finder)


def _load_evaluator(
    entry_point: EntryPoint,
    record: _VerifiedRecord,
    *,
    imports: _VerifiedImports | None = None,
) -> ProductEvaluator:
    finder = _VerifiedImports(((entry_point, record),)) if imports is None else imports
    try:
        with _verified_imports(finder):
            evaluator = import_module(entry_point.module)
            attributes = entry_point.attr.split(".") if entry_point.attr else ()
            for attribute in attributes:
                evaluator = getattr(evaluator, attribute)
    except Exception as error:
        raise EvaluationError(
            f"cannot load evaluator entry point {entry_point.name!r}: {error}"
        ) from error
    if not callable(evaluator):
        raise EvaluationError(f"entry point {entry_point.name!r} is not callable")
    product_evaluator = cast(ProductEvaluator, evaluator)

    def evaluate(context: EvaluationContext) -> Iterable[AssertionEvaluation]:
        with _verified_imports(finder):
            yield from product_evaluator(context)

    return evaluate


def _verify_entry_point_origin(
    entry_point: EntryPoint,
    hashed_paths: frozenset[Path],
    *,
    namespace_paths: frozenset[Path] | None = None,
) -> None:
    search_path: Sequence[str] | None = None
    qualified_name = ""
    for part in entry_point.module.split("."):
        qualified_name = f"{qualified_name}.{part}" if qualified_name else part
        spec = _record_spec(
            qualified_name, search_path, hashed_paths, namespace_paths=namespace_paths
        )
        search_path = spec.submodule_search_locations


def _qualified_entry_points(
    requirements: Sequence[Mapping[str, Any]],
    receipts: VerifiedReceiptSet,
    authentications: Mapping[str, AuthenticatedInstallation],
) -> tuple[tuple[EntryPoint, _VerifiedRecord], ...]:
    installed = tuple(entry_points(group=EVALUATOR_ENTRY_POINT_GROUP))
    qualified: list[tuple[EntryPoint, _VerifiedRecord]] = []
    for requirement in requirements:
        namespace = str(requirement["namespace"])
        candidates = [entry_point for entry_point in installed if entry_point.name == namespace]
        if len(candidates) != 1:
            raise EvaluationError(
                f"expected one evaluator entry point for {namespace!r}; found {len(candidates)}"
            )
        entry_point = candidates[0]
        distribution = entry_point.dist
        if distribution is None:
            raise EvaluationError(f"evaluator {namespace!r} has no owning distribution")
        observed = (
            entry_point.value,
            canonicalize_name(distribution.name),
            distribution.version,
        )
        expected = (
            requirement["entry_point"],
            canonicalize_name(str(requirement["distribution"])),
            requirement["version"],
        )
        if observed != expected:
            raise EvaluationError(f"installed evaluator {namespace!r} differs from its binding")
        receipts.verify_artifact(
            str(requirement["receipt_sha256"]),
            {"sha256": requirement["artifact_sha256"]},
        )
        record = _authenticated_record(requirement, entry_point, authentications)
        qualified.append((entry_point, record))
    if {str(item["receipt_sha256"]) for item in requirements} != set(receipts.by_digest):
        raise EvaluationError("evaluator qualification contains unreferenced receipts")
    if set(authentications) != {str(item["namespace"]) for item in requirements}:
        raise EvaluationError("evaluator authentication contains unreferenced namespaces")
    namespace_paths = frozenset(path for _, record in qualified for path in record.paths)
    for entry_point, record in qualified:
        # Namespace portions may be shared, but executable parents and the
        # entry-point module must still belong to this particular distribution.
        _verify_entry_point_origin(entry_point, record.paths, namespace_paths=namespace_paths)
    return tuple(qualified)


def _authenticated_record(
    requirement: Mapping[str, Any],
    entry_point: EntryPoint,
    authentications: Mapping[str, AuthenticatedInstallation],
) -> _VerifiedRecord:
    namespace = str(requirement["namespace"])
    admitted = authentications.get(namespace)
    if admitted is None:
        raise EvaluationError(
            f"evaluator {namespace!r} requires authenticated wheel/source admission"
        )
    require_authenticated_installation(admitted)
    expected = (
        str(requirement["artifact_sha256"]),
        canonicalize_name(str(requirement["distribution"])),
        str(requirement["version"]),
    )
    observed = (admitted.wheel_sha256, admitted.distribution, admitted.version)
    binding = (entry_point.group, entry_point.name, entry_point.value)
    if observed != expected or binding not in admitted.entry_points:
        raise EvaluationError(f"evaluator {namespace!r} differs from authenticated wheel bindings")
    return _VerifiedRecord(admitted.paths, admitted.sources)


def _installed_evaluators(
    requirements: Sequence[Mapping[str, Any]],
    receipts: VerifiedReceiptSet,
    authentications: Mapping[str, AuthenticatedInstallation],
) -> tuple[tuple[str, ProductEvaluator], ...]:
    qualified = _qualified_entry_points(requirements, receipts, authentications)
    imports = _VerifiedImports(qualified)
    return tuple(
        (entry_point.name, _load_evaluator(entry_point, record, imports=imports))
        for entry_point, record in qualified
    )


@contextmanager
def _evaluator_results(
    evaluator: ProductEvaluator, context: EvaluationContext
) -> Iterator[Iterator[AssertionEvaluation]]:
    results = iter(evaluator(context))
    try:
        yield results
    finally:
        # Consumer validation can fail while the verified wrapper is suspended
        # at a yield. Close it before an exception's traceback can retain it.
        if isinstance(results, Generator):
            results.close()


def _product_evaluations(
    context: EvaluationContext,
    evaluators: Sequence[tuple[str, ProductEvaluator]],
) -> tuple[AssertionEvaluation, ...]:
    evaluations: list[AssertionEvaluation] = []
    for namespace, evaluator in evaluators:
        if namespace.count(".") < 1:
            raise EvaluationError(
                f"evaluator namespace {namespace!r} must be a reverse-domain name"
            )
        try:
            with _evaluator_results(evaluator, context) as produced:
                for evaluation in produced:
                    if not isinstance(evaluation, AssertionEvaluation):
                        raise EvaluationError(
                            f"evaluator {namespace!r} returned {type(evaluation).__name__}; "
                            "expected AssertionEvaluation"
                        )
                    if evaluation.source != "product" or evaluation.namespace != namespace:
                        raise EvaluationError(
                            f"evaluator {namespace!r} must mark every result "
                            "as its product namespace"
                        )
                    if not evaluation.assertion_id.startswith(f"{namespace}."):
                        raise EvaluationError(
                            f"assertion {evaluation.assertion_id!r} "
                            f"is outside namespace {namespace!r}"
                        )
                    if not evaluation.evidence_sha256:
                        raise EvaluationError(
                            f"product assertion {evaluation.assertion_id!r} has no evidence digest"
                        )
                    missing = set(evaluation.evidence_sha256) - context.evidence_sha256
                    if missing:
                        raise EvaluationError(
                            "product assertion "
                            f"{evaluation.assertion_id!r} references unknown evidence "
                            f"{sorted(missing)}"
                        )
                    evaluations.append(evaluation)
        except EvaluationError:
            raise
        except Exception as error:
            raise EvaluationError(f"evaluator {namespace!r} failed: {error}") from error
    return tuple(evaluations)


def _validate_selected_calibration(context: EvaluationContext) -> None:
    if context.assessment_controls is None:
        return
    if context.bundle.scenario.schema_version != "acceptance-scenario.v2":
        raise EvaluationError("explicit assessment controls require native v2 source inputs")
    controls = context.method_controls
    if controls["calibration"]["state"] == "selected" and (
        controls["assertions"] or not controls["evaluator_requirements"]
    ):
        raise EvaluationError("core metric methods cannot apply selected calibration")


def _validate_calibration_bindings(
    context: EvaluationContext, evaluations: Sequence[AssertionEvaluation]
) -> None:
    calibration = context.method_controls.get("calibration")
    if calibration is None or calibration["state"] != "selected":
        return
    product = [item for item in evaluations if item.source == "product"]
    claimed = {digest for item in product for digest in item.evidence_sha256}
    if {item["sha256"] for item in calibration["artifacts"]} - claimed:
        raise EvaluationError("selected calibration has no product assertion source binding")
    if any(not set(item.evidence_sha256) & context.original_evidence_sha256 for item in product):
        raise EvaluationError("calibrated product assertions require original raw evidence")


def evaluate_acceptance(
    context: EvaluationContext,
    *,
    evaluators: Sequence[tuple[str, ProductEvaluator]] | None = None,
    evaluator_receipts: VerifiedReceiptSet | None = None,
    evaluator_authentications: Mapping[str, AuthenticatedInstallation] | None = None,
) -> tuple[AssertionEvaluation, ...]:
    """Evaluate evidence through the canonical core and installed product evaluators."""

    scenario = context.method_controls
    _validate_selected_calibration(context)
    validate_metric_definitions(scenario["metric_definitions"], context.metric_samples)
    evaluations = list(
        evaluate_metric_assertions(
            scenario["assertions"],
            context.metric_samples,
            window_start_ns=context.window_start_ns,
            window_end_ns=context.window_end_ns,
        )
    )
    if context.bundle.scenario.schema_version == "acceptance-scenario.v1":
        evaluations.extend(
            evaluate_data_plane_policy(
                scenario["data_plane_policy"],
                context.runtime,
                context.metric_samples,
                domain_id=context.domain_id,
                window_start_ns=context.window_start_ns,
                window_end_ns=context.window_end_ns,
            )
        )
    evidence_policy = (
        evaluate_native_evidence_policy
        if context.bundle.scenario.schema_version == "acceptance-scenario.v2"
        else evaluate_evidence_policy
    )
    evaluations.extend(evidence_policy(scenario["evidence_policy"], context.evidence))
    evaluations.extend(
        _product_evaluations(
            context,
            (
                tuple(evaluators)
                if evaluators is not None
                else _installed_evaluators(
                    scenario["evaluator_requirements"],
                    evaluator_receipts or VerifiedReceiptSet({}),
                    evaluator_authentications or {},
                )
            ),
        )
    )
    _validate_calibration_bindings(context, evaluations)
    identifiers = [item.assertion_id for item in evaluations]
    if len(identifiers) != len(set(identifiers)):
        duplicates = sorted({item for item in identifiers if identifiers.count(item) > 1})
        raise EvaluationError(f"duplicate assertion identifiers: {duplicates}")
    return tuple(evaluations)


def evaluator_inventory(
    requirements: Sequence[Mapping[str, Any]] = (),
    receipts: VerifiedReceiptSet | None = None,
    authentications: Mapping[str, AuthenticatedInstallation] | None = None,
) -> tuple[Mapping[str, str], ...]:
    """Describe installed product evaluators without importing their targets."""

    installed = (
        tuple(
            entry_point
            for entry_point, _record in _qualified_entry_points(
                requirements, receipts or VerifiedReceiptSet({}), authentications or {}
            )
        )
        if requirements
        else tuple(entry_points(group=EVALUATOR_ENTRY_POINT_GROUP))
    )
    inventory: list[Mapping[str, str]] = []
    for entry_point in sorted(
        installed,
        key=lambda item: (item.name, item.value),
    ):
        assert isinstance(entry_point, EntryPoint)
        inventory.append(
            {
                "namespace": entry_point.name,
                "target": entry_point.value,
                "distribution": (
                    entry_point.dist.name if entry_point.dist is not None else "unknown"
                ),
                "version": (
                    entry_point.dist.version if entry_point.dist is not None else "unknown"
                ),
                "status": "authenticated" if requirements else "discovered",
            }
        )
    return tuple(inventory)


__all__ = [
    "EVALUATOR_ENTRY_POINT_GROUP",
    "AssertionEvaluation",
    "EvaluationContext",
    "EvaluationError",
    "ProductEvaluator",
    "evaluate_acceptance",
    "evaluator_inventory",
]
