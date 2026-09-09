"""Type-check this consumer against installed wheels, outside the source checkout."""

from typing import assert_type

from robotics_acceptance_harness.sdk import (
    AssertionEvaluation,
    EvaluationContext,
    ProductEvaluator,
)

from recording_evaluator import evaluate

evaluator: ProductEvaluator = evaluate


def consume(context: EvaluationContext) -> tuple[AssertionEvaluation, ...]:
    results = evaluate(context)
    assert_type(results, tuple[AssertionEvaluation, ...])
    for result in results:
        assert_type(result, AssertionEvaluation)
    return results
