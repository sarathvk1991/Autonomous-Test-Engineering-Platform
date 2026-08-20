"""End-to-end proof of ADR-0051 D5's second-generator build:
`run_feature_content_eval` against `FEATURE_CONTENT_EVAL_SET`, driven by a
`StubFeatureContentGenerator` seeded with reconstructed real Gherkin text --
no live LLM call anywhere in this suite (mirrors `test_eval_harness_
runner.py`'s own deterministic-logic-only scope).

Feature-content has no known historical regression to replay (unlike
step-def's real, measured 76%-defective `gemini-2.5-flash` corpus) -- the
"worse model" stand-in here reintroduces a stray `@REQ-*` tag into every
case: the single most explicitly, unconditionally forbidden defect shape in
the governed `generate_feature` v1.1.0 prompt's own contract ("never write a
@REQ-* tag yourself, anywhere, under any circumstance"), standing in for a
model swap that stops honoring that contract.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from eval_harness.baseline_store import EvalBaselineStore, check_regression
from eval_harness.feature_content_eval_set import FEATURE_CONTENT_EVAL_SET
from eval_harness.feature_content_runner import run_feature_content_eval
from eval_harness.models import PropertyCheckOutcome, RegressionGateOutcome
from feature_engineering.generation.content_generator import StubFeatureContentGenerator
from requirement_intelligence.llm.generation_identity import GenerationIdentity

_IDENTITY_GOOD_MODEL = GenerationIdentity(
    prompt_id="generate_feature",
    prompt_version="1.1.0",
    prompt_sha256="a" * 64,
    provider="gemini",
    model="gemini-3.5-flash",
)

_IDENTITY_WORSE_MODEL = GenerationIdentity(
    prompt_id="generate_feature",
    prompt_version="1.1.0",
    prompt_sha256="a" * 64,
    provider="gemini",
    model="gemini-2.5-flash",
)

#: Reconstructed, real, clean raw generator output for all three curated
#: cases (see `test_eval_harness_feature_content_properties.py`'s own
#: module docstring for how these were derived from the real, live-
#: regenerated assembled `.feature` corpus).
_CLEAN_CONTENT_BY_REQUIREMENT_ID: dict[str, str] = {
    "REQ-c64bb0f7": (
        "@AC-c64bb0f7-01 @SCN-PENDING @login @regression\n"
        "Scenario Outline: Display error message for invalid login attempts\n"
        "  Given the user is on the login page\n"
        '  When the user attempts to login with "<username>" and "<password>"\n'
        "  Then the system displays an error message indicating invalid credentials\n"
        "  Examples:\n"
        "    | username | password |\n"
        "    | invalid_user | invalid_password |\n"
        "    | empty_username | valid_password |\n"
        "    | valid_username | empty_password |\n"
    ),
    "REQ-f90f23fa": (
        "@AC-f90f23fa-01 @SCN-PENDING @smoke\n"
        "Scenario: Successful user authentication redirects to inventory page\n"
        "  Given the user is on the login page\n"
        "  When the user authenticates with valid credentials\n"
        "  Then the inventory page should be displayed\n"
    ),
    "REQ-92502735": (
        "@AC-92502735-01 @SCN-PENDING @regression @session\n"
        "Scenario Outline: User session invalidation upon timeout\n"
        "  Given the user is logged into the application\n"
        "  And the user session has been inactive for the duration of the timeout period\n"
        "  When the user attempts to perform an action\n"
        "  Then the system should invalidate the user session\n"
        "  And the user should be redirected to the login page\n"
        "  Examples:\n"
        "    | action_type |\n"
        "    | navigation |\n"
        "    | data_submit |\n"
    ),
}


def _worse_model_content_by_requirement_id() -> dict[str, str]:
    """Reintroduces a stray `@REQ-*` tag into every case -- standing in for
    a model swap that regresses tag-contract quality."""
    return {
        req_id: f"@{req_id} " + text
        for req_id, text in _CLEAN_CONTENT_BY_REQUIREMENT_ID.items()
    }


@pytest.fixture
def store(tmp_path: Path) -> EvalBaselineStore:
    return EvalBaselineStore(tmp_path / "eval_baselines")


class TestRunFeatureContentEval:
    def test_scores_the_full_curated_eval_set(self) -> None:
        generator = StubFeatureContentGenerator(_CLEAN_CONTENT_BY_REQUIREMENT_ID)
        score = run_feature_content_eval(generator, identity=_IDENTITY_GOOD_MODEL)

        assert score.generator_id == "feature_content_generation"
        assert score.identity == _IDENTITY_GOOD_MODEL
        assert len(score.case_results) == len(FEATURE_CONTENT_EVAL_SET)

    def test_a_clean_generator_scores_a_perfect_pass_rate(self) -> None:
        generator = StubFeatureContentGenerator(_CLEAN_CONTENT_BY_REQUIREMENT_ID)
        score = run_feature_content_eval(generator, identity=_IDENTITY_GOOD_MODEL)
        assert score.pass_rate == 1.0

    def test_every_check_is_applicable_for_every_real_curated_case(self) -> None:
        """Every real requirement in this corpus carries exactly one AC and
        at least one scenario -- proves the curated set actually exercises
        every check's PASSED path, not silently degrading to
        NOT_APPLICABLE everywhere."""
        generator = StubFeatureContentGenerator(_CLEAN_CONTENT_BY_REQUIREMENT_ID)
        score = run_feature_content_eval(generator, identity=_IDENTITY_GOOD_MODEL)
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
        generator = StubFeatureContentGenerator(_CLEAN_CONTENT_BY_REQUIREMENT_ID)
        score = run_feature_content_eval(generator, identity=_IDENTITY_GOOD_MODEL)

        gate_result = check_regression(score, store)
        assert gate_result.outcome == RegressionGateOutcome.ESTABLISHED_BASELINE

        store.record_baseline(score.generator_id, score)
        assert store.get_baseline(score.generator_id) is not None
        assert store.get_baseline(score.generator_id).pass_rate == 1.0  # type: ignore[union-attr]

    def test_a_worse_model_swap_is_caught_as_a_regression(self, store: EvalBaselineStore) -> None:
        baseline_generator = StubFeatureContentGenerator(_CLEAN_CONTENT_BY_REQUIREMENT_ID)
        baseline_score = run_feature_content_eval(baseline_generator, identity=_IDENTITY_GOOD_MODEL)
        store.record_baseline(baseline_score.generator_id, baseline_score)

        worse_generator = StubFeatureContentGenerator(_worse_model_content_by_requirement_id())
        candidate_score = run_feature_content_eval(worse_generator, identity=_IDENTITY_WORSE_MODEL)

        gate_result = check_regression(candidate_score, store)
        assert gate_result.outcome == RegressionGateOutcome.REGRESSED
        assert candidate_score.pass_rate < baseline_score.pass_rate

    def test_re_running_the_same_good_generator_does_not_regress(
        self, store: EvalBaselineStore
    ) -> None:
        baseline_score = run_feature_content_eval(
            StubFeatureContentGenerator(_CLEAN_CONTENT_BY_REQUIREMENT_ID),
            identity=_IDENTITY_GOOD_MODEL,
        )
        store.record_baseline(baseline_score.generator_id, baseline_score)

        rerun_score = run_feature_content_eval(
            StubFeatureContentGenerator(_CLEAN_CONTENT_BY_REQUIREMENT_ID),
            identity=_IDENTITY_GOOD_MODEL,
        )
        gate_result = check_regression(rerun_score, store)
        assert gate_result.outcome == RegressionGateOutcome.PASSED
