"""D5 — the bounded remediation loop: Tier 1 (deterministic formatter) and
Tier 2 (bounded LLM remediation, behind the `FeatureRemediator` seam).

No LLM call anywhere in this module -- Tier 2 is exercised entirely against
`StubFeatureRemediator`, scripted per test. This module is about LOOP
CONTROL: attempt counting, escalation routing, and the gate-not-weakened
guarantee -- not about what a real model would produce.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from contracts.testable_requirement import (
    AcceptanceCriterionInput,
    Category,
    Priority,
    TestableRequirement,
    build_testable_requirement,
)
from feature_engineering.generation import (
    FeatureGenerationError,
    StubFeatureContentGenerator,
    generate_feature_file,
)
from feature_engineering.gherkin_lint import load_config, parse_source_text
from feature_engineering.gherkin_lint.linter import lint_source
from feature_engineering.remediation import (
    MAX_LLM_REMEDIATION_ATTEMPTS,
    RemediationStatus,
    StubFeatureRemediator,
    format_feature_content,
    run_cp2_remediation,
)

_LINTRC_PATH = Path("docs/reference/automation-poc/.gherkin-lintrc")


def _requirement(**overrides: object) -> TestableRequirement:
    defaults: dict[str, object] = {
        "title": "User can reset password",
        "component": "auth",
        "functional_tag": "@auth",
        "priority": Priority.HIGH,
        "traces_to": (),
        "narrative": "n",
        "acceptance_criteria": [
            AcceptanceCriterionInput(category=Category.FUNCTIONAL, statement="A"),
        ],
    }
    defaults.update(overrides)
    return build_testable_requirement(**defaults)  # type: ignore[arg-type]


def _lint_clean(content: str) -> bool:
    config = load_config(_LINTRC_PATH)
    return lint_source(parse_source_text(content), config).is_clean


def _scenario_facts(content: str) -> list[tuple[str, tuple[str, ...], tuple[str, ...]]]:
    """(name, tag_names, step_texts) per scenario -- for the semantic
    -identity proof: formatting must never change these."""
    source = parse_source_text(content)
    facts: list[tuple[str, tuple[str, ...], tuple[str, ...]]] = []
    if source.feature is None:
        return facts
    for child in source.feature.get("children", []):
        scenario = child.get("scenario")
        if not scenario:
            continue
        tags = tuple(t["name"] for t in scenario.get("tags", []))
        steps = tuple(s["keyword"] + s["text"] for s in scenario.get("steps", []))
        facts.append((scenario.get("name"), tags, steps))
    return facts


class TestTier1FormatterFixesFormattingOnly:
    def test_dirty_formatting_is_fixed_and_relints_clean(self) -> None:
        # Two scenarios, each with its own distinct SCN-*/functional tag --
        # deliberately not a single-scenario feature, so nothing is
        # trivially homogenous (n=1) and the ONLY dirt is formatting.
        dirty = (
            "@REQ-x1 @AC-x1-01   \n"
            "Feature: Sample feature   \n"
            "\n"
            "\n"
            "\n"
            "@SCN-x1-01-01 @smoke\n"
            "Scenario: One   \n"
            "Given a   \n"
            "When b\n"
            "      Then c\n"
            "\n"
            "@SCN-x1-01-02 @regression\n"
            "Scenario: Two\n"
            "  Given d\n"
            "  When e\n"
            "  Then f"
        )
        assert not _lint_clean(dirty)  # confirm the fixture is genuinely dirty first

        formatted = format_feature_content(dirty)

        assert _lint_clean(formatted)

    def test_formatting_preserves_scenario_tag_and_step_content_exactly(self) -> None:
        dirty = (
            "@REQ-x1 @AC-x1-01 @smoke   \n"
            "Feature: Sample feature   \n"
            "\n"
            "\n"
            "@SCN-x1-01-01\n"
            "Scenario: One   \n"
            "Given a   \n"
            "When b\n"
            "      Then c\n"
        )
        formatted = format_feature_content(dirty)

        before = _scenario_facts(dirty)
        after = _scenario_facts(formatted)
        assert before == after
        assert after == [("One", ("@SCN-x1-01-01",), ("Given a", "When b", "Then c"))]

    def test_a_lint_clean_feature_is_returned_byte_identical(self) -> None:
        req = _requirement()
        (ac,) = req.acceptance_criteria
        raw = (
            f"@smoke @{ac.criterion_id} @SCN-PENDING\n"
            "Scenario: One\n  Given a\n  When b\n  Then c\n"
        )
        gf = generate_feature_file(
            req,
            StubFeatureContentGenerator({req.requirement_id: raw}),
            features_root=Path("/tmp/unused"),
        )
        assert gf.lint_result.is_clean
        assert format_feature_content(gf.content) == gf.content

    def test_full_loop_on_a_formatting_only_defect_passes_via_tier1_alone(self) -> None:
        req = _requirement()
        (ac,) = req.acceptance_criteria
        # Two scenarios sharing the one AC, each with its own distinct
        # SCN-*/functional tag -- avoids the single-scenario homogeneity
        # edge case so the ONLY dirt here is formatting.
        dirty = (
            f"@REQ-{req.requirement_id.removeprefix('REQ-')} @{ac.criterion_id}   \n"
            f"Feature: {req.title}   \n"
            "\n"
            "\n"
            "@SCN-x1-01-01 @smoke\n"
            "Scenario: One   \n"
            "Given a   \n"
            "When b\n"
            "      Then c\n"
            "\n"
            "@SCN-x1-01-02 @regression\n"
            "Scenario: Two\n"
            "  Given d\n"
            "  When e\n"
            "  Then f\n"
        )
        result = run_cp2_remediation(
            req, dirty, req_tag=f"@{req.requirement_id}", remediator=StubFeatureRemediator([])
        )

        assert result.status == RemediationStatus.PASSED
        assert result.tier1_formatted is True
        assert result.llm_attempt_count == 0  # the stub was never called -- 0 responses sufficed


class TestTier2LoopMechanics:
    def _dupe_name_dirty_content(self, req: TestableRequirement) -> str:
        (ac,) = req.acceptance_criteria
        raw = (
            f"@smoke @{ac.criterion_id} @SCN-PENDING\n"
            "Scenario: Duplicate name\n"
            "  Given a\n"
            "  When b\n"
            "  Then c\n"
            "\n"
            f"@regression @{ac.criterion_id} @SCN-PENDING\n"
            "Scenario: Duplicate name\n"
            "  Given d\n"
            "  When e\n"
            "  Then f\n"
        )
        with pytest.raises(FeatureGenerationError) as excinfo:
            generate_feature_file(
                req,
                StubFeatureContentGenerator({req.requirement_id: raw}),
                features_root=Path("/tmp/unused"),
            )
        assert excinfo.value.content is not None
        return excinfo.value.content

    def _fixed_content(self, dirty: str) -> str:
        head, _sep, tail = dirty.rpartition("Scenario: Duplicate name")
        return head + "Scenario: Renamed second scenario" + tail

    def test_still_failing_content_never_falsely_passes_the_gate(self) -> None:
        """Gate-not-weakened proof: the remediator returns the SAME dirty
        content back (a remediator that fails to fix anything) -- CP2 must
        still, correctly, report it as failing, never a false PASS."""
        req = _requirement()
        dirty = self._dupe_name_dirty_content(req)
        remediator = StubFeatureRemediator([dirty, dirty])

        result = run_cp2_remediation(
            req, dirty, req_tag=f"@{req.requirement_id}", remediator=remediator
        )

        assert result.status == RemediationStatus.ESCALATED
        assert result.final_cp2_result.passed is False
        for attempt in result.attempts:
            assert attempt.cp2_result.passed is False

    def test_fixed_on_first_llm_attempt_passes_in_one_attempt(self) -> None:
        req = _requirement()
        dirty = self._dupe_name_dirty_content(req)
        fixed = self._fixed_content(dirty)
        assert _lint_clean(fixed)
        remediator = StubFeatureRemediator([fixed])

        result = run_cp2_remediation(
            req, dirty, req_tag=f"@{req.requirement_id}", remediator=remediator
        )

        assert result.status == RemediationStatus.PASSED
        assert result.llm_attempt_count == 1
        assert result.final_content == fixed

    def test_fixed_on_second_llm_attempt_passes_at_attempt_two(self) -> None:
        req = _requirement()
        dirty = self._dupe_name_dirty_content(req)
        fixed = self._fixed_content(dirty)
        # Attempt 1: remediator returns the SAME broken content (a bad fix).
        # Attempt 2: remediator returns the genuinely fixed content.
        remediator = StubFeatureRemediator([dirty, fixed])

        result = run_cp2_remediation(
            req, dirty, req_tag=f"@{req.requirement_id}", remediator=remediator
        )

        assert result.status == RemediationStatus.PASSED
        assert result.llm_attempt_count == 2
        assert result.attempts[0].cp2_result.passed is False
        assert result.attempts[1].cp2_result.passed is True
        assert result.final_content == fixed

    def test_never_fixed_escalates_at_exactly_two_attempts_not_one_not_three(self) -> None:
        req = _requirement()
        dirty = self._dupe_name_dirty_content(req)
        # Exactly MAX_LLM_REMEDIATION_ATTEMPTS (2) canned responses, both
        # still broken -- if the loop ever called remediate() a THIRD time,
        # StubFeatureRemediator would raise IndexError and this test would
        # error rather than reach the assertions below. Reaching them at
        # all is itself part of the "exactly 2" proof.
        remediator = StubFeatureRemediator([dirty, dirty])
        assert MAX_LLM_REMEDIATION_ATTEMPTS == 2

        result = run_cp2_remediation(
            req, dirty, req_tag=f"@{req.requirement_id}", remediator=remediator
        )

        assert result.status == RemediationStatus.ESCALATED
        assert result.llm_attempt_count == 2
        assert remediator.call_count == 2
        assert result.escalation_reason is not None
        assert "exhausted" in result.escalation_reason
        assert "2" in result.escalation_reason

    def test_non_remediable_no_files_without_scenarios_escalates_with_zero_llm_attempts(
        self,
    ) -> None:
        dirty = "@REQ-x1\nFeature: Empty of scenarios\n"
        remediator = StubFeatureRemediator([])  # zero responses -- must never be called

        result = run_cp2_remediation(
            _requirement(), dirty, req_tag="@REQ-x1", remediator=remediator
        )

        assert result.status == RemediationStatus.ESCALATED
        assert result.llm_attempt_count == 0
        assert result.tier1_formatted is False
        assert remediator.call_count == 0
        assert result.escalation_reason is not None
        assert "no-files-without-scenarios" in result.escalation_reason

    def test_non_remediable_no_empty_file_escalates_with_zero_llm_attempts(self) -> None:
        dirty = ""
        remediator = StubFeatureRemediator([])

        result = run_cp2_remediation(
            _requirement(), dirty, req_tag="@REQ-x1", remediator=remediator
        )

        assert result.status == RemediationStatus.ESCALATED
        assert result.llm_attempt_count == 0
        assert remediator.call_count == 0
        assert result.escalation_reason is not None
        assert "no-empty-file" in result.escalation_reason


class TestDeterminism:
    def test_same_inputs_and_stub_script_yield_the_same_outcome_across_two_runs(self) -> None:
        req = _requirement()
        (ac,) = req.acceptance_criteria
        raw = (
            f"@smoke @{ac.criterion_id} @SCN-PENDING\n"
            "Scenario: Duplicate name\n  Given a\n  When b\n  Then c\n"
            "\n"
            f"@regression @{ac.criterion_id} @SCN-PENDING\n"
            "Scenario: Duplicate name\n  Given d\n  When e\n  Then f\n"
        )
        with pytest.raises(FeatureGenerationError) as excinfo:
            generate_feature_file(
                req,
                StubFeatureContentGenerator({req.requirement_id: raw}),
                features_root=Path("/tmp/unused"),
            )
        dirty = excinfo.value.content
        assert dirty is not None
        head, _sep, tail = dirty.rpartition("Scenario: Duplicate name")
        fixed = head + "Scenario: Renamed" + tail

        first = run_cp2_remediation(
            req, dirty, req_tag=f"@{req.requirement_id}", remediator=StubFeatureRemediator([fixed])
        )
        second = run_cp2_remediation(
            req, dirty, req_tag=f"@{req.requirement_id}", remediator=StubFeatureRemediator([fixed])
        )

        assert first.status == second.status
        assert first.llm_attempt_count == second.llm_attempt_count
        assert first.final_content == second.final_content
        assert first.final_cp2_result == second.final_cp2_result


class TestSplitScenarioRemint:
    """ADR-0043 D2's split-scenario re-mint rule (2026-07-27 addendum;
    baseline register §4 item 13) -- Part 1's construct-tested proof.

    HONEST STATUS: two live runs (60 generations) observed ZERO scenario
    splits -- there is no real fixture to test this against. Every test
    below scripts a `StubFeatureRemediator` to construct a split by hand,
    including the one failure mode D2 explicitly forbids (the LLM copying
    the scenario-it-split-from's id onto BOTH resulting scenarios). This
    proves the mechanism works against a plausible worst case; it does not
    and cannot prove real model behaviour matches this shape.
    """

    def _dupe_name_dirty_content(self, req: TestableRequirement) -> str:
        (ac,) = req.acceptance_criteria
        raw = (
            f"@smoke @{ac.criterion_id} @SCN-PENDING\n"
            "Scenario: Duplicate name\n"
            "  Given a\n"
            "  When b\n"
            "  Then c\n"
            "\n"
            f"@regression @{ac.criterion_id} @SCN-PENDING\n"
            "Scenario: Duplicate name\n"
            "  Given d\n"
            "  When e\n"
            "  Then f\n"
        )
        with pytest.raises(FeatureGenerationError) as excinfo:
            generate_feature_file(
                req,
                StubFeatureContentGenerator({req.requirement_id: raw}),
                features_root=Path("/tmp/unused"),
            )
        assert excinfo.value.content is not None
        return excinfo.value.content

    def _scn_ids_in_document_order(self, content: str) -> list[str]:
        source = parse_source_text(content)
        assert source.feature is not None
        return [
            next(t["name"] for t in child["scenario"]["tags"] if t["name"].startswith("@SCN-"))
            for child in source.feature["children"]
        ]

    def _scn_tags_by_scenario(self, content: str) -> dict[str, str]:
        source = parse_source_text(content)
        assert source.feature is not None
        return {
            child["scenario"]["name"]: next(
                t["name"] for t in child["scenario"]["tags"] if t["name"].startswith("@SCN-")
            )
            for child in source.feature["children"]
        }

    def _construct_split_response(self, dirty: str, first_id: str) -> str:
        """Split scenario 1 ("Duplicate name", a/b/c) into a shortened
        survivor (a/b) keeping `first_id` untouched, plus a genuinely new
        scenario (c) the stub mis-tags with the SAME `first_id` -- copied
        from the scenario it split from, exactly what D2 forbids. Scenario
        2 is separately renamed to fix the original duplicate-name
        violation, unrelated to the split."""
        split = dirty.replace(
            f"  @smoke {first_id}\n"
            "  Scenario: Duplicate name\n"
            "    Given a\n"
            "    When b\n"
            "    Then c\n",
            f"  @smoke {first_id}\n"
            "  Scenario: Duplicate name\n"
            "    Given a\n"
            "    When b\n"
            "\n"
            f"  @smoke {first_id}\n"
            "  Scenario: Duplicate name split-off\n"
            "    Then c\n",
        )
        assert split != dirty  # confirm the replace actually matched
        return split.replace(
            "Scenario: Duplicate name\n    Given d",
            "Scenario: Renamed second scenario\n    Given d",
        )

    def test_survivor_keeps_id_new_scenario_gets_fresh_deterministic_id(self) -> None:
        req = _requirement()
        (ac,) = req.acceptance_criteria
        ac_short = ac.criterion_id.removeprefix("AC-")
        dirty = self._dupe_name_dirty_content(req)
        # Both original scenarios share the name "Duplicate name" (that's
        # the violation being fixed) -- `_scn_tags_by_scenario`'s name-keyed
        # dict can't disambiguate them, so read ids positionally instead.
        first_id, second_id = self._scn_ids_in_document_order(dirty)
        assert first_id != second_id

        split_response = self._construct_split_response(dirty, first_id)
        remediator = StubFeatureRemediator([split_response])

        result = run_cp2_remediation(
            req, dirty, req_tag=f"@{req.requirement_id}", remediator=remediator
        )

        assert result.status == RemediationStatus.PASSED
        assert result.llm_attempt_count == 1
        assert _lint_clean(result.final_content)

        final_tags = self._scn_tags_by_scenario(result.final_content)
        assert final_tags["Duplicate name"] == first_id  # survivor: untouched
        assert final_tags["Renamed second scenario"] == second_id  # unrelated survivor: untouched
        new_id = final_tags["Duplicate name split-off"]
        assert new_id not in (first_id, second_id)  # never copied from the original
        assert new_id == f"@SCN-{ac_short}-03"  # deterministic: next free ordinal past 01/02

    def test_determinism_same_split_content_yields_the_same_reminted_id(self) -> None:
        req = _requirement()
        dirty = self._dupe_name_dirty_content(req)
        first_id, _second_id = self._scn_ids_in_document_order(dirty)
        split_response = self._construct_split_response(dirty, first_id)
        req_tag = f"@{req.requirement_id}"

        first_run = run_cp2_remediation(
            req, dirty, req_tag=req_tag, remediator=StubFeatureRemediator([split_response])
        )
        second_run = run_cp2_remediation(
            req, dirty, req_tag=req_tag, remediator=StubFeatureRemediator([split_response])
        )

        assert first_run.status == second_run.status == RemediationStatus.PASSED
        assert first_run.final_content == second_run.final_content
        first_tags = self._scn_tags_by_scenario(first_run.final_content)
        second_tags = self._scn_tags_by_scenario(second_run.final_content)
        assert first_tags["Duplicate name split-off"] == second_tags["Duplicate name split-off"]

    def test_no_split_the_common_case_is_a_byte_identical_no_op(self) -> None:
        """All 60/60 live generations to date: a remediation that renames a
        scenario (or otherwise fixes a violation) without splitting must
        leave every SCN-* id exactly as the remediator returned it --
        proving the re-mint step is inert on the path every real run has
        actually taken."""
        req = _requirement()
        dirty = self._dupe_name_dirty_content(req)
        head, _sep, tail = dirty.rpartition("Scenario: Duplicate name")
        fixed = head + "Scenario: Renamed second scenario" + tail
        remediator = StubFeatureRemediator([fixed])

        result = run_cp2_remediation(
            req, dirty, req_tag=f"@{req.requirement_id}", remediator=remediator
        )

        assert result.status == RemediationStatus.PASSED
        assert result.final_content == fixed  # byte-identical: zero edits made
        assert result.attempts[0].content_after == fixed


class TestNoLlmNoNetworkNoIo:
    def test_remediation_package_never_imports_llm_factory(self) -> None:
        import ast

        remediation_dir = Path("feature_engineering/remediation")
        for py_file in remediation_dir.glob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "llm_factory" not in alias.name, f"{py_file}: imports {alias.name}"
                elif isinstance(node, ast.ImportFrom) and node.module:
                    assert "llm_factory" not in node.module, (
                        f"{py_file}: imports from {node.module}"
                    )
