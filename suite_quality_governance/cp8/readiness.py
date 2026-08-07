"""CP8's own capstone: static execution-readiness governance (ADR-0047
D7-D9) -- composes the six criteria built across `.assets`, `.pom_validation`,
`.junit_platform_config`, and `.glue_resolution` into one deterministic,
gating `Cp8Result`.

ADR-0047 D8, quoted in full -- this is CP8's own distinctness boundary
against CP5-cohesion (`suite_quality_governance.cp5.cohesion`), and the
reason CP8 never invokes `mvn` or any other build/execution tool:

    "CP5-cohesion answers 'does the assembled suite COMPILE' (a real `mvn
    test-compile`, the authoritative, expensive-but-conclusive proof every
    class's syntax is valid and every referenced dependency resolves); CP8
    answers 'is the suite CONFIGURED to be EXECUTABLE' (cheap, static, no
    JDK/Maven/network). The overlap is deliberate, not accidental: a
    missing `cucumber-java` dependency would trip both -- CP8 cheaply,
    first, before CP5-cohesion's own expensive compile is even attempted...
    Where they do not overlap is CP8's own real value: a `cucumber.glue`
    package pointing at zero classes compiles perfectly clean under `mvn
    test-compile` (a Java compiler has no concept of Cucumber's own runtime
    glue-scanning convention) and would only surface as 'zero steps
    matched' at Layer 5 execution time, absent CP8. CP8 does not verify
    dependency resolvability the strong way -- CP5-cohesion's successful
    compile already proves that, more authoritatively; CP8 claiming to
    verify it too would silently duplicate what CP5-cohesion already
    does."

**One `reconcile` call, never a second scan (D7's own "reuse, don't
rebuild").** The catalog is built once here and handed to both
`check_step_definitions_present` and `check_glue_package_resolves` --
mirroring `suite_quality_governance.cp5.promotion_wrap`'s own
caller-reconciles-once discipline one component over.

**`cucumber.glue`'s own raw value is read here, not inside
`.glue_resolution`.** `check_glue_package_resolves` deliberately performs
no file I/O of its own (its own docstring) -- this module is the one place
`junit-platform.properties` is parsed for that purpose. A missing or
unparseable properties file yields an empty glue value, which
`check_glue_package_resolves` already turns into its own "no package for
Cucumber to scan" failure -- no special-casing needed here.

**Read-only end to end (D9's own "flag for review, never auto-fix").**
Every check in this module's own composed criteria reads a file or the
already-reconciled catalog; none writes, edits, or deletes anything --
mirrors CP5-cohesion's own ambiguous-glue half, never its compile half.
"""

from __future__ import annotations

from pathlib import Path

from automation_engineering.catalog.scanner import reconcile
from shared.enums.base import ValidationVerdict
from suite_quality_governance.cp8.assets import (
    check_features_present,
    check_runner_present,
    check_step_definitions_present,
)
from suite_quality_governance.cp8.glue_resolution import check_glue_package_resolves
from suite_quality_governance.cp8.junit_platform_config import (
    CUCUMBER_GLUE_KEY,
    JUNIT_PLATFORM_PROPERTIES_RELATIVE_PATH,
    check_junit_platform_properties_valid,
    parse_java_properties,
)
from suite_quality_governance.cp8.models import Cp8Result
from suite_quality_governance.cp8.pom_validation import check_pom_well_formed


def _read_glue_value(baseline_root: Path) -> str:
    properties_path = baseline_root / JUNIT_PLATFORM_PROPERTIES_RELATIVE_PATH
    if not properties_path.is_file():
        return ""
    properties = parse_java_properties(properties_path.read_text(encoding="utf-8"))
    return properties.get(CUCUMBER_GLUE_KEY, "")


def evaluate_static_readiness(baseline_root: Path) -> Cp8Result:
    """CP8's own gate (ADR-0047 D7-D9). `overall_verdict` is `PASS` iff
    every named criterion (`CP8_CRITERIA`) is `PASS` -- a real, immediate,
    deterministic gate, unconditional on whether the suite currently
    compiles (D9). Makes no subprocess, build, or network call: every
    criterion here either parses a file already on disk or reads the
    already-reconciled catalog.
    """
    catalog = reconcile(baseline_root)
    glue_value = _read_glue_value(baseline_root)

    criteria = (
        check_features_present(baseline_root),
        check_step_definitions_present(catalog),
        check_runner_present(baseline_root),
        check_pom_well_formed(baseline_root),
        check_junit_platform_properties_valid(baseline_root),
        check_glue_package_resolves(catalog, glue_value),
    )
    overall_verdict = (
        ValidationVerdict.PASS
        if all(c.verdict == ValidationVerdict.PASS for c in criteria)
        else ValidationVerdict.FAIL
    )
    return Cp8Result(overall_verdict=overall_verdict, criteria=criteria)


__all__ = ["evaluate_static_readiness"]
