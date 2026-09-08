from __future__ import annotations

import json
import random
from copy import deepcopy
from pathlib import Path

import pytest

from robotics_runtime_contracts import ContractError, NonFiniteNumberError, load_mapping
from robotics_runtime_contracts._merge_patch import JSONValue, merge_patch
from robotics_runtime_contracts.cli import main
from robotics_runtime_contracts.document_ops import resolve_merge_patches, semantic_diff
from tests.test_cli import FIXTURE


# RFC 7396 Appendix A, https://www.rfc-editor.org/rfc/rfc7396#appendix-A
@pytest.mark.parametrize(
    ("source", "patch", "expected"),
    [
        ({"a": "b"}, {"a": "c"}, {"a": "c"}),
        ({"a": "b"}, {"b": "c"}, {"a": "b", "b": "c"}),
        ({"a": "b"}, {"a": None}, {}),
        ({"a": "b", "b": "c"}, {"a": None}, {"b": "c"}),
        ({"a": ["b"]}, {"a": "c"}, {"a": "c"}),
        ({"a": "c"}, {"a": ["b"]}, {"a": ["b"]}),
        ({"a": {"b": "c"}}, {"a": {"b": "d", "c": None}}, {"a": {"b": "d"}}),
        ({"a": [{"b": "c"}]}, {"a": [1]}, {"a": [1]}),
        (["a", "b"], ["c", "d"], ["c", "d"]),
        ({"a": "b"}, ["c"], ["c"]),
        ({"a": "foo"}, None, None),
        ({"a": "foo"}, "bar", "bar"),
        ({"e": None}, {"a": 1}, {"e": None, "a": 1}),
        ([1, 2], {"a": "b", "c": None}, {"a": "b"}),
        ({}, {"a": {"bb": {"ccc": None}}}, {"a": {"bb": {}}}),
    ],
)
def test_rfc7396_vectors(source: JSONValue, patch: JSONValue, expected: JSONValue) -> None:
    before_source, before_patch = deepcopy(source), deepcopy(patch)
    result = merge_patch(source, patch)
    assert json.dumps(result, sort_keys=True) == json.dumps(expected, sort_keys=True)
    assert source == before_source
    assert patch == before_patch


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (True, 1),
        (1, True),
        (False, 0),
        (0, False),
        (True, 1.0),
        (1.0, True),
        (1, 1.0),
        (1.0, 1),
        ([True], [1]),
        ([{"x": False}], [{"x": 0}]),
        ({"nested": {"flag": True}}, {"nested": {"flag": 1}}),
    ],
)
def test_diff_preserves_scalar_types_recursively(source: JSONValue, target: JSONValue) -> None:
    patch = semantic_diff({"a": source}, {"a": target})
    assert patch
    actual = merge_patch({"a": source}, patch)
    assert json.dumps(actual, sort_keys=True) == json.dumps({"a": target}, sort_keys=True)


@pytest.mark.parametrize("source", [{}, {"a": None}, {"a": 1}, {"a": []}])
def test_diff_does_not_drop_empty_object_replacements(source: dict[str, JSONValue]) -> None:
    assert semantic_diff(source, {"a": {}}) == {"a": {}}


@pytest.mark.parametrize(
    ("source", "target"),
    [
        ({}, {"a": None}),
        ({"a": 1}, {"a": None}),
        ({}, {"a": {"b": None}}),
        ({"a": []}, {"a": {"b": None}}),
    ],
)
def test_diff_rejects_unrepresentable_new_null_members(
    source: dict[str, JSONValue], target: dict[str, JSONValue]
) -> None:
    with pytest.raises(ContractError, match="null denotes member removal") as caught:
        semantic_diff(source, target)
    assert caught.value.error_id == "diff.unrepresentable"


