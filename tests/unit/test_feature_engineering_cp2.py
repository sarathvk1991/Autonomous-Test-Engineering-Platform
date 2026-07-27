"""CP2 — Layer 2's deterministic feature-governance gate.

Two kinds of fixture are used deliberately:

* Real `GeneratedFeature` objects produced through the unmodified generator
  core (`generate_feature_file` + `StubFeatureContentGenerator`) prove CP2
  against what the core actually emits -- no LLM call anywhere in this
  module.
* Hand-constructed `GeneratedFeature` objects (built directly via the
  dataclass constructor, bypassing the core) prove CP2's OWN evaluation
  logic against specific hypothetical inputs the core's own guarantees
  would never actually let through (e.g. a dirty `lint_result`) -- this is
  the only way to test each CP2 criterion in isolation, since a
  `GeneratedFeature` that failed lint never successfully returns from
  `generate_feature_file` at all (it raises `FeatureGenerationError`
  instead). These are TEST FIXTURES exercising CP2 in isolation, not claims
  about what the core would produce.
"""

from __future__ import annotations

from pathlib import Path

from contracts.testable_requirement import (
    AcceptanceCriterionInput,
    Category,
    Priority,
    TestableRequirement,
    build_testable_requirement,
)
from feature_engineering.cp2 import (
    CRITERION_AC_COVERAGE,
    CRITERION_DUPLICATE_DETECTION,
    CRITERION_LINT,
    CRITERION_TAG_PRESENCE,
    CP2AdvisorySignals,
    CP2Result,
    evaluate_cp2,
)
from feature_engineering.generation import (
    GeneratedFeature,
    ScenarioAssignment,
    StubFeatureContentGenerator,
    generate_feature_file,
)
from feature_engineering.gherkin_lint import LintResult, Violation
from shared.enums.base import ValidationVerdict


def _requirement(**overrides: object) -> TestableRequirement:
    defaults: dict[str, object] = {
        "title": "User can reset password",
        "component": "auth",
        "functional_tag": "@auth",
        "priority": Priority.HIGH,
        "traces_to": (),
        "narrative": "Users need a self-service password reset flow.",
        "acceptance_criteria": [
            AcceptanceCriterionInput(category=Category.FUNCTIONAL, statement="A"),
            AcceptanceCriterionInput(category=Category.FUNCTIONAL, statement="B"),
        ],
    }
    defaults.update(overrides)
    return build_testable_requirement(**defaults)  # type: ignore[arg-type]


def _two_scenario_content(req: TestableRequirement) -> str:
    ac1, ac2 = req.acceptance_criteria
    return f"""@smoke @{ac1.criterion_id} @SCN-PENDING
Scenario: User receives a password reset email
  Given a registered user requests a password reset
  When the reset request is submitted
  Then a reset email is sent

@regression @{ac2.criterion_id} @SCN-PENDING
Scenario: Expired reset link is rejected
  Given a user has an expired password reset link
  When the user opens the reset link
  Then the system rejects the expired link
"""


def _clean_hand_built_feature(
    *, requirement_id: str = "REQ-x123", scenario_two_functional_tag: str | None = "@regression"
) -> GeneratedFeature:
    """A hand-built, otherwise-clean `GeneratedFeature` -- used as the base
    for the isolated-failure fixtures below, which each mutate exactly one
    field/aspect away from clean. Deliberately NO feature-level functional
    tag: each scenario carries its own, distinct functional tag, so a
    missing one on scenario "Two" cannot be masked by a blanket
    feature-level tag this fixture itself introduced."""
    scenario_two_tag_line = f" {scenario_two_functional_tag}" if scenario_two_functional_tag else ""
    content = f"""@{requirement_id}
Feature: Sample feature

  @AC-x123-01 @SCN-x123-01-01 @smoke
  Scenario: One
    Given a
    When b
    Then c

  @AC-x123-02 @SCN-x123-01-02{scenario_two_tag_line}
  Scenario: Two
    Given a
    When b
    Then c
"""
    return GeneratedFeature(
        requirement_id=requirement_id,
        content=content,
        file_path=Path(f"/unused/{requirement_id}.feature"),
        req_tag=f"@{requirement_id}",
        scenarios=(
            ScenarioAssignment(name="One", scn_id="SCN-x123-01-01", ac_ids=("AC-x123-01",)),
            ScenarioAssignment(name="Two", scn_id="SCN-x123-01-02", ac_ids=("AC-x123-02",)),
        ),
        acceptance_criteria_coverage={"AC-x123-01": True, "AC-x123-02": True},
        lint_result=LintResult(),
    )


