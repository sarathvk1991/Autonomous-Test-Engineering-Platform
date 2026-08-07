"""Proves CP8's own capstone gate (ADR-0047 D7-D9):
`suite_quality_governance.cp8.readiness.evaluate_static_readiness`.

Covers: a fully-ready fixture passes every criterion; each criterion fails
independently of the others (mirroring CP4/cohesion's own per-criterion
independence proof); the D8-distinctive non-redundant-overlap proof (a
suite that COMPILES but has `cucumber.glue` pointing at the wrong package
-- CP5-cohesion PASSES, CP8 FAILS); the gate is deterministic and carries
a real `overall_verdict` (unlike CP7's report-only shape); no
build/subprocess/execution call is ever made; no baseline mutation; and
existing CP5 behavior is unaffected by CP8's own reuse of the scanner.
"""

from __future__ import annotations

import inspect
import os
from pathlib import Path

import suite_quality_governance.cp8.assets as cp8_assets
import suite_quality_governance.cp8.glue_resolution as cp8_glue_resolution
import suite_quality_governance.cp8.junit_platform_config as cp8_junit_platform_config
import suite_quality_governance.cp8.pom_validation as cp8_pom_validation
import suite_quality_governance.cp8.readiness as cp8_readiness
from automation_engineering.catalog.scanner import reconcile
from shared.enums.base import ValidationVerdict
from suite_quality_governance.cp5.cohesion import evaluate_cohesion
from suite_quality_governance.cp5.compile_check import StubCompileChecker
from suite_quality_governance.cp5.models import CompileResult
from suite_quality_governance.cp8.models import (
    CRITERION_FEATURES_PRESENT,
    CRITERION_GLUE_PACKAGE_RESOLVES,
    CRITERION_JUNIT_PLATFORM_PROPERTIES_VALID,
    CRITERION_POM_WELL_FORMED,
    CRITERION_RUNNER_PRESENT,
    CRITERION_STEP_DEFINITIONS_PRESENT,
)
from suite_quality_governance.cp8.readiness import evaluate_static_readiness

_VALID_POM = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.automation</groupId>
    <artifactId>test-suite-baseline</artifactId>
    <version>1.0-SNAPSHOT</version>
    <dependencies>
        <dependency>
            <groupId>io.cucumber</groupId>
            <artifactId>cucumber-java</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>
</project>
"""

_STEP_DEFINITION_JAVA = """package com.automation.steps;

import io.cucumber.java.en.Given;

public class LoginSteps {
    @Given("user logs in")
    public void userLogsIn() {
    }
}
"""

_RUNNER_JAVA = """package com.automation.runners;

import org.junit.platform.suite.api.IncludeEngines;
import org.junit.platform.suite.api.SelectClasspathResource;
import org.junit.platform.suite.api.Suite;

