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
re-CP2-gated from its own text (see `rebuild_generated_feature` below) --
a failed attempt's ids are never surfaced in any returned result, only the
final (successful, or last-escalated) attempt's ids ever are. No id from a
discarded attempt is ever treated as authoritative. This satisfies D2's
underlying invariant -- no id ever "survives" a split/rename it predates --
through re-derivation rather than through D5's literally-described deferred
-assignment mechanism.

Split-scenario re-mint (ADR-0043 D2, 2026-07-27 addendum; baseline register
§4 item 13) -- IMPLEMENTED, construct-tested, never observed live
-------------------------------------------------------------------------
The tension this note originally left open -- `fix_gherkin_lint`'s own
CONSTRAINTS demand "preserve every tag exactly as given" beside "you may
add/remove a scenario when a violation requires it" -- is now resolved and
built: `_remint_split_scenario_ids` runs on every Tier-2 (LLM) attempt,
after `remediator.remediate()` returns and before that attempt's content is
re-linted or re-CP2-gated. Identity is TAG-based, not content-based: a
scenario's *content* legitimately changes under ordinary remediation (e.g.
a rename to fix `no-dupe-scenario-names`) without becoming a different
scenario, so content can never be the identity signal -- only the preserved
tag can, matching the prompt's own "preserve every tag exactly as given"
contract. A post-remediation scenario survives, keeping its existing
`@SCN-*` untouched, exactly when its own tag matches a known pre
-remediation id that no earlier scenario (in document order) has already
claimed; the "not already claimed" guard is what catches the one failure
mode D2 actually forbids -- the LLM copying one scenario's id onto a
second, genuinely new one after a split. A scenario that fails to claim a
known id (untagged, an invented tag, or a losing duplicate claim) is minted
a fresh id via the same `contracts.id_generation.generate_scenario_ids`
mechanism the generator core calls (over that scenario's own canonical
content, `feature_engineering.generation.assembler.canonical_scenario_content`
-- not a second, divergent identity mechanism), offset past every ordinal
already used in its `AC-*` group so a fresh mint can never collide with a
preserved survivor's id. When every scenario legitimately claims a known
id -- every real remediation observed so far -- this step performs zero
edits and returns the attempt's content byte-identical to what the
remediator returned.