class TestCleanFeaturePasses:
    def test_single_ac_via_real_core_passes_cp2(self, tmp_path: Path) -> None:
        req = _requirement(
            acceptance_criteria=[
                AcceptanceCriterionInput(category=Category.FUNCTIONAL, statement="Only criterion")
            ]
        )
        (ac,) = req.acceptance_criteria
        raw = f"""@smoke @{ac.criterion_id} @SCN-PENDING
Scenario: User receives a password reset email
  Given a registered user requests a password reset
  When the reset request is submitted
  Then a reset email is sent
"""
        gf = generate_feature_file(
            req, StubFeatureContentGenerator({req.requirement_id: raw}), features_root=tmp_path
        )
        result = evaluate_cp2(gf)

        print("=== single-AC CP2 result ===")
        for c in result.criteria:
            print(f"  {c.criterion}: {c.verdict} {c.messages}")
        print(f"  overall: {result.overall_verdict}")

        assert result.overall_verdict == ValidationVerdict.PASS
        assert result.passed
        assert all(c.verdict == ValidationVerdict.PASS for c in result.criteria)

    def test_multi_ac_via_real_core_passes_cp2(self, tmp_path: Path) -> None:
        req = _requirement()
        raw = _two_scenario_content(req)
        gf = generate_feature_file(
            req, StubFeatureContentGenerator({req.requirement_id: raw}), features_root=tmp_path
        )
        result = evaluate_cp2(gf)

        print("=== multi-AC CP2 result ===")
        for c in result.criteria:
            print(f"  {c.criterion}: {c.verdict} {c.messages}")
        print(f"  overall: {result.overall_verdict}")

        assert result.overall_verdict == ValidationVerdict.PASS
        assert all(c.verdict == ValidationVerdict.PASS for c in result.criteria)


