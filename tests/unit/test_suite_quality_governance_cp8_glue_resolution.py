"""Proves CP8's own distinctive check (ADR-0047 D7's semantic half, D8's
own non-redundant value): `suite_quality_governance.cp8.glue_resolution`.

Covers: at least one resolving package passes (mirroring this platform's
own real, working `cucumber.glue=com.automation.steps,com.automation.base`
-- the second package legitimately unresolvable, per D7's own "at least
one" wording); every named package failing to resolve fails; an empty glue
value fails; and this module performs no file I/O of its own (`catalog`
and `glue_value` are both caller-supplied).
"""

from __future__ import annotations

import inspect

from automation_engineering.catalog.alignment import correlate
from automation_engineering.catalog.models import AssetCatalog, StepDefinitionAsset
from shared.enums.base import ValidationVerdict
from suite_quality_governance.cp8.glue_resolution import check_glue_package_resolves


def _step_asset(*, class_name: str, source_file: str) -> StepDefinitionAsset:
    return StepDefinitionAsset(
        asset_id=f"STEP-{source_file}",
        class_name=class_name,
        method_name="doThing",
        step_type="Given",
        pattern="a pattern",
        parameters=(),
        return_type="void",
        source_file=source_file,
        content_hash=f"hash-{source_file}",
        signature_alignment=correlate("a pattern", ()),
    )


_CATALOG = AssetCatalog(
    baseline_root="/fake",
    step_definitions=(
        _step_asset(
            class_name="com.automation.steps.LoginSteps",
            source_file="com/automation/steps/LoginSteps.java",
        ),
    ),
)


class TestAtLeastOnePackageResolves:
    def test_a_glue_value_naming_the_catalogued_package_passes(self) -> None:
        result = check_glue_package_resolves(_CATALOG, "com.automation.steps")

        assert result.verdict == ValidationVerdict.PASS
        assert result.messages == ()

    def test_a_glue_value_mixing_a_real_and_a_framework_only_package_passes(self) -> None:
        """This platform's own real configuration:
        `com.automation.steps,com.automation.base` -- the second package
        is framework-only (never a catalog candidate), and D7's own "at
        least one" wording means this must still pass."""
        result = check_glue_package_resolves(_CATALOG, "com.automation.steps,com.automation.base")

        assert result.verdict == ValidationVerdict.PASS


class TestNoPackageResolves:
    def test_a_glue_value_naming_only_a_nonexistent_package_fails(self) -> None:
        """The misconfiguration a Java compiler is structurally blind to
        (module docstring, ADR-0047 D8's own distinctive value)."""
        result = check_glue_package_resolves(_CATALOG, "com.totally.made.up.package")

        assert result.verdict == ValidationVerdict.FAIL
        assert "contain any class in the reconciled catalog" in result.messages[0]

    def test_an_empty_glue_value_fails(self) -> None:
        result = check_glue_package_resolves(_CATALOG, "")

        assert result.verdict == ValidationVerdict.FAIL
        assert "no package for Cucumber to scan" in result.messages[0]

    def test_empty_catalog_fails_even_with_a_real_looking_glue_value(self) -> None:
        empty_catalog = AssetCatalog(baseline_root="/fake")

        result = check_glue_package_resolves(empty_catalog, "com.automation.steps")

        assert result.verdict == ValidationVerdict.FAIL


class TestNoFileIO:
    def test_the_function_signature_takes_no_filesystem_path(self) -> None:
        signature = inspect.signature(check_glue_package_resolves)

        assert list(signature.parameters) == ["catalog", "glue_value"]
