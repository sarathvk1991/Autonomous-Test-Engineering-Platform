"""CP7's own result contracts: whole-suite Sonar quality governance
(ADR-0047 D1-D5, D3's own rating-gating amendment note, 2026-08-10).

**Report-only by construction for `Cp7WholeSuiteQualityReport` (ADR-0047
D3).** CP5's own components split along a deterministic-gates/advisory-
hints line (`suite_quality_governance.cp5.models`'s own module docstring);
`Cp7WholeSuiteQualityReport` does not straddle that line at all -- every
metric it carries is REPORT-ONLY, none of it gates anything, and it
carries no `overall_verdict`/`passed` field anywhere, the identical "no
verdict concept for a component that structurally never gates" shape
`Cp5NearDuplicateSweepResult` already establishes one component over, for
a related but distinct reason: there, the near-dup sweep is INHERENTLY
advisory (an embedding-derived hint, ADR-0040 Decision 2); here, the
REPORT's own measures are fully deterministic, server-computed numbers --
gating was simply DEFERRED for them, per-metric, not structurally
inapplicable.

**`reliability_rating`/`sqale_rating` now gate, via a SEPARATE result
shape (D3's own amendment note, 2026-08-10) -- `Cp7RatingGateResult`,
below.** ADR-0047 D3's own pre-declared trigger (the suite genuinely
compiles and a fresh Sonar scan against that compiling state produces
real, calibratable scores) is now met -- confirmed against a live scan
whose own `revision` matched the current tracked baseline's own commit
exactly. Rather than retrofit a verdict onto `Cp7WholeSuiteQualityReport`
itself (breaking every existing caller's "this type never gates"
assumption), gating lives in its own additive result
(`Cp7RatingGateResult`) computed FROM the same report
(`suite_quality_governance.cp7.rating_gate.evaluate_rating_gate`) --
mirroring how CP5's own near-dup sweep and cohesion gate are two
DIFFERENT result shapes over related inputs, never one shape straddling
both roles. `Cp7WholeSuiteQualityReport` itself is UNCHANGED by this
addition -- still report-only, still no verdict field -- it is simply no
longer the only CP7 result shape that exists.

Three metric families, each named explicitly by ADR-0047's own Decision
text, never invented here:

* **Generic quality (D3)** -- `violations`, `bugs`, `code_smells`,
  `sqale_rating`, `reliability_rating`. Currently unmeasured only in the
  sense that no calibrated threshold exists yet (D3) -- these five ARE
  populated on the real server today (ADR-0047 D10).
* **Security (D4)** -- `vulnerabilities`, `security_hotspots`,
  `security_rating`. Populated today; deliberately never gated (D4's own
  two reasons: the hotspot review/triage endpoint is permission-gated
  beyond the pipeline's own token, and test-automation code's own real
  security profile is thin).
* **Coverage and duplication (D5)** -- `coverage`,
  `duplicated_lines_density`. Genuinely UNMEASURED on the real server
  today (no JaCoCo report is ever submitted) -- every
  `Cp7MeasureFinding` in this family is expected to carry `value=None`
  until that separate, tracked prerequisite closes.
"""

from __future__ import annotations

from dataclasses import dataclass

from shared.enums.base import ValidationVerdict

#: ADR-0047 D3's own literal enumeration -- quoted, not paraphrased:
#: "every metric it reads (`violations`, `bugs`, `code_smells`,
#: `sqale_rating`, `reliability_rating`)". `sqale_index` (raw
#: maintainability-debt minutes) is a real, ADR-0047-D10-confirmed-readable
#: metric NOT named in D3's own list -- deliberately excluded here rather
#: than added speculatively; D3's own five are what CP7 reports, no more.
GENERIC_QUALITY_METRICS: tuple[str, ...] = (
    "violations",
    "bugs",
    "code_smells",
    "sqale_rating",
    "reliability_rating",
)

#: ADR-0047 D4's own literal enumeration.
SECURITY_METRICS: tuple[str, ...] = ("vulnerabilities", "security_hotspots", "security_rating")

#: ADR-0047 D5's own literal enumeration -- both genuinely unmeasured on
#: the real server today (module docstring).
COVERAGE_AND_DUPLICATION_METRICS: tuple[str, ...] = ("coverage", "duplicated_lines_density")

#: The full set CP7 fetches in one call, D3+D4+D5's own lists concatenated
#: -- one `fetch_measures` call per report (`suite_quality_governance.cp7
#: .measures.fetch_whole_suite_quality_report`), never one call per family.
ALL_CP7_METRICS: tuple[str, ...] = (
    *GENERIC_QUALITY_METRICS,
    *SECURITY_METRICS,
    *COVERAGE_AND_DUPLICATION_METRICS,
)


@dataclass(frozen=True, slots=True)
class Cp7MeasureFinding:
    """One metric's own reported value, or its own honest absence.

    `value` is `None` when the server has no computed value for this
    metric (ADR-0047 D5) -- NEVER defaulted to a passing-looking value
    ("0", "1.0") and never silently dropped from the report. `measured`
    is the one property a report renderer needs to tell "clean" apart
    from "not yet knowable" -- the exact distinction ADR-0047 D5 itself
    calls out as load-bearing ("a state distinct from and never conflated
    with 'measured and clean'").
    """

    metric_key: str
    value: str | None

    @property
    def measured(self) -> bool:
        return self.value is not None


