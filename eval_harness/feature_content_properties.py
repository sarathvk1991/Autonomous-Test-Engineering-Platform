"""ADR-0051 D2's deterministic property/assertion checks for one generated
feature-content artifact (`LiveFeatureContentGenerator`'s raw output).

**Composed, not invented (ADR-0051 D1, the reframe) -- and NOT copied from
`step_definition_properties.py`.** Feature-content is a different artifact
(raw Gherkin scenario/background text, not Java), governed by a different,
already-real contract: `feature_engineering.generation.assembler.
generate_feature_file` already deterministically validates every one of
these properties against the generator's raw output, today, live, before
ever attempting assembly -- raising `FeatureGenerationError` the instant one
is violated (`assembler.py` lines ~191-251). Each check below is a direct,
decomposed, independently-evaluable port of exactly one of those
already-real, already-enforced validation blocks (plus one, `check_no_
markdown_fence`, ported from the governed `generate_feature` v1.1.0 prompt's
own explicit OUTPUT CONTRACT clause: "no markdown code fence... anywhere") --
not a new detection idea, and not step-def's own three checks relabeled.
Unlike step-def, there is no known real historical feature-content defect on
record (the live corpus run scored 15/15 clean, 0 escalations,
`[[cap-stage14-live-cli-wiring]]`) -- these checks are grounded in the real,
already-enforced CONTRACT, not a real historical INCIDENT.

**One real `assembler.py` validation block is deliberately NOT ported: the
tagged-``Background:`` check, verified unreachable, not merely skipped.**
`assembler.py` raises when `background.get("tags")` is truthy -- but a tag
placed immediately before a `Background:` line is a hard Gherkin PARSE
ERROR under the real Cucumber grammar this platform's own gherkin-lint port
uses (confirmed empirically, this task: `parse_source_text` returns
`feature=None`/a populated `parse_error` for exactly this input, never a
background AST node with a non-empty `tags` list). `assembler.py`'s own
check is defensive code for a branch the real parser can never produce --
the defect it targets is already fully subsumed by `check_valid_gherkin_
structure` below. Porting it as an eighth, independent check would report a
FAILED outcome no real input can ever trigger — the opposite of this
package's own "every check catches a real, reachable defect shape"
discipline (mirrors this arc's own repeated practice of verifying a flag
against real code before trusting it, e.g. `[[cap-runtime-citation-not-built]]`).

Feature-content's own defect-shape/mechanism boundary (mirroring D4's CP5
framing): `generate_feature_file`'s FULL validation also lints the fully
ASSEMBLED file (CP2's `lint`/`acceptance_criteria_coverage`/`duplicate_
detection` criteria, `feature_engineering/cp2/evaluator.py`) -- that
dimension requires real id-minting, Feature-name derivation, and tag
hoisting, i.e. the whole-corpus/whole-file assembly grain CP2 already gates
at, deliberately not reimplemented at this per-case, pre-assembly grain
(ADR-0051 D2's own "not the whole-corpus grain CP5 itself operates at").
Only the tag-contract/structural properties checkable directly against the
generator's RAW, PRE-assembly output are Layer 1's scope here -- exactly the
same grain step-def's checks operate at (its own raw Java text, before any
Maven compile).

Every check is a pure function of ``(generated_text, requirement)`` -- no
LLM call, no filesystem access, no subprocess. Each returns
:class:`~eval_harness.models.PropertyCheckOutcome.NOT_APPLICABLE` rather
than a vacuous PASS when nothing in the parsed content gives the check
anything to evaluate (unparseable content, or no Scenario/Scenario Outline
block present) -- ``NOT_APPLICABLE`` results are excluded from the eval
score's pass-rate denominator (:mod:`.scoring`), never silently counted as
evidence of quality.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from contracts.testable_requirement import TestableRequirement
from eval_harness.models import PropertyCheckOutcome, PropertyCheckResult
from feature_engineering.gherkin_lint.source import SourceFile, parse_source_text

#: Mirrors `assembler.py`'s own temp-header wrap exactly: the raw content is
#: deliberately scenario-only (no Feature: line of its own, per the governed
#: prompt's OUTPUT CONTRACT), so a temporary header is required to parse it
#: as Gherkin at all.
_TEMP_HEADER = "Feature: __GENERATION_TEMP__\n\n"

_SCN_PENDING_TAG = "@SCN-PENDING"
_AC_TAG_RE = re.compile(r"^@AC-\S+$")

PropertyCheck = Callable[[str, TestableRequirement], PropertyCheckResult]


def _parse_raw_content(generated_text: str) -> SourceFile:
    """Wrap ``generated_text`` in the same temporary Feature: header
    `generate_feature_file` uses, then parse -- the identical mechanism, not
    a second, divergent one."""
    return parse_source_text(_TEMP_HEADER + generated_text, path="<eval_harness>")


def _scenario_children(source: SourceFile) -> list[dict[str, Any]]:
    if source.feature is None:
        return []
    return [
        child["scenario"] for child in source.feature.get("children", []) if child.get("scenario")
    ]


def check_no_req_tag(
    generated_text: str, requirement: TestableRequirement
) -> PropertyCheckResult:
    """Catches a stray ``@REQ-*`` tag: the generated prompt contract forbids
    it unconditionally ("never write a @REQ-* tag yourself, anywhere, under
    any circumstance") -- the platform attaches the requirement's own id to
    the Feature line it derives, never the generator. Exactly mirrors
    `generate_feature_file`'s own ``"@REQ-" in raw_content`` check
    (`assembler.py`). Always applicable.
    """
    if "@REQ-" in generated_text:
        return PropertyCheckResult(
            check_name="no_req_tag",
            outcome=PropertyCheckOutcome.FAILED,
            reason="generated content contains a @REQ-* tag, which the content generator "
            "must never write -- the platform attaches the requirement's id to the "
            "derived Feature line directly",
        )
    return PropertyCheckResult(check_name="no_req_tag", outcome=PropertyCheckOutcome.PASSED)


def check_no_markdown_fence(
    generated_text: str, requirement: TestableRequirement
) -> PropertyCheckResult:
    """Catches a fenced ``` code block wrapping the response, despite the
    governed `generate_feature` v1.1.0 prompt's own explicit OUTPUT CONTRACT
    ("no markdown code fence... anywhere"). Always applicable -- every
    generated artifact is either fenced or it isn't.
    """
    if "```" in generated_text:
        return PropertyCheckResult(
            check_name="no_markdown_fence",
            outcome=PropertyCheckOutcome.FAILED,
            reason="generated text contains a markdown code fence ('```')",
        )
    return PropertyCheckResult(
        check_name="no_markdown_fence", outcome=PropertyCheckOutcome.PASSED
    )


def check_valid_gherkin_structure(
    generated_text: str, requirement: TestableRequirement
) -> PropertyCheckResult:
    """Catches content that does not parse as Gherkin at all -- exactly
    mirrors `generate_feature_file`'s own ``source.parse_error or source.
    feature is None`` check (`assembler.py`), against the identical
    temp-header-wrapped parse. Always applicable.
    """
    source = _parse_raw_content(generated_text)
    if source.parse_error or source.feature is None:
        return PropertyCheckResult(
            check_name="valid_gherkin_structure",
            outcome=PropertyCheckOutcome.FAILED,
            reason=f"generated content is not valid Gherkin: "
            f"{source.parse_error or 'no Feature block parsed'}",
        )
    return PropertyCheckResult(
        check_name="valid_gherkin_structure", outcome=PropertyCheckOutcome.PASSED
    )


def check_scn_pending_tag_count(
    generated_text: str, requirement: TestableRequirement
) -> PropertyCheckResult:
    """Catches a missing or duplicated ``@SCN-PENDING`` tag -- exactly
    mirrors `generate_feature_file`'s own ``scn_pending_count != 1`` check
    per scenario (`assembler.py`): the platform mints the real,
    content-addressed ``@SCN-*`` id from this one true placeholder, so
    anything other than exactly one is unrecoverable downstream.

    ``NOT_APPLICABLE`` when the content is unparseable (`check_valid_
    gherkin_structure` already reports that defect; this check has nothing
    to count tags on) or carries no Scenario/Scenario Outline block at all.
    """
    source = _parse_raw_content(generated_text)
    scenarios = _scenario_children(source)
    if not scenarios:
        return PropertyCheckResult(
            check_name="scn_pending_tag_count",
            outcome=PropertyCheckOutcome.NOT_APPLICABLE,
            reason="no Scenario/Scenario Outline block to check a @SCN-PENDING count on",
        )

    offenders = []
    for scenario in scenarios:
        tag_names = [tag["name"] for tag in scenario.get("tags", [])]
        count = tag_names.count(_SCN_PENDING_TAG)
        if count != 1:
            offenders.append(f"{scenario.get('name')!r} has {count} @SCN-PENDING tags")

    if offenders:
        return PropertyCheckResult(
            check_name="scn_pending_tag_count",
            outcome=PropertyCheckOutcome.FAILED,
            reason="; ".join(offenders),
        )
    return PropertyCheckResult(
        check_name="scn_pending_tag_count", outcome=PropertyCheckOutcome.PASSED
    )


def check_ac_tag_presence(
    generated_text: str, requirement: TestableRequirement
) -> PropertyCheckResult:
    """Catches a scenario with no ``@AC-*`` tag at all -- exactly mirrors
    `generate_feature_file`'s own ``if not ac_ids`` check (`assembler.py`):
    every scenario must trace to at least one acceptance criterion it
    exercises.

    ``NOT_APPLICABLE`` when unparseable or no scenarios exist.
    """
    source = _parse_raw_content(generated_text)
    scenarios = _scenario_children(source)
    if not scenarios:
        return PropertyCheckResult(
            check_name="ac_tag_presence",
            outcome=PropertyCheckOutcome.NOT_APPLICABLE,
            reason="no Scenario/Scenario Outline block to check @AC-* tag presence on",
        )

    offenders = [
        scenario.get("name") or "<unnamed>"
        for scenario in scenarios
        if not any(_AC_TAG_RE.match(tag["name"]) for tag in scenario.get("tags", []))
    ]
    if offenders:
        return PropertyCheckResult(
            check_name="ac_tag_presence",
            outcome=PropertyCheckOutcome.FAILED,
            reason=f"scenario(s) with no @AC-* tag: {offenders}",
        )
    return PropertyCheckResult(
        check_name="ac_tag_presence", outcome=PropertyCheckOutcome.PASSED
    )


def check_no_unknown_ac_tag(
    generated_text: str, requirement: TestableRequirement
) -> PropertyCheckResult:
    """Catches a fabricated/unknown ``@AC-*`` tag -- exactly mirrors
    `generate_feature_file`'s own ``unknown = [ac for ac in ac_ids if ...
    not in known_ac_ids]`` check (`assembler.py`): every ac_id a scenario
    tags must be one of ``requirement.acceptance_criteria``'s real,
    already-minted ids, verbatim -- never invented by the model.

    ``NOT_APPLICABLE`` when unparseable or no scenarios exist. A scenario
    with zero @AC-* tags contributes nothing here (that is `check_ac_tag_
    presence`'s own, distinct defect shape) -- this check is vacuously
    satisfied for such a scenario, by design, so each check catches exactly
    one defect shape (ADR-0051 D1).
    """
    source = _parse_raw_content(generated_text)
    scenarios = _scenario_children(source)
    if not scenarios:
        return PropertyCheckResult(
            check_name="no_unknown_ac_tag",
            outcome=PropertyCheckOutcome.NOT_APPLICABLE,
            reason="no Scenario/Scenario Outline block to check @AC-* tag validity on",
        )

    known_ac_ids = {ac.criterion_id for ac in requirement.acceptance_criteria}
    offenders: list[str] = []
    for scenario in scenarios:
        tag_names = [tag["name"] for tag in scenario.get("tags", [])]
        ac_tags = [t for t in tag_names if _AC_TAG_RE.match(t)]
        unknown = [t for t in ac_tags if t.removeprefix("@") not in known_ac_ids]
        offenders.extend(unknown)

    if offenders:
        return PropertyCheckResult(
            check_name="no_unknown_ac_tag",
            outcome=PropertyCheckOutcome.FAILED,
            reason=f"tags unknown criterion id(s) not on the requirement: {offenders}",
        )
    return PropertyCheckResult(
        check_name="no_unknown_ac_tag", outcome=PropertyCheckOutcome.PASSED
    )


#: ADR-0051 D2/D5's feature-content check set -- targets exactly the six
#: real, reachable, already-enforced properties `generate_feature_file`
#: validates against the generator's raw output (five) plus the governed
#: prompt's own explicit no-markdown-fence contract clause (one). A seventh
#: real `assembler.py` block (the tagged-Background check) is deliberately
#: NOT ported here -- see the module docstring's "verified unreachable" note.
#: Ordered deterministically; a caller wanting a different or extended set
#: composes its own tuple rather than mutating this one.
FEATURE_CONTENT_PROPERTY_CHECKS: tuple[PropertyCheck, ...] = (
    check_no_req_tag,
    check_no_markdown_fence,
    check_valid_gherkin_structure,
    check_scn_pending_tag_count,
    check_ac_tag_presence,
    check_no_unknown_ac_tag,
)


def run_property_checks(
    generated_text: str,
    requirement: TestableRequirement,
    checks: tuple[PropertyCheck, ...] = FEATURE_CONTENT_PROPERTY_CHECKS,
) -> tuple[PropertyCheckResult, ...]:
    """Run every check in ``checks`` against one generated artifact,
    deterministically, in order -- no LLM call, no I/O."""
    return tuple(check(generated_text, requirement) for check in checks)


__all__ = [
    "FEATURE_CONTENT_PROPERTY_CHECKS",
    "PropertyCheck",
    "check_ac_tag_presence",
    "check_no_markdown_fence",
    "check_no_req_tag",
    "check_no_unknown_ac_tag",
    "check_scn_pending_tag_count",
    "check_valid_gherkin_structure",
    "run_property_checks",
]
