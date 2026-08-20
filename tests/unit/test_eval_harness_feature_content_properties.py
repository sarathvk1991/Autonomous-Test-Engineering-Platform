"""Proves ADR-0051 D2/D3's centerpiece claim directly, for the SECOND
generator (`LiveFeatureContentGenerator`): each deterministic property check
catches the real defect shape it was built for, and passes real, clean,
reconstructed content unmodified. No LLM call, no I/O -- every case here is
a fixture string.

The "clean" fixtures below are reconstructed from the REAL, live-regenerated
assembled `.feature` files under `output/executions/run-20260812T064317663150Z-
a20b0cc2/.../features/` (the same corpus `FEATURE_CONTENT_EVAL_SET` curates
its `TestableRequirement` contexts from) -- tags un-hoisted back onto the
scenario, the real minted `@SCN-*` id replaced with the one true
`@SCN-PENDING` placeholder, and the Feature:/comment lines stripped, exactly
undoing what `generate_feature_file`'s own assembly step does. This is the
raw shape `LiveFeatureContentGenerator.generate` itself would have returned.
"""

from __future__ import annotations

from contracts.testable_requirement import TestableRequirement
from eval_harness.feature_content_eval_set import FEATURE_CONTENT_EVAL_SET
from eval_harness.feature_content_properties import (
    check_ac_tag_presence,
    check_no_markdown_fence,
    check_no_req_tag,
    check_no_unknown_ac_tag,
    check_scn_pending_tag_count,
    check_valid_gherkin_structure,
    run_property_checks,
)
from eval_harness.models import PropertyCheckOutcome


def _requirement(case_id: str) -> TestableRequirement:
    return next(case.requirement for case in FEATURE_CONTENT_EVAL_SET if case.case_id == case_id)


_REQUIREMENT = _requirement("login_invalid_credentials_error")

#: Reconstructed, real, clean raw generator output for the curated
#: `login_invalid_credentials_error` case (see module docstring).
_CLEAN_LOGIN_INVALID = (
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
)


class TestCheckNoReqTag:
    def test_passes_the_real_clean_corpus_text(self) -> None:
        result = check_no_req_tag(_CLEAN_LOGIN_INVALID, _REQUIREMENT)
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_catches_a_stray_req_tag(self) -> None:
        """The generated prompt contract forbids a @REQ-* tag unconditionally
        -- the platform, never the generator, attaches the requirement id."""
        defective = "@REQ-c64bb0f7 " + _CLEAN_LOGIN_INVALID
        result = check_no_req_tag(defective, _REQUIREMENT)
        assert result.outcome == PropertyCheckOutcome.FAILED
        assert "@REQ-" in result.reason

    def test_always_applicable(self) -> None:
        result = check_no_req_tag("", _REQUIREMENT)
        assert result.outcome != PropertyCheckOutcome.NOT_APPLICABLE


class TestCheckNoMarkdownFence:
    def test_passes_the_real_clean_corpus_text(self) -> None:
        result = check_no_markdown_fence(_CLEAN_LOGIN_INVALID, _REQUIREMENT)
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_catches_a_markdown_fence(self) -> None:
        """The governed `generate_feature` v1.1.0 OUTPUT CONTRACT states
        explicitly: 'no markdown code fence... anywhere'."""
        defective = f"```gherkin\n{_CLEAN_LOGIN_INVALID}```\n"
        result = check_no_markdown_fence(defective, _REQUIREMENT)
        assert result.outcome == PropertyCheckOutcome.FAILED

    def test_always_applicable(self) -> None:
        result = check_no_markdown_fence("", _REQUIREMENT)
        assert result.outcome != PropertyCheckOutcome.NOT_APPLICABLE


class TestCheckValidGherkinStructure:
    def test_passes_the_real_clean_corpus_text(self) -> None:
        result = check_valid_gherkin_structure(_CLEAN_LOGIN_INVALID, _REQUIREMENT)
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_catches_unparseable_content(self) -> None:
        """A plausible real defect shape: the model drops the `Scenario:`
        keyword line entirely, leaving an orphaned step under the tag line
        -- a genuine Gherkin parse error, not free-form prose (which the
        grammar actually accepts as a Feature description, verified this
        task)."""
        defective = (
            "@AC-c64bb0f7-01 @SCN-PENDING\n  Given an orphan step with no Scenario keyword\n"
        )
        result = check_valid_gherkin_structure(defective, _REQUIREMENT)
        assert result.outcome == PropertyCheckOutcome.FAILED

    def test_catches_a_tagged_background_as_a_parse_failure(self) -> None:
        """Empirically verified this task (module docstring): a tag placed
        immediately before `Background:` is a hard Gherkin parse error, not
        a valid-but-tagged AST node -- this check, not a dedicated
        Background-tag check, is what actually catches that real shape."""
        defective = (
            "@sometag\nBackground:\n  Given the system is ready\n\n" + _CLEAN_LOGIN_INVALID
        )
        result = check_valid_gherkin_structure(defective, _REQUIREMENT)
        assert result.outcome == PropertyCheckOutcome.FAILED

    def test_always_applicable(self) -> None:
        result = check_valid_gherkin_structure("", _REQUIREMENT)
        assert result.outcome != PropertyCheckOutcome.NOT_APPLICABLE


