"""CP8's own result contracts: static execution-readiness governance
(ADR-0047 D7-D9).

**A real, gating deterministic result -- unlike CP7's own report-only
shape.** `Cp7WholeSuiteQualityReport` (`suite_quality_governance.cp7
.models`) deliberately carries no verdict field (ADR-0047 D3). CP8 is the
opposite case (ADR-0047 D9): "CP8 gates immediately, as a real
deterministic PASS/FAIL, from its first implementation." `Cp8Result`
therefore mirrors `automation_engineering.cp3.models.Cp3Result`/
`automation_engineering.cp4.models.Cp4Result`'s own
`overall_verdict`-derived-from-criteria shape exactly, not CP7's.

Six named criteria, one per D7's own two bullets (assets present bundles
three; config validity bundles three):

* `CRITERION_FEATURES_PRESENT` / `CRITERION_STEP_DEFINITIONS_PRESENT` /
  `CRITERION_RUNNER_PRESENT` -- D7's own "assets present" bullet.
* `CRITERION_POM_WELL_FORMED` -- D7's own `pom.xml` bullet: well-formed
  XML, every dependency/plugin declaration structurally valid. Never
  checked against a hardcoded expected-dependency list (D7's own explicit
  rejection of that lean).
* `CRITERION_JUNIT_PLATFORM_PROPERTIES_VALID` -- D7's own
  `junit-platform.properties` bullet's structural half: present,
  well-formed, `cucumber.glue` declared and non-empty,
  `cucumber.plugin`'s own declared paths syntactically well-formed.
* `CRITERION_GLUE_PACKAGE_RESOLVES` -- D7's own `junit-platform
  .properties` bullet's SEMANTIC half, and D8's own distinctive value:
  does at least one `cucumber.glue` package genuinely contain a class in
  the assembled suite's own reconciled catalog -- the misconfiguration a
  Java compiler is structurally blind to (D8).
"""

from __future__ import annotations

from dataclasses import dataclass

from shared.enums.base import ValidationVerdict

CRITERION_FEATURES_PRESENT = "features_present"
CRITERION_STEP_DEFINITIONS_PRESENT = "step_definitions_present"
CRITERION_RUNNER_PRESENT = "runner_present"
CRITERION_POM_WELL_FORMED = "pom_well_formed"
CRITERION_JUNIT_PLATFORM_PROPERTIES_VALID = "junit_platform_properties_valid"
CRITERION_GLUE_PACKAGE_RESOLVES = "glue_package_resolves"

#: D7's own six checks, in the order this module's own docstring names
#: them -- mirrors `automation_engineering.cp3.models.CP3_CRITERIA`'s own
#: "one named tuple, the full set" convention.
CP8_CRITERIA: tuple[str, ...] = (
    CRITERION_FEATURES_PRESENT,
    CRITERION_STEP_DEFINITIONS_PRESENT,
    CRITERION_RUNNER_PRESENT,
    CRITERION_POM_WELL_FORMED,
    CRITERION_JUNIT_PLATFORM_PROPERTIES_VALID,
    CRITERION_GLUE_PACKAGE_RESOLVES,
)


@dataclass(frozen=True, slots=True)
class Cp8CriterionResult:
    """One static-readiness criterion's own deterministic verdict --
    mirrors `automation_engineering.cp3.models.Cp3CriterionResult`/
    `automation_engineering.cp4.models.Cp4CriterionResult`'s own shape
    exactly. `messages` is empty on a clean `PASS`, one entry per distinct
    problem on a `FAIL`."""

    criterion: str
    verdict: ValidationVerdict
    messages: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Cp8Result:
    """CP8's own capstone verdict (ADR-0047 D7-D9) -- `overall_verdict` is
    `PASS` iff every named criterion (`CP8_CRITERIA`) is `PASS`. Unlike
    CP7, this DOES gate: `evaluate_static_readiness`
    (`suite_quality_governance.cp8.readiness`) is the one deterministic
    gate a caller acts on, mirroring CP3/CP4/CP5-cohesion's own
    `overall_verdict`-gates discipline (ADR-0040 Decision 2).
    """

    overall_verdict: ValidationVerdict
    criteria: tuple[Cp8CriterionResult, ...]

    def criterion(self, name: str) -> Cp8CriterionResult:
        """Return the named criterion's result.

        Raises
        ------
        KeyError
            If no criterion with this name was evaluated.
        """
        for c in self.criteria:
            if c.criterion == name:
                return c
        raise KeyError(f"No CP8 criterion named {name!r} in this result.")

    @property
    def passed(self) -> bool:
        return self.overall_verdict == ValidationVerdict.PASS


__all__ = [
    "CP8_CRITERIA",
    "CRITERION_FEATURES_PRESENT",
    "CRITERION_GLUE_PACKAGE_RESOLVES",
    "CRITERION_JUNIT_PLATFORM_PROPERTIES_VALID",
    "CRITERION_POM_WELL_FORMED",
    "CRITERION_RUNNER_PRESENT",
    "CRITERION_STEP_DEFINITIONS_PRESENT",
    "Cp8CriterionResult",
    "Cp8Result",
]