@Suite
@IncludeEngines("cucumber")
@SelectClasspathResource("features")
public class RunCucumberTest {
}
"""


def _junit_platform_properties(glue: str = "com.automation.steps") -> str:
    return (
        f"cucumber.glue={glue}\ncucumber.plugin=message:target/cucumber-reports/messages.ndjson\n"
    )


def _write_valid_baseline(root: Path, *, glue: str = "com.automation.steps") -> None:
    (root / "pom.xml").write_text(_VALID_POM, encoding="utf-8")

    properties_path = root / "src/test/resources/junit-platform.properties"
    properties_path.parent.mkdir(parents=True, exist_ok=True)
    properties_path.write_text(_junit_platform_properties(glue), encoding="utf-8")

    features_path = root / "src/test/resources/features/login.feature"
    features_path.parent.mkdir(parents=True, exist_ok=True)
    features_path.write_text(
        "Feature: login\n  Scenario: ok\n    Given user logs in\n", encoding="utf-8"
    )

    steps_path = root / "src/test/java/com/automation/steps/LoginSteps.java"
    steps_path.parent.mkdir(parents=True, exist_ok=True)
    steps_path.write_text(_STEP_DEFINITION_JAVA, encoding="utf-8")

    runner_path = root / "src/test/java/com/automation/runners/RunCucumberTest.java"
    runner_path.parent.mkdir(parents=True, exist_ok=True)
    runner_path.write_text(_RUNNER_JAVA, encoding="utf-8")


class TestFullyReadyFixturePasses:
    def test_every_criterion_passes_and_overall_verdict_is_pass(self, tmp_path: Path) -> None:
        _write_valid_baseline(tmp_path)

        result = evaluate_static_readiness(tmp_path)

        assert result.overall_verdict == ValidationVerdict.PASS
        assert result.passed is True
        for criterion in (
            CRITERION_FEATURES_PRESENT,
            CRITERION_STEP_DEFINITIONS_PRESENT,
            CRITERION_RUNNER_PRESENT,
            CRITERION_POM_WELL_FORMED,
            CRITERION_JUNIT_PLATFORM_PROPERTIES_VALID,
            CRITERION_GLUE_PACKAGE_RESOLVES,
        ):
            assert result.criterion(criterion).verdict == ValidationVerdict.PASS


class TestEachCriterionFailsIndependently:
    def test_missing_pom_fails_only_the_pom_criterion(self, tmp_path: Path) -> None:
        _write_valid_baseline(tmp_path)
        (tmp_path / "pom.xml").unlink()

        result = evaluate_static_readiness(tmp_path)

        assert result.overall_verdict == ValidationVerdict.FAIL
        assert result.criterion(CRITERION_POM_WELL_FORMED).verdict == ValidationVerdict.FAIL
        assert result.criterion(CRITERION_FEATURES_PRESENT).verdict == ValidationVerdict.PASS
        assert result.criterion(CRITERION_RUNNER_PRESENT).verdict == ValidationVerdict.PASS
        assert result.criterion(CRITERION_GLUE_PACKAGE_RESOLVES).verdict == ValidationVerdict.PASS

    def test_malformed_pom_fails_only_the_pom_criterion(self, tmp_path: Path) -> None:
        _write_valid_baseline(tmp_path)
        (tmp_path / "pom.xml").write_text("<project><unclosed>", encoding="utf-8")

        result = evaluate_static_readiness(tmp_path)

        assert result.overall_verdict == ValidationVerdict.FAIL
        assert result.criterion(CRITERION_POM_WELL_FORMED).verdict == ValidationVerdict.FAIL
        assert (
            result.criterion(CRITERION_JUNIT_PLATFORM_PROPERTIES_VALID).verdict
            == ValidationVerdict.PASS
        )

    def test_glue_pointing_at_a_nonexistent_package_fails_only_the_glue_criterion(
        self, tmp_path: Path
    ) -> None:
        _write_valid_baseline(tmp_path, glue="com.totally.made.up.package")

        result = evaluate_static_readiness(tmp_path)

        assert result.overall_verdict == ValidationVerdict.FAIL
        assert result.criterion(CRITERION_GLUE_PACKAGE_RESOLVES).verdict == ValidationVerdict.FAIL
        assert result.criterion(CRITERION_POM_WELL_FORMED).verdict == ValidationVerdict.PASS
        assert result.criterion(CRITERION_RUNNER_PRESENT).verdict == ValidationVerdict.PASS
        assert result.criterion(CRITERION_FEATURES_PRESENT).verdict == ValidationVerdict.PASS
        # cucumber.glue is present and non-empty, so the structural check
        # (junit_platform_config) still passes -- only the semantic,
        # catalog-aware check (glue_resolution) catches this.
        assert (
            result.criterion(CRITERION_JUNIT_PLATFORM_PROPERTIES_VALID).verdict
            == ValidationVerdict.PASS
        )

    def test_missing_runner_fails_only_the_runner_criterion(self, tmp_path: Path) -> None:
        _write_valid_baseline(tmp_path)
        (tmp_path / "src/test/java/com/automation/runners/RunCucumberTest.java").unlink()

        result = evaluate_static_readiness(tmp_path)

        assert result.overall_verdict == ValidationVerdict.FAIL
        assert result.criterion(CRITERION_RUNNER_PRESENT).verdict == ValidationVerdict.FAIL
        assert result.criterion(CRITERION_POM_WELL_FORMED).verdict == ValidationVerdict.PASS
        assert result.criterion(CRITERION_GLUE_PACKAGE_RESOLVES).verdict == ValidationVerdict.PASS

    def test_missing_features_fails_only_the_features_criterion(self, tmp_path: Path) -> None:
        _write_valid_baseline(tmp_path)
        (tmp_path / "src/test/resources/features/login.feature").unlink()

        result = evaluate_static_readiness(tmp_path)

        assert result.overall_verdict == ValidationVerdict.FAIL
        assert result.criterion(CRITERION_FEATURES_PRESENT).verdict == ValidationVerdict.FAIL
        assert result.criterion(CRITERION_RUNNER_PRESENT).verdict == ValidationVerdict.PASS
        assert (
            result.criterion(CRITERION_STEP_DEFINITIONS_PRESENT).verdict == ValidationVerdict.PASS
        )

    def test_missing_step_definitions_fails_only_that_criterion(self, tmp_path: Path) -> None:
        _write_valid_baseline(tmp_path)
        (tmp_path / "src/test/java/com/automation/steps/LoginSteps.java").unlink()

        result = evaluate_static_readiness(tmp_path)

        assert result.overall_verdict == ValidationVerdict.FAIL
        assert (
            result.criterion(CRITERION_STEP_DEFINITIONS_PRESENT).verdict == ValidationVerdict.FAIL
        )
        # No catalogued class anywhere means glue resolution also fails --
        # a real, honest cascading consequence, not independent noise: with
        # zero step-definition classes in the whole suite, no glue package
        # could possibly resolve either.
        assert result.criterion(CRITERION_GLUE_PACKAGE_RESOLVES).verdict == ValidationVerdict.FAIL
        assert result.criterion(CRITERION_FEATURES_PRESENT).verdict == ValidationVerdict.PASS
        assert result.criterion(CRITERION_RUNNER_PRESENT).verdict == ValidationVerdict.PASS


class TestNonRedundantOverlapWithCp5Cohesion:
    """ADR-0047 D8's own central proof: a suite that COMPILES but has
    `cucumber.glue` pointing at the wrong package passes CP5-cohesion and
    fails CP8 -- the exact defect a Java compiler cannot see."""

    def test_compiles_but_glue_misconfigured_cohesion_passes_cp8_fails(
        self, tmp_path: Path
    ) -> None:
        _write_valid_baseline(tmp_path, glue="com.totally.made.up.package")
        catalog = reconcile(tmp_path)
        # Real compilation is never invoked (that's CP5-cohesion's own,
        # separate concern) -- the stub simulates "the suite genuinely
        # compiles" so this test can isolate CP8's own distinctive value
        # without paying for a real `mvn test-compile`.
        stub_compiler = StubCompileChecker(result=CompileResult(passed=True))

        cohesion_result = evaluate_cohesion(catalog, tmp_path, stub_compiler)
        cp8_result = evaluate_static_readiness(tmp_path)

        assert cohesion_result.overall_verdict == ValidationVerdict.PASS
        assert cp8_result.overall_verdict == ValidationVerdict.FAIL
        assert cp8_result.criterion(CRITERION_GLUE_PACKAGE_RESOLVES).verdict == (
            ValidationVerdict.FAIL
        )


class TestGateIsDeterministicAndRealUnlikeCp7:
    def test_cp8_result_carries_a_real_overall_verdict_field(self, tmp_path: Path) -> None:
        _write_valid_baseline(tmp_path)

        result = evaluate_static_readiness(tmp_path)

        assert hasattr(result, "overall_verdict")
        assert hasattr(result, "passed")

    def test_same_fixture_yields_the_same_verdict_every_time(self, tmp_path: Path) -> None:
        _write_valid_baseline(tmp_path)

        first = evaluate_static_readiness(tmp_path)
        second = evaluate_static_readiness(tmp_path)

        assert first == second
        assert first.overall_verdict == second.overall_verdict == ValidationVerdict.PASS


class TestNoExecution:
    def test_evaluate_static_readiness_takes_only_a_path(self) -> None:
        signature = inspect.signature(evaluate_static_readiness)

        assert list(signature.parameters) == ["baseline_root"]

    def test_no_cp8_module_imports_subprocess_or_shells_out(self) -> None:
        """Structural proof: CP8 parses config files and reads the
        reconciled catalog -- it never invokes `mvn`, `subprocess`, or any
        other build/execution tool (unlike CP5-cohesion's own compile
        check, which genuinely does)."""
        modules = (
            cp8_assets,
            cp8_pom_validation,
            cp8_junit_platform_config,
            cp8_glue_resolution,
            cp8_readiness,
        )
        for module in modules:
            source = inspect.getsource(module)
            assert "import subprocess" not in source, f"{module.__name__} shells out"
            assert "Popen" not in source, f"{module.__name__} spawns a process"


class TestNoBaselineMutation:
    def test_evaluating_readiness_never_writes_or_modifies_the_fixture(
        self, tmp_path: Path
    ) -> None:
        _write_valid_baseline(tmp_path)
        before_snapshot = {
            p: (p.read_text(encoding="utf-8"), os.stat(p).st_mtime_ns)
            for p in tmp_path.rglob("*")
            if p.is_file()
        }
        before_tree = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))

        result = evaluate_static_readiness(tmp_path)

        assert result.overall_verdict == ValidationVerdict.PASS
        after_tree = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))
        assert after_tree == before_tree
        for path, (content, mtime) in before_snapshot.items():
            assert path.read_text(encoding="utf-8") == content
            assert os.stat(path).st_mtime_ns == mtime


class TestMissingJunitPlatformPropertiesFile:
    def test_missing_properties_file_fails_both_dependent_criteria(self, tmp_path: Path) -> None:
        _write_valid_baseline(tmp_path)
        (tmp_path / "src/test/resources/junit-platform.properties").unlink()

        result = evaluate_static_readiness(tmp_path)

        assert result.overall_verdict == ValidationVerdict.FAIL
        assert (
            result.criterion(CRITERION_JUNIT_PLATFORM_PROPERTIES_VALID).verdict
            == ValidationVerdict.FAIL
        )
        assert result.criterion(CRITERION_GLUE_PACKAGE_RESOLVES).verdict == ValidationVerdict.FAIL
        assert result.criterion(CRITERION_POM_WELL_FORMED).verdict == ValidationVerdict.PASS