def test_diff_keeps_existing_null_members_and_null_values_inside_replaced_arrays() -> None:
    assert semantic_diff({"a": None, "b": 1}, {"a": None, "b": 2}) == {"b": 2}
    assert semantic_diff({"a": [1]}, {"a": [None]}) == {"a": [None]}
    assert semantic_diff({"a": None}, {}) == {"a": None}


def test_inputs_and_results_do_not_share_mutable_containers() -> None:
    source: dict[str, JSONValue] = {"keep": {"x": [1]}}
    patch: dict[str, JSONValue] = {"new": {"x": [2]}}
    result = merge_patch(source, patch)
    assert isinstance(result, dict)
    for key in ("keep", "new"):
        nested = result[key]
        assert isinstance(nested, dict)
        values = nested["x"]
        assert isinstance(values, list)
        values.append(3)
    assert source == {"keep": {"x": [1]}}
    assert patch == {"new": {"x": [2]}}

    target: dict[str, JSONValue] = {"a": [1, {"b": 2}]}
    difference = semantic_diff({}, target)
    difference["a"].append(3)
    assert target == {"a": [1, {"b": 2}]}


def _value(rng: random.Random, depth: int = 0) -> JSONValue:
    kind = rng.randrange(3) if depth < 3 else 0
    if kind == 1:
        return [_value(rng, depth + 1) for _ in range(rng.randrange(4))]
    if kind == 2:
        return {str(i): _value(rng, depth + 1) for i in range(rng.randrange(4))}
    scalars: list[JSONValue] = [None, False, True, -1, 0, 1, 1.0, 2.5, "", "1", "x"]
    return rng.choice(scalars)


def _needs_new_null(source: dict[str, JSONValue], target: dict[str, JSONValue]) -> bool:
    # Arrays are replaced whole. Only object members can be unrepresentable.
    for key, value in target.items():
        if value is None and (key not in source or source[key] is not None):
            return True
        if isinstance(value, dict):
            previous = source.get(key)
            if _needs_new_null(previous if isinstance(previous, dict) else {}, value):
                return True
    return False


def test_generated_independent_targets_round_trip_or_report_new_null() -> None:
    rng = random.Random(7396)
    for _ in range(300):
        source = {str(i): _value(rng) for i in range(rng.randrange(4))}
        target = {str(i): _value(rng) for i in range(rng.randrange(4))}
        before_source, before_target = deepcopy(source), deepcopy(target)
        if _needs_new_null(source, target):
            with pytest.raises(ContractError, match="null denotes member removal"):
                semantic_diff(source, target)
        else:
            patch = semantic_diff(source, target)
            assert json.dumps(merge_patch(source, patch), sort_keys=True) == json.dumps(
                target, sort_keys=True
            )
        assert source == before_source and target == before_target


def test_ordered_overlays_validate_and_leave_the_base_unchanged() -> None:
    base = load_mapping(FIXTURE)
    before = deepcopy(base)
    resolved = resolve_merge_patches(base, [{"seed": 43}, {"seed": 44}])
    assert resolved["seed"] == 44
    assert base == before
    with pytest.raises(NonFiniteNumberError):
        resolve_merge_patches(base, [{"seed": float("nan")}, {"seed": 44}])


def test_diff_rejects_nonfinite_python_numbers() -> None:
    with pytest.raises(NonFiniteNumberError):
        semantic_diff({"a": float("nan")}, {"a": 1})
    with pytest.raises(NonFiniteNumberError):
        semantic_diff({"a": 1}, {"a": float("inf")})


def test_cli_diff_emits_bool_to_number_patch(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source, target = tmp_path / "source.json", tmp_path / "target.json"
    source.write_text('{"a": true}', encoding="utf-8")
    target.write_text('{"a": 1}', encoding="utf-8")
    assert main(["diff", str(source), str(target)]) == 0
    captured = capsys.readouterr()
    assert not captured.err
    assert captured.out.strip() != "{}"
    assert type(json.loads(captured.out)["a"]) is int
