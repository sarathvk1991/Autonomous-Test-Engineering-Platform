"""D5 — Layer 2's bounded remediation loop (ADR-0043 D5, ADR-0040 Decision 1).

D5's pipeline, verbatim: "generate -> deterministic formatter -> lint ->
[LLM remediate -> re-lint], max 2 attempts -> assign REQ/AC/SCN tags (D2's
hoist rule) -> final lint -> CP2 gate." :func:`run_cp2_remediation` is the
"[LLM remediate -> re-lint], max 2 attempts" stage plus Tier 1's
deterministic formatter immediately before it, entered only when the
generator core's own CP2-adjacent lint check has already failed once.

Sequencing note, reported rather than silently resolved
-----------------------------------------------------------
D5's own prose places tag assignment (REQ-*/AC-*/SCN-*, D2's hoist rule)
*after* the remediation loop, reasoning (D2) that "remediation can split or
rename scenarios, and an id assigned before that would be orphaned by the
split/rename it is meant to survive." The ALREADY-BUILT generator core
(`feature_engineering/generation/assembler.py`, built and tested across
several earlier tasks, out of this task's scope to rearchitect) does not
match that order: it mints `SCN-*` and assembles the fully-tagged feature
in ONE PASS, raising `FeatureGenerationError` (carrying the dirty, already
-tagged content) rather than returning something remediable pre-assignment.

This loop is built to fit that reality, not to silently reorder the core:
it receives ALREADY-ASSEMBLED, ALREADY-TAGGED dirty content and remediates
THAT. This is also what the ALREADY-REGISTERED `fix_gherkin_lint` v1.0.0
prompt itself expects and requires -- its own INPUT CONTRACT names
`feature_content` as "the full current text of one .feature file", and its
CONSTRAINTS explicitly instruct "Preserve every @REQ-*, @SCN-*, and @AC-*
tag exactly as given... never remove, rename, or relocate" -- a contract
that presupposes those tags already exist. So the governed PROMPT content
(D4, an earlier task) is itself built for post-assignment remediation,
diverging from D5's own stated pre-assignment rationale.

Given this, `SCN-*` orphaning is avoided here by RE-DERIVATION, not
deferral: every remediation attempt is independently re-parsed and
re-CP2-gated from its own text (see `_rebuild_generated_feature` below) --
a failed attempt's ids are never surfaced in any returned result, only the
final (successful, or last-escalated) attempt's ids ever are. No id from a
discarded attempt is ever treated as authoritative. This satisfies D2's
underlying invariant -- no id ever "survives" a split/rename it predates --
through re-derivation rather than through D5's literally-described deferred
-assignment mechanism. The residual, genuinely open question this task does
NOT resolve: the fix-gherkin-lint prompt's own tension between "preserve
ids verbatim" and "you may add/remove a scenario when a violation requires
it" (its own CONSTRAINTS block) is not reconciled by either the prompt text
or this loop -- a live remediation that both satisfies "preserve" and
"may split" simultaneously needs a future, explicit ADR-level decision on
how a split scenario's identifiers are chosen, which this task does not
invent an answer to.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from contracts.testable_requirement import TestableRequirement
from feature_engineering.cp2 import CP2Result, evaluate_cp2
from feature_engineering.generation.models import GeneratedFeature, ScenarioAssignment
from feature_engineering.gherkin_lint import (
    LintResult,
    load_config,
    parse_source_text,
)
from feature_engineering.gherkin_lint.linter import lint_source
from feature_engineering.remediation.formatter import format_feature_content
from feature_engineering.remediation.models import (
    MAX_LLM_REMEDIATION_ATTEMPTS,
    NON_REMEDIABLE_RULES,
    RemediationAttempt,
    RemediationResult,
    RemediationStatus,
)
from feature_engineering.remediation.remediator import FeatureRemediator

_LINTRC_PATH = Path("docs/reference/automation-poc/.gherkin-lintrc")
_AC_TAG_RE = re.compile(r"^@AC-\S+$")
_SCN_TAG_RE = re.compile(r"^@SCN-\S+$")


def _rebuild_generated_feature(
    requirement: TestableRequirement,
    content: str,
    req_tag: str,
    lint_result: LintResult,
) -> GeneratedFeature:
    """Re-derive a `GeneratedFeature`'s facts from already-assembled text
    alone -- the read-only counterpart to what `assembler.py`'s
    `generate_feature_file` computes while MINTING a feature the first
    time. Never mints an id: `content` already carries whatever `@SCN-*`/
    `@AC-*` values the remediator preserved or the formatter left
    untouched. Used only to re-gate a remediation attempt via the SAME,
    unmodified `evaluate_cp2` every other caller uses.
    """
    source = parse_source_text(content)
    known_ac_ids = {ac.criterion_id for ac in requirement.acceptance_criteria}
    coverage: dict[str, bool] = dict.fromkeys(known_ac_ids, False)
    scenario_assignments: list[ScenarioAssignment] = []

    if source.feature is not None:
        feature_tags = {t["name"] for t in source.feature.get("tags", [])}
        for child in source.feature.get("children", []):
            scenario = child.get("scenario")
            if not scenario:
                continue
            own_tags = {t["name"] for t in scenario.get("tags", [])}
            effective_tags = own_tags | feature_tags
            ac_ids = tuple(
                sorted(t.removeprefix("@") for t in effective_tags if _AC_TAG_RE.match(t))
            )
            scn_ids = [t.removeprefix("@") for t in effective_tags if _SCN_TAG_RE.match(t)]
            for ac_id in ac_ids:
                if ac_id in coverage:
                    coverage[ac_id] = True
            scenario_assignments.append(
                ScenarioAssignment(
                    name=scenario.get("name") or "",
                    scn_id=scn_ids[0] if scn_ids else "",
                    ac_ids=ac_ids,
                )
            )

    return GeneratedFeature(
        requirement_id=requirement.requirement_id,
        content=content,
        # Never written to disk by this loop -- a placeholder, not a real
        # target. `write_generated_feature` is a separate, later concern
        # (ADR-0036 stage 14, not built here).
        file_path=Path(f"{requirement.requirement_id}.feature"),
        req_tag=req_tag,
        scenarios=tuple(scenario_assignments),
        acceptance_criteria_coverage=coverage,
        lint_result=lint_result,
    )


def _relint(content: str, lint_config: dict[str, Any]) -> LintResult:
    return lint_source(parse_source_text(content), lint_config)


def _cp2_result_for(
    requirement: TestableRequirement,
    content: str,
    req_tag: str,
    lint_config: dict[str, Any],
) -> CP2Result:
    lint_result = _relint(content, lint_config)
    feature = _rebuild_generated_feature(requirement, content, req_tag, lint_result)
    return evaluate_cp2(feature)


def _non_remediable_violations(lint_result: LintResult) -> tuple[str, ...]:
    return tuple(sorted({v.rule for v in lint_result.violations if v.rule in NON_REMEDIABLE_RULES}))


def run_cp2_remediation(
    requirement: TestableRequirement,
    dirty_content: str,
    req_tag: str,
    remediator: FeatureRemediator,
) -> RemediationResult:
    """Run D5's bounded remediation loop over one CP2/lint-failing feature.

    Parameters
    ----------
    requirement:
        The originating `TestableRequirement` -- needed to know the full
        set of `AC-*` ids for coverage re-derivation (`_rebuild_generated_feature`).
    dirty_content:
        The fully-assembled, already-tagged `.feature` text that failed
        lint/CP2 -- e.g. `FeatureGenerationError.content` from the
        generator core.
    req_tag:
        The requirement's own `@REQ-*` tag (`GeneratedFeature.req_tag`),
        needed to re-derive CP2 facts from `content` alone.
    remediator:
        The Tier 2 content source (`StubFeatureRemediator` in tests; a live
        `llm_factory`-backed implementation is a documented follow-up, not
        built here).

    Returns
    -------
    RemediationResult
        `status` is `PASSED` the moment any stage's CP2 re-gate passes, or
        `ESCALATED` on a non-remediable violation (immediately, zero LLM
        calls) or after exhausting
        `feature_engineering.remediation.models.MAX_LLM_REMEDIATION_ATTEMPTS`
        LLM attempts. The gate is never weakened: every verdict here comes
        from the same, unmodified `evaluate_cp2` — this function contains
        no pass/fail logic of its own beyond reading that verdict.
    """
    lint_config = load_config(_LINTRC_PATH)

    # Non-remediable rules escalate immediately, bypassing Tier 1 and Tier 2
    # entirely (D5: "generation itself failed -- there is no content to
    # remediate").
    dirty_lint = _relint(dirty_content, lint_config)
    non_remediable = _non_remediable_violations(dirty_lint)
    if non_remediable:
        cp2_result = _cp2_result_for(requirement, dirty_content, req_tag, lint_config)
        return RemediationResult(
            status=RemediationStatus.ESCALATED,
            requirement_id=requirement.requirement_id,
            tier1_formatted=False,
            attempts=(),
            final_content=dirty_content,
            final_cp2_result=cp2_result,
            escalation_reason=f"non-remediable lint violation(s): {', '.join(non_remediable)}",
        )

    # --- Tier 1: deterministic formatter, zero LLM cost ---
    formatted = format_feature_content(dirty_content)
    tier1_formatted = formatted != dirty_content
    cp2_after_tier1 = _cp2_result_for(requirement, formatted, req_tag, lint_config)
    if cp2_after_tier1.passed:
        return RemediationResult(
            status=RemediationStatus.PASSED,
            requirement_id=requirement.requirement_id,
            tier1_formatted=tier1_formatted,
            attempts=(),
            final_content=formatted,
            final_cp2_result=cp2_after_tier1,
        )

    post_tier1_lint = _relint(formatted, lint_config)
    non_remediable = _non_remediable_violations(post_tier1_lint)
    if non_remediable:
        return RemediationResult(
            status=RemediationStatus.ESCALATED,
            requirement_id=requirement.requirement_id,
            tier1_formatted=tier1_formatted,
            attempts=(),
            final_content=formatted,
            final_cp2_result=cp2_after_tier1,
            escalation_reason=f"non-remediable lint violation(s): {', '.join(non_remediable)}",
        )

    # --- Tier 2: bounded LLM remediation, max MAX_LLM_REMEDIATION_ATTEMPTS ---
    attempts: list[RemediationAttempt] = []
    current_content = formatted
    for attempt_number in range(1, MAX_LLM_REMEDIATION_ATTEMPTS + 1):
        current_lint = _relint(current_content, lint_config)
        remediated = remediator.remediate(current_content, current_lint.violations)
        cp2_result = _cp2_result_for(requirement, remediated, req_tag, lint_config)
        attempts.append(
            RemediationAttempt(
                attempt_number=attempt_number,
                content_before=current_content,
                content_after=remediated,
                cp2_result=cp2_result,
            )
        )
        current_content = remediated
        if cp2_result.passed:
            return RemediationResult(
                status=RemediationStatus.PASSED,
                requirement_id=requirement.requirement_id,
                tier1_formatted=tier1_formatted,
                attempts=tuple(attempts),
                final_content=remediated,
                final_cp2_result=cp2_result,
            )

    return RemediationResult(
        status=RemediationStatus.ESCALATED,
        requirement_id=requirement.requirement_id,
        tier1_formatted=tier1_formatted,
        attempts=tuple(attempts),
        final_content=current_content,
        final_cp2_result=attempts[-1].cp2_result,
        escalation_reason=f"exhausted {MAX_LLM_REMEDIATION_ATTEMPTS} LLM remediation attempts",
    )


__all__ = ["run_cp2_remediation"]
