"""CP3's deterministic coverage gate (ADR-0044 D5) -- static, always-
runnable, no infrastructure of any kind: no network call, no subprocess, no
Sonar. Computed from two already-in-hand inputs only, per D5's own words
("computed from the generated Java and feature files alone"):

* the real ``.feature`` text, re-parsed with the SAME Gherkin parser CP2
  already uses (:func:`feature_engineering.gherkin_lint.parse_source_text`)
  -- this module never invents a second Gherkin parser;
* the ``StepDefinitionOutcome`` a generation run already computed for each
  step (:mod:`automation_engineering.generation.orchestrator`'s own output)
  -- this module never re-runs the reuse engine or a generator; it only
  checks that every step the feature file declares actually got a mapped
  outcome, and that the post-run step-definition catalog carries no
  pattern collision.

Four named criteria, matching D5's own four verbatim:

* ``step_coverage`` / ``unmapped_steps`` -- the SAME underlying
  computation ("does every step have a binding"), reported under both of
  D5's own two names (mirroring CP2's own established precedent of one
  underlying fact failing more than one named criterion, e.g. a duplicate
  scenario name failing both ``lint`` and ``duplicate_detection`` --
  :mod:`feature_engineering.cp2.evaluator`). ``step_coverage``'s own
  message is a summary count; ``unmapped_steps``'s is the itemized list.
* ``scenario_coverage`` -- a scenario is covered iff every one of its own
  steps is.
* ``duplicate_steps`` -- computed independently, over the post-run
  step-definition asset catalog alone (not the outcome set): two catalog
  assets sharing the identical Cucumber ``pattern`` is what Cucumber
  itself calls ambiguous/duplicate glue, regardless of which Gherkin step
  either one happens to satisfy in this run.

Reuse percentage (:class:`~.models.Cp3ReuseReport`) is computed here too,
alongside the four gating criteria, but is never one of them -- nothing in
:mod:`.gate` reads it when deriving ``overall_verdict``.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from automation_engineering.catalog.models import StepDefinitionAsset
from automation_engineering.cp3.models import (
    CRITERION_DUPLICATE_STEPS,
    CRITERION_SCENARIO_COVERAGE,
    CRITERION_STEP_COVERAGE,
    CRITERION_UNMAPPED_STEPS,
    Cp3CoverageInput,
    Cp3CriterionResult,
    Cp3FeatureInput,
    Cp3ReuseReport,
)
from automation_engineering.generation.models import (
    BoundStepDefinition,
    EscalatedStepNeed,
    GeneratedStepDefinition,
    StepDefinitionOutcome,
)
from feature_engineering.gherkin_lint import parse_source_text
from shared.enums.base import ValidationVerdict

_SCN_TAG_RE = re.compile(r"^@SCN-\S+$")


@dataclass(frozen=True, slots=True)
class _ScenarioSteps:
    scn_id: str
    scenario_name: str
    step_texts: tuple[str, ...]


def _extract_scenarios(content: str, *, path: str) -> tuple[_ScenarioSteps, ...]:
    """Every scenario's own ``@SCN-*`` id (falling back to its plain name
    when untagged) plus its ordered, keyword-stripped step texts -- exactly
    the shape :class:`~automation_engineering.reuse.models.GherkinStepNeed.text`
    already uses, so a step text extracted here matches an outcome's own
    ``need.text`` by simple equality, no normalization needed.
    """
    source = parse_source_text(content, path=path)
    feature = source.feature
    if not feature:
        return ()
    scenarios: list[_ScenarioSteps] = []
    for child in feature.get("children", []):
        scenario = child.get("scenario")
        if scenario is None:
            continue
        scn_id = next(
            (tag["name"] for tag in scenario.get("tags", []) if _SCN_TAG_RE.match(tag["name"])),
            scenario.get("name", ""),
        )
        step_texts = tuple(step.get("text", "") for step in scenario.get("steps", []))
        scenarios.append(
            _ScenarioSteps(
                scn_id=scn_id, scenario_name=scenario.get("name", ""), step_texts=step_texts
            )
        )
    return tuple(scenarios)


def _is_mapped(outcome: StepDefinitionOutcome | None) -> bool:
    return isinstance(outcome, GeneratedStepDefinition | BoundStepDefinition)


def _find_duplicate_patterns(assets: tuple[StepDefinitionAsset, ...]) -> tuple[str, ...]:
    by_pattern: dict[str, list[StepDefinitionAsset]] = defaultdict(list)
    for asset in assets:
        by_pattern[asset.pattern].append(asset)
    messages: list[str] = []
    for pattern in sorted(by_pattern):
        group = by_pattern[pattern]
        if len(group) > 1:
            ids = ", ".join(f"{a.asset_id} ({a.class_name}#{a.method_name})" for a in group)
            messages.append(
                f"pattern {pattern!r} bound by {len(group)} step-definition assets: {ids}"
            )
    return tuple(messages)


def _compute_reuse(features: tuple[Cp3FeatureInput, ...]) -> Cp3ReuseReport:
    reused = generated = escalated = 0
    for feature in features:
        for outcome in feature.outcomes:
            if isinstance(outcome, BoundStepDefinition):
                reused += 1
            elif isinstance(outcome, GeneratedStepDefinition):
                generated += 1
            elif isinstance(outcome, EscalatedStepNeed):
                escalated += 1
    denominator = reused + generated
    percentage = (reused / denominator * 100.0) if denominator else 0.0
    return Cp3ReuseReport(
        reused=reused, generated=generated, escalated=escalated, reuse_percentage=percentage
    )


def evaluate_coverage(
    coverage_input: Cp3CoverageInput,
) -> tuple[tuple[Cp3CriterionResult, ...], Cp3ReuseReport]:
    """Evaluate CP3's four deterministic coverage criteria plus the
    (never-gating) reuse report.

    Returns
    -------
    tuple[tuple[Cp3CriterionResult, ...], Cp3ReuseReport]
        Four criteria, in :data:`~.models.CP3_CRITERIA` order (step
        coverage, scenario coverage, unmapped steps, duplicate steps), and
        the reuse report. Deterministic: the same input always yields the
        same result, and this function makes no network call.
    """
    outcome_by_text: dict[str, StepDefinitionOutcome] = {}
    for feature in coverage_input.features:
        for outcome in feature.outcomes:
            outcome_by_text[outcome.need.text] = outcome

    total_steps = 0
    unmapped_count = 0
    unmapped_messages: list[str] = []
    scenario_messages: list[str] = []

    for feature in coverage_input.features:
        for scenario in _extract_scenarios(feature.content, path=str(feature.file_path)):
            scenario_unmapped = 0
            for step_text in scenario.step_texts:
                total_steps += 1
                found = outcome_by_text.get(step_text)
                if _is_mapped(found):
                    continue
                unmapped_count += 1
                scenario_unmapped += 1
                reason = (
                    "no outcome computed for this step"
                    if found is None
                    else "escalated, no automatic binding"
                )
                unmapped_messages.append(
                    f"{scenario.scn_id} ({scenario.scenario_name!r}): {step_text!r} -- {reason}"
                )
            if scenario_unmapped:
                scenario_messages.append(
                    f"{scenario.scn_id} ({scenario.scenario_name!r}): "
                    f"{scenario_unmapped}/{len(scenario.step_texts)} steps unmapped"
                )

    step_coverage_messages: tuple[str, ...] = ()
    if unmapped_count:
        mapped = total_steps - unmapped_count
        percentage = (mapped / total_steps * 100.0) if total_steps else 0.0
        step_coverage_messages = (
            f"{unmapped_count}/{total_steps} steps unmapped ({percentage:.1f}% step coverage)",
        )

    coverage_verdict = ValidationVerdict.FAIL if unmapped_count else ValidationVerdict.PASS
    duplicate_messages = _find_duplicate_patterns(coverage_input.step_definition_assets)
    duplicate_verdict = ValidationVerdict.FAIL if duplicate_messages else ValidationVerdict.PASS

    criteria = (
        Cp3CriterionResult(
            criterion=CRITERION_STEP_COVERAGE,
            verdict=coverage_verdict,
            messages=step_coverage_messages,
        ),
        Cp3CriterionResult(
            criterion=CRITERION_SCENARIO_COVERAGE,
            verdict=ValidationVerdict.FAIL if scenario_messages else ValidationVerdict.PASS,
            messages=tuple(scenario_messages),
        ),
        Cp3CriterionResult(
            criterion=CRITERION_UNMAPPED_STEPS,
            verdict=coverage_verdict,
            messages=tuple(unmapped_messages),
        ),
        Cp3CriterionResult(
            criterion=CRITERION_DUPLICATE_STEPS,
            verdict=duplicate_verdict,
            messages=duplicate_messages,
        ),
    )
    return criteria, _compute_reuse(coverage_input.features)


__all__ = ["evaluate_coverage"]
