"""New product artifact roles, including their independently consumable resources."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry
from referencing.jsonschema import DRAFT202012

from robotics_runtime_contracts import (
    ContractValidationError,
    NonFiniteNumberError,
    contract_roles,
    file_sha256,
    load_mapping,
    load_schema,
    resolve_schema_name,
    schema_digest,
    schema_for_role,
    schema_names,
    schema_path,
    schema_resource_names,
    validate_document,
    validate_role,
)
from robotics_runtime_contracts.cli import main

EXAMPLES = Path(__file__).parents[1] / "consumer-examples"
PRODUCT = EXAMPLES / "robot-description"
POLICY = EXAMPLES / "execution-trust-policy/trust-policy.json"
ROBOT = PRODUCT / "sim/robot-description.json"
ROLES = {"execution_trust_policy": POLICY, "robot_description": ROBOT}


def replace_field(document: dict[str, Any], path: tuple[str | int, ...], value: object) -> None:
    target: Any = document
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value


@pytest.mark.parametrize("role", ROLES)
def test_new_role_exports_resolve_offline(tmp_path: Path, role: str) -> None:
    name = schema_for_role(role)
    schema_id = f"urn:robotics-runtime-contracts:v1:{name.removesuffix('.v1')}"
    assert role in contract_roles()
    assert name in schema_names()
    for alias in (name, f"{name}.schema.json", schema_id):
        assert resolve_schema_name(alias) == name
        assert load_schema(alias) == load_schema(name)

    # Consume copied JSON resources with jsonschema/referencing, without the
    # package's validator or registry. Cross-resource primitive refs must work.
    registry: Registry[Any] = Registry()
    for resource_name in schema_resource_names():
        exported = tmp_path / f"{resource_name}.schema.json"
        exported.write_bytes(schema_path(resource_name).read_bytes())
        assert file_sha256(exported) == schema_digest(resource_name)
        resource = json.loads(exported.read_bytes())
        registry = registry.with_resource(resource["$id"], DRAFT202012.create_resource(resource))
    schema = json.loads((tmp_path / f"{name}.schema.json").read_bytes())
    document = load_mapping(ROLES[role])
    Draft202012Validator(
        schema, registry=registry, format_checker=Draft202012Validator.FORMAT_CHECKER
    ).validate(document)
    validate_role(document, role)


@pytest.mark.parametrize("role", ROLES)
def test_existing_cli_validates_and_describes_new_roles(
    role: str, capsys: pytest.CaptureFixture[str]
) -> None:
    name = schema_for_role(role)
    assert main(["validate", str(ROLES[role])]) == 0
    assert capsys.readouterr().out == f"valid: {name}\n"
    assert main(["describe", name]) == 0
    description = json.loads(capsys.readouterr().out)
    assert description["schema"] == name
    assert description["sha256"] == schema_digest(name)


@pytest.mark.parametrize(
    ("path", "value", "error_path"),
    [
        (("max_permit_lifetime_seconds",), 0, "$.max_permit_lifetime_seconds"),
        (("max_permit_lifetime_seconds",), True, "$.max_permit_lifetime_seconds"),
        (("max_permit_lifetime_seconds",), 1.5, "$.max_permit_lifetime_seconds"),
        (("principals",), [], "$.principals"),
        (("principals", 0, "role"), "owner", "$.principals"),
        (("principals", 0, "identity"), "operator with spaces", "$.principals[0].identity"),
        (("principals", 0, "issuer"), "http://issuer.example.org", "$.principals[0].issuer"),
        (("principals", 0, "issuer"), "not-a-uri", "$.principals[0].issuer"),
        (("targets",), [], "$.targets"),
        (("targets", 0, "target_id"), "*", "$.targets[0].target_id"),
        (("targets", 0, "identity_kind"), "serial", "$.targets[0].identity_kind"),
        (("targets", 0, "identity_sha256"), "a" * 63, "$.targets[0].identity_sha256"),
        (("targets", 0, "identity_sha256"), "a" * 64 + "\n", "$.targets[0].identity_sha256"),
        (("targets", 0, "environments"), [], "$.targets[0].environments"),
        (("targets", 0, "environments"), ["simulation"], "$.targets[0].environments[0]"),
        (("targets", 0, "environments"), ["hil", "hil"], "$.targets[0].environments"),
        (("trust_policy_sha256",), "a" * 64, "$"),
        (("hardware_scope",), {}, "$"),
    ],
)
def test_policy_rejects_unusable_allowlist_fields(
    path: tuple[str | int, ...], value: object, error_path: str
) -> None:
    document = load_mapping(POLICY)
    replace_field(document, path, value)
    with pytest.raises(ContractValidationError) as caught:
        validate_document(document)
    assert caught.value.error_id == "schema.validation_failed"
    assert caught.value.json_path == error_path


@pytest.mark.parametrize("lifetime", [1, 1800])
def test_policy_supports_both_physical_environments_and_multiple_principals(lifetime: int) -> None:
    document = load_mapping(POLICY)
    document["max_permit_lifetime_seconds"] = lifetime
    document["targets"][0]["environments"] = ["hil", "real_robot"]
    document["principals"].append(
        {**document["principals"][0], "identity": "second-operator@example.org"}
    )
    validate_document(document)


@pytest.mark.parametrize("field", ["principals", "targets"])
def test_policy_rejects_duplicate_allowlist_entries(field: str) -> None:
    document = load_mapping(POLICY)
    document[field].append(deepcopy(document[field][0]))
    with pytest.raises(ContractValidationError) as caught:
        validate_document(document)
    assert caught.value.json_path == f"$.{field}"


def test_policy_target_identity_is_a_file_byte_digest() -> None:
    document = load_mapping(POLICY)
    identity = POLICY.parent / "target-identity.txt"
    assert identity.read_bytes() == b"EXAMPLE-UNIT-0001\n"
    assert document["targets"][0]["identity_sha256"] == file_sha256(identity)


@pytest.mark.parametrize(
    ("path", "value", "error_path"),
    [
        (("robot_id",), "", "$.robot_id"),
        (("mass_kg",), 0, "$.mass_kg"),
        (("mass_kg",), -1, "$.mass_kg"),
        (("mass_kg",), True, "$.mass_kg"),
        (("center_of_mass_m",), [0, 0], "$.center_of_mass_m"),
        (("center_of_mass_m",), [0, 0, "0"], "$.center_of_mass_m[2]"),
        (("spawn", "pose"), [0, 0, 0], "$.spawn.pose"),
        (("spawn", "pose"), [0, 0, 0, 0, 0, False], "$.spawn.pose[5]"),
        (("spawn", "frame"), "", "$.spawn.frame"),
        (("spawn", "frame"), "world\n", "$.spawn.frame"),
        (("inertia_check", "status"), "unknown", "$.inertia_check.status"),
        (("inertia_check",), True, "$.inertia_check"),
        (("package", "name"), "invalid-name", "$.package.name"),
        (("package", "name"), "unit_description\n", "$.package.name"),
        (("meshes", 0, "sha256"), "A" * 64, "$.meshes[0].sha256"),
        (("meshes", 0, "sha256"), "a" * 64 + "\n", "$.meshes[0].sha256"),
        (("description", "sha256"), "", "$.description.sha256"),
        (("description", "sha256"), "a" * 64 + "\n", "$.description.sha256"),
        (("description", "format"), "xacro", "$.description.format"),
        (("source", "revision"), "main", "$.source.revision"),
        (("source", "sha256"), "a" * 64 + "\n", "$.source.sha256"),
        (("hardware_scope",), {}, "$"),
    ],
)
def test_robot_rejects_invalid_artifact_and_geometry_fields(
    path: tuple[str | int, ...], value: object, error_path: str
) -> None:
    document = load_mapping(ROBOT)
    replace_field(document, path, value)
    with pytest.raises(ContractValidationError) as caught:
        validate_document(document)
    assert caught.value.error_id == "schema.validation_failed"
    assert caught.value.json_path == error_path


@pytest.mark.parametrize(
    "path",
    [
        "",
        "/absolute/body.urdf",
        "../body.urdf",
        "ros/../body.urdf",
        "./body.urdf",
        "ros/./body.urdf",
        "ros//body.urdf",
        "C:/body.urdf",
        r"ros\body.urdf",
        "file:///body.urdf",
        "https://example.org/body.urdf",
        "body.urdf\n",
    ],
)
def test_robot_paths_are_portable_product_relative_paths(path: str) -> None:
    document = load_mapping(ROBOT)
    document["description"]["path"] = path
    with pytest.raises(ContractValidationError) as caught:
        validate_document(document)
    assert caught.value.json_path == "$.description.path"


def test_robot_source_uri_is_an_alternative_to_a_local_path() -> None:
    document = load_mapping(ROBOT)
    source = document["source"]
    source["uri"] = (PRODUCT / source.pop("path")).as_uri()
    validate_document(document)
    source["uri"] = "cad/body.scad"
    with pytest.raises(ContractValidationError) as caught:
        validate_document(document)
    assert caught.value.json_path == "$.source.uri"


@pytest.mark.parametrize("both", [False, True])
def test_robot_source_requires_exactly_one_locator(both: bool) -> None:
    document = load_mapping(ROBOT)
    source = document["source"]
    if both:
        source["uri"] = (PRODUCT / source["path"]).as_uri()
    else:
        del source["path"]
    with pytest.raises(ContractValidationError) as caught:
        validate_document(document)
    assert caught.value.json_path == "$.source"


@pytest.mark.parametrize("status", ["passed", "failed", "not_checked"])
def test_robot_manifest_can_record_an_inertia_check_outcome(status: str) -> None:
    document = load_mapping(PRODUCT / "sim/robot-description-sdf.json")
    document["inertia_check"] = {"status": status}
    assert document["meshes"] == []  # This SDF uses analytic geometry only.
    validate_document(document)


@pytest.mark.parametrize("value", [float("inf"), float("-inf"), float("nan")])
def test_robot_geometry_rejects_non_finite_numbers(value: float) -> None:
    document = load_mapping(ROBOT)
    document["spawn"]["pose"][0] = value
    with pytest.raises(NonFiniteNumberError) as caught:
        validate_document(document)
    assert caught.value.json_path == "$.spawn.pose[0]"


@pytest.mark.parametrize("name", ["robot-description.json", "robot-description-sdf.json"])
def test_robot_examples_bind_real_source_description_and_mesh_bytes(name: str) -> None:
    document = load_mapping(PRODUCT / "sim" / name)
    validate_role(document, "robot_description")
    artifacts = [document["source"], document["description"], *document["meshes"]]
    for artifact in artifacts:
        assert artifact["sha256"] == file_sha256(PRODUCT / artifact["path"])
    package = ElementTree.parse(PRODUCT / document["package"]["path"] / "package.xml")
    assert package.findtext("name") == document["package"]["name"]
    description = ElementTree.parse(PRODUCT / document["description"]["path"])
    expected_tag = {"urdf": "robot", "sdf": "sdf"}[document["description"]["format"]]
    assert description.getroot().tag == expected_tag


def test_example_urdf_mass_geometry_and_inertia_agree_with_manifest() -> None:
    document = load_mapping(ROBOT)
    robot = ElementTree.parse(PRODUCT / document["description"]["path"])
    mass = robot.find("link/inertial/mass")
    inertia = robot.find("link/inertial/inertia")
    origin = robot.find("link/inertial/origin")
    box = robot.find("link/collision/geometry/box")
    mesh = robot.find("link/visual/geometry/mesh")
    assert mass is not None and inertia is not None and origin is not None
    assert box is not None and mesh is not None
    assert float(mass.attrib["value"]) == document["mass_kg"]
    assert list(map(float, origin.attrib["xyz"].split())) == document["center_of_mass_m"]
    assert list(map(float, box.attrib["size"].split())) == [0.1, 0.1, 0.1]
    for axis in ("ixx", "iyy", "izz"):
        assert float(inertia.attrib[axis]) == pytest.approx(document["mass_kg"] * 0.1**2 / 6)
    assert [float(inertia.attrib[axis]) for axis in ("ixy", "ixz", "iyz")] == [0, 0, 0]
    assert mesh.attrib["filename"] == "package://unit_description/meshes/body.obj"


def test_example_mesh_bounds_use_metres() -> None:
    document = load_mapping(ROBOT)
    lines = (PRODUCT / document["meshes"][0]["path"]).read_text(encoding="utf-8").splitlines()
    vertices = [tuple(map(float, line.split()[1:])) for line in lines if line.startswith("v ")]
    assert len(vertices) == 8
    assert set(vertices) == {
        (x, y, z) for x in (-0.05, 0.05) for y in (-0.05, 0.05) for z in (-0.05, 0.05)
    }


def test_example_sdf_has_the_recorded_mass_and_analytic_geometry() -> None:
    document = load_mapping(PRODUCT / "sim/robot-description-sdf.json")
    sdf = ElementTree.parse(PRODUCT / document["description"]["path"])
    assert float(sdf.findtext("model/link/inertial/mass", "0")) == document["mass_kg"]
    assert sdf.findtext("model/link/visual/geometry/box/size") == "0.1 0.1 0.1"
    assert sdf.findtext("model/link/collision/geometry/box/size") == "0.1 0.1 0.1"
    assert sdf.findall(".//mesh") == []
    assert document["meshes"] == []
