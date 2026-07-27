"""Deterministic-mechanics proof for the Layer 2 feature generation core.

One `TestableRequirement` in, one validated `.feature` file out. Every
mechanic this module proves is platform-owned and deterministic: id
minting/substitution, tag scoping and the homogenous-tag hoist, Feature-name
derivation, file placement, structural + lint validation, and
acceptance-criteria coverage computation. No LLM is called anywhere here --
`StubFeatureContentGenerator` supplies fixed, canned content authored below.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from contracts.testable_requirement import (
    AcceptanceCriterionInput,
    Category,
    PolarityHint,
    Priority,
    TestableRequirement,
    build_testable_requirement,
)
from feature_engineering.generation import (
    FeatureGenerationError,
    StubFeatureContentGenerator,
    generate_feature_file,
    write_generated_feature,
)


def _requirement(**overrides: object) -> TestableRequirement:
    defaults: dict[str, object] = {
        "title": "User can reset password",
        "component": "auth",
        "functional_tag": "@auth",
        "priority": Priority.HIGH,
        "traces_to": (),
        "narrative": "Users need a self-service password reset flow.",
        "acceptance_criteria": [
            AcceptanceCriterionInput(
                category=Category.FUNCTIONAL,
                statement="User receives a reset email",
                polarity_hints=(PolarityHint.POSITIVE,),
            ),
            AcceptanceCriterionInput(
                category=Category.FUNCTIONAL,
                statement="Expired reset link is rejected",
                polarity_hints=(PolarityHint.NEGATIVE,),
            ),
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


class TestDeterminism:
    def test_same_requirement_and_stub_yield_identical_ids_and_path_across_calls(
        self, tmp_path: Path
    ) -> None:
        req = _requirement()
        raw = _two_scenario_content(req)

        first = generate_feature_file(
            req, StubFeatureContentGenerator({req.requirement_id: raw}), features_root=tmp_path
        )
        # A second, fully independent stub instance and call -- proving
        # stability is a property of the (requirement, content) pair, not
        # of any shared in-process state.
        second = generate_feature_file(
            req, StubFeatureContentGenerator({req.requirement_id: raw}), features_root=tmp_path
        )

        first_scn_ids = [s.scn_id for s in first.scenarios]
        second_scn_ids = [s.scn_id for s in second.scenarios]
        print(f"run 1 SCN-* ids: {first_scn_ids}")
        print(f"run 2 SCN-* ids: {second_scn_ids}")
        assert first_scn_ids == second_scn_ids
        assert first.file_path == second.file_path
        assert first.content == second.content

    def test_scenario_order_in_raw_content_does_not_change_ids(self, tmp_path: Path) -> None:
        """Ids are content-addressed, not position-addressed (ADR-0043 D2) --
        reordering the two scenarios in the raw text must not reassign ids."""
        req = _requirement()
        ac1, ac2 = req.acceptance_criteria
        forward = _two_scenario_content(req)
        reversed_order = f"""@regression @{ac2.criterion_id} @SCN-PENDING
Scenario: Expired reset link is rejected
  Given a user has an expired password reset link
  When the user opens the reset link
  Then the system rejects the expired link

@smoke @{ac1.criterion_id} @SCN-PENDING
Scenario: User receives a password reset email
  Given a registered user requests a password reset
  When the reset request is submitted
  Then a reset email is sent
