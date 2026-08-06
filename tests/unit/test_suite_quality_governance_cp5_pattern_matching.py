"""Proves `suite_quality_governance.cp5.pattern_matching.pattern_matches_text`
reproduces Cucumber-JVM's own literal step-binding rule, deterministically,
for all three pattern shapes `automation_engineering.catalog.alignment.
parse_captures` already classifies (ADR-0046 D2)."""

from __future__ import annotations

from suite_quality_governance.cp5.pattern_matching import pattern_matches_text


class TestCucumberExpressionPatterns:
    def test_string_placeholder_matches_quoted_text(self) -> None:
        assert pattern_matches_text('user submits {string}', 'user submits "validpass"') is True

    def test_string_placeholder_rejects_unquoted_text(self) -> None:
        assert pattern_matches_text('user submits {string}', "user submits validpass") is False

    def test_int_placeholder_matches_digits(self) -> None:
        assert pattern_matches_text("user waits {int} seconds", "user waits 5 seconds") is True

    def test_int_placeholder_rejects_non_digits(self) -> None:
        assert (
            pattern_matches_text("user waits {int} seconds", "user waits five seconds") is False
        )

    def test_multiple_placeholders_all_must_fit(self) -> None:
        pattern = "user enters {string} and {string}"
        assert pattern_matches_text(pattern, 'user enters "alice" and "bob"') is True

    def test_wrong_capture_count_does_not_match(self) -> None:
        pattern = "user enters {string} and {string}"
        assert pattern_matches_text(pattern, 'user enters "alice"') is False

    def test_literal_segments_around_placeholders_are_escaped(self) -> None:
        # A literal '.' beside a placeholder must be matched literally, not
        # as "any character" -- proves the surrounding text is re.escape'd.
        pattern = "user waits {int}. seconds"
        assert pattern_matches_text(pattern, "user waits 5. seconds") is True
        assert pattern_matches_text(pattern, "user waits 5X seconds") is False

    def test_unrecognized_placeholder_type_is_permissive(self) -> None:
        # A custom Cucumber Expression type has no known shape -- falls back
        # to a permissive non-empty-token match, never a hard rejection.
        assert pattern_matches_text("user selects {color}", "user selects red") is True


class TestRegexStylePatterns:
    def test_anchored_regex_matches_full_text(self) -> None:
        assert pattern_matches_text("^user logs in as (.*)$", "user logs in as admin") is True

    def test_unanchored_regex_still_requires_full_match(self) -> None:
        # fullmatch requires the ENTIRE text to match, mirroring
        # Cucumber-JVM's own Pattern.matcher(text).matches() semantics.
        assert pattern_matches_text("user logs in as (.*)", "user logs in as admin") is True

    def test_regex_pattern_does_not_match_different_text(self) -> None:
        assert pattern_matches_text("^user logs in as (.*)$", "administrator logs in") is False

    def test_uncompilable_regex_falls_back_to_exact_literal_comparison(self) -> None:
        # An unclosed group is not valid Python regex syntax -- the
        # conservative fallback (module docstring) is exact string equality.
        bad_pattern = "user clicks (button"
        assert pattern_matches_text(bad_pattern, bad_pattern) is True
        assert pattern_matches_text(bad_pattern, "user clicks button") is False


class TestPlainLiteralPatterns:
    def test_exact_text_matches(self) -> None:
        assert pattern_matches_text("user is on the login page", "user is on the login page")

    def test_different_text_does_not_match(self) -> None:
        assert not pattern_matches_text("user is on the login page", "user is on login page")

    def test_case_sensitive(self) -> None:
        assert not pattern_matches_text("User is on the login page", "user is on the login page")
