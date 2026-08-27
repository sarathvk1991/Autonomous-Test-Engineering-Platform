"""The SUT-vs-framework-SAST lexical filter and its report-only backlog
(ADR-0043 additive note, `feature_engineering.stage.code_quality_backlog`).

Proves, against the REAL 20-requirement corpus shape a live run actually
produced (not a contrived fixture): the lexical rule correctly classifies
all 5 genuine framework-SAST statements ("The automation test suite
shall...") and all 15 genuine SUT statements ("The system shall..."),
INCLUDING the 3 `Category.QUALITY` statements that are real, browser-testable
SUT behaviors -- the exact case a bare `category == QUALITY` filter would
have misclassified. Also proves the safer-error rule (ambiguous statement
shape -> default KEEP/SUT, never a silent drop) and the report's own
report-only shape (no verdict field, mirrors CP7).
"""

from __future__ import annotations

from contracts.testable_requirement import (
    AcceptanceCriterionInput,
    Category,
    Priority,
    TestableRequirement,
    build_testable_requirement,
)
from feature_engineering.stage.code_quality_backlog import (
    CODE_QUALITY_BACKLOG_FILENAME,
    FRAMEWORK_SAST_REASON,
    CodeQualityBacklogReport,
    build_code_quality_backlog_markdown,
    build_code_quality_backlog_report,
    is_framework_sast_statement,
    split_sut_and_framework_sast,
)

# ---------------------------------------------------------------------------
# THE REAL CORPUS -- verbatim statements from a real, committed live run
# (output/executions/run-20260812T064317663150Z-a20b0cc2/analysis_result.json)
# ---------------------------------------------------------------------------

_REAL_FUNCTIONAL_STATEMENTS = (
    "The system shall display the inventory page upon successful user authentication.",
    "The system shall deny access to users with locked accounts upon login attempt.",
    "The system shall display an error message when a user attempts to login with "
    "invalid credentials.",
    "The system shall increment the cart count when a user clicks the Add To Cart "
    "button for an inventory item.",
    "The system shall display selected items when a user opens the cart.",
    "The system shall remove an item from the cart when the user clicks the Remove "
    "button.",
    "The system shall proceed to checkout when valid checkout information is "
    "submitted.",
    "The system shall abort the checkout process when the user clicks the Cancel "
    "button.",
    "The system shall complete the order transaction when the user clicks the Finish "
    "button on the checkout page.",
)

_REAL_SECURITY_STATEMENTS = (
    "The system shall invalidate the user session and redirect to the login page "
    "upon session timeout.",
    "The system shall ensure the browser session is fully terminated upon user "
    "logout.",
    "The system shall validate that the postal code field in the checkout form "
    "accepts only valid postal code formats.",
)

#: The 3 real, genuine SUT behaviors the LLM filed under `Category.QUALITY` --
#: the exact case that makes a bare category filter wrong.
_REAL_SUT_QUALITY_STATEMENTS = (
    "The system shall ensure the cart count refreshes immediately following an item "
    "removal action.",
    "The system shall maintain consistent sorting order for inventory items.",
    "The system shall ensure the order confirmation page loads within a defined "
    "performance threshold.",
)

#: The 5 real framework-SAST statements -- about the automation test suite's OWN
#: Java code, never the SUT.
_REAL_FRAMEWORK_SAST_STATEMENTS = (
    "The automation test suite shall replace all Thread.sleep() calls with explicit "
    "WebDriver waits.",
    "The automation test suite shall implement a Page Object Model to eliminate "
    "repeated locators and redundant method implementations.",
    "The automation test suite shall refactor methods exceeding 40 lines to improve "
    "modularity and readability.",
    "The automation test suite shall implement robust exception handling, replacing "
    "generic catch blocks with specific exception types.",
    "The automation test suite shall enforce consistent naming conventions for all "
    "variables and methods.",
)

_ALL_REAL_SUT_STATEMENTS = (
    *_REAL_FUNCTIONAL_STATEMENTS,
    *_REAL_SECURITY_STATEMENTS,
    *_REAL_SUT_QUALITY_STATEMENTS,
)


