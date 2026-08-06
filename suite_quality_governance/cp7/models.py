"""CP7's own result contracts: whole-suite Sonar quality governance
(ADR-0047 D1-D5).

**Report-only by construction (ADR-0047 D3).** CP5's own components split
along a deterministic-gates/advisory-hints line (`suite_quality_governance
.cp5.models`'s own module docstring); CP7 does not straddle that line at
all -- every metric it reads is REPORT-ONLY today, none of it gates
anything. `Cp7WholeSuiteQualityReport` therefore carries no
`overall_verdict`/`passed` field anywhere, the identical "no verdict
concept for a component that structurally never gates" shape
`Cp5NearDuplicateSweepResult` already establishes one component over, for
a related but distinct reason: there, the near-dup sweep is INHERENTLY
advisory (an embedding-derived hint, ADR-0040 Decision 2); here, CP7's own
measures are fully deterministic, server-computed numbers -- gating is
simply DEFERRED, not structurally inapplicable (ADR-0047 D3's own trigger:
the suite genuinely compiles and real, calibratable scores exist). A
future CP7 revision that adds gating adds a NEW result shape reusing these
same findings, per that same precedent -- it does not retrofit a verdict
onto this one.

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


__all__ = [
    "ALL_CP7_METRICS",
    "COVERAGE_AND_DUPLICATION_METRICS",
    "GENERIC_QUALITY_METRICS",
    "SECURITY_METRICS",
    "Cp7MeasureFinding",
    "Cp7WholeSuiteQualityReport",
]