HONEST STATUS: two live runs (60 generations) observed ZERO scenario
splits. This path is implemented and exercised only against a CONSTRUCTED
split -- a stub `FeatureRemediator` scripted to turn one scenario into two
(`tests/unit/test_feature_engineering_remediation.py`,
`TestSplitScenarioRemint`) -- never against real live-model split
behaviour, because no real split has ever been observed. Building it
defensively is still correct (rare is not never; an unhandled split would
silently orphan an id), but its status is "implemented, construct-tested,
never observed live," not "proven."
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from contracts.id_generation import generate_scenario_ids
from contracts.testable_requirement import TestableRequirement
from feature_engineering.cp2 import CP2Result, evaluate_cp2
from feature_engineering.generation.assembler import canonical_scenario_content
from feature_engineering.generation.models import GeneratedFeature, ScenarioAssignment
from feature_engineering.gherkin_lint import (
    LintResult,
    SourceFile,
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


def rebuild_generated_feature(
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
    untouched. Used to re-gate a remediation attempt via the SAME,
    unmodified `evaluate_cp2` every other caller uses, and reused by
    stage 14's own wiring (`feature_engineering.stage`) to reconstruct a
    `GeneratedFeature` for an unchanged, reused requirement's on-disk
    content -- not a new mechanism, the same read-only reconstruction this
    loop already needed.
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


@dataclass(frozen=True, slots=True)
class _ScenarioFact:
    """One scenario's identity facts, read back from already-assembled
    text, for the split-scenario re-mint step below. Distinct from
    `ScenarioAssignment` -- that type is the platform's own public output
    shape; this one carries the raw AST tag node (with source location) a
    text-level edit needs, which no public type exposes."""

    canonical_content: str
    ac_ids: tuple[str, ...]
    effective_scn_id: str | None
    own_scn_tag: dict[str, Any] | None
    scenario_location: dict[str, int]
    last_own_tag_location: dict[str, int] | None


def _extract_scenario_facts(source: SourceFile) -> list[_ScenarioFact]:
    facts: list[_ScenarioFact] = []
    if source.feature is None:
        return facts
    feature_tag_names = {t["name"] for t in source.feature.get("tags", [])}
    for child in source.feature.get("children", []):
        scenario = child.get("scenario")
        if not scenario:
            continue
        own_tags = list(scenario.get("tags", []))
        own_tag_names = {t["name"] for t in own_tags}
        effective_names = own_tag_names | feature_tag_names
        ac_ids = tuple(sorted(n.removeprefix("@") for n in effective_names if _AC_TAG_RE.match(n)))
        effective_scn_names = [n for n in effective_names if _SCN_TAG_RE.match(n)]
        own_scn_tags = [t for t in own_tags if _SCN_TAG_RE.match(t["name"])]
        facts.append(
            _ScenarioFact(
                canonical_content=canonical_scenario_content(scenario),
                ac_ids=ac_ids,
                effective_scn_id=effective_scn_names[0].removeprefix("@")
                if effective_scn_names
                else None,
                own_scn_tag=own_scn_tags[0] if own_scn_tags else None,
                scenario_location=scenario["location"],
                last_own_tag_location=own_tags[-1]["location"] if own_tags else None,
            )
        )
    return facts


def _used_ordinals_for_group(facts: list[_ScenarioFact], ac_short: str) -> set[int]:
    used: set[int] = set()
    for fact in facts:
        scn_id = fact.effective_scn_id
        if scn_id is None:
            continue
        prefix, _, ordinal_str = scn_id.rpartition("-")
        if prefix.removeprefix("SCN-") == ac_short and ordinal_str.isdigit():
            used.add(int(ordinal_str))
    return used


def _remint_split_scenario_ids(pre_content: str, post_content: str) -> str:
    """ADR-0043 D2's split-scenario re-mint rule (2026-07-27 addendum;
    baseline register §4 item 13) -- see the module docstring's "Split
    -scenario re-mint" section for the full design and its HONEST STATUS.

    Identity is TAG-based, not content-based -- matching the fix-gherkin
    -lint prompt's own "preserve every tag exactly as given" contract: a
    post-remediation scenario survives, keeping its id untouched, exactly
    when its own `@SCN-*` tag matches a known pre-remediation id that no
    earlier scenario (in document order) has already claimed. This is
    deliberate, not incidental -- a scenario's *content* legitimately
    changes under remediation (e.g. a rename to fix `no-dupe-scenario
    -names`) without becoming a different scenario, so content can never be
    the identity signal; only the preserved tag can. The "no earlier
    scenario already claimed it" guard is what catches the one failure mode
    D2 actually forbids: the LLM copying one scenario's id onto a second,
    genuinely new one after a split -- the first (in document order) claims
    it as the true survivor, the second falls through to re-minting below,
    same as a scenario carrying no id, or an invented one, at all.

    A scenario that fails to claim a known id is minted a fresh,
    deterministic id via `generate_scenario_ids`, offset past every ordinal
    already used in its `AC-*` group so a fresh mint can never collide with
    a preserved survivor's id.

    Returns `post_content` byte-identical when every scenario's current tag
    already matches its target -- the common, real-world case (60/60 live
    generations so far) is a true no-op, not a reformat.
    """
    pre_facts = _extract_scenario_facts(parse_source_text(pre_content))
    post_facts = _extract_scenario_facts(parse_source_text(post_content))

    known_pre_ids = {
        fact.effective_scn_id for fact in pre_facts if fact.effective_scn_id is not None
    }

    targets: list[str | None] = []
    claimed: set[str] = set()
    for fact in post_facts:
        own_id = fact.own_scn_tag["name"].removeprefix("@") if fact.own_scn_tag else None
        if own_id is not None and own_id in known_pre_ids and own_id not in claimed:
            targets.append(own_id)
            claimed.add(own_id)
        else:
            targets.append(None)

    new_groups: dict[str, list[int]] = {}
    for index, (fact, target) in enumerate(zip(post_facts, targets, strict=True)):
        if target is not None:
            continue
        if not fact.ac_ids:
            continue  # untagged scenario: nothing to group under; CP2 will reject it
        new_groups.setdefault(fact.ac_ids[0], []).append(index)

    all_facts = pre_facts + post_facts
    for parent_ac_id, indices in new_groups.items():
        ac_short = parent_ac_id.removeprefix("AC-")
        offset = max(_used_ordinals_for_group(all_facts, ac_short), default=0)
        contents = [post_facts[i].canonical_content for i in indices]
        relative_ids = generate_scenario_ids(parent_ac_id, contents)
        for index, relative_id in zip(indices, relative_ids, strict=True):
            relative_ordinal = int(relative_id.rsplit("-", 1)[-1])
            targets[index] = f"SCN-{ac_short}-{offset + relative_ordinal:02d}"

    edits: list[tuple[_ScenarioFact, str]] = [
        (fact, target)
        for fact, target in zip(post_facts, targets, strict=True)
        if target is not None
        and (fact.own_scn_tag is None or fact.own_scn_tag["name"].removeprefix("@") != target)
    ]
    if not edits:
        return post_content

    post_source = parse_source_text(post_content)
    lines = list(post_source.lines)
    # Descending scenario-line order: an insertion (the zero-own-tags case)
    # adds a line, which would otherwise invalidate the still-to-process,
    # smaller line numbers of scenarios earlier in the document.
    def _scenario_line(pair: tuple[_ScenarioFact, str]) -> int:
        return pair[0].scenario_location["line"]

    for fact, target in sorted(edits, key=_scenario_line, reverse=True):
        new_tag_name = f"@{target}"
        if fact.own_scn_tag is not None:
            location = fact.own_scn_tag["location"]
            old_name = fact.own_scn_tag["name"]
            line_index = location["line"] - 1
            col_index = location["column"] - 1
            line = lines[line_index]
            lines[line_index] = line[:col_index] + new_tag_name + line[col_index + len(old_name) :]
        elif fact.last_own_tag_location is not None:
            line_index = fact.last_own_tag_location["line"] - 1
            lines[line_index] = lines[line_index] + " " + new_tag_name
        else:
            insert_at = fact.scenario_location["line"] - 1
            lines.insert(insert_at, "  " + new_tag_name)

    return "\n".join(lines)


def _relint(content: str, lint_config: dict[str, Any]) -> LintResult:
    return lint_source(parse_source_text(content), lint_config)


def _cp2_result_for(
    requirement: TestableRequirement,
    content: str,
    req_tag: str,
    lint_config: dict[str, Any],
) -> CP2Result:
    lint_result = _relint(content, lint_config)
    feature = rebuild_generated_feature(requirement, content, req_tag, lint_result)
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
        set of `AC-*` ids for coverage re-derivation (`rebuild_generated_feature`).
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
        raw_remediated = remediator.remediate(current_content, current_lint.violations)
        remediated = _remint_split_scenario_ids(current_content, raw_remediated)
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


__all__ = ["rebuild_generated_feature", "run_cp2_remediation"]
