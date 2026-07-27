"""CP2 — Layer 2's deterministic feature-governance gate.

ADR-0040 Decision 1 places CP2 at Layer 2 ("Gherkin lint + feature
governance"); Decision 2 requires every control-point gate to evaluate only
deterministic evidence. ADR-0043 D5 names CP2's own criteria, verbatim:
"lint result; acceptance-criteria coverage (every AC-* on the input
TestableRequirement has at least one mapped SCN-*); tag presence (@REQ-*/
@SCN-*/@AC-* all present per D2); duplicate detection (the no-dupe-* rules)."
The LLD's own two LLM-judged checks (Business readability, Step
reusability) are explicitly named as advisory-only, never gating -- see
:class:`~.models.CP2AdvisorySignals`.

:func:`evaluate_cp2` is a pure function: one
:class:`~feature_engineering.generation.models.GeneratedFeature` (already
validated and lint-computed by the generator core) in, one
:class:`~.models.CP2Result` out. No disk I/O, no network call, no LLM
provider -- this module never imports ``llm_factory``, mirroring the same
guard the generation core's own tests already carry. It builds no
remediation loop and no run-state wiring; see :mod:`.models` for exactly
which future consumer reads which field.

No threshold below 100%
------------------------
The Layer 2 LLD's own §15 "CP2 Validation Rules" table lists ">95%" for
"Naming Compliance" and "Tagging Compliance". ADR-0043 D5 -- the Accepted,
binding document ADR-0040 itself deferred CP2's rule catalogue to -- does
**not** carry either threshold forward. D5's own criteria are exact floors,
not percentages: "zero" lint violations, "every" AC-* covered, tag presence
"all present", "no" duplicates. ADR-0043's own preamble explicitly treats
the LLD as evidentiary input whose superseded sections are bound to their
superseding ADR decision, never taken as-is -- and D5 already made that
substitution for CP2 specifically. This implementation follows D5, not the
LLD: every criterion here is a 100%-exact computation. There is no `<100%`
threshold to implement, and none is silently hardcoded.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from feature_engineering.cp2.models import (
    CRITERION_AC_COVERAGE,
    CRITERION_DUPLICATE_DETECTION,
    CRITERION_LINT,
    CRITERION_TAG_PRESENCE,
    CP2CriterionResult,
    CP2Result,
)
from feature_engineering.generation.models import GeneratedFeature
from feature_engineering.gherkin_lint import (
    lint_in_memory_corpus,
    load_config,
    parse_source_text,
)
from shared.enums.base import ValidationVerdict

_LINTRC_PATH = Path("docs/reference/automation-poc/.gherkin-lintrc")
_AC_TAG_RE = re.compile(r"^@AC-\S+$")
_SCN_TAG_RE = re.compile(r"^@SCN-\S+$")


def evaluate_cp2(
    feature: GeneratedFeature,
    *,
    feature_set: Sequence[GeneratedFeature] | None = None,
) -> CP2Result:
    """Evaluate CP2's four deterministic criteria against one generated feature.

    Parameters
    ----------
    feature:
        The already-assembled, already-validated
        :class:`~feature_engineering.generation.models.GeneratedFeature` to
        gate.
    feature_set:
        Every ``GeneratedFeature`` produced in the same run, ``feature``
        included -- required only for the corpus-scoped
        ``no-dupe-feature-names`` sub-check of ``duplicate_detection``
        (ADR-0043 D3: "cross-file by definition", unreachable from a single
        feature). When omitted, that sub-check is reported as not evaluated
        and never fails the gate on its own account -- the scenario-scoped
        ``no-dupe-scenario-names`` sub-check is always evaluated regardless.

    Returns
    -------
    CP2Result
        ``overall_verdict`` is ``PASS`` iff every criterion's own verdict is
        ``PASS``. Deterministic: the same ``feature`` (and ``feature_set``)
        always yields the same result.
    """
    criteria = (
        _evaluate_lint(feature),
        _evaluate_ac_coverage(feature),
        _evaluate_tag_presence(feature),
        _evaluate_duplicate_detection(feature, feature_set),
    )
    overall = (
        ValidationVerdict.PASS
        if all(c.verdict == ValidationVerdict.PASS for c in criteria)
        else ValidationVerdict.FAIL
    )
    return CP2Result(
        requirement_id=feature.requirement_id,
        overall_verdict=overall,
        criteria=criteria,
        # RESERVED, never set here -- see CP2AdvisorySignals: this evaluator
        # produces no LLM-judged signal and structurally cannot gate on one.
        advisory=None,
    )


def _evaluate_lint(feature: GeneratedFeature) -> CP2CriterionResult:
    """D5 criterion 1: "lint result" -- reuses `feature.lint_result`
    verbatim; CP2 never re-lints the content differently."""
    if feature.lint_result.is_clean:
        return CP2CriterionResult(criterion=CRITERION_LINT, verdict=ValidationVerdict.PASS)
    messages = tuple(
        f"{v.rule} (line {v.line}): {v.message}" for v in feature.lint_result.violations
    )
    return CP2CriterionResult(
        criterion=CRITERION_LINT, verdict=ValidationVerdict.FAIL, messages=messages
    )


def _evaluate_ac_coverage(feature: GeneratedFeature) -> CP2CriterionResult:
    """D5 criterion 2: "acceptance-criteria coverage (every AC-* ... has at
    least one mapped SCN-*)" -- reuses `feature.fully_covered`/
    `acceptance_criteria_coverage` verbatim; 100%, no percentage threshold."""
    if feature.fully_covered:
        return CP2CriterionResult(criterion=CRITERION_AC_COVERAGE, verdict=ValidationVerdict.PASS)
    uncovered = sorted(
        ac_id for ac_id, covered in feature.acceptance_criteria_coverage.items() if not covered
    )
    messages = tuple(
        f"{ac_id}: no scenario maps to this acceptance criterion" for ac_id in uncovered
    )
    return CP2CriterionResult(
        criterion=CRITERION_AC_COVERAGE, verdict=ValidationVerdict.FAIL, messages=messages
    )


def _evaluate_tag_presence(feature: GeneratedFeature) -> CP2CriterionResult:
    """D5 criterion 3: "tag presence (@REQ-*/@SCN-*/@AC-* all present per
    D2)", extended per this task's own BUILD scope to the generate-feature
    contract's "each scenario carries >=1 functional tag" requirement.

    Independently re-parses `feature.content` (in-memory, no disk I/O) so
    this is a real, self-contained governance check -- not a re-read of
    fields the core already computed -- and so a future core regression
    that stops honoring its own tag contract is still caught here. A
    scenario's *effective* tag set is its own tags UNION the Feature-level
    tags: the D2 hoist-extension note establishes Cucumber resolves
    Feature- and scenario-level tags identically for a scenario, so a
    hoisted functional/AC tag still counts as "carried" by every scenario
    it was hoisted from.
    """
    source = parse_source_text(feature.content, path=feature.requirement_id)
    messages: list[str] = []

    if source.feature is None:
        return CP2CriterionResult(
            criterion=CRITERION_TAG_PRESENCE,
            verdict=ValidationVerdict.FAIL,
            messages=(
                f"assembled content for {feature.requirement_id} did not parse as a Feature",
            ),
        )

    feature_tags = {t["name"] for t in source.feature.get("tags", [])}
    if feature.req_tag not in feature_tags:
        messages.append(f"{feature.req_tag} is missing from the Feature-level tag line")

    scenario_nodes = [
        c["scenario"] for c in source.feature.get("children", []) if c.get("scenario")
    ]
    if not scenario_nodes:
        messages.append("no scenarios found to check tag presence against")

    for scenario_node in scenario_nodes:
        name = scenario_node.get("name") or "<unnamed>"
        own_tags = {t["name"] for t in scenario_node.get("tags", [])}

        if feature.req_tag in own_tags:
            messages.append(
                f"scenario {name!r}: {feature.req_tag} must never appear at scenario scope"
            )

        # @SCN-* is unique per scenario by construction, so it is never
        # homogenous across TWO OR MORE distinct scenarios and stays
        # scenario-level there -- but for a single-scenario feature (n=1)
        # it IS trivially homogenous (the one scenario's own tag set,
        # intersected with itself) and correctly hoists, same as @AC-*
        # (the existing, already-tested single-scenario hoist case). The
        # check must therefore look at the EFFECTIVE tag set, exactly like
        # @AC-* and the functional-tag check below.
        effective_tags = own_tags | feature_tags
        scn_tags = [t for t in effective_tags if _SCN_TAG_RE.match(t)]
        if len(scn_tags) != 1:
            messages.append(
                f"scenario {name!r}: expected exactly one @SCN-* tag "
                f"(scenario-level or hoisted), found {len(scn_tags)}"
            )

        ac_tags = [t for t in effective_tags if _AC_TAG_RE.match(t)]
        if not ac_tags:
            messages.append(f"scenario {name!r}: no @AC-* tag present (scenario-level or hoisted)")

        functional_tags = [
            t
            for t in effective_tags
            if t != feature.req_tag and not _AC_TAG_RE.match(t) and not _SCN_TAG_RE.match(t)
        ]
        if not functional_tags:
            messages.append(
                f"scenario {name!r}: no functional tag present (scenario-level or hoisted)"
            )

    verdict = ValidationVerdict.FAIL if messages else ValidationVerdict.PASS
    return CP2CriterionResult(
        criterion=CRITERION_TAG_PRESENCE, verdict=verdict, messages=tuple(messages)
    )


def _evaluate_duplicate_detection(
    feature: GeneratedFeature, feature_set: Sequence[GeneratedFeature] | None
) -> CP2CriterionResult:
    """D5 criterion 4: "duplicate detection (the no-dupe-* rules)" -- both
    `no-dupe-scenario-names` (in-feature, always evaluable from
    `feature.lint_result`) and `no-dupe-feature-names` (cross-file, D3;
    evaluated only when `feature_set` is supplied, via the SAME committed,
    D3-locked rule (`lint_in_memory_corpus`) the workspace-scoped lint
    stage would use -- never a reimplemented duplicate check).

    Ordering note (inherited from the committed rule, not a CP2 defect):
    `no-dupe-feature-names` flags the *second and later* occurrence of a
    repeated Feature name, never the first -- this is `gherkin-lint`'s own,
    D3-locked behaviour (`feature_engineering/gherkin_lint/rules.py`,
    `no_dupe_feature_names`), reused verbatim here, not reinvented.
    """
    scenario_dupe_violations = feature.lint_result.for_rule("no-dupe-scenario-names")
    messages: list[str] = [
        f"no-dupe-scenario-names (line {v.line}): {v.message}" for v in scenario_dupe_violations
    ]

    corpus_scope_failed = False
    if feature_set is None:
        messages.append(
            "no-dupe-feature-names: not evaluated -- no feature_set was supplied. This "
            "corpus-scoped check (ADR-0043 D3) requires every sibling GeneratedFeature in "
            "the same run; its absence here does not fail the gate on its own."
        )
    else:
        sources = [
            parse_source_text(f.content, path=f.requirement_id) for f in feature_set
        ]
        config = load_config(_LINTRC_PATH)
        corpus_result = lint_in_memory_corpus(sources, config)
        own_violations = corpus_result.for_rule("no-dupe-feature-names")
        this_file_violations = [v for v in own_violations if v.file == feature.requirement_id]
        if this_file_violations:
            corpus_scope_failed = True
            messages.extend(f"no-dupe-feature-names: {v.message}" for v in this_file_violations)

    verdict = (
        ValidationVerdict.FAIL
        if (scenario_dupe_violations or corpus_scope_failed)
        else ValidationVerdict.PASS
    )
    return CP2CriterionResult(
        criterion=CRITERION_DUPLICATE_DETECTION, verdict=verdict, messages=tuple(messages)
    )


__all__ = ["evaluate_cp2"]
