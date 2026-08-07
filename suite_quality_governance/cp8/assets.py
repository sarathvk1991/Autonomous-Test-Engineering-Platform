"""CP8, "assets present" (ADR-0047 D7's own first bullet): at least one
`.feature` file, at least one step-definition class in the reconciled
catalog, and the tracked runner class -- all three checked by PRESENCE
alone, no parse beyond what the catalog already performed.

**Read-only by construction, reuses the catalog, never a second scan.**
`step_definitions_present` takes an already-reconciled `AssetCatalog`
(`automation_engineering.catalog.scanner.reconcile`) as its own input --
this module never scans a filesystem for Java itself, mirroring
`suite_quality_governance.cp5.orphaned_glue`'s own "caller reconciles
once, every component reads the same catalog" discipline (ADR-0046 D7,
extended here to CP8).
"""

from __future__ import annotations

from pathlib import Path

from automation_engineering.catalog.models import AssetCatalog
from feature_engineering.stage.workspace import FEATURES_SUBPATH
from shared.enums.base import ValidationVerdict
from suite_quality_governance.cp8.models import (
    CRITERION_FEATURES_PRESENT,
    CRITERION_RUNNER_PRESENT,
    CRITERION_STEP_DEFINITIONS_PRESENT,
    Cp8CriterionResult,
)

#: The tracked runner class ADR-0041 D3 requires and ADR-0044 D2 forbids
#: regenerating -- relative to `baseline_root`, the same path this
#: platform's own `test-suite-baseline/` carries today.
RUNNER_RELATIVE_PATH = Path("src/test/java/com/automation/runners/RunCucumberTest.java")


def check_features_present(baseline_root: Path) -> Cp8CriterionResult:
    """At least one `.feature` file exists under the tracked baseline's
    own features root (D7's own first bullet)."""
    features_root = baseline_root / FEATURES_SUBPATH
    if features_root.exists() and any(features_root.rglob("*.feature")):
        return Cp8CriterionResult(
            criterion=CRITERION_FEATURES_PRESENT, verdict=ValidationVerdict.PASS
        )
    return Cp8CriterionResult(
        criterion=CRITERION_FEATURES_PRESENT,
        verdict=ValidationVerdict.FAIL,
        messages=(f"no .feature file found under {features_root}",),
    )


def check_step_definitions_present(catalog: AssetCatalog) -> Cp8CriterionResult:
    """At least one step-definition class in the reconciled catalog (D7's
    own first bullet) -- reads `catalog`, never scans."""
    if catalog.step_definitions:
        return Cp8CriterionResult(
            criterion=CRITERION_STEP_DEFINITIONS_PRESENT, verdict=ValidationVerdict.PASS
        )
    return Cp8CriterionResult(
        criterion=CRITERION_STEP_DEFINITIONS_PRESENT,
        verdict=ValidationVerdict.FAIL,
        messages=("no step-definition asset found in the reconciled catalog",),
    )


def check_runner_present(baseline_root: Path) -> Cp8CriterionResult:
    """The tracked runner class exists at its own known path (D7's own
    first bullet)."""
    runner_path = baseline_root / RUNNER_RELATIVE_PATH
    if runner_path.is_file():
        return Cp8CriterionResult(
            criterion=CRITERION_RUNNER_PRESENT, verdict=ValidationVerdict.PASS
        )
    return Cp8CriterionResult(
        criterion=CRITERION_RUNNER_PRESENT,
        verdict=ValidationVerdict.FAIL,
        messages=(f"no runner class found at {runner_path}",),
    )


__all__ = [
    "RUNNER_RELATIVE_PATH",
    "check_features_present",
    "check_runner_present",
    "check_step_definitions_present",
]
