"""PyPA wheel/installation byte binding for self-contained Python evaluators."""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import os
import stat
from collections.abc import Mapping
from configparser import ConfigParser
from email.parser import BytesParser
from importlib.metadata import Distribution
from importlib.util import source_from_cache
from itertools import chain
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from zipfile import BadZipFile, ZipFile

from packaging.utils import canonicalize_name, parse_wheel_filename
from packaging.version import Version

from robotics_acceptance_harness.evaluator_trust import (
    AuthenticatedInstallation,
    AuthenticatedWheel,
    EvaluatorTrustError,
    read_once,
)

_INSTALLER_FILES = frozenset({"INSTALLER", "REQUESTED", "direct_url.json"})
_NATIVE_SUFFIXES = frozenset({".so", ".pyd", ".dll", ".dylib", ".pyc", ".pyo"})


def _name(value: str) -> str:
    path = PurePosixPath(value)
    if (
        not value
        or len(value.encode("utf-8")) > 4096
        or "\\" in value
        or "\x00" in value
        or path.is_absolute()
        or ".." in path.parts
        or path.as_posix() != value
    ):
        raise EvaluatorTrustError(f"noncanonical wheel/RECORD path: {value!r}")
    return value


def _members(wheel: AuthenticatedWheel) -> dict[str, bytes]:
    limits = wheel.limits
    try:
        with ZipFile(io.BytesIO(wheel.wheel_bytes)) as archive:
            infos = archive.infolist()
            if len(infos) > limits.max_members:
                raise EvaluatorTrustError("wheel has too many members")
            names = [info.filename for info in infos]
            if len(set(names)) != len(names):
                raise EvaluatorTrustError("wheel has duplicate member names")
            total = 0
            files: dict[str, bytes] = {}
            for info in infos:
                _name(info.filename.rstrip("/") if info.is_dir() else info.filename)
                mode = info.external_attr >> 16
                if stat.S_IFMT(mode) not in {0, stat.S_IFREG, stat.S_IFDIR} or info.flag_bits & 1:
                    raise EvaluatorTrustError("wheel links and encrypted members are unsupported")
                total += info.file_size
                if info.file_size > limits.max_member_bytes or total > limits.max_expanded_bytes:
                    raise EvaluatorTrustError("wheel exceeds its expanded byte limits")
                if not info.is_dir():
                    files[info.filename] = archive.read(info)
            return files
    except (BadZipFile, RuntimeError) as failure:
        raise EvaluatorTrustError(f"invalid wheel archive: {failure}") from failure


def _record(raw: bytes, max_rows: int) -> dict[str, tuple[str, str]]:
    rows: dict[str, tuple[str, str]] = {}
    try:
        for row in csv.reader(io.StringIO(raw.decode("utf-8"), newline=""), strict=True):
            if len(row) != 3:
                raise EvaluatorTrustError("RECORD rows must have path, hash and size")
            if len(rows) >= max_rows:
                raise EvaluatorTrustError("RECORD has too many rows")
            name = _name(row[0])
            if name in rows:
                raise EvaluatorTrustError(f"duplicate RECORD path: {name}")
            rows[name] = (row[1], row[2])
    except (UnicodeError, csv.Error) as failure:
        raise EvaluatorTrustError("invalid UTF-8 CSV RECORD") from failure
    return rows


def _record_digest(payload: bytes, fields: tuple[str, str], *, name: str) -> None:
    encoded, size = fields
    algorithm, separator, expected = encoded.partition("=")
    if not separator or algorithm not in {"sha256", "sha384", "sha512"}:
        raise EvaluatorTrustError(f"unsupported or absent RECORD digest: {name}")
    digest = base64.urlsafe_b64encode(hashlib.new(algorithm, payload).digest()).rstrip(b"=")
    if digest.decode("ascii") != expected or str(len(payload)) != size:
        raise EvaluatorTrustError(f"file bytes disagree with RECORD: {name}")


