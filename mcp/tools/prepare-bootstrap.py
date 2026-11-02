#!/usr/bin/env python3
"""Project a prepared qualification package into the existing offline MCP bootstrap."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import sys
from pathlib import Path

from robotics_runtime_contracts import schema_names
from robotics_runtime_contracts.errors import ContractError
from robotics_runtime_contracts.qualification import (
    ARTIFACT_ROLES,
    RAW_ARTIFACT_KINDS,
    load_qualification_artifact,
)

CATALOG_LIMIT = 64
INPUT_LIMIT = 16 * 1024 * 1024
BOOTSTRAP_LIMIT = 65536
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")
BUNDLE_ROLES = {
    "model_manifest": "model",
    "dataset_manifest": "dataset",
    "execution_permit": "permit",
    "execution_verification": "verification",
}


class InventoryParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError("inventory arguments: " + message[:512])


def unchanged(before, after):
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns", "st_mode")
    return all(getattr(before, field) == getattr(after, field) for field in fields)


def private_root(value):
    path = Path(value)
    info = path.lstat()
    if not path.is_absolute() or path.resolve() != path or not stat.S_ISDIR(info.st_mode):
        raise ValueError("roots must be absolute canonical directories without links")
    if info.st_mode & 0o022:
        raise ValueError("roots must not be group/other writable")
    return path


def confined(root, value):
    if not value or "\\" in value or Path(value).is_absolute():
        raise ValueError("inventory paths must be relative to the package root")
    if any(part in {"", ".", ".."} for part in value.split("/")):
        raise ValueError("inventory path contains a non-canonical component")
    path = root
    for part in value.split("/"):
        path = path / part
        if stat.S_ISLNK(path.lstat().st_mode):
            raise ValueError("inventory path contains a link")
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or path.resolve() != path:
        raise ValueError("inventory input must be a canonical regular file")
    return path, info


def stable_read(root, value, maximum):
    path, before = confined(root, value)
    if before.st_mode & 0o222 or before.st_size > maximum:
        raise ValueError("prepared input must be read-only and within its byte limit")
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    if len(raw) > maximum or not unchanged(before, path.lstat()):
        raise ValueError("prepared input changed or exceeded its byte limit")
    confined(root, value)
    return raw


def artifact_id(subject):
    return "artifact_" + hashlib.sha256(subject.encode()).hexdigest()[:48]


def prepare(args):
    root = private_root(args.package_root)
    scratch = private_root(args.scratch_root)
    for command in (args.contracts_cli, args.harness_cli):
        if not Path(command).is_absolute():
            raise ValueError("worker executable paths must be absolute operator inputs")
    parser = InventoryParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--artifact", action="append", default=[])
    parser.add_argument("--extension-schema", action="append", default=[])
    parser.add_argument(
        "--schema-version",
        choices=("qualification-bundle.v1", "qualification-bundle.v2"),
        action="append",
        default=[],
    )
    parser.add_argument(
        "--comparison-rule", choices=("exact_assertion_outcome",), action="append", default=[]
    )
    tokens = (
        stable_read(root, "qualification-arguments.txt", BOOTSTRAP_LIMIT)
        .decode("utf-8")
        .splitlines()
    )
    if any(not token for token in tokens):
        raise ValueError("inventory must contain one literal argument per nonempty line")
    inventory = parser.parse_args(tokens)
    if len(inventory.schema_version) > 1 or len(inventory.comparison_rule) > 1:
        raise ValueError("duplicate qualification profile selection")
    version = inventory.schema_version[0] if inventory.schema_version else "qualification-bundle.v1"
    comparison = inventory.comparison_rule[0] if inventory.comparison_rule else None
    if (version, comparison) not in {
        ("qualification-bundle.v1", None),
        ("qualification-bundle.v2", "exact_assertion_outcome"),
    }:
        raise ValueError(
            "qualification profile must select v1 without a rule or v2 with exact_assertion_outcome"
        )
    extensions, extension_rows, records, ids, subjects = {}, [], {}, {}, {}
    total = 0

    def register(subject, relative, digest, size):
        nonlocal total
        identity = artifact_id(subject)
        if identity in ids and ids[identity] != subject:
            raise ValueError("generated artifact ID collision")
        ids[identity] = subject
        row = {"id": identity, "path": relative, "sha256": digest, "size_bytes": size}
        if subject in records:
            if records[subject] != row:
                raise ValueError("ambiguous repeated subject")
            return identity
        total += size
        if total > INPUT_LIMIT or len(records) >= CATALOG_LIMIT:
            raise ValueError("selected read corpus exceeds the existing MCP input/catalog limit")
        records[subject] = row
        return identity

    for specification in inventory.extension_schema:
        uri, separator, relative = specification.partition("=")
        if not separator or not uri or len(uri) > 512 or re.search(r"[\s=\x00]", uri):
            raise ValueError("invalid extension-schema URI/path binding")
        if uri in extensions:
            raise ValueError("duplicate extension-schema URI")
        raw = stable_read(root, relative, INPUT_LIMIT)
        extensions[uri] = raw
        identity = register(
            "extension-schema/" + uri, relative, hashlib.sha256(raw).hexdigest(), len(raw)
        )
        extension_rows.append({"uri": uri, "artifact_id": identity})
    if len(extension_rows) > 16:
        raise ValueError("extension registry exceeds the existing MCP limit")

    loaded = []
    for specification in inventory.artifact:
        kind, separator, remainder = specification.partition(":")
        subject, equals, relative = remainder.partition("=")
        if (
            not separator
            or not equals
            or not subject
            or kind not in ARTIFACT_ROLES.keys() | RAW_ARTIFACT_KINDS
        ):
            raise ValueError("artifact must use a published KIND:SUBJECT=PATH")
        path, before = confined(root, relative)
        binding = (kind, relative)
        if subject in subjects:
            if subjects[subject] != binding:
                raise ValueError("ambiguous repeated subject")
            continue
        subjects[subject] = binding
        if kind not in ARTIFACT_ROLES and kind != "metrics":
            continue
        if before.st_mode & 0o222 or before.st_size > INPUT_LIMIT:
            raise ValueError("selected artifact must be read-only and within the MCP input limit")
        artifact = load_qualification_artifact(f"{kind}:{subject}={path}", extensions)
        if not unchanged(before, path.lstat()) or artifact.size_bytes != before.st_size:
            raise ValueError("selected artifact changed during preparation")
        confined(root, relative)
        identity = register(subject, relative, artifact.sha256, artifact.size_bytes)
        loaded.append((artifact, identity))

    scenarios = [identity for artifact, identity in loaded if artifact.kind == "scenario"]
    if len(scenarios) != 1:
        raise ValueError("select a package with exactly one scenario")
    optional = {}
    for kind, role in BUNDLE_ROLES.items():
        matches = [identity for artifact, identity in loaded if artifact.kind == kind]
        if len(matches) > 1:
            raise ValueError("ambiguous optional bundle role: " + role)
        if matches:
            optional[role] = matches[0]
    bundles = []
    for domain in sorted(set(args.domain)):
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,127}", domain):
            raise ValueError("domain must be a canonical qualification label")
        runtimes = [
            identity
            for artifact, identity in loaded
            if artifact.kind == "runtime_manifest"
            and artifact.subject_name == f"runtime-manifests/{domain}.json"
        ]
        if len(runtimes) != 1:
            raise ValueError("selected domain requires exactly one runtime manifest: " + domain)
        bundles.append(
            {
                "id": "bundle_" + hashlib.sha256(domain.encode()).hexdigest()[:48],
                "scenario": scenarios[0],
                "runtime": runtimes[0],
                **optional,
            }
        )
    schemas = [{"id": name.replace(".", "_"), "schema": name} for name in schema_names()]
    for rows in (bundles, schemas):
        values = [row["id"] for row in rows]
        if (
            len(rows) > CATALOG_LIMIT
            or len(set(values)) != len(values)
            or any(not IDENTIFIER.fullmatch(value) for value in values)
        ):
            raise ValueError("generated catalog exceeds existing MCP ID/count limits")
    config = {
        "artifactRoot": str(root),
        "scratchRoot": str(scratch),
        "contractsCli": args.contracts_cli,
        "harnessCli": args.harness_cli,
        "artifacts": sorted(records.values(), key=lambda row: row["id"]),
        "schemas": schemas,
        "bundles": bundles,
    }
    if extension_rows:
        config["extensionSchemas"] = extension_rows
    output = json.dumps(config, indent=2, ensure_ascii=True) + "\n"
    if len(output.encode()) > BOOTSTRAP_LIMIT:
        raise ValueError("generated bootstrap exceeds the existing 64 KiB limit")
    mapping = {subject: row["id"] for subject, row in sorted(records.items())}
    print(
        json.dumps(
            {
                "artifact_ids": mapping,
                "bundle_ids": dict(
                    zip(sorted(set(args.domain)), [row["id"] for row in bundles], strict=True)
                ),
            }
        ),
        file=sys.stderr,
    )
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for option in ("package-root", "scratch-root", "contracts-cli", "harness-cli"):
        parser.add_argument("--" + option, required=True)
    parser.add_argument("--domain", action="append", required=True)
    args = parser.parse_args()
    try:
        output = prepare(args)
    except (ContractError, OSError, UnicodeError, ValueError) as error:
        print("bootstrap preparation refused: " + str(error)[:2048], file=sys.stderr)
        return 2
    print(output, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
