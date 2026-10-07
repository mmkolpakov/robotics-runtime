"""Bind the one reviewed dataset-v2 break to exact source and refusal witnesses."""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from scripts.schema_compatibility.history import Baseline, extract, git
from scripts.schema_compatibility.structure import ReviewRequired, token


@dataclass(frozen=True)
class DatasetMigration:
    row: dict[str, Any]
    before_raw: bytes
    after_raw: bytes
    published_dataset_name: str = "dataset-manifest.v1"

    def verify(self) -> None:
        old, new = self.row["before"], self.row["after"]
        if (
            set(self.row) != {"role", "before", "after", "reason", "semantic"}
            or self.row["role"] != "dataset_manifest"
            or old["tag"] != "contracts-v0.18.3"
            or old["commit"] != "ecfb0446fddad70e8ab1094694dddacfeb496d53"
            or new["contracts_version"] != "0.19.0"
            or new["harness_version"] != "0.20.0"
            or old["schema_name"] != "dataset-manifest.v1"
            or new["schema_name"] != "dataset-manifest.v2"
            or old["schema_id"] != "urn:robotics-runtime-contracts:v1:dataset-manifest"
            or new["schema_id"] != "urn:robotics-runtime-contracts:v2:dataset-manifest"
            or not self.row["reason"]
        ):
            raise ReviewRequired("Unsupported dataset migration witness")
        for raw, record in ((self.before_raw, old), (self.after_raw, new)):
            if sha256(raw).hexdigest() != record["sha256"]:
                raise ReviewRequired("Dataset migration raw schema SHA256 differs")
            if json.loads(raw)["$id"] != record["schema_id"]:
                raise ReviewRequired("Dataset migration schema $id differs")

    def bind(
        self,
        before: dict[str, Any],
        after: dict[str, Any],
        old_catalog: dict[str, Any],
        new_catalog: dict[str, Any],
    ) -> tuple[str, str] | None:
        self.verify()
        old, new = self.row["before"], self.row["after"]
        old_file, new_file = (
            old["schema_name"] + ".schema.json",
            new["schema_name"] + ".schema.json",
        )
        if self.published_dataset_name == new["schema_name"]:
            if (
                old_catalog["roles"].get("dataset_manifest") != new["schema_name"]
                or new_catalog["roles"].get("dataset_manifest") != new["schema_name"]
                or old_file in before
                or old_file in after
                or token(before.get(new_file)) != token(json.loads(self.after_raw))
                or token(after.get(new_file)) != token(json.loads(self.after_raw))
            ):
                raise ReviewRequired("Applied dataset migration snapshot differs")
            return None
        if (
            old_catalog["roles"].get("dataset_manifest") != old["schema_name"]
            or new_catalog["roles"].get("dataset_manifest") != new["schema_name"]
            or old_file not in before
            or old_file in after
            or new_file not in after
            or token(before[old_file]) != token(json.loads(self.before_raw))
            or token(after[new_file]) != token(json.loads(self.after_raw))
        ):
            raise ReviewRequired("Dataset migration role/resource snapshot differs")
        return old_file, new_file

    def historical_source(self, root: Path, destination: Path) -> Path:
        self.verify()
        old = self.row["before"]
        release = Baseline(old["tag"], old["commit"], "packages/contracts/")
        actual = git(root, "rev-parse", f"refs/tags/{release.tag}^{{commit}}").decode().strip()
        if actual != release.commit:
            raise ReviewRequired("Dataset migration immutable source tag moved")
        return extract(root, release, destination)

    def refusals(self, request: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
        self.verify()
        digest = sha256(token(request).encode()).hexdigest()
        matches = [
            value for value in self.row["semantic"].values() if value["request_sha256"] == digest
        ]
        if len(matches) != 1 or matches[0]["case_count"] != len(request["cases"]):
            raise ReviewRequired("Dataset migration frozen request differs")
        records: dict[str, Any] = matches[0]["refusals"]
        cases = {case["id"]: case for case in request["cases"]}
        if not records or not records.keys() <= cases.keys():
            raise ReviewRequired("Dataset migration refusal inventory differs")
        for name, record in records.items():
            case = cases[name]
            documents = request["documents"]
            references = [case.get("document")] + [
                item.get("document") for item in case.get("artifacts", [])
            ]
            dependent = case.get("role") == "dataset_manifest" or any(
                value in documents
                and documents[value].get("schema_version") == "dataset-manifest.v1"
                for value in references
                if value is not None
            )
            if not dependent:
                raise ReviewRequired(f"Dataset migration cannot acknowledge another role: {name}")
            if sha256(token(expected[name]).encode()).hexdigest() != record["old_outcome_sha256"]:
                raise ReviewRequired(f"Dataset migration historical outcome differs: {name}")
        return records


def dataset_migration(
    root: Path, release: Baseline, published: Path, candidate: Path
) -> DatasetMigration | None:
    old_path = published / "src/robotics_runtime_contracts/schemas"
    new_path = candidate / "src/robotics_runtime_contracts/schemas"
    old_catalog = json.loads((old_path / "catalog.v1.json").read_bytes())
    new_catalog = json.loads((new_path / "catalog.v1.json").read_bytes())
    old_name = old_catalog["roles"].get("dataset_manifest")
    new_name = new_catalog["roles"].get("dataset_manifest")
    if new_name != "dataset-manifest.v2" and old_name == new_name:
        return None
    row = json.loads((Path(__file__).with_name("dataset-v2-migration.json")).read_bytes())
    old, new = row["before"], row["after"]
    if old_name == old["schema_name"]:
        if (release.tag, release.commit) != (old["tag"], old["commit"]):
            raise ReviewRequired("Dataset migration published baseline differs")
        versions = (
            tomllib.loads((candidate / "pyproject.toml").read_text())["project"]["version"],
            tomllib.loads((root / "packages/harness/pyproject.toml").read_text())["project"][
                "version"
            ],
        )
        if versions != (new["contracts_version"], new["harness_version"]):
            raise ReviewRequired("Dataset migration requires contracts0.19.0/harness0.20.0 train")
    elif old_name != new["schema_name"] or (release.tag, release.commit) != (
        "contracts-v0.19.0",
        "6c8bc47d1bc416e1b40cdaebf04983e172e78c21",
    ):
        raise ReviewRequired("Dataset migration published baseline differs")
    original = git(root, "rev-parse", f"refs/tags/{old['tag']}^{{commit}}").decode().strip()
    if original != old["commit"]:
        raise ReviewRequired("Dataset migration immutable source tag moved")
    witness = DatasetMigration(
        row,
        git(
            root,
            "show",
            f"{old['commit']}:packages/contracts/src/robotics_runtime_contracts/schemas/"
            f"{old['schema_name']}.schema.json",
        ),
        (new_path / (new["schema_name"] + ".schema.json")).read_bytes(),
        old_name,
    )
    witness.verify()
    return witness
