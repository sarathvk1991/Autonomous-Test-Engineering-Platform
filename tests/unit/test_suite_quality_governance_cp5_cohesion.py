"""Proves CP5's aggregate-release cohesion component (ADR-0046 D5/D6):
`suite_quality_governance.cp5.cohesion.evaluate_cohesion`.

Covers: the compile criterion (pass, fail, infra-error-fails-closed), the
ambiguous-glue criterion (cross-class collision flagged, same-class
repeat not flagged, different patterns not flagged), the composed
deterministic verdict (PASS iff both criteria pass), no tracked-baseline
mutation from the ambiguous-glue scan, and determinism.
"""

from __future__ import annotations

import os
from pathlib import Path

from automation_engineering.catalog.alignment import correlate
from automation_engineering.catalog.models import AssetCatalog, StepDefinitionAsset
from automation_engineering.catalog.scanner import reconcile
from shared.enums.base import ValidationVerdict
from suite_quality_governance.cp5.cohesion import evaluate_cohesion
from suite_quality_governance.cp5.compile_check import CompileError, StubCompileChecker
from suite_quality_governance.cp5.models import (
    CRITERION_COMPILES,
    CRITERION_NO_AMBIGUOUS_GLUE,
    CompileResult,
)


def _step_asset(
    *, asset_id: str, class_name: str, method_name: str, pattern: str
) -> StepDefinitionAsset:
    return StepDefinitionAsset(
        asset_id=asset_id,
        class_name=class_name,
        method_name=method_name,
        step_type="Given",
        pattern=pattern,
        parameters=(),
        return_type="void",
        source_file=f"{class_name.replace('.', '/')}.java",
        content_hash=f"hash-{asset_id}",
        signature_alignment=correlate(pattern, ()),
    )


_EMPTY_CATALOG = AssetCatalog(baseline_root="/fake", step_definitions=())


class TestCompileCriterion:
    def test_passing_compile_gates_pass(self, tmp_path: Path) -> None:
        checker = StubCompileChecker(result=CompileResult(passed=True))
        result = evaluate_cohesion(_EMPTY_CATALOG, tmp_path, checker)

        assert result.criterion(CRITERION_COMPILES).verdict == ValidationVerdict.PASS
        assert result.criterion(CRITERION_COMPILES).messages == ()

    def test_failing_compile_gates_fail_with_errors_surfaced(self, tmp_path: Path) -> None:
        checker = StubCompileChecker(
            result=CompileResult(passed=False, errors=("cannot find symbol: LoginPage",))
        )
        result = evaluate_cohesion(_EMPTY_CATALOG, tmp_path, checker)

        criterion = result.criterion(CRITERION_COMPILES)
        assert criterion.verdict == ValidationVerdict.FAIL
        assert criterion.messages == ("cannot find symbol: LoginPage",)

    def test_infra_failure_fails_closed_never_crashes(self, tmp_path: Path) -> None:
        checker = StubCompileChecker(error=CompileError("mvn not found on PATH"))
        result = evaluate_cohesion(_EMPTY_CATALOG, tmp_path, checker)

        criterion = result.criterion(CRITERION_COMPILES)
        assert criterion.verdict == ValidationVerdict.FAIL
        assert criterion.messages == ("mvn not found on PATH",)

    def test_checker_is_invoked_with_the_given_project_root(self, tmp_path: Path) -> None:
        checker = StubCompileChecker(result=CompileResult(passed=True))
        evaluate_cohesion(_EMPTY_CATALOG, tmp_path, checker)

        assert checker.calls == [tmp_path]


