"""The SUT-vs-framework-SAST filter and its own report-only backlog
(ADR-0043 additive note, alongside D7's own additive-note pattern).

**The finding this closes.** Layer 1 does not distinguish "this requirement
describes SUT-observable behavior" from "this requirement is a SonarQube
SAST finding about the automation framework's own Java code" -- both flow
identically through `AcceptanceCriterion.category` (`Category.FUNCTIONAL` /
`.SECURITY` / `.QUALITY`, `contracts/testable_requirement.py`, ADR-0042) as
undifferentiated `TestableRequirement`s. `Category.QUALITY` is not a clean
proxy for "not browser-testable": a real run's own `quality_requirements`
bucket held both genuine framework-SAST findings ("The automation test
suite shall refactor methods exceeding 40 lines...") AND legitimate,
browser-testable SUT quality behaviors ("The system shall ensure the cart
count refreshes immediately following an item removal action.") -- filtering
on bare category would silently drop the latter. The signal that DOES split
them cleanly, observed directly on that same real corpus, is the
requirement's own grammatical subject: every framework-SAST statement names
"the automation test suite" (or an equivalent self-reference) as its
subject; every SUT statement names "the system".

**Where this lives, and why it is freeze-clean.** This is Layer 2 code
(`feature_engineering/`), never Layer 1 (`requirement_intelligence/`) --
ADR-0032's freeze restricts new Layer 1 capability only ("no new Layer 1 CAP
number"); this module adds nothing to Layer 1, reads a field
(`TestableRequirement.title`) Layer 1 already emits faithfully today, and
never mutates or re-derives anything about how that field was produced. It
mirrors ADR-0043 D7's own `test_data_spec.py`: a small, additive Layer 2
derivation, not a new stage.

**Nothing is silently dropped.** A requirement classified as framework-SAST
is routed to :class:`CodeQualityBacklogReport` instead of Feature/Automation
Engineering -- report-only, structurally non-gating (no `overall_verdict`/
`passed` field, mirroring CP7's own `Cp7WholeSuiteQualityReport`,
`suite_quality_governance/cp7/models.py`), never a verdict that blocks
anything. Every requirement in a `TestableRequirementSet` is accounted for
by exactly one of: a `FeatureRecord` (SUT, processed as before) or a
`CodeQualityBacklogEntry` (framework-SAST, reported instead).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from contracts.testable_requirement import TestableRequirement

CODE_QUALITY_BACKLOG_FILENAME = "code_quality_backlog.json"
CODE_QUALITY_BACKLOG_REPORT_FILENAME = "code_quality_backlog_report.md"

#: Modal verbs a well-formed requirement statement uses to separate its own
#: subject clause from its predicate ("The system SHALL...", "The
#: automation test suite MUST..."). Checked in this order; the first match
#: wins. A statement with none of these is structurally ambiguous -- see
#: `_subject_clause`'s own handling below.
_MODAL_VERBS: tuple[str, ...] = (" shall ", " should ", " must ", " will ")

#: Self-referential phrases that mark a requirement's subject as the
#: automation framework's OWN code, never the SUT. Substring-matched against
#: the statement's own subject clause only (never its full body), so a SUT
#: requirement that happens to mention "test suite" somewhere in its
#: predicate is never misclassified by this alone.
_FRAMEWORK_SUBJECT_MARKERS: tuple[str, ...] = (
    "automation test suite",
    "test automation suite",
    "automation suite",
    "test automation framework",
    "test framework",
    "automation framework",
    "automation code",
    "test suite",
)


def _subject_clause(statement: str) -> str | None:
    """The lowercased text before the first modal verb, or `None` when no
    modal verb is present at all -- a statement shaped too differently from
    "The X shall/should/must/will..." to safely classify at all."""
    lowered = statement.strip().lower()
    positions = (lowered.find(modal) for modal in _MODAL_VERBS)
    found = [p for p in positions if p != -1]
    if not found:
        return None
    return lowered[: min(found)]


def is_framework_sast_statement(statement: str) -> bool:
    """True only when *statement*'s own subject clause names the automation
    framework itself (`_FRAMEWORK_SUBJECT_MARKERS`), never the SUT.

    **Ambiguity defaults to `False` (SUT, kept).** A statement with no modal
    verb at all (`_subject_clause` returns `None`) is never classified as
    framework-SAST -- the safer error here is a false-KEEP (an ordinary SUT
    requirement proceeds through Feature/Automation Engineering exactly as
    it does today, and any generation-quality issue is CP2/CP3/CP4's job to
    catch) rather than a false-DROP (a real SUT scenario silently vanishes
    from the suite with no gate ever seeing it happen).
    """
    subject = _subject_clause(statement)
    if subject is None:
        return False
    return any(marker in subject for marker in _FRAMEWORK_SUBJECT_MARKERS)


def split_sut_and_framework_sast(
    requirements: tuple[TestableRequirement, ...],
) -> tuple[tuple[TestableRequirement, ...], tuple[TestableRequirement, ...]]:
    """Partition *requirements* into ``(sut, framework_sast)``, preserving
    each group's own relative order from the input. Every requirement lands
    in exactly one of the two -- this function drops nothing."""
    sut: list[TestableRequirement] = []
    framework_sast: list[TestableRequirement] = []
    for requirement in requirements:
        if is_framework_sast_statement(requirement.title):
            framework_sast.append(requirement)
        else:
            sut.append(requirement)
    return tuple(sut), tuple(framework_sast)


@dataclass(frozen=True, slots=True)
class CodeQualityBacklogEntry:
    """One framework-SAST requirement routed out of Feature/Automation
    Engineering -- the statement, its own Layer 1 category, and why it was
    routed. Never a verdict; this is a backlog line item, not a gate."""

    requirement_id: str
    title: str
    category: str
    reason: str

    def to_json(self) -> dict[str, Any]:
        return {
            "requirementId": self.requirement_id,
            "title": self.title,
            "category": self.category,
            "reason": self.reason,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> CodeQualityBacklogEntry:
        return cls(
            requirement_id=str(data["requirementId"]),
            title=str(data["title"]),
            category=str(data["category"]),
            reason=str(data["reason"]),
        )


#: The single reason every entry in this report carries today. A constant,
#: not a free-text field per entry, because this module implements exactly
#: one routing rule (`is_framework_sast_statement`) -- a future second
#: routing rule would add its own distinct reason string, never overload
#: this one's meaning.
FRAMEWORK_SAST_REASON = (
    "framework-SAST: this requirement's own subject is the automation test "
    "suite's code, not the SUT -- not browser-testable, routed out of "
    "Feature/Automation Engineering."
)


@dataclass(frozen=True, slots=True)
class CodeQualityBacklogReport:
    """Report-only, structurally non-gating (mirrors
    `suite_quality_governance.cp7.models.Cp7WholeSuiteQualityReport`):
    deliberately no `overall_verdict`/`passed` field. Every entry is a
    requirement that Feature/Automation Engineering never saw."""

    run_id: str
    entries: tuple[CodeQualityBacklogEntry, ...]

    def to_json(self) -> dict[str, Any]:
        return {
            "runId": self.run_id,
            "entries": [entry.to_json() for entry in self.entries],
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> CodeQualityBacklogReport:
        return cls(
            run_id=str(data["runId"]),
            entries=tuple(CodeQualityBacklogEntry.from_json(e) for e in data["entries"]),
        )


def build_code_quality_backlog_report(
    run_id: str, framework_sast_requirements: tuple[TestableRequirement, ...]
) -> CodeQualityBacklogReport:
    """One entry per routed-out requirement, in the SAME order given --
    unconditionally, including the empty case (a run with no framework-SAST
    requirements still gets a report, with zero entries, never no report at
    all -- the same "always emit, even empty" discipline
    `test_data_spec.build_test_data_specifications` already establishes)."""
    entries = tuple(
        CodeQualityBacklogEntry(
            requirement_id=requirement.requirement_id,
            title=requirement.title,
            category=(
                # `Schema.model_config` sets `use_enum_values=True`, so
                # `category` is already a plain string (e.g. "quality"), not
                # a `Category` member -- `str()` itself is the correct
                # normalization, no `.value` unwrap (mirrors
                # `test_data_spec.build_test_data_specification`'s own note
                # on `required_variants`).
                str(requirement.acceptance_criteria[0].category)
                if requirement.acceptance_criteria
                else "unknown"
            ),
            reason=FRAMEWORK_SAST_REASON,
        )
        for requirement in framework_sast_requirements
    )
    return CodeQualityBacklogReport(run_id=run_id, entries=entries)


def build_code_quality_backlog_markdown(report: CodeQualityBacklogReport) -> str:
    """Human-readable rendering, mirroring `feature_engineering.stage.report
    .build_report`'s own posture: pure projection, computes no verdict."""
    lines = [
        "# Code Quality Backlog (Stage 14)",
        "",
        f"Run: {report.run_id}",
        f"Requirements routed out of Feature/Automation Engineering: {len(report.entries)}",
        "",
        "Report-only. Not a gate -- nothing here blocks a release.",
        "",
        "| Requirement | Category | Title |",
        "|---|---|---|",
    ]
    for entry in report.entries:
        lines.append(f"| {entry.requirement_id} | {entry.category} | {entry.title} |")
    return "\n".join(lines) + "\n"


__all__ = [
    "CODE_QUALITY_BACKLOG_FILENAME",
    "CODE_QUALITY_BACKLOG_REPORT_FILENAME",
    "FRAMEWORK_SAST_REASON",
    "CodeQualityBacklogEntry",
    "CodeQualityBacklogReport",
    "build_code_quality_backlog_markdown",
    "build_code_quality_backlog_report",
    "is_framework_sast_statement",
    "split_sut_and_framework_sast",
]
