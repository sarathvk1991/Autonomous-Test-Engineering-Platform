"""CP8 -- static execution-readiness governance (ADR-0047 D7-D9).

Gates immediately, as a real deterministic PASS/FAIL, from its first
implementation (D9) -- unlike CP7's report-only shape. Distinct from
CP5-cohesion's compile check by construction, not convention (D8):
CP8 validates the suite is CONFIGURED to be executable (config/deps
declared and well-formed, `cucumber.glue` pointing at a real package),
never that it COMPILES. Makes no subprocess, build, or network call.
"""

from __future__ import annotations

from suite_quality_governance.cp8.assets import (
    RUNNER_RELATIVE_PATH,
    check_features_present,
    check_runner_present,
    check_step_definitions_present,
)
from suite_quality_governance.cp8.glue_resolution import check_glue_package_resolves
from suite_quality_governance.cp8.junit_platform_config import (
    CUCUMBER_GLUE_KEY,
    CUCUMBER_PLUGIN_KEY,
    JUNIT_PLATFORM_PROPERTIES_RELATIVE_PATH,
    check_junit_platform_properties_valid,
    parse_java_properties,
)
from suite_quality_governance.cp8.models import (
    CP8_CRITERIA,
    CRITERION_FEATURES_PRESENT,
    CRITERION_GLUE_PACKAGE_RESOLVES,
    CRITERION_JUNIT_PLATFORM_PROPERTIES_VALID,
    CRITERION_POM_WELL_FORMED,
    CRITERION_RUNNER_PRESENT,
    CRITERION_STEP_DEFINITIONS_PRESENT,
    Cp8CriterionResult,
    Cp8Result,
)
from suite_quality_governance.cp8.pom_validation import POM_RELATIVE_PATH, check_pom_well_formed
from suite_quality_governance.cp8.readiness import evaluate_static_readiness

__all__ = [
    "CP8_CRITERIA",
    "CRITERION_FEATURES_PRESENT",
    "CRITERION_GLUE_PACKAGE_RESOLVES",
    "CRITERION_JUNIT_PLATFORM_PROPERTIES_VALID",
    "CRITERION_POM_WELL_FORMED",
    "CRITERION_RUNNER_PRESENT",
    "CRITERION_STEP_DEFINITIONS_PRESENT",
    "CUCUMBER_GLUE_KEY",
    "CUCUMBER_PLUGIN_KEY",
    "JUNIT_PLATFORM_PROPERTIES_RELATIVE_PATH",
    "POM_RELATIVE_PATH",
    "RUNNER_RELATIVE_PATH",
    "Cp8CriterionResult",
    "Cp8Result",
    "check_features_present",
    "check_glue_package_resolves",
    "check_junit_platform_properties_valid",
    "check_pom_well_formed",
    "check_runner_present",
    "check_step_definitions_present",
    "evaluate_static_readiness",
    "parse_java_properties",
]
