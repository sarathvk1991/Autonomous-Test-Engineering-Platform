"""Proves ADR-0051 D2/D3's centerpiece claim directly, for the FIFTH
generator (`LiveUtilityGenerator`): each deterministic property check catches
the real defect shape it guards, and passes real/constructed clean content
unmodified. No LLM call, no I/O -- every case here is a fixture string.

`_CLEAN_CONFIG_READER` is the real, currently-tracked
`test-suite-baseline/src/test/java/com/automation/base/ConfigReader.java`
content, verbatim -- no reconstruction needed, mirroring test-data's own
finding that a Java generator's raw output IS its final text, no assembly
step in between. `_CLEAN_DATE_DISPLAY` is the constructed clean fixture for
the eval set's own third, non-real-tracked case.
"""

from __future__ import annotations

from eval_harness.models import PropertyCheckOutcome
from eval_harness.utility_eval_set import UTILITY_EVAL_SET
from eval_harness.utility_properties import (
    check_class_name_matches,
    check_no_long_method,
    check_no_markdown_fence,
    check_no_selenium_or_basepage_reference,
    check_static_utility_shape,
    run_property_checks,
)


def _context(case_id: str):  # type: ignore[no-untyped-def]
    return next(case.context for case in UTILITY_EVAL_SET if case.case_id == case_id)


_CONFIG_READER_ENV_CONTEXT = _context("config_reader_env")
_CONFIG_READER_DATA_CONTEXT = _context("config_reader_data")
_FRESH_CONTEXT = _context("fresh_date_formatting_utility")

#: Verbatim from the real, currently-tracked
#: `test-suite-baseline/src/test/java/com/automation/base/ConfigReader.java`.
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

#: The constructed clean fixture for the eval set's own third, non-real-
#: tracked case (`derive_utility_class_name` computes `"DateDisplay"`).
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