def _requirement(
    title: str, *, category: Category = Category.FUNCTIONAL, **overrides: object
) -> TestableRequirement:
    defaults: dict[str, object] = {
        "title": title,
        "component": "saucedemo",
        "functional_tag": "@saucedemo",
        "priority": Priority.HIGH,
        "traces_to": (),
        "acceptance_criteria": [
            AcceptanceCriterionInput(category=category, statement=title),
        ],
    }
    defaults.update(overrides)
    return build_testable_requirement(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# THE LEXICAL RULE -- correct on the real corpus, including the impure
# QUALITY-category edge cases
# ---------------------------------------------------------------------------


class TestLexicalRuleOnTheRealCorpus:
    def test_every_real_sut_statement_is_kept_including_the_three_quality_category_ones(
        self,
    ) -> None:
        for statement in _ALL_REAL_SUT_STATEMENTS:
            assert is_framework_sast_statement(statement) is False, statement

    def test_every_real_framework_sast_statement_is_routed(self) -> None:
        for statement in _REAL_FRAMEWORK_SAST_STATEMENTS:
            assert is_framework_sast_statement(statement) is True, statement

    def test_bare_category_would_have_wrongly_dropped_the_three_sut_quality_statements(
        self,
    ) -> None:
        """The regression this module exists to avoid: filtering on
        `category == QUALITY` alone is NOT what this module does -- these
        three are `Category.QUALITY` and genuinely SUT-about, and must
        survive the lexical filter even though a naive category filter
        would drop them."""
        for statement in _REAL_SUT_QUALITY_STATEMENTS:
            req = _requirement(statement, category=Category.QUALITY)
            assert req.acceptance_criteria[0].category == Category.QUALITY
            assert is_framework_sast_statement(statement) is False


# ---------------------------------------------------------------------------
# ROBUSTNESS -- case-insensitivity, phrasing variants, ambiguity defaults
# ---------------------------------------------------------------------------


class TestRobustness:
    def test_case_insensitive(self) -> None:
        assert is_framework_sast_statement(
            "THE AUTOMATION TEST SUITE SHALL enforce naming conventions."
        )

    def test_recognizes_equivalent_framework_self_reference_phrasings(self) -> None:
        for phrasing in (
            "The test suite must not use Thread.sleep().",
            "The automation framework should isolate driver instances per thread.",
            "This test framework will enforce a maximum method length of 40 lines.",
        ):
            assert is_framework_sast_statement(phrasing) is True, phrasing

    def test_a_sut_statement_mentioning_test_suite_only_in_its_predicate_is_not_flagged(
        self,
    ) -> None:
        """The subject-clause scoping matters: "test suite" appearing after
        the modal verb (in the predicate, not the subject) must never flip
        the classification -- only the SUBJECT determines it."""
        statement = "The system shall log an audit entry for every test suite run."
        assert is_framework_sast_statement(statement) is False

    def test_a_statement_with_no_modal_verb_defaults_to_kept_not_dropped(self) -> None:
        """The safer-error rule, exercised directly: a statement shaped too
        differently to classify (no shall/should/must/will) is NEVER routed
        out -- ambiguity defaults to SUT/keep, per the decision (a
        false-keep is caught downstream by CP2/CP3/CP4; a false-drop is
        silent)."""
        assert is_framework_sast_statement("Improve checkout reliability.") is False

    def test_empty_statement_defaults_to_kept(self) -> None:
        assert is_framework_sast_statement("") is False


# ---------------------------------------------------------------------------
# THE SPLIT -- every requirement lands in exactly one bucket
# ---------------------------------------------------------------------------


class TestSplitSutAndFrameworkSast:
    def test_the_real_20_requirement_corpus_splits_15_sut_5_framework_sast(self) -> None:
        requirements = tuple(
            _requirement(statement, category=Category.FUNCTIONAL)
            for statement in _REAL_FUNCTIONAL_STATEMENTS
        ) + tuple(
            _requirement(statement, category=Category.SECURITY)
            for statement in _REAL_SECURITY_STATEMENTS
        ) + tuple(
            _requirement(statement, category=Category.QUALITY)
            for statement in (*_REAL_SUT_QUALITY_STATEMENTS, *_REAL_FRAMEWORK_SAST_STATEMENTS)
        )
        assert len(requirements) == 20

        sut, framework_sast = split_sut_and_framework_sast(requirements)

        assert len(sut) == 15
        assert len(framework_sast) == 5
        assert len(sut) + len(framework_sast) == len(requirements)  # nothing lost
        assert {r.title for r in framework_sast} == set(_REAL_FRAMEWORK_SAST_STATEMENTS)
        assert {r.title for r in sut} == set(_ALL_REAL_SUT_STATEMENTS)

    def test_preserves_relative_order_within_each_bucket(self) -> None:
        req_a = _requirement("The system shall show A.")
        req_b = _requirement("The automation test suite shall fix B.")
        req_c = _requirement("The system shall show C.")
        req_d = _requirement("The automation test suite shall fix D.")

        sut, framework_sast = split_sut_and_framework_sast((req_a, req_b, req_c, req_d))

        assert [r.requirement_id for r in sut] == [req_a.requirement_id, req_c.requirement_id]
        assert [r.requirement_id for r in framework_sast] == [
            req_b.requirement_id,
            req_d.requirement_id,
        ]

    def test_empty_input_splits_to_two_empty_tuples(self) -> None:
        sut, framework_sast = split_sut_and_framework_sast(())
        assert sut == ()
        assert framework_sast == ()


# ---------------------------------------------------------------------------
# THE REPORT -- report-only, no verdict, lists every routed requirement
# ---------------------------------------------------------------------------


class TestCodeQualityBacklogReport:
    def test_report_lists_one_entry_per_routed_requirement_with_its_reason(self) -> None:
        req = _requirement(
            "The automation test suite shall refactor methods exceeding 40 lines.",
            category=Category.QUALITY,
        )

        report = build_code_quality_backlog_report("run-1", (req,))

        assert isinstance(report, CodeQualityBacklogReport)
        assert report.run_id == "run-1"
        assert len(report.entries) == 1
        entry = report.entries[0]
        assert entry.requirement_id == req.requirement_id
        assert entry.title == req.title
        assert entry.category == "quality"
        assert entry.reason == FRAMEWORK_SAST_REASON

    def test_report_is_structurally_non_gating_no_verdict_field(self) -> None:
        """Mirrors CP7's own `Cp7WholeSuiteQualityReport`: no
        `overall_verdict`/`passed` attribute anywhere on this type."""
        report = build_code_quality_backlog_report("run-1", ())
        field_names = set(report.__dataclass_fields__)
        assert "overall_verdict" not in field_names
        assert "passed" not in field_names
        assert "verdict" not in field_names

    def test_report_is_still_emitted_when_nothing_was_routed_empty_not_absent(self) -> None:
        """Same "always emit, even empty" discipline as
        `test_data_spec.build_test_data_specifications`."""
        report = build_code_quality_backlog_report("run-1", ())
        assert report.entries == ()
        assert report.run_id == "run-1"

    def test_json_round_trip(self) -> None:
        req = _requirement(
            "The automation test suite shall enforce consistent naming conventions.",
            category=Category.QUALITY,
        )
        report = build_code_quality_backlog_report("run-1", (req,))

        payload = report.to_json()
        assert payload["runId"] == "run-1"
        assert len(payload["entries"]) == 1

        rebuilt = CodeQualityBacklogReport.from_json(payload)
        assert rebuilt == report

    def test_markdown_rendering_lists_every_entry_and_states_report_only(self) -> None:
        req = _requirement(
            "The automation test suite shall replace all Thread.sleep() calls.",
            category=Category.QUALITY,
        )
        report = build_code_quality_backlog_report("run-1", (req,))

        markdown = build_code_quality_backlog_markdown(report)

        assert req.requirement_id in markdown
        assert req.title in markdown
        assert "quality" in markdown
        assert "Not a gate" in markdown

    def test_filename_constant_is_a_plain_json_file(self) -> None:
        assert CODE_QUALITY_BACKLOG_FILENAME == "code_quality_backlog.json"
