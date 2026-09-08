from __future__ import annotations

from copy import deepcopy

type JSONValue = None | bool | int | float | str | list[JSONValue] | dict[str, JSONValue]


def json_equal(left: JSONValue, right: JSONValue) -> bool:
    """Compare JSON trees without Python's bool/int/float equality coercions."""

    if type(left) is not type(right):
        return False
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(
            json_equal(value, right[key]) for key, value in left.items()
        )
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            json_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return left == right


def merge_patch(target: JSONValue, patch: JSONValue) -> JSONValue:
    """Apply RFC 7396 section 2 without modifying or sharing input containers."""

    # https://www.rfc-editor.org/rfc/rfc7396#section-2
    if not isinstance(patch, dict):
        return deepcopy(patch)
    result = deepcopy(target) if isinstance(target, dict) else {}
    for key, value in patch.items():
        if value is None:
            result.pop(key, None)
        else:
            result[key] = merge_patch(result.get(key), value)
    return result


def create_patch(
    source: dict[str, JSONValue], target: dict[str, JSONValue]
) -> dict[str, JSONValue]:
    """Build an object patch; callers must check representability by round-trip."""

    patch: dict[str, JSONValue] = {key: None for key in source if key not in target}
    for key, value in target.items():
        if key in source and json_equal(source[key], value):
            continue
        if isinstance(value, dict):
            previous = source.get(key)
            # Keep even an empty patch when adding an object or replacing a scalar.
            patch[key] = create_patch(previous if isinstance(previous, dict) else {}, value)
        else:
            patch[key] = deepcopy(value)
    return patch
