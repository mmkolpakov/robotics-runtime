"""Attach-only acceptance harness for validated robotics executions."""

from importlib.metadata import PackageNotFoundError, version

from robotics_acceptance_harness.errors import HarnessError, HarnessInputError
from robotics_acceptance_harness.evaluation import (
    AssertionEvaluation,
    EvaluationContext,
    ProductEvaluator,
)

try:
    __version__ = version("robotics-acceptance-harness")
except PackageNotFoundError:
    __version__ = "0+unknown"

__all__ = [
    "AssertionEvaluation",
    "EvaluationContext",
    "HarnessError",
    "HarnessInputError",
    "ProductEvaluator",
    "__version__",
]