class TestPerCriterionIndependentFailure:
    def test_non_dupe_lint_violation_fails_only_the_lint_criterion(self) -> None:
        feature = _clean_hand_built_feature()
        dirty = GeneratedFeature(
            requirement_id=feature.requirement_id,
            content=feature.content,
            file_path=feature.file_path,
            req_tag=feature.req_tag,
            scenarios=feature.scenarios,
            acceptance_criteria_coverage=feature.acceptance_criteria_coverage,
            lint_result=LintResult(
                violations=(
                    Violation(
                        rule="scenario-size",
                        file=feature.requirement_id,
                        line=5,
                        message="Element Scenario too long: actual 13, expected 12",
                    ),
                )
            ),
        )
        result = evaluate_cp2(dirty)

        assert result.overall_verdict == ValidationVerdict.FAIL
        assert result.criterion(CRITERION_LINT).verdict == ValidationVerdict.FAIL
        assert result.criterion(CRITERION_AC_COVERAGE).verdict == ValidationVerdict.PASS
        assert result.criterion(CRITERION_TAG_PRESENCE).verdict == ValidationVerdict.PASS
        assert result.criterion(CRITERION_DUPLICATE_DETECTION).verdict == ValidationVerdict.PASS

    def test_uncovered_ac_fails_only_the_coverage_criterion(self) -> None:
        feature = _clean_hand_built_feature()
        dirty = GeneratedFeature(
            requirement_id=feature.requirement_id,
            content=feature.content,
            file_path=feature.file_path,
            req_tag=feature.req_tag,
            scenarios=feature.scenarios,
            acceptance_criteria_coverage={"AC-x123-01": True, "AC-x123-02": False},
            lint_result=feature.lint_result,
        )
        result = evaluate_cp2(dirty)

        assert result.overall_verdict == ValidationVerdict.FAIL
        coverage = result.criterion(CRITERION_AC_COVERAGE)
        assert coverage.verdict == ValidationVerdict.FAIL
        assert coverage.messages == ("AC-x123-02: no scenario maps to this acceptance criterion",)
        assert result.criterion(CRITERION_LINT).verdict == ValidationVerdict.PASS
        assert result.criterion(CRITERION_TAG_PRESENCE).verdict == ValidationVerdict.PASS
        assert result.criterion(CRITERION_DUPLICATE_DETECTION).verdict == ValidationVerdict.PASS

    def test_scenario_missing_a_functional_tag_fails_only_the_tag_criterion(self) -> None:
        # scenario_two_functional_tag=None -- the scenario carries only its
        # @AC-* and @SCN-*, neither hoisted at feature level either.
        dirty = _clean_hand_built_feature(scenario_two_functional_tag=None)
        result = evaluate_cp2(dirty)

        assert result.overall_verdict == ValidationVerdict.FAIL
        tags = result.criterion(CRITERION_TAG_PRESENCE)
        assert tags.verdict == ValidationVerdict.FAIL
        assert any("no functional tag present" in m for m in tags.messages)
        assert result.criterion(CRITERION_LINT).verdict == ValidationVerdict.PASS
        assert result.criterion(CRITERION_AC_COVERAGE).verdict == ValidationVerdict.PASS
        assert result.criterion(CRITERION_DUPLICATE_DETECTION).verdict == ValidationVerdict.PASS

    def test_missing_req_tag_fails_only_the_tag_criterion(self) -> None:
        feature = _clean_hand_built_feature()
        content_without_req_tag = feature.content.replace(f"{feature.req_tag}\n", "")
        dirty = GeneratedFeature(
            requirement_id=feature.requirement_id,
            content=content_without_req_tag,
            file_path=feature.file_path,
            req_tag=feature.req_tag,
            scenarios=feature.scenarios,
            acceptance_criteria_coverage=feature.acceptance_criteria_coverage,
            lint_result=feature.lint_result,
        )
        result = evaluate_cp2(dirty)

        assert result.overall_verdict == ValidationVerdict.FAIL
        tags = result.criterion(CRITERION_TAG_PRESENCE)
        assert tags.verdict == ValidationVerdict.FAIL
        assert any("is missing from the Feature-level tag line" in m for m in tags.messages)
        assert result.criterion(CRITERION_LINT).verdict == ValidationVerdict.PASS
        assert result.criterion(CRITERION_AC_COVERAGE).verdict == ValidationVerdict.PASS
        assert result.criterion(CRITERION_DUPLICATE_DETECTION).verdict == ValidationVerdict.PASS

    def test_duplicate_scenario_names_fails_lint_and_duplicate_detection_named_criteria(
        self,
    ) -> None:
        """A no-dupe-scenario-names violation is real evidence in BOTH
        buckets by design (D5 names duplicate detection as its own
        criterion even though the underlying evidence is a lint rule) --
        this proves it surfaces as its OWN, specifically-named criterion
        (not buried, invisible, inside the generic lint bucket), while
        coverage and tag_presence -- genuinely unrelated evidence -- stay
        clean."""
        feature = _clean_hand_built_feature()
        dirty = GeneratedFeature(
            requirement_id=feature.requirement_id,
            content=feature.content,
            file_path=feature.file_path,
            req_tag=feature.req_tag,
            scenarios=feature.scenarios,
            acceptance_criteria_coverage=feature.acceptance_criteria_coverage,
            lint_result=LintResult(
                violations=(
                    Violation(
                        rule="no-dupe-scenario-names",
                        file=feature.requirement_id,
                        line=8,
                        message="Scenario name is already used in: x:4",
                    ),
                )
            ),
        )
        result = evaluate_cp2(dirty)

        assert result.overall_verdict == ValidationVerdict.FAIL
        assert result.criterion(CRITERION_LINT).verdict == ValidationVerdict.FAIL
        dupes = result.criterion(CRITERION_DUPLICATE_DETECTION)
        assert dupes.verdict == ValidationVerdict.FAIL
        assert any("no-dupe-scenario-names" in m for m in dupes.messages)
        # Genuinely unrelated criteria are unaffected.
        assert result.criterion(CRITERION_AC_COVERAGE).verdict == ValidationVerdict.PASS
        assert result.criterion(CRITERION_TAG_PRESENCE).verdict == ValidationVerdict.PASS


