import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parents[2] / "scripts" / "ci" / "check_complexity.py"
SPEC = importlib.util.spec_from_file_location("check_complexity", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def test_budget_tracks_function_after_line_changes_and_rejects_growth(tmp_path: Path) -> None:
    source = "def calculate(x):\n" + "".join(
        f"    if x == {value}:\n        x += 1\n" for value in range(11)
    )
    path = tmp_path / "sample.py"
    path.write_text(source, encoding="utf-8")
    baseline = gate.measure(tmp_path, ["sample.py"])
    assert baseline == {"sample.py::calculate::C901": 12}
    path.write_text("\n\n" + source, encoding="utf-8")
    assert gate.violations(gate.measure(tmp_path, ["sample.py"]), baseline) == []
    path.write_text(source + "    if x < 0:\n        x = 0\n", encoding="utf-8")
    assert gate.violations(gate.measure(tmp_path, ["sample.py"]), baseline) == [
        "Budget increased: sample.py::calculate::C901 = 13, allowed 12"
    ]


def test_new_function_cannot_reuse_another_functions_budget(tmp_path: Path) -> None:
    (tmp_path / "sample.py").write_text(
        "def original(a, b, c, d, e, f):\n    pass\ndef added(a, b, c, d, e, f):\n    pass\n",
        encoding="utf-8",
    )
    baseline = {"sample.py::original::PLR0913": 6}
    assert gate.violations(gate.measure(tmp_path, ["sample.py"]), baseline) == [
        "New violation: sample.py::added::PLR0913 = 6"
    ]


def test_reduced_or_resolved_budget_cannot_allow_regrowth(tmp_path: Path) -> None:
    path = tmp_path / "sample.py"

    def measure(branches: int) -> dict[str, int]:
        path.write_text(
            "def calculate(x):\n"
            + "".join(f"    if x == {value}:\n        x += 1\n" for value in range(branches)),
            encoding="utf-8",
        )
        return gate.measure(tmp_path, ["sample.py"])

    original = measure(11)
    improved = measure(10)
    key = "sample.py::calculate::C901"
    assert gate.violations(improved, original) == [f"Lower stale budget: {key} from 12 to 11"]
    assert gate.violations(original, improved) == [f"Budget increased: {key} = 12, allowed 11"]
    resolved = measure(9)
    assert resolved == {}
    assert gate.violations(resolved, improved) == [f"Remove resolved budget: {key}"]
    assert gate.violations(original, resolved) == [f"New violation: {key} = 12"]
