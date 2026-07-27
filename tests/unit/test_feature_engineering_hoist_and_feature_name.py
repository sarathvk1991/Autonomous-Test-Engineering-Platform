"""ADR-0043 D1/D2's two deterministic-core fixes, closed without an LLM.

The live generation run against REQ-6e894aae exposed two platform-side lint
failures -- neither model-caused: an over-length derived Feature name
(`name-length`) and functional tags tripping `no-homogenous-tags` on a
single-scenario feature. Both are deterministic transforms, proven here
entirely against `StubFeatureContentGenerator` fixtures -- no LLM call
anywhere in this module.
"""

from __future__ import annotations

from pathlib import Path

from contracts.id_generation import generate_requirement_id
from contracts.testable_requirement import (
    AcceptanceCriterionInput,
    Category,
    Priority,
    TestableRequirement,
    build_testable_requirement,
)
from feature_engineering.generation import (
    StubFeatureContentGenerator,
    derive_feature_name,
    generate_feature_file,
)

_LONG_TITLE = (
    "The system shall display a list of available products upon successful "
    "loading of the inventory page for a logged-in user."
)  # 121 chars -- the real REQ-6e894aae title, over the 70-char name-length limit.


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
            ),
            AcceptanceCriterionInput(
                category=Category.FUNCTIONAL,
                statement="Expired reset link is rejected",
            ),
        ],
    }
    defaults.update(overrides)
    return build_testable_requirement(**defaults)  # type: ignore[arg-type]


class TestFeatureNameDerivation:
    def test_title_within_limit_is_unchanged_and_no_comment_is_produced(self) -> None:
        name, comment = derive_feature_name("Short title", "REQ-aaaaaaaa")
        assert name == "Short title"
        assert comment is None

    def test_over_length_title_is_shortened_to_the_70_char_limit(self) -> None:
        name, comment = derive_feature_name(_LONG_TITLE, "REQ-6e894aae")
        assert len(_LONG_TITLE) > 70
        assert len(name) <= 70
        assert comment is not None

    def test_same_title_and_id_yield_an_identical_result_across_calls(self) -> None:
        first = derive_feature_name(_LONG_TITLE, "REQ-6e894aae")
        second = derive_feature_name(_LONG_TITLE, "REQ-6e894aae")
        assert first == second

    def test_full_title_is_preserved_verbatim_in_the_comment(self) -> None:
        _name, comment = derive_feature_name(_LONG_TITLE, "REQ-6e894aae")
        assert comment is not None
        assert _LONG_TITLE in comment

    def test_two_distinct_titles_sharing_a_truncation_prefix_do_not_collide(self) -> None:
        shared_prefix = "A" * 60
        title_a = shared_prefix + " variant one tail content that differs"
        title_b = shared_prefix + " variant two tail content that differs"
        name_a, _ = derive_feature_name(title_a, "REQ-aaaaaaaa")
        name_b, _ = derive_feature_name(title_b, "REQ-bbbbbbbb")
        assert name_a != name_b
        assert name_a.endswith("[REQ-aaaaaaaa]")
        assert name_b.endswith("[REQ-bbbbbbbb]")

    def test_requirement_id_is_unaffected_by_feature_name_shortening(self) -> None:
        """Only `title` feeds REQ-* (ADR-0042 Decision 2); the derived
        Feature *name* is never hashed. Confirmed two ways: the id computed
        independently from the full title matches the requirement's own id
        regardless of what the derived short name became, and the id round
        -tripped through `generate_feature_file` is untouched."""
        req = _requirement(title=_LONG_TITLE)
        name, _comment = derive_feature_name(req.title, req.requirement_id)
        assert name != req.title  # shortening actually happened

        recomputed_id = generate_requirement_id(req.title, [])
        assert recomputed_id == req.requirement_id

    def test_content_hash_is_unaffected_by_feature_name_shortening(self, tmp_path: Path) -> None:
        req = _requirement(title=_LONG_TITLE)
        content_hash_before = req.content_hash
        ac1, ac2 = req.acceptance_criteria
        raw = (
            f"@{ac1.criterion_id} @SCN-PENDING\n"
            "Scenario: one\n  Given a\n  When b\n  Then c\n"
            "\n"
            f"@{ac2.criterion_id} @SCN-PENDING\n"
            "Scenario: two\n  Given a\n  When b\n  Then c\n"
        )
        generate_feature_file(
            req, StubFeatureContentGenerator({req.requirement_id: raw}), features_root=tmp_path
        )
        assert req.content_hash == content_hash_before  # frozen model, never mutated

    def test_shortened_name_and_full_title_both_appear_in_the_assembled_file(
        self, tmp_path: Path
    ) -> None:
        req = _requirement(title=_LONG_TITLE)
        ac1, ac2 = req.acceptance_criteria
        raw = (
            f"@{ac1.criterion_id} @SCN-PENDING\n"
            "Scenario: one\n  Given a\n  When b\n  Then c\n"
            "\n"
            f"@{ac2.criterion_id} @SCN-PENDING\n"
            "Scenario: two\n  Given a\n  When b\n  Then c\n"
        )
        result = generate_feature_file(
            req, StubFeatureContentGenerator({req.requirement_id: raw}), features_root=tmp_path
        )
        assert result.lint_result.is_clean
        assert _LONG_TITLE in result.content  # full title preserved, in the comment
        feature_line = next(
            line for line in result.content.splitlines() if line.startswith("Feature:")
        )
        assert len(feature_line.removeprefix("Feature: ")) <= 70
        assert result.requirement_id == req.requirement_id