class TestCorpusScopedDuplicateFeatureNames:
    def _feature_with_name(self, requirement_id: str, feature_name: str) -> GeneratedFeature:
        content = f"""@{requirement_id} @regression
Feature: {feature_name}

  @AC-x-01 @SCN-x-01-01 @smoke
  Scenario: Only scenario
    Given a
    When b
    Then c
"""
        return GeneratedFeature(
            requirement_id=requirement_id,
            content=content,
            file_path=Path(f"/unused/{requirement_id}.feature"),
            req_tag=f"@{requirement_id}",
            scenarios=(
                ScenarioAssignment(name="Only scenario", scn_id="SCN-x-01-01", ac_ids=("AC-x-01",)),
            ),
            acceptance_criteria_coverage={"AC-x-01": True},
            lint_result=LintResult(),
        )

    def test_without_feature_set_the_corpus_check_is_not_evaluated_and_does_not_fail(self) -> None:
        feature = self._feature_with_name("REQ-aaa", "Any name")
        result = evaluate_cp2(feature)
        dupes = result.criterion(CRITERION_DUPLICATE_DETECTION)
        assert dupes.verdict == ValidationVerdict.PASS
        assert any("not evaluated" in m for m in dupes.messages)

    def test_with_feature_set_a_genuine_duplicate_feature_name_fails_the_second_occurrence(
        self,
    ) -> None:
        first = self._feature_with_name("REQ-aaa", "Duplicate feature name")
        second = self._feature_with_name("REQ-bbb", "Duplicate feature name")
        feature_set = [first, second]

        first_result = evaluate_cp2(first, feature_set=feature_set)
        second_result = evaluate_cp2(second, feature_set=feature_set)

        # Inherited from the committed, D3-locked rule: only the SECOND
        # occurrence is flagged, never the first -- documented, not a bug.
        first_dupes = first_result.criterion(CRITERION_DUPLICATE_DETECTION)
        assert first_dupes.verdict == ValidationVerdict.PASS
        second_dupes = second_result.criterion(CRITERION_DUPLICATE_DETECTION)
        assert second_dupes.verdict == ValidationVerdict.FAIL
        assert any("no-dupe-feature-names" in m for m in second_dupes.messages)

    def test_with_feature_set_distinct_names_both_pass(self) -> None:
        first = self._feature_with_name("REQ-aaa", "First feature")
        second = self._feature_with_name("REQ-bbb", "Second feature")
        feature_set = [first, second]

        assert evaluate_cp2(first, feature_set=feature_set).passed
        assert evaluate_cp2(second, feature_set=feature_set).passed


class TestAdvisoryCannotGate:
    def test_evaluate_cp2_never_sets_an_advisory_signal(self) -> None:
        feature = _clean_hand_built_feature()
        result = evaluate_cp2(feature)
        assert result.advisory is None

    def test_a_negative_advisory_signal_cannot_flip_an_otherwise_passing_verdict(self) -> None:
        feature = _clean_hand_built_feature()
        clean_result = evaluate_cp2(feature)
        assert clean_result.overall_verdict == ValidationVerdict.PASS

        # Manually attach a maximally negative advisory signal to the SAME
        # criteria/verdict -- nothing in CP2Result derives overall_verdict
        # from advisory, so it must be unchanged.
        result_with_negative_advisory = CP2Result(
            requirement_id=clean_result.requirement_id,
            overall_verdict=clean_result.overall_verdict,
            criteria=clean_result.criteria,
            advisory=CP2AdvisorySignals(
                business_readability="low confidence -- steps describe implementation detail",
                step_reusability="poor -- overly specific phrasing, not reusable",
            ),
        )
        assert result_with_negative_advisory.overall_verdict == ValidationVerdict.PASS
        assert result_with_negative_advisory.passed

    def test_evaluator_module_never_imports_the_advisory_model(self) -> None:
        """Structural proof, stronger than a behavioural one: the evaluator
        cannot even construct a CP2AdvisorySignals, let alone gate on one."""
        import ast

        tree = ast.parse(
            Path("feature_engineering/cp2/evaluator.py").read_text(encoding="utf-8"),
            filename="evaluator.py",
        )
        imported_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imported_names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.Import):
                imported_names.update(alias.name for alias in node.names)
        assert "CP2AdvisorySignals" not in imported_names


class TestDeterminism:
    def test_same_feature_yields_an_identical_cp2_result_across_two_calls(self) -> None:
        feature = _clean_hand_built_feature()
        first = evaluate_cp2(feature)
        second = evaluate_cp2(feature)
        assert first == second


class TestNoLlmNoIo:
    def test_cp2_package_never_imports_llm_factory(self) -> None:
        import ast

        cp2_dir = Path("feature_engineering/cp2")
        for py_file in cp2_dir.glob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "llm_factory" not in alias.name, f"{py_file}: imports {alias.name}"
                elif isinstance(node, ast.ImportFrom) and node.module:
                    assert "llm_factory" not in node.module, (
                        f"{py_file}: imports from {node.module}"
                    )
