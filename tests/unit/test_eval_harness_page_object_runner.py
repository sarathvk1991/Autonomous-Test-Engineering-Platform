"""End-to-end proof of ADR-0051 D5's fourth-generator build: `run_page_object_
eval` against `PAGE_OBJECT_EVAL_SET`, driven by a `StubPageObjectGenerator`
seeded with real, currently-tracked-corpus-shaped page-object Java text -- no
live LLM call anywhere in this suite.

Page-object has THREE real, measured historical defects to replay (unlike
feature-content/test-data, which had none) -- the "worse model" stand-in
below reintroduces defect 1's own shape (a paraphrased method name, the
dominant one at 67% of requested calls, `[[cap-page-object-live-regen-
findings]]`) into every case.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from automation_engineering.generation.page_object_generator import StubPageObjectGenerator
from eval_harness.baseline_store import EvalBaselineStore, check_regression
from eval_harness.models import PropertyCheckOutcome, RegressionGateOutcome
from eval_harness.page_object_eval_set import PAGE_OBJECT_EVAL_SET
from eval_harness.page_object_runner import run_page_object_eval
from requirement_intelligence.llm.generation_identity import GenerationIdentity

_IDENTITY_GOOD_MODEL = GenerationIdentity(
    prompt_id="generate_page_objects",
    prompt_version="1.3.0",
    prompt_sha256="a" * 64,
    provider="gemini",
    model="gemini-3.5-flash",
)

_IDENTITY_WORSE_MODEL = GenerationIdentity(
    prompt_id="generate_page_objects",
    prompt_version="1.3.0",
    prompt_sha256="a" * 64,
    provider="gemini",
    model="gemini-2.5-flash",
)

#: Verbatim / directly lifted from the real, currently-tracked
#: `test-suite-baseline/src/test/java/com/automation/pages/LoginPage.java`
#: and `InventoryPage.java`, one entry per curated case's own `need.text`.
_CLEAN_JAVA_BY_NEED_TEXT: dict[str, str] = {
    "attempt login with credentials": (
        "package com.automation.pages;\n\n"
        "import com.automation.base.BasePage;\n"
        "import org.openqa.selenium.By;\n"
        "import org.openqa.selenium.WebDriver;\n"
        "import org.openqa.selenium.support.ui.ExpectedConditions;\n\n"
        "public class LoginPage extends BasePage {\n\n"
        '    private final By usernameField = By.id("username");\n'
        '    private final By passwordField = By.id("password");\n'
        '    private final By loginButton = By.id("login-button");\n\n'
        "    public LoginPage(WebDriver driver) {\n"
        "        super(driver);\n"
        "    }\n\n"
        "    public void attemptLogin(String credentials) {\n"
        "        wait.until(ExpectedConditions.visibilityOfElementLocated(usernameField))"
        ".sendKeys(credentials);\n"
        "        driver.findElement(passwordField).sendKeys(credentials);\n"
        "        driver.findElement(loginButton).click();\n"
        "    }\n"
        "}\n"
    ),
    "the error message is displayed": (
        "package com.automation.pages;\n\n"
        "import com.automation.base.BasePage;\n"
        "import org.openqa.selenium.By;\n"
        "import org.openqa.selenium.WebDriver;\n"
        "import org.openqa.selenium.support.ui.ExpectedConditions;\n\n"
        "public class LoginPage extends BasePage {\n\n"
        '    private final By errorMessage = By.id("error-message");\n\n'
        "    public LoginPage(WebDriver driver) {\n"
        "        super(driver);\n"
        "    }\n\n"
        "    public boolean isErrorMessageDisplayed() {\n"
        "        try {\n"
        "            return wait.until(ExpectedConditions.visibilityOfElementLocated(errorMessage))"
        ".isDisplayed();\n"
        "        } catch (Exception e) {\n"
        "            return false;\n"
        "        }\n"
        "    }\n"
        "}\n"
    ),
    "the inventory is sorted by order": (
        "package com.automation.pages;\n\n"
        "import com.automation.base.BasePage;\n"
        "import org.openqa.selenium.By;\n"
        "import org.openqa.selenium.WebDriver;\n"
        "import org.openqa.selenium.WebElement;\n"
        "import org.openqa.selenium.support.ui.ExpectedConditions;\n"
        "import java.util.List;\n"
        "import java.util.stream.Collectors;\n"
        "import java.util.ArrayList;\n"
        "import java.util.Collections;\n\n"
        "public class InventoryPage extends BasePage {\n\n"
        '    private final By inventoryItemNames = By.className("inventory_item_name");\n\n'
        "    public InventoryPage(WebDriver driver) {\n"
        "        super(driver);\n"
        "    }\n\n"
        "    public boolean isInventorySortedBy(String order) {\n"
        "        List<WebElement> items = "
        "wait.until(ExpectedConditions.presenceOfAllElementsLocatedBy(inventoryItemNames));\n"
        "        List<String> names = items.stream()\n"
        "                .map(WebElement::getText)\n"
        "                .collect(Collectors.toList());\n\n"
        "        List<String> sortedNames = new ArrayList<>(names);\n"
        '        if ("asc".equalsIgnoreCase(order)) {\n'
        "            Collections.sort(sortedNames);\n"
        '        } else if ("desc".equalsIgnoreCase(order)) {\n'
        "            sortedNames.sort(Collections.reverseOrder());\n"
        "        }\n\n"
        "        return names.equals(sortedNames);\n"
        "    }\n"
        "}\n"
    ),
}

#: Every case's own real, requested `method_name` -- the exact name defect
#: 1's regression must rename to be caught.
_METHOD_NAMES_BY_NEED_TEXT: dict[str, str] = {
    "attempt login with credentials": "attemptLogin",
    "the error message is displayed": "isErrorMessageDisplayed",
    "the inventory is sorted by order": "isInventorySortedBy",
}


def _worse_model_java_by_need_text() -> dict[str, str]:
    """Reintroduces defect 1's own real, measured shape (a paraphrased
    method name, 67% of requested calls, `[[cap-page-object-live-regen-
    findings]]`) into every case -- standing in for a model swap that stops
    honoring the caller-supplied `method_name`."""
    return {
        need_text: java.replace(
            _METHOD_NAMES_BY_NEED_TEXT[need_text],
            _METHOD_NAMES_BY_NEED_TEXT[need_text] + "Paraphrased",
        )
        for need_text, java in _CLEAN_JAVA_BY_NEED_TEXT.items()
    }


@pytest.fixture
def store(tmp_path: Path) -> EvalBaselineStore:
    return EvalBaselineStore(tmp_path / "eval_baselines")


class TestRunPageObjectEval:
    def test_scores_the_full_curated_eval_set(self) -> None:
        generator = StubPageObjectGenerator(_CLEAN_JAVA_BY_NEED_TEXT)
        score = run_page_object_eval(generator, identity=_IDENTITY_GOOD_MODEL)

        assert score.generator_id == "page_object_generation"
        assert score.identity == _IDENTITY_GOOD_MODEL
        assert len(score.case_results) == len(PAGE_OBJECT_EVAL_SET)

    def test_a_clean_generator_scores_a_perfect_pass_rate(self) -> None:
        generator = StubPageObjectGenerator(_CLEAN_JAVA_BY_NEED_TEXT)
        score = run_page_object_eval(generator, identity=_IDENTITY_GOOD_MODEL)
        assert score.pass_rate == 1.0

    def test_every_check_is_applicable_for_every_real_curated_case(self) -> None:
        generator = StubPageObjectGenerator(_CLEAN_JAVA_BY_NEED_TEXT)
        score = run_page_object_eval(generator, identity=_IDENTITY_GOOD_MODEL)
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
        generator = StubPageObjectGenerator(_CLEAN_JAVA_BY_NEED_TEXT)
        score = run_page_object_eval(generator, identity=_IDENTITY_GOOD_MODEL)

        gate_result = check_regression(score, store)
        assert gate_result.outcome == RegressionGateOutcome.ESTABLISHED_BASELINE

        store.record_baseline(score.generator_id, score)
        assert store.get_baseline(score.generator_id) is not None
        assert store.get_baseline(score.generator_id).pass_rate == 1.0  # type: ignore[union-attr]

    def test_a_worse_model_swap_is_caught_as_a_regression(self, store: EvalBaselineStore) -> None:
        baseline_generator = StubPageObjectGenerator(_CLEAN_JAVA_BY_NEED_TEXT)
        baseline_score = run_page_object_eval(baseline_generator, identity=_IDENTITY_GOOD_MODEL)
        store.record_baseline(baseline_score.generator_id, baseline_score)

        worse_generator = StubPageObjectGenerator(_worse_model_java_by_need_text())
        candidate_score = run_page_object_eval(worse_generator, identity=_IDENTITY_WORSE_MODEL)

        gate_result = check_regression(candidate_score, store)
        assert gate_result.outcome == RegressionGateOutcome.REGRESSED
        assert candidate_score.pass_rate < baseline_score.pass_rate

    def test_re_running_the_same_good_generator_does_not_regress(
        self, store: EvalBaselineStore
    ) -> None:
        baseline_score = run_page_object_eval(
            StubPageObjectGenerator(_CLEAN_JAVA_BY_NEED_TEXT), identity=_IDENTITY_GOOD_MODEL
        )
        store.record_baseline(baseline_score.generator_id, baseline_score)

        rerun_score = run_page_object_eval(
            StubPageObjectGenerator(_CLEAN_JAVA_BY_NEED_TEXT), identity=_IDENTITY_GOOD_MODEL
        )
        gate_result = check_regression(rerun_score, store)
        assert gate_result.outcome == RegressionGateOutcome.PASSED
