"""CP3's structured result contract (ADR-0044 D5, ADR-0040 Decision 1/2).

D5 names CP3's own deterministic criteria, verbatim: "step coverage = 100%,
scenario coverage = 100%, zero unmapped steps, zero duplicate steps" --
computed statically from the generated Java and feature files alone -- PLUS
a fifth, hard-gating criterion this ADR locks as binding, not deferred:
"CP3 does not pass unless a running SonarQube server scans the generated
Java and its quality gate -- evaluated against the ``customqa:*`` profile
-- passes." Reuse percentage is REPORTED (:class:`Cp3ReuseReport`), never
one of these gating criteria -- D5's own words: "reuse % is reported,
never gated," mirroring ADR-0043 D5's exact-floors-not-percentages
discipline for CP2.

**Sixth criterion, added 2026-08-04 (ADR-0044 D5 revision, the F4 discovery's
Path A).** The fifth criterion's own ``customqa:*`` profile splits: only
part of it (``long-method``) is expressible as a SonarQube rule at all --
``direct-webdriver-action`` is an architectural, caller-class-role
constraint SonarQube cannot natively express. It is verified instead by a
static, ``javalang``-based check (:mod:`automation_engineering.cp3
.architecture`), a sixth CP3 criterion, not a Sonar-side addition.

**Seventh criterion, added 2026-08-05 (ADR-0044 D5's third revision, the
Sonar-config discovery).** ``long-method`` itself moves off the Sonar gate:
its own backing rule, ``java:S138``, is permanently ``scope:MAIN`` on this
server (a rule-catalog property, not something a profile's activation can
override), and this platform's generated code is deliberately placed under
``src/test/java`` (ADR-0037 Path A) -- ``S138`` structurally cannot reach
it, on any project, ever. ``long-method`` is therefore verified instead by
its own static, ``javalang``-based check
(:func:`automation_engineering.cp3.architecture.evaluate_long_method`), the
same mechanism ``direct-webdriver-action`` already uses -- a seventh CP3
criterion. **CP3's Sonar gate now verifies only generic Java quality** (the
built-in profile's own stock rules, e.g. ``Sonar way``) -- neither
``customqa:*`` rule is Sonar-gated any longer; both are static. CP3's own
composite gate is therefore coverage (four criteria) + the Sonar quality
gate (generic Java quality) + ``direct-webdriver-action`` (static) +
``long-method`` (static), all seven required for ``PASS``.

Mirrors :mod:`feature_engineering.cp2.models` deliberately -- same
``<Prefix>CriterionResult``/``<Prefix>Result`` shape, same ``.criterion(name)``
lookup, same ``overall_verdict`` derived from ``criteria`` alone -- so a
CP3 result reads exactly like a CP2 result to any future caller (run-state,
a remediation loop) that already knows CP2's shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from automation_engineering.catalog.models import StepDefinitionAsset
from automation_engineering.generation.models import StepDefinitionOutcome
from shared.enums.base import ValidationVerdict

#: D5's own four deterministic coverage criteria, verbatim, plus the fifth
#: (Sonar) criterion D5 locks as a hard CP3 requirement -- now GENERIC Java
#: quality only (2026-08-05 revision, below) -- plus a sixth,
#: direct_webdriver_action, and a seventh, long_method (ADR-0044 D5's third
#: revision, 2026-08-05) -- BOTH customqa:* rules are static, javalang-based
#: checks (:mod:`automation_engineering.cp3.architecture`), neither Sonar-
#: gated. CP3's composite gate is now: coverage (four criteria, static) +
#: the Sonar quality gate (generic Java quality) + direct_webdriver_action
#: (static) + long_method (static). All seven required for PASS.
CRITERION_STEP_COVERAGE = "step_coverage"
CRITERION_SCENARIO_COVERAGE = "scenario_coverage"
CRITERION_UNMAPPED_STEPS = "unmapped_steps"
CRITERION_DUPLICATE_STEPS = "duplicate_steps"
CRITERION_SONAR_QUALITY_GATE = "sonar_quality_gate"
CRITERION_DIRECT_WEBDRIVER_ACTION = "direct_webdriver_action"
CRITERION_LONG_METHOD = "long_method"

CP3_CRITERIA: tuple[str, ...] = (
    CRITERION_STEP_COVERAGE,
    CRITERION_SCENARIO_COVERAGE,
    CRITERION_UNMAPPED_STEPS,
    CRITERION_DUPLICATE_STEPS,
    CRITERION_SONAR_QUALITY_GATE,
    CRITERION_DIRECT_WEBDRIVER_ACTION,
    CRITERION_LONG_METHOD,
)


@dataclass(frozen=True, slots=True)
class Cp3CriterionResult:
    """One CP3 gate criterion's own deterministic verdict -- see
    :class:`feature_engineering.cp2.models.CP2CriterionResult`, the same
    shape. ``messages`` is empty on a clean ``PASS``, one entry per
    distinct problem on a ``FAIL``.
    """

    criterion: str
    verdict: ValidationVerdict
    messages: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Cp3ReuseReport:
    """Reuse percentage, REPORTED only -- read by nothing in this package's
    own verdict computation (:mod:`.gate`). ``reuse_percentage`` is
    ``reused / (reused + generated) * 100``, or ``0.0`` when that
    denominator is zero (an empty-catalog bootstrap run, or a run whose
    every step escalated) -- zero is the honest value, never a failure
    (D5: "an empty catalog's bootstrap run reuses 0% of its steps --
    correctly, not as a failure").
    """

    reused: int
    generated: int
    escalated: int
    reuse_percentage: float


@dataclass(frozen=True, slots=True)
class Cp3FeatureInput:
    """One ``.feature`` file's own real Gherkin text plus the step-
    definition outcomes a generation run already produced for its steps
    (:mod:`automation_engineering.generation.orchestrator`'s own
    ``StepDefinitionOutcome`` union) -- CP3 gates on what generation
    already decided, it never re-runs the reuse engine or the generator
    itself (ADR-0040 Decision 2: a control point gates on deterministic
    evidence, it does not re-derive it).
    """

    content: str
    file_path: Path
    outcomes: tuple[StepDefinitionOutcome, ...]


@dataclass(frozen=True, slots=True)
class Cp3CoverageInput:
    """Everything the deterministic coverage gate (:mod:`.coverage`) needs:
    every feature this run touched, plus the post-run step-definition
    asset catalog (:class:`~automation_engineering.catalog.models.
    StepDefinitionAsset`) the duplicate-steps criterion scans for pattern
    collisions.
    """

    features: tuple[Cp3FeatureInput, ...]
    step_definition_assets: tuple[StepDefinitionAsset, ...] = ()


@dataclass(frozen=True, slots=True)
class Cp3Result:
    """The single output of one CP3 evaluation (:func:`automation_engineering.
    cp3.gate.evaluate_cp3`). ``overall_verdict`` is ``PASS`` iff every one
    of the seven named criteria is ``PASS`` -- the coverage gate, the Sonar
    gate (generic Java quality), and the static direct-webdriver-action AND
    long-method checks, all required."""

    overall_verdict: ValidationVerdict
    criteria: tuple[Cp3CriterionResult, ...]
    reuse: Cp3ReuseReport

    def criterion(self, name: str) -> Cp3CriterionResult:
        """Return the named criterion's result.

        Raises
        ------
        KeyError
            If no criterion with this name was evaluated.
        """
        for c in self.criteria:
            if c.criterion == name:
                return c
        raise KeyError(f"No CP3 criterion named {name!r} in this result.")

    @property
    def passed(self) -> bool:
        return self.overall_verdict == ValidationVerdict.PASS


__all__ = [
    "CP3_CRITERIA",
    "CRITERION_DIRECT_WEBDRIVER_ACTION",
    "CRITERION_DUPLICATE_STEPS",
    "CRITERION_LONG_METHOD",
    "CRITERION_SCENARIO_COVERAGE",
    "CRITERION_SONAR_QUALITY_GATE",
    "CRITERION_STEP_COVERAGE",
    "CRITERION_UNMAPPED_STEPS",
    "Cp3CoverageInput",
    "Cp3CriterionResult",
    "Cp3FeatureInput",
    "Cp3Result",
    "Cp3ReuseReport",
]
