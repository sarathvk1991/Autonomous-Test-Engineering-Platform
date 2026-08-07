"""Proves CP8's "assets present" component (ADR-0047 D7's own first
bullet): `suite_quality_governance.cp8.assets`.

Covers: each of the three checks (features, step definitions, runner)
passing and failing independently, and that `check_step_definitions_present`
reads an already-reconciled catalog rather than scanning a filesystem
itself.
"""

from __future__ import annotations

from pathlib import Path

from automation_engineering.catalog.alignment import correlate
from automation_engineering.catalog.models import AssetCatalog, StepDefinitionAsset
from feature_engineering.stage.workspace import FEATURES_SUBPATH
from shared.enums.base import ValidationVerdict
from suite_quality_governance.cp8.assets import (
    RUNNER_RELATIVE_PATH,
    check_features_present,
    check_runner_present,
    check_step_definitions_present,
)

_EMPTY_CATALOG = AssetCatalog(baseline_root="/fake")


def _step_asset() -> StepDefinitionAsset:
    return StepDefinitionAsset(
        asset_id="STEP-1",
        class_name="com.automation.steps.LoginSteps",
        method_name="userLogsIn",
        step_type="Given",
        pattern="user logs in",
        parameters=(),
        return_type="void",
        source_file="com/automation/steps/LoginSteps.java",
        content_hash="hash-1",
        signature_alignment=correlate("user logs in", ()),
    )


class TestFeaturesPresent:
    def test_at_least_one_feature_file_passes(self, tmp_path: Path) -> None:
        features_root = tmp_path / FEATURES_SUBPATH
        features_root.mkdir(parents=True)
        (features_root / "login.feature").write_text("Feature: login\n", encoding="utf-8")

        result = check_features_present(tmp_path)

        assert result.verdict == ValidationVerdict.PASS
        assert result.messages == ()

    def test_missing_features_root_fails(self, tmp_path: Path) -> None:
        result = check_features_present(tmp_path)

        assert result.verdict == ValidationVerdict.FAIL
        assert "no .feature file found" in result.messages[0]

    def test_empty_features_root_fails(self, tmp_path: Path) -> None:
        (tmp_path / FEATURES_SUBPATH).mkdir(parents=True)

        result = check_features_present(tmp_path)

        assert result.verdict == ValidationVerdict.FAIL


class TestStepDefinitionsPresent:
    def test_catalog_with_at_least_one_step_definition_passes(self) -> None:
        catalog = AssetCatalog(baseline_root="/fake", step_definitions=(_step_asset(),))

        result = check_step_definitions_present(catalog)

        assert result.verdict == ValidationVerdict.PASS

    def test_empty_catalog_fails(self) -> None:
        result = check_step_definitions_present(_EMPTY_CATALOG)

        assert result.verdict == ValidationVerdict.FAIL
        assert "no step-definition asset found" in result.messages[0]

    def test_never_scans_a_filesystem_itself(self, tmp_path: Path) -> None:
        """Reads whatever catalog it is handed -- even one whose own
        `baseline_root` points nowhere real -- proving this check performs
        no scan of its own."""
        catalog = AssetCatalog(baseline_root="/does/not/exist", step_definitions=(_step_asset(),))

        result = check_step_definitions_present(catalog)

        assert result.verdict == ValidationVerdict.PASS


class TestRunnerPresent:
    def test_runner_at_the_tracked_path_passes(self, tmp_path: Path) -> None:
        runner_path = tmp_path / RUNNER_RELATIVE_PATH
        runner_path.parent.mkdir(parents=True)
        runner_path.write_text("package com.automation.runners;\n", encoding="utf-8")

        result = check_runner_present(tmp_path)

        assert result.verdict == ValidationVerdict.PASS
        assert result.messages == ()

    def test_missing_runner_fails(self, tmp_path: Path) -> None:
        result = check_runner_present(tmp_path)

        assert result.verdict == ValidationVerdict.FAIL
        assert str(RUNNER_RELATIVE_PATH) in result.messages[0]
