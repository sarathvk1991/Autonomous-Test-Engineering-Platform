"""End-to-end proof of ADR-0051 D5's first build: `run_step_definition_eval`
against `STEP_DEFINITION_EVAL_SET`, driven by a `StubStepDefinitionGenerator`
seeded with captured/fixture Java text -- no live LLM call anywhere in this
suite (the "live-vs-cached" open question ADR-0051 D2 flagged for CI is
deliberately not resolved here; this proves the eval LOGIC deterministically
on captured artifacts, the lean path the surfacing named).

The scenario mirrors the real history this arc measured
(`[[cap-compile-gap-closed]]`): a clean generator establishes the baseline
(scores-first); a generator standing in for a worse model (reintroducing
the real wrong-import defect) is caught by the regression gate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from automation_engineering.generation.step_definition_generator import (
    StubStepDefinitionGenerator,
)
from eval_harness.baseline_store import EvalBaselineStore, check_regression
from eval_harness.models import PropertyCheckOutcome, RegressionGateOutcome
from eval_harness.runner import run_step_definition_eval
from eval_harness.step_definition_eval_set import STEP_DEFINITION_EVAL_SET
from requirement_intelligence.llm.generation_identity import GenerationIdentity

_IDENTITY_GOOD_MODEL = GenerationIdentity(
    prompt_id="generate_step_definitions",
    prompt_version="1.1.0",
    prompt_sha256="a" * 64,
    provider="gemini",
    model="gemini-3.5-flash",
)

_IDENTITY_WORSE_MODEL = GenerationIdentity(
    prompt_id="generate_step_definitions",
    prompt_version="1.1.0",
    prompt_sha256="a" * 64,
    provider="gemini",
    model="gemini-2.5-flash",
)

#: Clean, correctly-imported, non-fenced, real-page-object-referencing Java
#: for each of the three curated cases -- realistic, not full expected-text
#: comparison (ADR-0051 D2 rejects that as the primary mechanism); this text
#: exists only to drive the property checks, not to be compared against.
_CLEAN_JAVA_BY_STEP_TEXT: dict[str, str] = {
    "the user attempts to login with {string} credentials": (
        "package com.automation.steps;\n\n"
        "import com.automation.base.DriverFactory;\n"
        "import com.automation.pages.LoginPage;\n"
        "import io.cucumber.java.en.When;\n\n"
        "public class LoginSteps {\n"
        "    private LoginPage loginPage;\n\n"
        '    @When("the user attempts to login with {string} credentials")\n'
        "    public void step(String credentials) {\n"
        "        loginPage = loginPage != null ? loginPage : new LoginPage(DriverFactory.get());\n"
        "        loginPage.attemptLogin(credentials);\n"
        "    }\n"
        "}\n"
    ),
    "the system displays an error message indicating invalid credentials": (
        "package com.automation.steps;\n\n"
        "import com.automation.base.DriverFactory;\n"
        "import com.automation.pages.LoginPage;\n"
        "import io.cucumber.java.en.Then;\n\n"
        "public class LoginSteps {\n"
        "    private LoginPage loginPage;\n\n"
        '    @Then("the system displays an error message indicating invalid credentials")\n'
        "    public void step() {\n"
        "        loginPage = loginPage != null ? loginPage : new LoginPage(DriverFactory.get());\n"
        "    }\n"
        "}\n"
    ),
    "the system reaches a ready state": (
        "package com.automation.steps;\n\n"
        "import io.cucumber.java.en.Given;\n\n"
        "public class SystemSteps {\n"
        '    @Given("the system reaches a ready state")\n'
        "    public void step() {}\n"
        "}\n"
    ),
}


def _worse_model_java_by_step_text() -> dict[str, str]:
    """The real defect-1 shape (`[[cap-compile-gap-closed]]`) reintroduced
    into every case that has a Cucumber annotation to corrupt -- standing in
    for a model swap that regresses import-package quality."""
    return {
        text: java.replace("import io.cucumber.java.en.", "import io.cucumber.java.")
        for text, java in _CLEAN_JAVA_BY_STEP_TEXT.items()
    }


@pytest.fixture
def store(tmp_path: Path) -> EvalBaselineStore:
    return EvalBaselineStore(tmp_path / "eval_baselines")


class TestRunStepDefinitionEval:
    def test_scores_the_full_curated_eval_set(self) -> None:
        generator = StubStepDefinitionGenerator(_CLEAN_JAVA_BY_STEP_TEXT)
        score = run_step_definition_eval(generator, identity=_IDENTITY_GOOD_MODEL)

        assert score.generator_id == "step_definition_generation"
        assert score.identity == _IDENTITY_GOOD_MODEL
        assert len(score.case_results) == len(STEP_DEFINITION_EVAL_SET)
        assert generator.call_count == len(STEP_DEFINITION_EVAL_SET)

    def test_a_clean_generator_scores_a_perfect_pass_rate(self) -> None:
        generator = StubStepDefinitionGenerator(_CLEAN_JAVA_BY_STEP_TEXT)
        score = run_step_definition_eval(generator, identity=_IDENTITY_GOOD_MODEL)
        assert score.pass_rate == 1.0

    def test_the_third_orderly_case_exercises_not_applicable_page_object_check(self) -> None:
        """`system_reaches_ready_state` expects no page object -- proves the
        curated set actually exercises the NOT_APPLICABLE path, not just the
        FAILED/PASSED ones."""
        generator = StubStepDefinitionGenerator(_CLEAN_JAVA_BY_STEP_TEXT)
        score = run_step_definition_eval(generator, identity=_IDENTITY_GOOD_MODEL)
        ready_state_case = next(
            case for case in score.case_results if case.case_id == "system_reaches_ready_state"
        )
        page_object_result = next(
            result
            for result in ready_state_case.check_results
            if result.check_name == "no_fabricated_page_object_class"
        )
        assert page_object_result.outcome == PropertyCheckOutcome.NOT_APPLICABLE


class TestScoresFirstBaselineEstablishmentAndRegressionDetection:
    """The full arc: measure the real score, establish it as the baseline,
    then prove a worse model is caught relative to it -- never against an
    absolute bar."""

    def test_the_first_real_measurement_establishes_the_baseline(
        self, store: EvalBaselineStore
    ) -> None:
        generator = StubStepDefinitionGenerator(_CLEAN_JAVA_BY_STEP_TEXT)
        score = run_step_definition_eval(generator, identity=_IDENTITY_GOOD_MODEL)

        gate_result = check_regression(score, store)
        assert gate_result.outcome == RegressionGateOutcome.ESTABLISHED_BASELINE

        store.record_baseline(score.generator_id, score)
        assert store.get_baseline(score.generator_id) is not None
        assert store.get_baseline(score.generator_id).pass_rate == 1.0  # type: ignore[union-attr]

    def test_a_worse_model_swap_is_caught_as_a_regression(self, store: EvalBaselineStore) -> None:
        baseline_generator = StubStepDefinitionGenerator(_CLEAN_JAVA_BY_STEP_TEXT)
        baseline_score = run_step_definition_eval(baseline_generator, identity=_IDENTITY_GOOD_MODEL)
        store.record_baseline(baseline_score.generator_id, baseline_score)

        worse_generator = StubStepDefinitionGenerator(_worse_model_java_by_step_text())
        candidate_score = run_step_definition_eval(worse_generator, identity=_IDENTITY_WORSE_MODEL)

        gate_result = check_regression(candidate_score, store)
        assert gate_result.outcome == RegressionGateOutcome.REGRESSED
        assert candidate_score.pass_rate < baseline_score.pass_rate

    def test_re_running_the_same_good_generator_does_not_regress(
        self, store: EvalBaselineStore
    ) -> None:
        baseline_score = run_step_definition_eval(
            StubStepDefinitionGenerator(_CLEAN_JAVA_BY_STEP_TEXT), identity=_IDENTITY_GOOD_MODEL
        )
        store.record_baseline(baseline_score.generator_id, baseline_score)

        rerun_score = run_step_definition_eval(
            StubStepDefinitionGenerator(_CLEAN_JAVA_BY_STEP_TEXT), identity=_IDENTITY_GOOD_MODEL
        )
        gate_result = check_regression(rerun_score, store)
        assert gate_result.outcome == RegressionGateOutcome.PASSED