class TestCheckNoMarkdownFence:
    def test_passes_the_real_clean_corpus_text(self) -> None:
        result = check_no_markdown_fence(_CLEAN_CONFIG_READER, _CONFIG_READER_ENV_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_catches_a_markdown_fence(self) -> None:
        defective = f"```java\n{_CLEAN_CONFIG_READER}```\n"
        result = check_no_markdown_fence(defective, _CONFIG_READER_ENV_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.FAILED
        assert "```" in result.reason

    def test_always_applicable(self) -> None:
        result = check_no_markdown_fence("", _CONFIG_READER_ENV_CONTEXT)
        assert result.outcome != PropertyCheckOutcome.NOT_APPLICABLE


class TestCheckClassNameMatches:
    def test_passes_the_real_clean_corpus_text(self) -> None:
        result = check_class_name_matches(_CLEAN_CONFIG_READER, _CONFIG_READER_ENV_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_passes_the_constructed_clean_fresh_case(self) -> None:
        result = check_class_name_matches(_CLEAN_DATE_DISPLAY, _FRESH_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_catches_a_renamed_class(self) -> None:
        defective = _CLEAN_CONFIG_READER.replace("class ConfigReader", "class ConfigurationReader")
        result = check_class_name_matches(defective, _CONFIG_READER_ENV_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.FAILED
        assert "ConfigReader" in result.reason

    def test_always_applicable(self) -> None:
        result = check_class_name_matches("", _CONFIG_READER_ENV_CONTEXT)
        assert result.outcome != PropertyCheckOutcome.NOT_APPLICABLE


class TestCheckStaticUtilityShape:
    def test_passes_the_real_clean_corpus_text(self) -> None:
        result = check_static_utility_shape(_CLEAN_CONFIG_READER, _CONFIG_READER_ENV_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_passes_the_constructed_clean_fresh_case(self) -> None:
        result = check_static_utility_shape(_CLEAN_DATE_DISPLAY, _FRESH_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_catches_a_non_final_class(self) -> None:
        defective = _CLEAN_CONFIG_READER.replace(
            "public final class ConfigReader", "public class ConfigReader"
        )
        result = check_static_utility_shape(defective, _CONFIG_READER_ENV_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.FAILED
        assert "not declared final" in result.reason

    def test_catches_a_public_no_arg_constructor(self) -> None:
        defective = _CLEAN_CONFIG_READER.replace(
            "private ConfigReader() {\n    }", "public ConfigReader() {\n    }"
        )
        result = check_static_utility_shape(defective, _CONFIG_READER_ENV_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.FAILED
        assert "not private" in result.reason

    def test_catches_a_parameterized_constructor(self) -> None:
        defective = _CLEAN_CONFIG_READER.replace(
            "private ConfigReader() {\n    }",
            "private ConfigReader(String seed) {\n    }",
        )
        result = check_static_utility_shape(defective, _CONFIG_READER_ENV_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.FAILED
        assert "not no-argument" in result.reason

    def test_catches_a_non_static_method(self) -> None:
        defective = _CLEAN_CONFIG_READER.replace(
            "public static String env(String key) {", "public String env(String key) {"
        )
        result = check_static_utility_shape(defective, _CONFIG_READER_ENV_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.FAILED
        assert "non-static" in result.reason
        assert "env" in result.reason

    def test_not_applicable_for_unparseable_java(self) -> None:
        result = check_static_utility_shape("not even java", _CONFIG_READER_ENV_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.NOT_APPLICABLE

    def test_not_applicable_when_no_class_of_that_name_is_declared(self) -> None:
        defective = _CLEAN_CONFIG_READER.replace(
            "class ConfigReader", "class SomeOtherClass"
        ).replace("ConfigReader()", "SomeOtherClass()").replace(
            "ConfigReader.class", "SomeOtherClass.class"
        )
        result = check_static_utility_shape(defective, _CONFIG_READER_ENV_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.NOT_APPLICABLE


class TestCheckNoSeleniumOrBasepageReference:
    def test_passes_the_real_clean_corpus_text(self) -> None:
        result = check_no_selenium_or_basepage_reference(
            _CLEAN_CONFIG_READER, _CONFIG_READER_ENV_CONTEXT
        )
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_passes_the_constructed_clean_fresh_case(self) -> None:
        result = check_no_selenium_or_basepage_reference(_CLEAN_DATE_DISPLAY, _FRESH_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_catches_a_webdriver_reference(self) -> None:
        defective = _CLEAN_CONFIG_READER.replace(
            "import java.util.Properties;",
            "import java.util.Properties;\nimport org.openqa.selenium.WebDriver;",
        )
        result = check_no_selenium_or_basepage_reference(defective, _CONFIG_READER_ENV_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.FAILED
        assert "org.openqa.selenium" in result.reason

    def test_catches_extending_basepage(self) -> None:
        defective = _CLEAN_CONFIG_READER.replace(
            "public final class ConfigReader {",
            "public final class ConfigReader extends BasePage {",
        )
        result = check_no_selenium_or_basepage_reference(defective, _CONFIG_READER_ENV_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.FAILED
        assert "extends BasePage" in result.reason

    def test_always_applicable(self) -> None:
        result = check_no_selenium_or_basepage_reference("", _CONFIG_READER_ENV_CONTEXT)
        assert result.outcome != PropertyCheckOutcome.NOT_APPLICABLE


class TestCheckNoLongMethod:
    def test_passes_the_real_clean_corpus_text(self) -> None:
        result = check_no_long_method(_CLEAN_CONFIG_READER, _CONFIG_READER_ENV_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_catches_a_method_exceeding_the_line_threshold(self) -> None:
        padding_lines = "\n".join(f'        String s{i} = "{i}";' for i in range(45))
        defective = _CLEAN_CONFIG_READER.replace(
            "    public static String env(String key) {\n"
            '        String fullKey = "env." + key;\n',
            "    public static String env(String key) {\n"
            f"{padding_lines}\n"
            '        String fullKey = "env." + key;\n',
        )
        result = check_no_long_method(defective, _CONFIG_READER_ENV_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.FAILED
        assert "env" in result.reason

    def test_always_applicable(self) -> None:
        result = check_no_long_method("not even java", _CONFIG_READER_ENV_CONTEXT)
        assert result.outcome == PropertyCheckOutcome.PASSED


class TestRunPropertyChecks:
    def test_runs_every_check_in_order_against_the_real_clean_corpus_text(self) -> None:
        results = run_property_checks(_CLEAN_CONFIG_READER, _CONFIG_READER_ENV_CONTEXT)
        assert [result.check_name for result in results] == [
            "no_markdown_fence",
            "class_name_matches",
            "static_utility_shape",
            "no_selenium_or_basepage_reference",
            "no_long_method",
        ]
        assert all(result.outcome == PropertyCheckOutcome.PASSED for result in results)

    def test_runs_every_check_in_order_against_the_constructed_clean_fresh_case(self) -> None:
        results = run_property_checks(_CLEAN_DATE_DISPLAY, _FRESH_CONTEXT)
        assert all(result.outcome == PropertyCheckOutcome.PASSED for result in results)