class TestAmbiguousGlueCriterion:
    def _passing_compile_checker(self) -> StubCompileChecker:
        return StubCompileChecker(result=CompileResult(passed=True))

    def test_same_pattern_different_classes_is_flagged(self, tmp_path: Path) -> None:
        first = _step_asset(
            asset_id="STEP-1",
            class_name="com.automation.steps.LoginSteps",
            method_name="userLogsIn",
            pattern="user logs in",
        )
        second = _step_asset(
            asset_id="STEP-2",
            class_name="com.automation.steps.LegacyLoginSteps",
            method_name="userLogsInLegacy",
            pattern="user logs in",  # identical pattern, DIFFERENT class
        )
        catalog = AssetCatalog(baseline_root="/fake", step_definitions=(first, second))

        result = evaluate_cohesion(catalog, tmp_path, self._passing_compile_checker())

        criterion = result.criterion(CRITERION_NO_AMBIGUOUS_GLUE)
        assert criterion.verdict == ValidationVerdict.FAIL
        assert len(criterion.messages) == 1
        assert "user logs in" in criterion.messages[0]
        assert "LoginSteps" in criterion.messages[0]
        assert "LegacyLoginSteps" in criterion.messages[0]

    def test_same_pattern_same_class_is_not_flagged_here(self, tmp_path: Path) -> None:
        """A different concern (CP3's own duplicate-steps criterion,
        ADR-0044 D5) -- cohesion's ambiguous-glue check is cross-class
        only."""
        first = _step_asset(
            asset_id="STEP-3",
            class_name="com.automation.steps.LoginSteps",
            method_name="userLogsInA",
            pattern="user logs in",
        )
        second = _step_asset(
            asset_id="STEP-4",
            class_name="com.automation.steps.LoginSteps",  # SAME class
            method_name="userLogsInB",
            pattern="user logs in",
        )
        catalog = AssetCatalog(baseline_root="/fake", step_definitions=(first, second))

        result = evaluate_cohesion(catalog, tmp_path, self._passing_compile_checker())

        assert result.criterion(CRITERION_NO_AMBIGUOUS_GLUE).verdict == ValidationVerdict.PASS

    def test_different_patterns_different_classes_is_not_flagged(self, tmp_path: Path) -> None:
        first = _step_asset(
            asset_id="STEP-5",
            class_name="com.automation.steps.LoginSteps",
            method_name="userLogsIn",
            pattern="user logs in",
        )
        second = _step_asset(
            asset_id="STEP-6",
            class_name="com.automation.steps.CheckoutSteps",
            method_name="userChecksOut",
            pattern="user completes checkout",
        )
        catalog = AssetCatalog(baseline_root="/fake", step_definitions=(first, second))

        result = evaluate_cohesion(catalog, tmp_path, self._passing_compile_checker())

        assert result.criterion(CRITERION_NO_AMBIGUOUS_GLUE).verdict == ValidationVerdict.PASS

    def test_v1_is_exact_collision_only_not_semantic_overlap(self, tmp_path: Path) -> None:
        """The deferred stretch (ADR-0046 D5): two syntactically DIFFERENT
        patterns that a Cucumber Expression engine might still consider
        overlapping are NOT flagged by v1 -- only byte-identical patterns
        are."""
        first = _step_asset(
            asset_id="STEP-7",
            class_name="com.automation.steps.A",
            method_name="a",
            pattern="user enters {string}",
        )
        second = _step_asset(
            asset_id="STEP-8",
            class_name="com.automation.steps.B",
            method_name="b",
            pattern="user enters {word}",  # different placeholder type, same shape
        )
        catalog = AssetCatalog(baseline_root="/fake", step_definitions=(first, second))

        result = evaluate_cohesion(catalog, tmp_path, self._passing_compile_checker())

        assert result.criterion(CRITERION_NO_AMBIGUOUS_GLUE).verdict == ValidationVerdict.PASS

    def test_three_classes_sharing_one_pattern_is_one_finding_naming_all_three(
        self, tmp_path: Path
    ) -> None:
        assets = tuple(
            _step_asset(
                asset_id=f"STEP-{i}",
                class_name=f"com.automation.steps.C{i}",
                method_name="doThing",
                pattern="user does the thing",
            )
            for i in range(3)
        )
        catalog = AssetCatalog(baseline_root="/fake", step_definitions=assets)

        result = evaluate_cohesion(catalog, tmp_path, self._passing_compile_checker())

        criterion = result.criterion(CRITERION_NO_AMBIGUOUS_GLUE)
        assert criterion.verdict == ValidationVerdict.FAIL
        assert len(criterion.messages) == 1
        for i in range(3):
            assert f"C{i}" in criterion.messages[0]