@dataclass(frozen=True, slots=True)
class Cp7WholeSuiteQualityReport:
    """CP7's own capstone -- the whole-suite Sonar quality report
    (ADR-0047 D1-D5). Deliberately no `overall_verdict`/`passed` field
    (module docstring): this is a REPORT, not a gate. `project_key` is
    carried through so a report consumer never has to guess which Sonar
    project it describes.
    """

    project_key: str
    generic_quality: tuple[Cp7MeasureFinding, ...]
    security: tuple[Cp7MeasureFinding, ...]
    coverage_and_duplication: tuple[Cp7MeasureFinding, ...]

    @property
    def all_findings(self) -> tuple[Cp7MeasureFinding, ...]:
        return (*self.generic_quality, *self.security, *self.coverage_and_duplication)

    @property
    def has_unmeasured_findings(self) -> bool:
        """True whenever at least one metric this report requested has no
        server-side value yet (ADR-0047 D5's own "not yet measured" state)
        -- informational only; this NEVER gates (module docstring)."""
        return any(not finding.measured for finding in self.all_findings)


#: D3's own amendment note (2026-08-10) names exactly these two RATINGS as
#: the gating candidates -- never the raw counts (`violations`/`bugs`/
#: `code_smells`), which stay report-only alongside security/coverage.
CRITERION_RELIABILITY_RATING_GATE = "reliability_rating_gate"
CRITERION_SQALE_RATING_GATE = "sqale_rating_gate"

#: One-to-one with the two gating criteria above, in the same order.
RATING_GATE_METRICS: tuple[str, ...] = ("reliability_rating", "sqale_rating")

#: Sonar's own rating scale is 1.0=A .. 5.0=E. The gate floor is A-or-B
#: (<= 2.0) -- one notch of headroom above this suite's own real, current
#: A/A measurement (D3's amendment note): gates a genuine regression to
#: C/D/E, never demands perfection from the very next MAJOR-severity smell.
RATING_GATE_MAX_VALUE = 2.0


@dataclass(frozen=True, slots=True)
class Cp7RatingGateCriterionResult:
    """One rating's own gate verdict -- mirrors
    `suite_quality_governance.cp8.models.Cp8CriterionResult`'s shape.

    `verdict` is `ValidationVerdict.WARN`, never `FAIL`, when `value` is
    `None` (the rating was never measured -- Sonar unavailable, or the
    server returned no value for this specific metric) -- an unmeasured
    rating is honestly unknown, not a release-blocking regression (D3's
    amendment note: mirrors CP1's own governed FAIL > WARN > PASS
    aggregation, `requirement_intelligence.cp1.engine.cp1_engine
    ._derive_verdict`, ADR-0012 §8).
    """

    criterion: str
    metric_key: str
    verdict: ValidationVerdict
    value: str | None
    detail: str


@dataclass(frozen=True, slots=True)
class Cp7RatingGateResult:
    """CP7's own rating-gate verdict (ADR-0047 D3's amendment note,
    2026-08-10) -- a REAL, deterministic PASS/WARN/FAIL over exactly the
    two rating criteria (`RATING_GATE_METRICS`), computed FROM an already-
    fetched `Cp7WholeSuiteQualityReport` (or its own honest absence).
    Deliberately a SEPARATE type from `Cp7WholeSuiteQualityReport` (module
    docstring) -- that type stays report-only and verdict-free; this one
    is CP7's own new, additive gating half.

    `overall_verdict` is `FAIL` iff any criterion is `FAIL`; else `WARN`
    iff any criterion is `WARN` (a rating went unmeasured); else `PASS` --
    the identical aggregation `requirement_intelligence.cp1.engine
    .cp1_engine._derive_verdict` already establishes (ADR-0012 §8), reused
    here rather than a new rule invented for this one gate.
    """

    overall_verdict: ValidationVerdict
    criteria: tuple[Cp7RatingGateCriterionResult, ...]

    def criterion(self, name: str) -> Cp7RatingGateCriterionResult:
        """Return the named criterion's result.

        Raises
        ------
        KeyError
            If no criterion with this name was evaluated.
        """
        for c in self.criteria:
            if c.criterion == name:
                return c
        raise KeyError(f"No CP7 rating-gate criterion named {name!r} in this result.")

    @property
    def passed(self) -> bool:
        """`True` for `PASS` AND `WARN` -- an unmeasured rating never blocks
        (module docstring); only a real, measured, worse-than-B rating
        (`FAIL`) does. Mirrors `Cp7ReportOutcome.available`'s own "distinct,
        honest, non-fatal absence" shape one level up."""
        return self.overall_verdict != ValidationVerdict.FAIL


__all__ = [
    "ALL_CP7_METRICS",
    "COVERAGE_AND_DUPLICATION_METRICS",
    "CRITERION_RELIABILITY_RATING_GATE",
    "CRITERION_SQALE_RATING_GATE",
    "GENERIC_QUALITY_METRICS",
    "RATING_GATE_MAX_VALUE",
    "RATING_GATE_METRICS",
    "SECURITY_METRICS",
    "Cp7MeasureFinding",
    "Cp7RatingGateCriterionResult",
    "Cp7RatingGateResult",
    "Cp7WholeSuiteQualityReport",
]