def _wheel_layout(wheel: AuthenticatedWheel, files: Mapping[str, bytes]) -> tuple[str, str, str]:
    candidates = [name for name in files if name.endswith(".dist-info/WHEEL")]
    if len(candidates) != 1:
        raise EvaluatorTrustError("wheel must have exactly one .dist-info/WHEEL")
    directory = str(PurePosixPath(candidates[0]).parent)
    if "/" in directory:
        raise EvaluatorTrustError("wheel dist-info must be at the archive root")
    for field in ("METADATA", "RECORD"):
        if f"{directory}/{field}" not in files:
            raise EvaluatorTrustError(f"wheel lacks {field}")
    metadata = BytesParser().parsebytes(files[f"{directory}/METADATA"])
    name = str(metadata.get("Name", ""))
    version = str(metadata.get("Version", ""))
    filename_name, filename_version, _, _ = parse_wheel_filename(wheel.filename)
    if canonicalize_name(name) != filename_name or Version(version) != filename_version:
        raise EvaluatorTrustError("wheel filename and metadata identities disagree")
    configuration = BytesParser().parsebytes(files[candidates[0]])
    if configuration.get("Wheel-Version") != "1.0":
        raise EvaluatorTrustError("only Wheel-Version 1.0 is admitted")
    if configuration.get("Root-Is-Purelib") != "true":
        raise EvaluatorTrustError("only self-contained purelib evaluator wheels are admitted")
    if any(".data/" in name or PurePosixPath(name).suffix in _NATIVE_SUFFIXES for name in files):
        raise EvaluatorTrustError("wheel requires unsupported installation/code transformations")
    _reject_startup(files)
    _verify_wheel_record(files, directory, wheel.limits.max_members)
    return directory, name, version


def _verify_wheel_record(files: Mapping[str, bytes], directory: str, max_members: int) -> None:
    records = _record(files[f"{directory}/RECORD"], max_members)
    if set(records) != set(files) or records[f"{directory}/RECORD"] != ("", ""):
        raise EvaluatorTrustError("wheel RECORD must cover exactly its original files")
    for path, payload in files.items():
        if path != f"{directory}/RECORD":
            _record_digest(payload, records[path], name=path)


def _installed_root(distribution: Distribution) -> Path:
    root = Path(os.path.abspath(str(distribution.locate_file(""))))
    if root.resolve(strict=True) != root or not root.is_dir():
        raise EvaluatorTrustError("installed distribution root must be a canonical directory")
    return root


def _installation_files(
    root: Path,
    dist_info: str,
    files: Mapping[str, bytes],
    wheel: AuthenticatedWheel,
) -> dict[Path, bytes]:
    record_name = f"{dist_info}/RECORD"
    records = _record(
        read_once(root / record_name, wheel.limits.max_member_bytes),
        wheel.limits.max_members + wheel.limits.max_cache_entries + 3,
    )
    expected = set(files) - {record_name}
    if not expected <= set(records) or records.get(record_name) != ("", ""):
        raise EvaluatorTrustError(
            "installed RECORD omits original wheel members or rewrites itself"
        )
    source_paths = {root / name for name in expected if PurePosixPath(name).suffix == ".py"}
    captured: dict[Path, bytes] = {}
    for name, fields in records.items():
        path = root / name
        if name == record_name:
            continue
        if _derived_cache(path, source_paths):
            continue
        payload = read_once(path, wheel.limits.max_member_bytes)
        if name in expected:
            if payload != files[name]:
                raise EvaluatorTrustError(
                    f"installed bytes differ from authenticated wheel: {name}"
                )
            captured[path] = payload
        elif (
            PurePosixPath(name).parent.as_posix() != dist_info
            or PurePosixPath(name).name not in _INSTALLER_FILES
        ):
            raise EvaluatorTrustError(f"installed RECORD contains unadmitted file: {name}")
        if fields == ("", ""):
            if name in expected:
                raise EvaluatorTrustError(f"installed wheel member lacks a digest: {name}")
        else:
            _record_digest(payload, fields, name=name)
    return captured


def _derived_cache(path: Path, sources: set[Path]) -> bool:
    if path.suffix != ".pyc":
        return False
    if path.is_symlink():
        raise EvaluatorTrustError("derived cache must not be a symlink")
    try:
        source = Path(source_from_cache(str(path)))
    except ValueError:
        return False
    return source in sources and source.suffix == ".py" and source.is_file()