class TestComposedVerdict:
    def test_both_pass_yields_overall_pass(self, tmp_path: Path) -> None:
        checker = StubCompileChecker(result=CompileResult(passed=True))
        result = evaluate_cohesion(_EMPTY_CATALOG, tmp_path, checker)

        assert result.overall_verdict == ValidationVerdict.PASS
        assert result.passed is True

    def test_compile_fail_alone_yields_overall_fail(self, tmp_path: Path) -> None:
        checker = StubCompileChecker(result=CompileResult(passed=False, errors=("boom",)))
        result = evaluate_cohesion(_EMPTY_CATALOG, tmp_path, checker)

        assert result.overall_verdict == ValidationVerdict.FAIL
        assert result.criterion(CRITERION_NO_AMBIGUOUS_GLUE).verdict == ValidationVerdict.PASS

    def test_ambiguous_glue_alone_yields_overall_fail(self, tmp_path: Path) -> None:
        first = _step_asset(
            asset_id="STEP-9",
            class_name="com.automation.steps.A",
            method_name="a",
            pattern="same pattern",
        )
        second = _step_asset(
            asset_id="STEP-10",
            class_name="com.automation.steps.B",
            method_name="b",
            pattern="same pattern",
        )
        catalog = AssetCatalog(baseline_root="/fake", step_definitions=(first, second))
        checker = StubCompileChecker(result=CompileResult(passed=True))

        result = evaluate_cohesion(catalog, tmp_path, checker)

        assert result.overall_verdict == ValidationVerdict.FAIL
        assert result.criterion(CRITERION_COMPILES).verdict == ValidationVerdict.PASS

    def test_both_fail_yields_overall_fail_with_both_reported(self, tmp_path: Path) -> None:
        first = _step_asset(
            asset_id="STEP-11",
            class_name="com.automation.steps.A",
            method_name="a",
            pattern="same pattern",
        )
        second = _step_asset(
            asset_id="STEP-12",
            class_name="com.automation.steps.B",
            method_name="b",
            pattern="same pattern",
        )
        catalog = AssetCatalog(baseline_root="/fake", step_definitions=(first, second))
        checker = StubCompileChecker(result=CompileResult(passed=False, errors=("boom",)))

        result = evaluate_cohesion(catalog, tmp_path, checker)

        assert result.overall_verdict == ValidationVerdict.FAIL
        assert result.criterion(CRITERION_COMPILES).verdict == ValidationVerdict.FAIL
        assert result.criterion(CRITERION_NO_AMBIGUOUS_GLUE).verdict == ValidationVerdict.FAIL


class TestNoBaselineMutation:
    def test_ambiguous_glue_scan_never_writes_or_modifies_the_baseline(
        self, tmp_path: Path
    ) -> None:
        """End-to-end against a REAL filesystem scan: reconciles a real
        tracked-baseline layout carrying a genuine ambiguous-glue
        collision, evaluates cohesion (compile stubbed out -- this proof
        is about the catalog-reading half only), then proves every file's
        content and mtime are byte-for-byte unchanged and no new file was
        created -- the same read-only proof components 1-2 already
        established."""
        java_dir = tmp_path / "src" / "test" / "java" / "com" / "automation" / "steps"
        java_dir.mkdir(parents=True)
        first_file = java_dir / "LoginSteps.java"
        first_file.write_text(
            "package com.automation.steps;\n\n"
            "import io.cucumber.java.en.Given;\n\n"
            "public class LoginSteps {\n"
            '    @Given("user logs in")\n'
            "    public void userLogsIn() {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        second_file = java_dir / "LegacyLoginSteps.java"
        second_file.write_text(
            "package com.automation.steps;\n\n"
            "import io.cucumber.java.en.Given;\n\n"
            "public class LegacyLoginSteps {\n"
            '    @Given("user logs in")\n'
            "    public void userLogsInLegacy() {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        before_snapshot = {
            p: (p.read_text(encoding="utf-8"), os.stat(p).st_mtime_ns)
            for p in (first_file, second_file)
        }
        before_tree = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))

        catalog = reconcile(tmp_path)
        checker = StubCompileChecker(result=CompileResult(passed=True))
        result = evaluate_cohesion(catalog, tmp_path, checker)

        # The collision is correctly found (proves the read side worked).
        assert result.criterion(CRITERION_NO_AMBIGUOUS_GLUE).verdict == ValidationVerdict.FAIL

        after_tree = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))
        assert after_tree == before_tree
        for path, (content, mtime) in before_snapshot.items():
            assert path.read_text(encoding="utf-8") == content
            assert os.stat(path).st_mtime_ns == mtime


class TestDeterminism:
    def test_same_inputs_yield_the_same_result_every_time(self, tmp_path: Path) -> None:
        first = _step_asset(
            asset_id="STEP-13",
            class_name="com.automation.steps.A",
            method_name="a",
            pattern="a pattern",
        )
        catalog = AssetCatalog(baseline_root="/fake", step_definitions=(first,))
        checker_result = CompileResult(passed=True)

        first_run = evaluate_cohesion(catalog, tmp_path, StubCompileChecker(result=checker_result))
        second_run = evaluate_cohesion(
            catalog, tmp_path, StubCompileChecker(result=checker_result)
        )

        assert first_run == second_run
