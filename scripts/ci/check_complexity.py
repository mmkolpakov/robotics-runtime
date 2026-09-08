"""Reject new Ruff complexity violations or increases to reviewed function budgets."""

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "quality" / "complexity-budgets.json"
RULES = "C901,PLR0913"


def function_names(source: str) -> dict[int, str]:
    names: dict[int, str] = {}

    def visit(node: ast.AST, parents: tuple[str, ...]) -> None:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            parents = (*parents, node.name)
            if not isinstance(node, ast.ClassDef):
                names[node.lineno] = ".".join(parents)
        for child in ast.iter_child_nodes(node):
            visit(child, parents)

    visit(ast.parse(source), ())
    return names


def measure(root: Path, paths: list[str]) -> dict[str, int]:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            *paths,
            "--select",
            RULES,
            "--output-format",
            "json",
            "--no-cache",
        ],
        cwd=root,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(f"Ruff failed: {result.stderr}")
    symbols: dict[Path, dict[int, str]] = {}
    budgets: dict[str, int] = {}
    for item in json.loads(result.stdout):
        path = Path(item["filename"]).resolve()
        relative = path.relative_to(root.resolve()).as_posix()
        if path not in symbols:
            symbols[path] = function_names(path.read_text(encoding="utf-8"))
        name = symbols[path][item["location"]["row"]]
        value = re.search(r"\((\d+) > \d+\)$", item["message"])
        if value is None or item["code"] not in RULES.split(","):
            raise ValueError(f"Unexpected Ruff diagnostic: {item}")
        key = f"{relative}::{name}::{item['code']}"
        if key in budgets:
            raise ValueError(f"Ambiguous function budget: {key}")
        budgets[key] = int(value.group(1))
    return dict(sorted(budgets.items()))


def violations(actual: dict[str, int], baseline: dict[str, int]) -> list[str]:
    failures = []
    for key, value in actual.items():
        limit = baseline.get(key)
        if limit is None:
            failures.append(f"New violation: {key} = {value}")
        elif value > limit:
            failures.append(f"Budget increased: {key} = {value}, allowed {limit}")
        elif value < limit:
            failures.append(f"Lower stale budget: {key} from {limit} to {value}")
    for key in sorted(set(baseline) - set(actual)):
        failures.append(f"Remove resolved budget: {key}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Write measured values for explicit review; never used by CI",
    )
    args = parser.parse_args()
    actual = measure(ROOT, ["packages"])
    if args.write_baseline:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps(actual, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 0
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    if not isinstance(baseline, dict) or any(
        not isinstance(key, str) or type(value) is not int or value < 1
        for key, value in baseline.items()
    ):
        raise ValueError("Function budgets must map names to positive integers")
    failures = violations(actual, baseline)
    for failure in failures:
        print(failure, file=sys.stderr)
    resolved = len(set(baseline) - set(actual))
    print(
        f"Complexity: {len(actual)} existing violations, {len(failures)} regressions, "
        f"{resolved} resolved budgets to remove."
    )
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
