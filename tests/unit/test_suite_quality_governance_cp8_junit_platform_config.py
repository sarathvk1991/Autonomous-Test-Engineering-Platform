"""Proves CP8's `junit-platform.properties` structural-validity component
(ADR-0047 D7's own third bullet, structural half):
`suite_quality_governance.cp8.junit_platform_config`.

Covers: the real file's own conventions (comments, `key=value`,
backslash line continuation) parsed correctly; presence/well-formedness
failing independently of `cucumber.glue`/`cucumber.plugin` content; and
that this module never inspects the catalog (that is `.glue_resolution`'s
own, separate job).
"""

from __future__ import annotations

from pathlib import Path

from shared.enums.base import ValidationVerdict
from suite_quality_governance.cp8.junit_platform_config import (
    JUNIT_PLATFORM_PROPERTIES_RELATIVE_PATH,
    check_junit_platform_properties_valid,
    parse_java_properties,
)

_REAL_SHAPED_PROPERTIES = """# Cucumber configuration for the JUnit Platform Suite runner.
cucumber.glue=com.automation.steps,com.automation.base

cucumber.filter.tags=not @wip

cucumber.plugin=message:target/cucumber-reports/messages.ndjson,\\
  junit:target/cucumber-reports/cucumber.xml,\\
  html:target/cucumber-reports/report.html,\\
  rerun:target/cucumber-reports/rerun.txt

cucumber.snippet-type=camelcase
"""


class TestParseJavaProperties:
    def test_parses_key_value_pairs_ignoring_comments(self) -> None:
        properties = parse_java_properties(_REAL_SHAPED_PROPERTIES)

        assert properties["cucumber.filter.tags"] == "not @wip"
        assert properties["cucumber.snippet-type"] == "camelcase"

    def test_joins_backslash_continuations_into_one_logical_value(self) -> None:
        properties = parse_java_properties(_REAL_SHAPED_PROPERTIES)

        assert properties["cucumber.plugin"] == (
            "message:target/cucumber-reports/messages.ndjson,"
            "junit:target/cucumber-reports/cucumber.xml,"
            "html:target/cucumber-reports/report.html,"
            "rerun:target/cucumber-reports/rerun.txt"
        )

    def test_a_line_with_no_equals_sign_contributes_no_key(self) -> None:
        properties = parse_java_properties(
            "not.a.property.line\ncucumber.glue=com.automation.steps\n"
        )

        assert properties == {"cucumber.glue": "com.automation.steps"}


class TestFileLevelValidity:
    def test_the_real_shaped_file_passes(self, tmp_path: Path) -> None:
        path = tmp_path / JUNIT_PLATFORM_PROPERTIES_RELATIVE_PATH
        path.parent.mkdir(parents=True)
        path.write_text(_REAL_SHAPED_PROPERTIES, encoding="utf-8")

        result = check_junit_platform_properties_valid(tmp_path)

        assert result.verdict == ValidationVerdict.PASS
        assert result.messages == ()

    def test_missing_file_fails(self, tmp_path: Path) -> None:
        result = check_junit_platform_properties_valid(tmp_path)

        assert result.verdict == ValidationVerdict.FAIL
        assert "no junit-platform.properties found" in result.messages[0]

    def test_missing_cucumber_glue_fails(self, tmp_path: Path) -> None:
        path = tmp_path / JUNIT_PLATFORM_PROPERTIES_RELATIVE_PATH
        path.parent.mkdir(parents=True)
        path.write_text("cucumber.filter.tags=not @wip\n", encoding="utf-8")

        result = check_junit_platform_properties_valid(tmp_path)

        assert result.verdict == ValidationVerdict.FAIL
        assert "cucumber.glue is missing or empty" in result.messages[0]

    def test_empty_cucumber_glue_fails(self, tmp_path: Path) -> None:
        path = tmp_path / JUNIT_PLATFORM_PROPERTIES_RELATIVE_PATH
        path.parent.mkdir(parents=True)
        path.write_text("cucumber.glue=\n", encoding="utf-8")

        result = check_junit_platform_properties_valid(tmp_path)

        assert result.verdict == ValidationVerdict.FAIL

    def test_malformed_plugin_entry_fails_independently_of_valid_glue(self, tmp_path: Path) -> None:
        path = tmp_path / JUNIT_PLATFORM_PROPERTIES_RELATIVE_PATH
        path.parent.mkdir(parents=True)
        path.write_text(
            "cucumber.glue=com.automation.steps\ncucumber.plugin=not-name-colon-path\n",
            encoding="utf-8",
        )

        result = check_junit_platform_properties_valid(tmp_path)

        assert result.verdict == ValidationVerdict.FAIL
        assert "not name:path-shaped" in result.messages[0]

    def test_this_module_never_inspects_the_catalog(self, tmp_path: Path) -> None:
        """Structural half only (module docstring) -- `cucumber.glue`
        naming a package with zero real classes is not this module's
        concern (`.glue_resolution`'s own job); a syntactically valid,
        non-empty glue value always passes here regardless of whether it
        resolves to anything real."""
        path = tmp_path / JUNIT_PLATFORM_PROPERTIES_RELATIVE_PATH
        path.parent.mkdir(parents=True)
        path.write_text("cucumber.glue=com.totally.made.up.package\n", encoding="utf-8")

        result = check_junit_platform_properties_valid(tmp_path)

        assert result.verdict == ValidationVerdict.PASS
