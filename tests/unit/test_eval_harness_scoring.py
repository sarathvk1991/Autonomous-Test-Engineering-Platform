"""Proves `score_case`/`score_eval_set`'s own arithmetic: NOT_APPLICABLE
results are excluded from the pass-rate denominator, the score is keyed by
`GenerationIdentity`, and `EvalScore`'s own consistency validator rejects a
score whose totals don't match its case_results.
"""

from __future__ import annotations

import pytest

from automation_engineering.generation.step_definition_generator import (
    StepDefinitionGenerationContext,
)
from automation_engineering.reuse.models import GherkinStepNeed
from eval_harness.models import CaseResult, EvalScore, PropertyCheckOutcome, PropertyCheckResult
from eval_harness.scoring import score_case, score_eval_set
from requirement_intelligence.llm.generation_identity import GenerationIdentity

_IDENTITY = GenerationIdentity(
    prompt_id="generate_step_definitions",
    prompt_version="1.1.0",
    prompt_sha256="a" * 64,
    provider="gemini",
    model="gemini-3.5-flash",
)

_CONTEXT_WITH_PAGE_OBJECT = StepDefinitionGenerationContext(
    need=GherkinStepNeed(text="a step needing a page object", step_type="When"),
    target_package="com.automation.steps",
    customqa_constraints=(),
    page_object_interface="com.automation.pages.LoginPage",
)

_CONTEXT_WITHOUT_PAGE_OBJECT = StepDefinitionGenerationContext(
    need=GherkinStepNeed(text="a step needing nothing extra", step_type="Given"),
    target_package="com.automation.steps",
    customqa_constraints=(),
    page_object_interface=None,
)


class TestScoreCase:
    def test_runs_the_default_checks_against_one_generated_artifact(self) -> None:
        clean_text = (
            "package com.automation.steps;\n\n"
            "import com.automation.pages.LoginPage;\n"
            "import io.cucumber.java.en.When;\n\n"
            "public class Steps {\n"
            '    @When("a step needing a page object")\n'
            "    public void step() { LoginPage page = new LoginPage(null); }\n"
            "}\n"
        )
        result = score_case("case-1", clean_text, _CONTEXT_WITH_PAGE_OBJECT)
        assert result.case_id == "case-1"
        assert result.passed is True

    def test_a_failing_check_makes_the_case_fail(self) -> None:
        defective_text = "no cucumber annotation, no page object reference at all"
        result = score_case("case-1", defective_text, _CONTEXT_WITH_PAGE_OBJECT)
        assert result.passed is False


class TestScoreEvalSet:
    def _case(self, case_id: str, *outcomes: PropertyCheckOutcome) -> CaseResult:
        return CaseResult(
            case_id=case_id,
            check_results=tuple(
                PropertyCheckResult(check_name=f"check_{i}", outcome=outcome)
                for i, outcome in enumerate(outcomes)
            ),
        )

    def test_pass_rate_excludes_not_applicable_results(self) -> None:
        case_results = [
            self._case(
                "case-1",
                PropertyCheckOutcome.PASSED,
                PropertyCheckOutcome.NOT_APPLICABLE,
            ),
            self._case(
                "case-2",
                PropertyCheckOutcome.FAILED,
                PropertyCheckOutcome.NOT_APPLICABLE,
            ),
        ]
        score = score_eval_set(
            case_results,
            generator_id="step_definition_generation",
            eval_set_version="1.0.0",
            identity=_IDENTITY,
        )
        # 2 applicable checks total (the two NOT_APPLICABLE ones excluded), 1 passed.
        assert score.total_checks_applicable == 2
        assert score.total_checks_passed == 1
        assert score.pass_rate == pytest.approx(0.5)

    def test_score_is_keyed_by_generator_id_and_identity(self) -> None:
        case_results = [self._case("case-1", PropertyCheckOutcome.PASSED)]
        score = score_eval_set(
            case_results,
            generator_id="step_definition_generation",
            eval_set_version="1.0.0",
            identity=_IDENTITY,
        )
        assert score.generator_id == "step_definition_generation"
        assert score.identity == _IDENTITY

    def test_all_not_applicable_scores_a_vacuous_pass_rate_of_one(self) -> None:
        case_results = [self._case("case-1", PropertyCheckOutcome.NOT_APPLICABLE)]
        score = score_eval_set(
            case_results,
            generator_id="step_definition_generation",
            eval_set_version="1.0.0",
            identity=_IDENTITY,
        )
        assert score.total_checks_applicable == 0
        assert score.pass_rate == 1.0

    def test_a_score_with_inconsistent_totals_is_rejected(self) -> None:
        case_results = (self._case("case-1", PropertyCheckOutcome.PASSED),)
        with pytest.raises(ValueError, match="total_checks_applicable"):
            EvalScore(
                generator_id="step_definition_generation",
                eval_set_version="1.0.0",
                identity=_IDENTITY,
                case_results=case_results,
                total_checks_applicable=99,
                total_checks_passed=1,
                pass_rate=1.0,
            )
