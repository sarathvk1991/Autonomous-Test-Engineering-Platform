"""CP5, component 4 of 4 -- aggregate-release cohesion (ADR-0046 D5, D6).

Checks whether the ASSEMBLED suite (the tracked baseline, or baseline plus
any newly-staged promotions -- component 3's own job to assemble; this
module takes whatever `project_root`/`catalog` it is handed) coheres as a
WHOLE, beyond each asset having already passed its own per-asset gates.
This module builds ONLY cohesion. It does not build promotion-wrapping
(component 3, the capstone that composes all four CP5 detectors) -- CP5's
remaining component.

ADR-0046 D5, quoted in full, is this component's own binding spec:

    "The compile boundary is the same live-tool-but-not-live-SUT line
    CP3/CP4 already drew, applied consistently... Invoking a JDK/Maven
    toolchain to compile the assembled suite is the same kind of
    dependency as CP3's Sonar server -- a build-time tool call, never a
    SUT or browser -- so it is consistently Layer 4's, not Layer 5's...
    'Does it then successfully run' (a smoke test passing) remains Layer
    5's...

    Ambiguous-glue detection, v1: exact pattern-string collision across
    distinct classes. Cucumber raises an 'Ambiguous step definitions'
    runtime error when two step-definition methods in different classes
    both match the same literal step text. The achievable first version
    compares every catalogued `StepDefinitionAsset.pattern` against every
    other's, flagging exact string matches attributed to different
    `class_name`s... Full Cucumber Expression/regex overlap detection...
    is a stretch goal, explicitly deferred."

**Both criteria are DETERMINISTIC, so both gate (ADR-0046 D6's own
composition table) -- unlike component 2's near-dup sweep.** Compiling is
a real subprocess invocation (a build-time TOOL, not a live SUT), but its
own PASS/FAIL outcome is exactly as deterministic as CP3's Sonar
quality-gate boolean; ambiguous-glue detection is pure string comparison,
no embedding involved at all. `Cp5CohesionResult.overall_verdict` is
therefore a real gate, mirroring `Cp3Result`/`Cp4Result`'s own shape --
unlike component 2's `Cp5NearDuplicateSweepResult`, which structurally has
no `overall_verdict` at all.

**Read-only w.r.t. the CATALOG's own detection (ambiguous-glue); the
compile check writes only build artifacts, never source.** Ambiguous-glue
detection never mutates anything -- pure comparison over an
already-reconciled `AssetCatalog`. The compile check invokes a real
`mvn test-compile`, which writes Maven's own build output (`target/`,
already `.gitignore`d in `test-suite-baseline/`) -- it never writes,
edits, or deletes a tracked SOURCE file; `LiveCompileChecker` never
constructs an argv capable of doing so (`compile_check.py`'s own module
docstring).
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from automation_engineering.catalog.models import AssetCatalog
from shared.enums.base import ValidationVerdict
from suite_quality_governance.cp5.compile_check import (
    CompileChecker,
    CompileError,
    run_compile_check,
)
from suite_quality_governance.cp5.models import (
    CRITERION_COMPILES,
    CRITERION_NO_AMBIGUOUS_GLUE,
    Cp5CohesionCriterionResult,
    Cp5CohesionResult,
)


def _evaluate_compiles(
    checker: CompileChecker, project_root: Path
) -> Cp5CohesionCriterionResult:
    """A deterministic pass/fail on whether the assembled suite's test
    sources compile (ADR-0040 Decision 2) -- mirrors
    `automation_engineering.cp3.gate._evaluate_sonar_gate`'s own shape
    exactly, including "fails closed, never crashes": a `CompileError`
    (missing `pom.xml`, `mvn` unreachable, an unexpected subprocess crash)
    is caught here and turned into a `FAIL` criterion, never propagated.
    """
    try:
        result = run_compile_check(checker, project_root)
    except CompileError as exc:
        return Cp5CohesionCriterionResult(
            criterion=CRITERION_COMPILES, verdict=ValidationVerdict.FAIL, messages=(str(exc),)
        )
    if result.passed:
        return Cp5CohesionCriterionResult(
            criterion=CRITERION_COMPILES, verdict=ValidationVerdict.PASS
        )
    return Cp5CohesionCriterionResult(
        criterion=CRITERION_COMPILES, verdict=ValidationVerdict.FAIL, messages=result.errors
    )


def _evaluate_no_ambiguous_glue(catalog: AssetCatalog) -> Cp5CohesionCriterionResult:
    """Ambiguous-glue v1 (ADR-0046 D5): exact pattern-string collision
    ACROSS DISTINCT CLASSES -- mirrors `automation_engineering.cp4.gate.
    _evaluate_duplicates`'s own cross-asset grouping shape exactly (group
    by the identifying key, flag only when more than one DISTINCT class
    participates).

    The SAME pattern declared twice within the SAME class is a different
    concern (CP3's own `duplicate_steps` criterion, ADR-0044 D5) and is
    NOT flagged here -- `classes` below collapses to a single entry for
    that case, `len(classes) > 1` correctly excludes it.
    """
    by_pattern: dict[str, list[str]] = defaultdict(list)
    for asset in catalog.step_definitions:
        by_pattern[asset.pattern].append(asset.class_name)

    messages: list[str] = []
    for pattern, class_names in sorted(by_pattern.items()):
        distinct_classes = sorted(set(class_names))
        if len(distinct_classes) > 1:
            messages.append(
                f"pattern {pattern!r} is bound in {len(distinct_classes)} different classes: "
                f"{', '.join(distinct_classes)} (Cucumber would raise "
                "'Ambiguous step definitions' for a matching step)"
            )
    verdict = ValidationVerdict.FAIL if messages else ValidationVerdict.PASS
    return Cp5CohesionCriterionResult(
        criterion=CRITERION_NO_AMBIGUOUS_GLUE, verdict=verdict, messages=tuple(messages)
    )


def evaluate_cohesion(
    catalog: AssetCatalog,
    project_root: Path,
    compile_checker: CompileChecker,
) -> Cp5CohesionResult:
    """CP5's aggregate-release cohesion component (ADR-0046 D5). `catalog`
    is an already-reconciled, caller-supplied input (ambiguous-glue
    detection never scans a filesystem itself); `project_root` is the
    already-assembled suite's own location (a workspace copy, or the
    tracked baseline -- this function does not decide which, mirroring
    `automation_engineering.cp3.models.Cp3SonarInput.project_root`'s own
    caller-decides discipline).

    `overall_verdict` is `PASS` iff BOTH criteria are `PASS` -- both
    deterministic, both gate (module docstring; ADR-0046 D6).
    """
    criteria = (
        _evaluate_compiles(compile_checker, project_root),
        _evaluate_no_ambiguous_glue(catalog),
    )
    overall_verdict = (
        ValidationVerdict.PASS
        if all(c.verdict == ValidationVerdict.PASS for c in criteria)
        else ValidationVerdict.FAIL
    )
    return Cp5CohesionResult(overall_verdict=overall_verdict, criteria=criteria)


__all__ = ["evaluate_cohesion"]
