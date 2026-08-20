"""Proves ADR-0051 D2/D3's centerpiece claim directly, for the THIRD
generator (`LiveTestDataGenerator`): each deterministic property check
catches the real defect shape it was built for, and passes real, clean,
currently-tracked content unmodified. No LLM call, no I/O -- every case
here is a fixture string.

Unlike feature-content (whose raw generator output required reconstruction
from the assembled `.feature` file), test-data's raw generator output IS
the final Java text -- no assembly step exists for this artifact type -- so
the "clean" fixture below is the real, currently-tracked
`ReqC64bb0f7TestData.java` content, verbatim, not reconstructed.
"""

from __future__ import annotations

from eval_harness.models import PropertyCheckOutcome
from eval_harness.test_data_eval_set import TEST_DATA_EVAL_SET
from eval_harness.test_data_properties import (
    check_class_name_matches,
    check_no_env_binding,
    check_no_long_method,
    check_no_markdown_fence,
    check_no_webdriver_reference,
    run_property_checks,
)

_CONTEXT = next(
    case.context for case in TEST_DATA_EVAL_SET if case.case_id == "login_invalid_credentials_error"
)

#: Verbatim from the real, currently-tracked
#: `output/latest/workspace/src/test/java/com/automation/utils/
#: ReqC64bb0f7TestData.java` -- this platform's own real generated output
#: for a zero-field specification (the honest, real shape every
#: requirement's own specification has today).
_CLEAN_TEST_DATA = (
    "package com.automation.utils;\n\n"
    "import com.automation.base.ConfigReader;\n\n"
    "public final class ReqC64bb0f7TestData {\n\n"
    "    private ReqC64bb0f7TestData() {\n"
    '        throw new UnsupportedOperationException("Utility class");\n'
    "    }\n"
    "}\n"
)


class TestCheckNoEnvBinding:
    def test_passes_the_real_clean_corpus_text(self) -> None:
        result = check_no_env_binding(_CLEAN_TEST_DATA, _CONTEXT)
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_catches_a_config_reader_env_call(self) -> None:
        """Ports the real, always-on `test_data_orchestrator._check_no_env_
        binding` guard -- ADR-0037 D3's SUT-binding boundary."""
        defective = _CLEAN_TEST_DATA.replace(
            "throw new UnsupportedOperationException",
            'String url = ConfigReader.env("baseUrl"); throw new UnsupportedOperationException',
        )
        result = check_no_env_binding(defective, _CONTEXT)
        assert result.outcome == PropertyCheckOutcome.FAILED
        assert "ConfigReader" in result.reason

    def test_catches_an_env_namespaced_literal(self) -> None:
        defective = _CLEAN_TEST_DATA.replace(
            "throw new UnsupportedOperationException",
            'String key = "env.baseUrl"; throw new UnsupportedOperationException',
        )
        result = check_no_env_binding(defective, _CONTEXT)
        assert result.outcome == PropertyCheckOutcome.FAILED
        assert "env." in result.reason

    def test_always_applicable(self) -> None:
        result = check_no_env_binding("", _CONTEXT)
        assert result.outcome != PropertyCheckOutcome.NOT_APPLICABLE


class TestCheckNoMarkdownFence:
    def test_passes_the_real_clean_corpus_text(self) -> None:
        result = check_no_markdown_fence(_CLEAN_TEST_DATA, _CONTEXT)
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_catches_a_markdown_fence(self) -> None:
        """The governed `generate_test_data` v1.0.0 OUTPUT CONTRACT states
        explicitly: 'No markdown code fence... before or after the code'."""
        defective = f"```java\n{_CLEAN_TEST_DATA}```\n"
        result = check_no_markdown_fence(defective, _CONTEXT)
        assert result.outcome == PropertyCheckOutcome.FAILED

    def test_always_applicable(self) -> None:
        result = check_no_markdown_fence("", _CONTEXT)
        assert result.outcome != PropertyCheckOutcome.NOT_APPLICABLE


class TestCheckClassNameMatches:
    def test_passes_the_real_clean_corpus_text(self) -> None:
        result = check_class_name_matches(_CLEAN_TEST_DATA, _CONTEXT)
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_catches_a_renamed_class(self) -> None:
        """The governed prompt's own OUTPUT CONTRACT: 'Use target_class_name
        verbatim as the class name... never renamed.'"""
        defective = _CLEAN_TEST_DATA.replace("ReqC64bb0f7TestData", "LoginTestData")
        result = check_class_name_matches(defective, _CONTEXT)
        assert result.outcome == PropertyCheckOutcome.FAILED
        assert _CONTEXT.class_name in result.reason

    def test_always_applicable(self) -> None:
        result = check_class_name_matches("", _CONTEXT)
        assert result.outcome != PropertyCheckOutcome.NOT_APPLICABLE


class TestCheckNoWebdriverReference:
    def test_passes_the_real_clean_corpus_text(self) -> None:
        result = check_no_webdriver_reference(_CLEAN_TEST_DATA, _CONTEXT)
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_catches_a_webdriver_import(self) -> None:
        """The governed prompt's own OUTPUT CONTRACT: 'never reference
        org.openqa.selenium.WebDriver or any Selenium type' -- a real gap
        CP3's own `direct_webdriver_action` criterion does not cover for
        test-data's package."""
        defective = "import org.openqa.selenium.WebDriver;\n" + _CLEAN_TEST_DATA
        result = check_no_webdriver_reference(defective, _CONTEXT)
        assert result.outcome == PropertyCheckOutcome.FAILED

    def test_always_applicable(self) -> None:
        result = check_no_webdriver_reference("", _CONTEXT)
        assert result.outcome != PropertyCheckOutcome.NOT_APPLICABLE


class TestCheckNoLongMethod:
    def test_passes_the_real_clean_corpus_text(self) -> None:
        """The real clean text has no methods at all (only a constructor,
        excluded from `long_method`'s own scope) -- trivially clean."""
        result = check_no_long_method(_CLEAN_TEST_DATA, _CONTEXT)
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_catches_a_method_exceeding_40_lines(self) -> None:
        """Proves this check CAN fire on real input -- not structurally
        unreachable, mirroring the lesson from feature-content's own
        tagged-Background finding: verify reachability, don't assume it."""
        padding = "\n".join(f"        int line{i} = {i};" for i in range(45))
        defective = (
            "package com.automation.utils;\n\n"
            "import com.automation.base.ConfigReader;\n\n"
            "public final class ReqC64bb0f7TestData {\n\n"
            "    private ReqC64bb0f7TestData() {\n"
            '        throw new UnsupportedOperationException("Utility class");\n'
            "    }\n\n"
            "    public static String username() {\n"
            f"{padding}\n"
            '        return ConfigReader.data("username");\n'
            "    }\n"
            "}\n"
        )
        result = check_no_long_method(defective, _CONTEXT)
        assert result.outcome == PropertyCheckOutcome.FAILED
        assert "username" in result.reason

    def test_always_applicable(self) -> None:
        result = check_no_long_method("not even java", _CONTEXT)
        assert result.outcome != PropertyCheckOutcome.NOT_APPLICABLE


class TestRunPropertyChecks:
    def test_runs_every_check_in_order_against_the_real_clean_corpus_text(self) -> None:
        results = run_property_checks(_CLEAN_TEST_DATA, _CONTEXT)
        assert [result.check_name for result in results] == [
            "no_env_binding",
            "no_markdown_fence",
            "class_name_matches",
            "no_webdriver_reference",
            "no_long_method",
        ]
        assert all(result.outcome == PropertyCheckOutcome.PASSED for result in results)