class TestHoistExtensionToFunctionalTags:
    def test_single_scenario_functional_tags_hoist_and_lint_clean(self, tmp_path: Path) -> None:
        req = _requirement(
            acceptance_criteria=[
                AcceptanceCriterionInput(category=Category.FUNCTIONAL, statement="Only criterion")
            ]
        )
        (ac,) = req.acceptance_criteria
        raw = (
            f"@inventory @smoke @{ac.criterion_id} @SCN-PENDING\n"
            "Scenario: Display available products\n"
            "  Given I am a logged-in user\n"
            "  When I navigate to the inventory page\n"
            "  Then I should see a list of available products\n"
        )
        result = generate_feature_file(
            req, StubFeatureContentGenerator({req.requirement_id: raw}), features_root=tmp_path
        )

        assert result.lint_result.is_clean
        lines = result.content.splitlines()
        feature_tag_line = next(line for line in lines if line.startswith("@"))
        scenario_line = next(line for line in lines if "Scenario:" in line)
        line_before_scenario = lines[lines.index(scenario_line) - 1]

        assert "@inventory" in feature_tag_line
        assert "@smoke" in feature_tag_line
        # Nothing left dangling at scenario level -- the line immediately
        # before `Scenario:` is the (blank-separated) body, not a tag line.
        assert not line_before_scenario.strip().startswith("@")

    def test_functional_tag_on_some_but_not_all_scenarios_stays_scenario_level(
        self, tmp_path: Path
    ) -> None:
        req = _requirement()
        ac1, ac2 = req.acceptance_criteria
        raw = (
            f"@smoke @{ac1.criterion_id} @SCN-PENDING\n"
            "Scenario: User receives a password reset email\n"
            "  Given a registered user requests a password reset\n"
            "  When the reset request is submitted\n"
            "  Then a reset email is sent\n"
            "\n"
            f"@{ac2.criterion_id} @SCN-PENDING\n"
            "Scenario: Expired reset link is rejected\n"
            "  Given a user has an expired password reset link\n"
            "  When the user opens the reset link\n"
            "  Then the system rejects the expired link\n"
        )
        result = generate_feature_file(
            req, StubFeatureContentGenerator({req.requirement_id: raw}), features_root=tmp_path
        )

        assert result.lint_result.is_clean
        feature_tag_line = result.content.splitlines()[0]
        assert "@smoke" not in feature_tag_line  # not homogenous -- must not hoist
        assert "@smoke" in result.content  # still present, at scenario level

    def test_functional_tag_on_every_scenario_hoists(self, tmp_path: Path) -> None:
        req = _requirement()
        ac1, ac2 = req.acceptance_criteria
        raw = (
            f"@regression @{ac1.criterion_id} @SCN-PENDING\n"
            "Scenario: User receives a password reset email\n"
            "  Given a registered user requests a password reset\n"
            "  When the reset request is submitted\n"
            "  Then a reset email is sent\n"
            "\n"
            f"@regression @{ac2.criterion_id} @SCN-PENDING\n"
            "Scenario: Expired reset link is rejected\n"
            "  Given a user has an expired password reset link\n"
            "  When the user opens the reset link\n"
            "  Then the system rejects the expired link\n"
        )
        result = generate_feature_file(
            req, StubFeatureContentGenerator({req.requirement_id: raw}), features_root=tmp_path
        )

        assert result.lint_result.is_clean
        feature_tag_line = result.content.splitlines()[0]
        assert "@regression" in feature_tag_line
        lines = result.content.splitlines()
        scenario_tag_lines = [
            lines[i - 1] for i, line in enumerate(lines) if "Scenario:" in line
        ]
        for tag_line in scenario_tag_lines:
            assert "@regression" not in tag_line


class TestRegressionPreviouslyCleanFixturesStillLintClean:
    def test_two_scenario_ac_and_scn_only_content_still_lints_clean(self, tmp_path: Path) -> None:
        req = _requirement()
        ac1, ac2 = req.acceptance_criteria
        raw = (
            f"@smoke @{ac1.criterion_id} @SCN-PENDING\n"
            "Scenario: User receives a password reset email\n"
            "  Given a registered user requests a password reset\n"
            "  When the reset request is submitted\n"
            "  Then a reset email is sent\n"
            "\n"
            f"@regression @{ac2.criterion_id} @SCN-PENDING\n"
            "Scenario: Expired reset link is rejected\n"
            "  Given a user has an expired password reset link\n"
            "  When the user opens the reset link\n"
            "  Then the system rejects the expired link\n"
        )
        result = generate_feature_file(
            req, StubFeatureContentGenerator({req.requirement_id: raw}), features_root=tmp_path
        )
        assert result.lint_result.is_clean

    def test_short_title_produces_byte_identical_feature_line_as_before(
        self, tmp_path: Path
    ) -> None:
        req = _requirement(title="Password Reset Self-Service")
        ac1, ac2 = req.acceptance_criteria
        raw = (
            f"@{ac1.criterion_id} @SCN-PENDING\nScenario: one\n  Given a\n  When b\n  Then c\n"
            "\n"
            f"@{ac2.criterion_id} @SCN-PENDING\nScenario: two\n  Given a\n  When b\n  Then c\n"
        )
        result = generate_feature_file(
            req, StubFeatureContentGenerator({req.requirement_id: raw}), features_root=tmp_path
        )
        assert result.content.splitlines()[1] == "Feature: Password Reset Self-Service"
