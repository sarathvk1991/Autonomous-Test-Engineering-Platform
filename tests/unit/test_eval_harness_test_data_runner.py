"""End-to-end proof of ADR-0051 D5's third-generator build:
`run_test_data_eval` against `TEST_DATA_EVAL_SET`, driven by a
`StubTestDataGenerator` seeded with the real, currently-tracked test-data
Java text -- no live LLM call anywhere in this suite.

Test-data has no known historical regression to replay (like feature-
content, unlike step-def's real, measured 76%-defective `gemini-2.5-flash`
corpus) -- the "worse model" stand-in reintroduces a `ConfigReader.env(...)`
call into every case: the real, always-on orchestration guard's own
SUT-binding-boundary violation, standing in for a model swap that stops
honoring that boundary.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from automation_engineering.generation.test_data_generator import StubTestDataGenerator
from eval_harness.baseline_store import EvalBaselineStore, check_regression
from eval_harness.models import PropertyCheckOutcome, RegressionGateOutcome
from eval_harness.test_data_eval_set import TEST_DATA_EVAL_SET
from eval_harness.test_data_runner import run_test_data_eval
from requirement_intelligence.llm.generation_identity import GenerationIdentity

_IDENTITY_GOOD_MODEL = GenerationIdentity(
    prompt_id="generate_test_data",
    prompt_version="1.0.0",
    prompt_sha256="a" * 64,
    provider="gemini",
    model="gemini-3.5-flash",
)

_IDENTITY_WORSE_MODEL = GenerationIdentity(
    prompt_id="generate_test_data",
    prompt_version="1.0.0",
    prompt_sha256="a" * 64,
    provider="gemini",
    model="gemini-2.5-flash",
)

#: Verbatim from the real, currently-tracked test-data corpus
#: (`output/latest/workspace/src/test/java/com/automation/utils/*.java`) --
#: every real requirement's own zero-field specification produces this
#: exact shape, class name substituted per case.
_CLASS_NAMES_BY_REQUIREMENT_ID: dict[str, str] = {
    "REQ-c64bb0f7": "ReqC64bb0f7TestData",
    "REQ-f90f23fa": "ReqF90f23faTestData",
    "REQ-92502735": "Req92502735TestData",
}


def _clean_java(class_name: str) -> str:
    return (
        "package com.automation.utils;\n\n"
        "import com.automation.base.ConfigReader;\n\n"
        f"public final class {class_name} {{\n\n"
        f"    private {class_name}() {{\n"
        '        throw new UnsupportedOperationException("Utility class");\n'
        "    }\n"
        "}\n"
    )


_CLEAN_JAVA_BY_REQUIREMENT_ID: dict[str, str] = {
    req_id: _clean_java(class_name) for req_id, class_name in _CLASS_NAMES_BY_REQUIREMENT_ID.items()
}


def _worse_model_java_by_requirement_id() -> dict[str, str]:
    """Reintroduces a `ConfigReader.env(...)` call into every case --
    standing in for a model swap that regresses SUT-binding-boundary
    quality."""
    return {
        req_id: java.replace(
            "throw new UnsupportedOperationException",
            'String url = ConfigReader.env("baseUrl"); '
            "throw new UnsupportedOperationException",
        )
        for req_id, java in _CLEAN_JAVA_BY_REQUIREMENT_ID.items()
    }


@pytest.fixture
def store(tmp_path: Path) -> EvalBaselineStore:
    return EvalBaselineStore(tmp_path / "eval_baselines")


class TestRunTestDataEval:
    def test_scores_the_full_curated_eval_set(self) -> None:
        generator = StubTestDataGenerator(_CLEAN_JAVA_BY_REQUIREMENT_ID)
        score = run_test_data_eval(generator, identity=_IDENTITY_GOOD_MODEL)

        assert score.generator_id == "test_data_generation"
        assert score.identity == _IDENTITY_GOOD_MODEL
        assert len(score.case_results) == len(TEST_DATA_EVAL_SET)

    def test_a_clean_generator_scores_a_perfect_pass_rate(self) -> None:
        generator = StubTestDataGenerator(_CLEAN_JAVA_BY_REQUIREMENT_ID)
        score = run_test_data_eval(generator, identity=_IDENTITY_GOOD_MODEL)
        assert score.pass_rate == 1.0

    def test_every_check_is_applicable_for_every_real_curated_case(self) -> None:
        generator = StubTestDataGenerator(_CLEAN_JAVA_BY_REQUIREMENT_ID)
        score = run_test_data_eval(generator, identity=_IDENTITY_GOOD_MODEL)
        outcomes = {
            result.outcome for case in score.case_results for result in case.check_results
        }
        assert outcomes == {PropertyCheckOutcome.PASSED}


class TestScoresFirstBaselineEstablishmentAndRegressionDetection:
    """The full arc: measure the real score, establish it as the baseline,
    then prove a worse model is caught relative to it -- never against an
    absolute bar."""

    def test_the_first_real_measurement_establishes_the_baseline(
        self, store: EvalBaselineStore
    ) -> None:
        generator = StubTestDataGenerator(_CLEAN_JAVA_BY_REQUIREMENT_ID)
        score = run_test_data_eval(generator, identity=_IDENTITY_GOOD_MODEL)

        gate_result = check_regression(score, store)
        assert gate_result.outcome == RegressionGateOutcome.ESTABLISHED_BASELINE

        store.record_baseline(score.generator_id, score)
        assert store.get_baseline(score.generator_id) is not None
        assert store.get_baseline(score.generator_id).pass_rate == 1.0  # type: ignore[union-attr]

    def test_a_worse_model_swap_is_caught_as_a_regression(self, store: EvalBaselineStore) -> None:
        baseline_generator = StubTestDataGenerator(_CLEAN_JAVA_BY_REQUIREMENT_ID)
        baseline_score = run_test_data_eval(baseline_generator, identity=_IDENTITY_GOOD_MODEL)
        store.record_baseline(baseline_score.generator_id, baseline_score)

        worse_generator = StubTestDataGenerator(_worse_model_java_by_requirement_id())
        candidate_score = run_test_data_eval(worse_generator, identity=_IDENTITY_WORSE_MODEL)

        gate_result = check_regression(candidate_score, store)
        assert gate_result.outcome == RegressionGateOutcome.REGRESSED
        assert candidate_score.pass_rate < baseline_score.pass_rate

    def test_re_running_the_same_good_generator_does_not_regress(
        self, store: EvalBaselineStore
    ) -> None:
        baseline_score = run_test_data_eval(
            StubTestDataGenerator(_CLEAN_JAVA_BY_REQUIREMENT_ID), identity=_IDENTITY_GOOD_MODEL
        )
        store.record_baseline(baseline_score.generator_id, baseline_score)

        rerun_score = run_test_data_eval(
            StubTestDataGenerator(_CLEAN_JAVA_BY_REQUIREMENT_ID), identity=_IDENTITY_GOOD_MODEL
        )
        gate_result = check_regression(rerun_score, store)
        assert gate_result.outcome == RegressionGateOutcome.PASSED