class TestCheckScnPendingTagCount:
    def test_passes_the_real_clean_corpus_text(self) -> None:
        result = check_scn_pending_tag_count(_CLEAN_LOGIN_INVALID, _REQUIREMENT)
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_catches_a_missing_scn_pending_tag(self) -> None:
        defective = _CLEAN_LOGIN_INVALID.replace("@SCN-PENDING ", "")
        result = check_scn_pending_tag_count(defective, _REQUIREMENT)
        assert result.outcome == PropertyCheckOutcome.FAILED
        assert "0 @SCN-PENDING" in result.reason

    def test_catches_a_duplicated_scn_pending_tag(self) -> None:
        defective = _CLEAN_LOGIN_INVALID.replace(
            "@SCN-PENDING ", "@SCN-PENDING @SCN-PENDING "
        )
        result = check_scn_pending_tag_count(defective, _REQUIREMENT)
        assert result.outcome == PropertyCheckOutcome.FAILED
        assert "2 @SCN-PENDING" in result.reason

    def test_not_applicable_when_unparseable(self) -> None:
        result = check_scn_pending_tag_count("not gherkin at all", _REQUIREMENT)
        assert result.outcome == PropertyCheckOutcome.NOT_APPLICABLE

    def test_not_applicable_when_no_scenarios(self) -> None:
        result = check_scn_pending_tag_count("", _REQUIREMENT)
        assert result.outcome == PropertyCheckOutcome.NOT_APPLICABLE


class TestCheckAcTagPresence:
    def test_passes_the_real_clean_corpus_text(self) -> None:
        result = check_ac_tag_presence(_CLEAN_LOGIN_INVALID, _REQUIREMENT)
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_catches_a_scenario_with_no_ac_tag(self) -> None:
        defective = _CLEAN_LOGIN_INVALID.replace("@AC-c64bb0f7-01 ", "")
        result = check_ac_tag_presence(defective, _REQUIREMENT)
        assert result.outcome == PropertyCheckOutcome.FAILED
        assert "Display error message" in result.reason

    def test_not_applicable_when_no_scenarios(self) -> None:
        result = check_ac_tag_presence("", _REQUIREMENT)
        assert result.outcome == PropertyCheckOutcome.NOT_APPLICABLE


class TestCheckNoUnknownAcTag:
    def test_passes_the_real_clean_corpus_text(self) -> None:
        result = check_no_unknown_ac_tag(_CLEAN_LOGIN_INVALID, _REQUIREMENT)
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_catches_a_fabricated_ac_tag(self) -> None:
        defective = _CLEAN_LOGIN_INVALID.replace(
            "@AC-c64bb0f7-01", "@AC-fabricated-99"
        )
        result = check_no_unknown_ac_tag(defective, _REQUIREMENT)
        assert result.outcome == PropertyCheckOutcome.FAILED
        assert "AC-fabricated-99" in result.reason

    def test_vacuously_passes_a_scenario_with_no_ac_tag_at_all(self) -> None:
        """Distinct defect shape from `check_ac_tag_presence` -- a missing
        tag is not an unknown one; each check owns exactly one shape."""
        defective = _CLEAN_LOGIN_INVALID.replace("@AC-c64bb0f7-01 ", "")
        result = check_no_unknown_ac_tag(defective, _REQUIREMENT)
        assert result.outcome == PropertyCheckOutcome.PASSED

    def test_not_applicable_when_no_scenarios(self) -> None:
        result = check_no_unknown_ac_tag("", _REQUIREMENT)
        assert result.outcome == PropertyCheckOutcome.NOT_APPLICABLE


class TestRunPropertyChecks:
    def test_runs_every_check_in_order_against_the_real_clean_corpus_text(self) -> None:
        results = run_property_checks(_CLEAN_LOGIN_INVALID, _REQUIREMENT)
        assert [result.check_name for result in results] == [
            "no_req_tag",
            "no_markdown_fence",
            "valid_gherkin_structure",
            "scn_pending_tag_count",
            "ac_tag_presence",
            "no_unknown_ac_tag",
        ]
        assert all(result.outcome == PropertyCheckOutcome.PASSED for result in results)
