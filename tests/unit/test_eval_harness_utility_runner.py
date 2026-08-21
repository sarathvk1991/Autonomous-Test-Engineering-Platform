"""End-to-end proof of ADR-0051 D5's fifth-generator build: `run_utility_eval`
against `UTILITY_EVAL_SET`, driven by a `StubUtilityGenerator` seeded with
real/constructed clean utility Java text -- no live LLM call anywhere in this
suite.

Utility has NO known real historical defect to replay (unlike step-def/
page-object) -- the "worse model" stand-in below reintroduces a markdown code
fence, the governed `generate_utilities` v1.0.0 prompt's own single most
explicit, unconditionally forbidden defect shape ("No markdown code fence,
no explanation, no commentary before or after the code"), mirroring
feature-content's own identical choice (a stray `@REQ-*` tag, its own most
explicitly forbidden clause) for the same reason: no real incident exists to
replay.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from automation_engineering.generation.utility_generator import StubUtilityGenerator
from eval_harness.baseline_store import EvalBaselineStore, check_regression
from eval_harness.models import PropertyCheckOutcome, RegressionGateOutcome
from eval_harness.utility_eval_set import UTILITY_EVAL_SET
from eval_harness.utility_runner import run_utility_eval
from requirement_intelligence.llm.generation_identity import GenerationIdentity

_IDENTITY_GOOD_MODEL = GenerationIdentity(
    prompt_id="generate_utilities",
    prompt_version="1.0.0",
    prompt_sha256="a" * 64,
    provider="gemini",
    model="gemini-3.5-flash",
)

_IDENTITY_WORSE_MODEL = GenerationIdentity(
    prompt_id="generate_utilities",
    prompt_version="1.0.0",
    prompt_sha256="a" * 64,
    provider="gemini",
    model="gemini-2.5-flash",
)

#: Verbatim from the real, currently-tracked
#: `test-suite-baseline/src/test/java/com/automation/base/ConfigReader.java`
#: -- shared by both `ConfigReader`-seeded cases (`env`/`data`).
_CLEAN_CONFIG_READER = (
    "package com.automation.base;\n\n"
    "import java.io.IOException;\n"
    "import java.io.InputStream;\n"
    "import java.util.Locale;\n"
    "import java.util.Properties;\n\n"
    "public final class ConfigReader {\n\n"
    "    private static final Properties PROPERTIES = load();\n\n"
    "    private ConfigReader() {\n"
    "    }\n\n"
    "    private static Properties load() {\n"
    "        Properties properties = new Properties();\n"
    "        try (InputStream stream =\n"
    "                ConfigReader.class.getClassLoader()"
    '.getResourceAsStream("config.properties")) {\n'
    "            if (stream == null) {\n"
    "                throw new IllegalStateException"
    '("config.properties not found on the classpath");\n'
    "            }\n"
    "            properties.load(stream);\n"
    "        } catch (IOException e) {\n"
    '            throw new IllegalStateException("Failed to load config.properties", e);\n'
    "        }\n"
    "        return properties;\n"
    "    }\n\n"
    "    public static String env(String key) {\n"
    '        String fullKey = "env." + key;\n'
    "        String override = System.getProperty(fullKey);\n"
    "        return override != null ? override : require(fullKey);\n"
    "    }\n\n"
    "    public static String data(String key) {\n"
    '        String envVar = "TEST_DATA_" + key.toUpperCase(Locale.ROOT)'
    ".replace('.', '_').replace('-', '_');\n"
    "        String override = System.getenv(envVar);\n"
    '        return override != null ? override : require("data." + key);\n'
    "    }\n\n"
    "    private static String require(String fullKey) {\n"
    "        String value = PROPERTIES.getProperty(fullKey);\n"
    "        if (value == null) {\n"
    '            throw new IllegalStateException("Missing config key: " + fullKey);\n'
    "        }\n"
    "        return value;\n"
    "    }\n"
    "}\n"
)

#: The constructed clean fixture for the eval set's own third,
#: non-real-tracked case.
_CLEAN_DATE_DISPLAY = (
    "package com.automation.utils;\n\n"
    "public final class DateDisplay {\n\n"
    "    private DateDisplay() {\n"
    "    }\n\n"
    "    public static String formatDate(String rawDate) {\n"
    "        return rawDate.trim();\n"
    "    }\n"
    "}\n"
)

#: Every case's own real `need.text` -> its clean Java source, keyed the way
#: `StubUtilityGenerator` looks generation up.
_CLEAN_JAVA_BY_NEED_TEXT: dict[str, str] = {
    "read an environment/SUT-binding config value by key": _CLEAN_CONFIG_READER,
    "read a test-data value by key": _CLEAN_CONFIG_READER,
    "format a date for display": _CLEAN_DATE_DISPLAY,
}


def _worse_model_java_by_need_text() -> dict[str, str]:
    """Reintroduces the prompt's own single most explicit, unconditionally
    forbidden defect shape (a markdown code fence) into every case -- the
    honest stand-in for a model swap that stops honoring the no-markdown-
    fence contract, since no real historical utility defect exists to
    replay."""
    return {
        need_text: f"```java\n{java}```\n"
        for need_text, java in _CLEAN_JAVA_BY_NEED_TEXT.items()
    }


@pytest.fixture
def store(tmp_path: Path) -> EvalBaselineStore:
    return EvalBaselineStore(tmp_path / "eval_baselines")


class TestRunUtilityEval:
    def test_scores_the_full_curated_eval_set(self) -> None:
        generator = StubUtilityGenerator(_CLEAN_JAVA_BY_NEED_TEXT)
        score = run_utility_eval(generator, identity=_IDENTITY_GOOD_MODEL)

        assert score.generator_id == "utility_generation"
        assert score.identity == _IDENTITY_GOOD_MODEL
        assert len(score.case_results) == len(UTILITY_EVAL_SET)

    def test_a_clean_generator_scores_a_perfect_pass_rate(self) -> None:
        generator = StubUtilityGenerator(_CLEAN_JAVA_BY_NEED_TEXT)
        score = run_utility_eval(generator, identity=_IDENTITY_GOOD_MODEL)
        assert score.pass_rate == 1.0

    def test_every_check_is_applicable_for_every_real_curated_case(self) -> None:
        generator = StubUtilityGenerator(_CLEAN_JAVA_BY_NEED_TEXT)
        score = run_utility_eval(generator, identity=_IDENTITY_GOOD_MODEL)
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
        generator = StubUtilityGenerator(_CLEAN_JAVA_BY_NEED_TEXT)
        score = run_utility_eval(generator, identity=_IDENTITY_GOOD_MODEL)

        gate_result = check_regression(score, store)
        assert gate_result.outcome == RegressionGateOutcome.ESTABLISHED_BASELINE

        store.record_baseline(score.generator_id, score)
        assert store.get_baseline(score.generator_id) is not None
        assert store.get_baseline(score.generator_id).pass_rate == 1.0  # type: ignore[union-attr]

    def test_a_worse_model_swap_is_caught_as_a_regression(self, store: EvalBaselineStore) -> None:
        baseline_generator = StubUtilityGenerator(_CLEAN_JAVA_BY_NEED_TEXT)
        baseline_score = run_utility_eval(baseline_generator, identity=_IDENTITY_GOOD_MODEL)
        store.record_baseline(baseline_score.generator_id, baseline_score)

        worse_generator = StubUtilityGenerator(_worse_model_java_by_need_text())
        candidate_score = run_utility_eval(worse_generator, identity=_IDENTITY_WORSE_MODEL)

        gate_result = check_regression(candidate_score, store)
        assert gate_result.outcome == RegressionGateOutcome.REGRESSED
        assert candidate_score.pass_rate < baseline_score.pass_rate

    def test_re_running_the_same_good_generator_does_not_regress(
        self, store: EvalBaselineStore
    ) -> None:
        baseline_score = run_utility_eval(
            StubUtilityGenerator(_CLEAN_JAVA_BY_NEED_TEXT), identity=_IDENTITY_GOOD_MODEL
        )
        store.record_baseline(baseline_score.generator_id, baseline_score)

        rerun_score = run_utility_eval(
            StubUtilityGenerator(_CLEAN_JAVA_BY_NEED_TEXT), identity=_IDENTITY_GOOD_MODEL
        )
        gate_result = check_regression(rerun_score, store)
        assert gate_result.outcome == RegressionGateOutcome.PASSED