def _namespace_closure(
    root: Path, captured: Mapping[Path, bytes], wheel: AuthenticatedWheel
) -> None:
    source_paths = {path for path in captured if path.suffix == ".py"}
    namespaces = {path.relative_to(root).parts[0].removesuffix(".py") for path in source_paths}
    checked: set[Path] = set()
    covered = {
        path
        for path in captured
        if path.relative_to(root).parts[0] in namespaces
        or (path.parent == root and path.stem in namespaces)
    }
    budget = len(covered) + wheel.limits.max_cache_entries
    directories = {
        parent
        for path in covered
        for parent in path.parents
        if parent != root and parent.is_relative_to(root)
    }
    cache_directories = {path.parent / "__pycache__" for path in source_paths}
    for namespace in namespaces:
        for candidate in chain(
            (root / namespace,),
            root.glob(f"{namespace}.*"),
            root.glob(f"__pycache__/{namespace}.*"),
        ):
            if not candidate.exists() and not candidate.is_symlink():
                continue
            if candidate.is_symlink():
                raise EvaluatorTrustError("installed namespace contains a link")
            if candidate.is_file():
                _check_namespace_file(candidate, captured, source_paths, checked, budget)
                continue
            for directory, children, names in os.walk(candidate, followlinks=False):
                parent = Path(directory)
                _check_namespace_directories(parent, children, directories | cache_directories)
                for name in names:
                    _check_namespace_file(parent / name, captured, source_paths, checked, budget)


def _check_namespace_directories(parent: Path, children: list[str], allowed: set[Path]) -> None:
    if len(children) > len(allowed):
        raise EvaluatorTrustError("installed namespace exceeds its directory entry budget")
    for name in children:
        child = parent / name
        if child.is_symlink() or child not in allowed:
            raise EvaluatorTrustError("installed namespace contains an extra directory or link")


def _check_namespace_file(
    path: Path, captured: Mapping[Path, bytes], sources: set[Path], checked: set[Path], budget: int
) -> None:
    if path in checked:
        return
    if len(checked) >= budget:
        raise EvaluatorTrustError("installed namespace exceeds its file/cache entry budget")
    checked.add(path)
    if path.is_symlink():
        raise EvaluatorTrustError("installed namespace contains a link")
    if path not in captured and not _derived_cache(path, sources):
        raise EvaluatorTrustError(f"installed namespace contains an extra file: {path}")


def bind_installation(
    wheel: AuthenticatedWheel, distribution: Distribution
) -> AuthenticatedInstallation:
    files = _members(wheel)
    dist_info, name, version = _wheel_layout(wheel, files)
    root = _installed_root(distribution)
    _metadata_binding(distribution, dist_info, files)
    captured = _installation_files(root, dist_info, files, wheel)
    _namespace_closure(root, captured, wheel)
    sources = {path: payload for path, payload in captured.items() if path.suffix == ".py"}
    if not sources:
        raise EvaluatorTrustError("evaluator wheel contains no authenticated Python source")
    return AuthenticatedInstallation(
        wheel_sha256=wheel.sha256,
        distribution=canonicalize_name(name),
        version=version,
        paths=frozenset(captured),
        files=MappingProxyType(captured),
        sources=MappingProxyType(sources),
        entry_points=_entry_points(files.get(f"{dist_info}/entry_points.txt")),
    )


def _reject_startup(files: Mapping[str, bytes]) -> None:
    if any(
        ("/" not in name and name.endswith(".pth"))
        or name in {"sitecustomize.py", "usercustomize.py"}
        for name in files
    ):
        raise EvaluatorTrustError("evaluator profile rejects Python startup hooks")


def _metadata_binding(
    distribution: Distribution, dist_info: str, files: Mapping[str, bytes]
) -> None:
    for filename in ("METADATA", "WHEEL", "entry_points.txt"):
        raw = files.get(f"{dist_info}/{filename}")
        expected = None if raw is None else raw.decode("utf-8").replace("\r\n", "\n")
        if distribution.read_text(filename) != expected:
            raise EvaluatorTrustError(
                f"supplied distribution metadata differs from wheel: {filename}"
            )


class _EntryPointParser(ConfigParser):
    def optionxform(self, optionstr: str) -> str:
        return optionstr


def _entry_points(raw: bytes | None) -> tuple[tuple[str, str, str], ...]:
    if raw is None:
        return ()
    parser = _EntryPointParser(interpolation=None)
    parser.read_string(raw.decode("utf-8"))
    return tuple(
        (group, name, value) for group in parser.sections() for name, value in parser.items(group)
    )


def validate_profile(wheel: AuthenticatedWheel) -> None:
    files = _members(wheel)
    dist_info, _, _ = _wheel_layout(wheel, files)
    if any(
        group in {"console_scripts", "gui_scripts"}
        for group, _, _ in _entry_points(files.get(f"{dist_info}/entry_points.txt"))
    ):
        raise EvaluatorTrustError("evaluator profile does not admit generated script wrappers")
