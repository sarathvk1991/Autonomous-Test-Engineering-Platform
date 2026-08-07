"""CP8's own distinctive check (ADR-0047 D7's semantic half, D8's own
"non-redundant with CP5-cohesion" value): does `cucumber.glue` actually
name a package the assembled suite's own catalog has a class under.

**The misconfiguration a Java compiler is structurally blind to.** A
`cucumber.glue` package pointing at zero classes compiles perfectly clean
under `mvn test-compile` -- a Java compiler has no concept of Cucumber's
own runtime glue-scanning convention -- and would only surface as "zero
steps matched" at Layer 5 execution time, absent this check (ADR-0047
D8, quoted in full in `.readiness`'s own module docstring).

**Reuses `automation_engineering.catalog.scanner.package_from_relative_path`,
never a second package-derivation rule (D7's own "reuse, don't rebuild").**
Every catalogued asset's own `source_file` is already the exact shape
that function expects -- promoted to public specifically for this second
consumer, mirroring `_cosine_similarity`/`_embedding_text`'s own
promotion precedent one component over (ADR-0046 D3).

**"At least one," per D7's own literal text -- not "every."** A suite's
own real `cucumber.glue` legitimately names a package this platform's own
catalog never scans at all (`com.automation.base`, `EXCLUDED_PACKAGES` --
framework code, hooks, never a catalog candidate) alongside one that
genuinely holds every step definition (`com.automation.steps`). Requiring
EVERY named package to resolve would incorrectly fail this platform's own
real, working configuration; D7's own "at least one" wording is not an
approximation -- it is the correct check for a `cucumber.glue` value that
may legitimately mix catalogued and framework-only packages.
"""

from __future__ import annotations

from automation_engineering.catalog.models import AssetCatalog
from automation_engineering.catalog.scanner import package_from_relative_path
from shared.enums.base import ValidationVerdict
from suite_quality_governance.cp8.junit_platform_config import CUCUMBER_GLUE_KEY
from suite_quality_governance.cp8.models import CRITERION_GLUE_PACKAGE_RESOLVES, Cp8CriterionResult


def check_glue_package_resolves(catalog: AssetCatalog, glue_value: str) -> Cp8CriterionResult:
    """`glue_value` is `junit-platform.properties`'s own already-parsed
    `cucumber.glue` value (`suite_quality_governance.cp8
    .junit_platform_config.parse_java_properties`'s own output for that
    key) -- this function performs no file I/O itself. `catalog` is an
    already-reconciled `AssetCatalog`, read, never scanned here.
    """
    glue_packages = tuple(p.strip() for p in glue_value.split(",") if p.strip())
    if not glue_packages:
        return Cp8CriterionResult(
            criterion=CRITERION_GLUE_PACKAGE_RESOLVES,
            verdict=ValidationVerdict.FAIL,
            messages=(f"{CUCUMBER_GLUE_KEY} is empty -- no package for Cucumber to scan",),
        )

    catalogued_packages = {
        package_from_relative_path(asset.source_file) for asset in catalog.all_assets()
    }
    if any(package in catalogued_packages for package in glue_packages):
        return Cp8CriterionResult(
            criterion=CRITERION_GLUE_PACKAGE_RESOLVES, verdict=ValidationVerdict.PASS
        )
    return Cp8CriterionResult(
        criterion=CRITERION_GLUE_PACKAGE_RESOLVES,
        verdict=ValidationVerdict.FAIL,
        messages=(
            f"none of {CUCUMBER_GLUE_KEY}'s own packages ({', '.join(glue_packages)}) "
            "contain any class in the reconciled catalog -- Cucumber would match zero "
            "steps against this configuration",
        ),
    )


__all__ = ["check_glue_package_resolves"]