"""
        forward_result = generate_feature_file(
            req, StubFeatureContentGenerator({req.requirement_id: forward}), features_root=tmp_path
        )
        reversed_result = generate_feature_file(
            req,
            StubFeatureContentGenerator({req.requirement_id: reversed_order}),
            features_root=tmp_path,
        )

        forward_by_name = {s.name: s.scn_id for s in forward_result.scenarios}
        reversed_by_name = {s.name: s.scn_id for s in reversed_result.scenarios}
        assert forward_by_name == reversed_by_name


class TestTagScopingAndHoist:
    def test_multi_scenario_ac_and_scn_stay_at_scenario_level(self, tmp_path: Path) -> None:
        req = _requirement()
        raw = _two_scenario_content(req)
        result = generate_feature_file(
            req, StubFeatureContentGenerator({req.requirement_id: raw}), features_root=tmp_path
        )

        feature_line, tag_line = result.content.splitlines()[1], result.content.splitlines()[0]
        assert tag_line == result.req_tag
        assert "AC-" not in tag_line
        assert "SCN-" not in tag_line
        for scenario in result.scenarios:
            assert f"@{scenario.ac_ids[0]}" in result.content
            assert f"@{scenario.scn_id}" in result.content
        assert feature_line.startswith("Feature:")

    def test_single_scenario_hoists_ac_and_scn_to_feature_level(self, tmp_path: Path) -> None:
        """A lone scenario's AC-*/SCN-* tags are trivially identical across
        "every" scenario (n=1) -- the generic hoist (D2, generalized) moves
        both to Feature level, leaving no id tag at scenario level.

        No functional tag on this fixture on purpose: the hoist mechanic is
        scoped to id tags only (the task's own scope), and a functional tag
        (e.g. @smoke) on a lone scenario is *also* trivially homogenous --
        that is a separate concern this fixture deliberately avoids so the
        id-tag hoist proof is isolated and unambiguous."""
        req = _requirement(
            acceptance_criteria=[
                AcceptanceCriterionInput(
                    category=Category.FUNCTIONAL, statement="User receives a reset email"
                )
            ]
        )
        (ac,) = req.acceptance_criteria
        raw = f"""@{ac.criterion_id} @SCN-PENDING
Scenario: User receives a password reset email
  Given a registered user requests a password reset
  When the reset request is submitted
  Then a reset email is sent
"""
        result = generate_feature_file(
            req, StubFeatureContentGenerator({req.requirement_id: raw}), features_root=tmp_path
        )

        lines = result.content.splitlines()
        feature_tag_line = lines[0]
        print(f"Feature-level tag line: {feature_tag_line!r}")
        assert result.req_tag in feature_tag_line
        assert f"@{result.scenarios[0].ac_ids[0]}" in feature_tag_line
        assert f"@{result.scenarios[0].scn_id}" in feature_tag_line

        scenario_line = next(line for line in lines if "Scenario:" in line)
        line_before_scenario = lines[lines.index(scenario_line) - 1]
        print(f"Line immediately before Scenario:: {line_before_scenario!r}")
        assert "AC-" not in line_before_scenario
        assert "SCN-" not in line_before_scenario
        assert result.lint_result.is_clean


class TestFeatureNameDerivation:
    def test_feature_name_comes_from_title_never_from_stub(self, tmp_path: Path) -> None:
        req = _requirement(title="Password Reset Self-Service")
        raw = _two_scenario_content(req)
        assert "Feature:" not in raw  # the content generator never writes one

        result = generate_feature_file(
            req, StubFeatureContentGenerator({req.requirement_id: raw}), features_root=tmp_path
        )
        assert result.content.splitlines()[1] == "Feature: Password Reset Self-Service"


class TestFilePlacement:
    def test_placement_is_deterministic_and_under_the_features_root(self, tmp_path: Path) -> None:
        req = _requirement(component="auth")
        raw = _two_scenario_content(req)
        result = generate_feature_file(
            req, StubFeatureContentGenerator({req.requirement_id: raw}), features_root=tmp_path
        )

        assert result.file_path.parent == tmp_path / "auth"
        assert result.file_path.suffix == ".feature"
        assert result.file_path == generate_feature_file(
            req, StubFeatureContentGenerator({req.requirement_id: raw}), features_root=tmp_path
        ).file_path

    def test_write_generated_feature_lands_the_file_on_disk(self, tmp_path: Path) -> None:
        features_root = tmp_path / "src" / "test" / "resources" / "features"
        req = _requirement()
        raw = _two_scenario_content(req)
        result = generate_feature_file(
            req, StubFeatureContentGenerator({req.requirement_id: raw}), features_root=features_root
        )

        write_generated_feature(result)

        assert result.file_path.exists()
        assert result.file_path.read_text(encoding="utf-8") == result.content
        assert result.file_path.is_relative_to(features_root)


class TestStructuralAndLintValidation:
    def test_assembled_content_parses_and_lints_clean(self, tmp_path: Path) -> None:
        from feature_engineering.gherkin_lint import load_config, parse_source_text
        from feature_engineering.gherkin_lint.linter import lint_source

        req = _requirement()
        raw = _two_scenario_content(req)
        result = generate_feature_file(
            req, StubFeatureContentGenerator({req.requirement_id: raw}), features_root=tmp_path
        )

        reparsed = parse_source_text(result.content)
        assert reparsed.parse_error is None
        assert reparsed.feature is not None

        config = load_config(Path("docs/reference/automation-poc/.gherkin-lintrc"))
        independent_lint = lint_source(reparsed, config)
        assert independent_lint.is_clean
        assert result.lint_result.is_clean

    def test_dirty_stub_content_is_rejected_not_silently_emitted(self, tmp_path: Path) -> None:
        """A duplicate scenario name is a real no-dupe-scenario-names
        violation -- the validator must reject it, not pass it through."""
        req = _requirement()
        ac1, ac2 = req.acceptance_criteria
        dirty = f"""@smoke @{ac1.criterion_id} @SCN-PENDING
Scenario: Duplicate scenario name
  Given a registered user requests a password reset
  When the reset request is submitted
  Then a reset email is sent

@regression @{ac2.criterion_id} @SCN-PENDING
Scenario: Duplicate scenario name
  Given a user has an expired password reset link
  When the user opens the reset link
  Then the system rejects the expired link
"""
        stub = StubFeatureContentGenerator({req.requirement_id: dirty})
        with pytest.raises(FeatureGenerationError) as excinfo:
            generate_feature_file(req, stub, features_root=tmp_path)

        assert excinfo.value.lint_result is not None
        assert not excinfo.value.lint_result.is_clean
        rules_fired = {v.rule for v in excinfo.value.lint_result.violations}
        print(f"dirty-stub rejection fired rules: {rules_fired}")
        assert "no-dupe-scenario-names" in rules_fired

    def test_stray_req_tag_in_raw_content_is_rejected(self, tmp_path: Path) -> None:
        req = _requirement()
        ac1, ac2 = req.acceptance_criteria
        raw = f"""@{req.requirement_id}
@smoke @{ac1.criterion_id} @SCN-PENDING
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
        with pytest.raises(FeatureGenerationError, match="@REQ-"):
            generate_feature_file(
                req, StubFeatureContentGenerator({req.requirement_id: raw}), features_root=tmp_path
            )

    def test_missing_scn_pending_tag_is_rejected(self, tmp_path: Path) -> None:
        req = _requirement()
        (ac1, _ac2) = req.acceptance_criteria
        raw = f"""@smoke @{ac1.criterion_id}
Scenario: User receives a password reset email
  Given a registered user requests a password reset
  When the reset request is submitted
  Then a reset email is sent
"""
        with pytest.raises(FeatureGenerationError, match="@SCN-PENDING"):
            generate_feature_file(
                req,
                StubFeatureContentGenerator({req.requirement_id: raw}),
                features_root=tmp_path,
            )

    def test_untagged_scenario_is_rejected(self, tmp_path: Path) -> None:
        req = _requirement()
        raw = """@smoke @SCN-PENDING
Scenario: User receives a password reset email
  Given a registered user requests a password reset
  When the reset request is submitted
  Then a reset email is sent
"""
        with pytest.raises(FeatureGenerationError, match="no @AC-\\* tag"):
            generate_feature_file(
                req,
                StubFeatureContentGenerator({req.requirement_id: raw}),
                features_root=tmp_path,
            )

    def test_tag_on_background_is_rejected(self, tmp_path: Path) -> None:
        req = _requirement()
        (ac1, ac2) = req.acceptance_criteria
        raw = f"""@bad-tag
Background:
  Given a shared precondition

@smoke @{ac1.criterion_id} @SCN-PENDING
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
        with pytest.raises(FeatureGenerationError):
            generate_feature_file(
                req,
                StubFeatureContentGenerator({req.requirement_id: raw}),
                features_root=tmp_path,
            )


class TestAcceptanceCriteriaCoverage:
    def test_every_ac_covered_reports_fully_covered(self, tmp_path: Path) -> None:
        req = _requirement()
        raw = _two_scenario_content(req)
        result = generate_feature_file(
            req, StubFeatureContentGenerator({req.requirement_id: raw}), features_root=tmp_path
        )

        assert result.fully_covered
        assert all(result.acceptance_criteria_coverage.values())

    def test_uncovered_ac_is_reported_as_a_gap_not_silently_passed(self, tmp_path: Path) -> None:
        """D5: coverage is computed here, gated by CP2 later -- an uncovered
        AC must not raise, but must be visible as False in the result."""
        req = _requirement()
        ac1, _ac2_uncovered = req.acceptance_criteria
        raw = f"""@{ac1.criterion_id} @SCN-PENDING
Scenario: User receives a password reset email
  Given a registered user requests a password reset
  When the reset request is submitted
  Then a reset email is sent
"""
        result = generate_feature_file(
            req, StubFeatureContentGenerator({req.requirement_id: raw}), features_root=tmp_path
        )

        assert not result.fully_covered
        assert result.acceptance_criteria_coverage[ac1.criterion_id] is True
        assert result.acceptance_criteria_coverage[_ac2_uncovered.criterion_id] is False


class TestNoLiveLlmInvolvement:
    def test_generation_module_never_imports_llm_factory(self) -> None:
        import ast
        from pathlib import Path as _Path

        generation_dir = _Path("feature_engineering/generation")
        for py_file in generation_dir.glob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "llm_factory" not in alias.name, f"{py_file}: imports {alias.name}"
                elif isinstance(node, ast.ImportFrom) and node.module:
                    assert "llm_factory" not in node.module, (
                        f"{py_file}: imports from {node.module}"
                    )

    def test_stub_is_explicitly_marked_as_non_production(self) -> None:
        from feature_engineering.generation.content_generator import StubFeatureContentGenerator

        doc = StubFeatureContentGenerator.__doc__ or ""
        assert "test/dev scaffolding" in doc.lower() or "never the production path" in doc.lower()

    def test_stub_raises_rather_than_inventing_content_for_an_unmapped_requirement(
        self, tmp_path: Path
    ) -> None:
        req = _requirement()
        stub = StubFeatureContentGenerator({})
        with pytest.raises(KeyError):
            generate_feature_file(req, stub, features_root=tmp_path)
