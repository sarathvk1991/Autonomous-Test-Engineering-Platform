"""Stage 14 -- Feature Engineering as a resumable, persisted run/stage-state
stage (ADR-0036, ADR-0043 D8).

Proves: the two distinct output locations (untracked workspace `.feature`
files vs. the run-directory Validated Feature Package), the ADR-0036
SKIP-safety invariant (hash-match alone never sufficient -- exercised here
for the FIRST time at a genuine per-stage granularity, since stage 14 is the
first stage with on-disk artifacts before the pipeline's final bundle
write), the atomic-write guarantee stage 14 shares with every other stage,
per-requirement idempotency via `content_hash`, `traceability.json`'s
derived-not-authoritative status, and escalation handling (recorded, never
dropped; the stage's own run-state verdict stays SUCCEEDED). No LLM call
anywhere -- `StubFeatureContentGenerator`/`StubFeatureRemediator` throughout,
exactly like the generation/CP2/remediation unit's own tests.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from contracts.testable_requirement import (
    AcceptanceCriterionInput,
    Category,
    Priority,
    RequirementQualityGovernanceDecision,
    TestableRequirement,
    TestableRequirementSet,
    TestableRequirementSetProvenance,
    build_testable_requirement,
)
from feature_engineering.generation import FeatureGenerationError, StubFeatureContentGenerator
from feature_engineering.remediation import StubFeatureRemediator
from feature_engineering.stage import (
    execute_feature_engineering_stage,
    run_feature_engineering_stage,
)
from feature_engineering.stage.traceability import build_traceability_index
from requirement_intelligence.run_state import RunStateManager, StageStatus
from requirement_intelligence.run_state.models import StageRecord

_RUN_STATE_CONTRACT_VERSION = "1.0.0"


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
        ],
    }
    defaults.update(overrides)
    return build_testable_requirement(**defaults)  # type: ignore[arg-type]


def _requirement_set(
    requirements: list[TestableRequirement], *, run_id: str = "run-test"
) -> TestableRequirementSet:
    return TestableRequirementSet(
        run_id=run_id,
        generated_at=datetime.now(UTC),
        provenance=TestableRequirementSetProvenance(
            prompt_id="requirement_analysis",
            prompt_version="1.0.0",
            prompt_sha256="0" * 64,
            provider="stub",
            model="stub-model",
            requirement_quality_governance_decision=RequirementQualityGovernanceDecision.PASS,
            governance_report_ref="quality_governance_report.md",
        ),
        requirements=tuple(requirements),
        risks=(),
    )


def _clean_content(req: TestableRequirement, *, scenario_name: str | None = None) -> str:
    (ac,) = req.acceptance_criteria
    name = scenario_name or req.title
    return (
        f"@smoke @{ac.criterion_id} @SCN-PENDING\n"
        f"Scenario: {name}\n"
        "  Given a precondition\n"
        "  When an action occurs\n"
        "  Then an outcome is observed\n"
    )


def _dupe_name_raw_content(req: TestableRequirement) -> str:
    """RAW (un-assembled, no Feature-level `@REQ-*` tag) scenario content
    with duplicate scenario names -- reliably lint-dirty once assembled
    (`no-dupe-scenario-names`). This is what a `FeatureContentGenerator`
    returns; feeding it to `generate_feature_file` raises
    `FeatureGenerationError` with the ASSEMBLED (tagged) dirty text on
    `.content` -- the same technique `test_feature_engineering_remediation.py`
    uses to reach a real, remediable dirty feature."""
    (ac,) = req.acceptance_criteria
    return (
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


class _CountingContentGenerator:
    """Wraps `StubFeatureContentGenerator`, recording every requirement_id
    `.generate()` was actually called for -- the observable proof that an
    unchanged, reused requirement's content generator is never invoked."""

    def __init__(self, canned: dict[str, str]) -> None:
        self._stub = StubFeatureContentGenerator(canned)
        self.calls: list[str] = []

    def generate(self, requirement: TestableRequirement) -> str:
        self.calls.append(requirement.requirement_id)
        return self._stub.generate(requirement)


def _find_stage(run_state_mgr: RunStateManager, stage_id: str) -> StageRecord:
    return next(s for s in run_state_mgr.state.stages if s.stage_id == stage_id)


def _new_run_state_manager(run_dir: Path, *, run_id: str = "run-1") -> RunStateManager:
    return RunStateManager.create(
        run_dir,
        run_id=run_id,
        execution_name=None,
        contract_version=_RUN_STATE_CONTRACT_VERSION,
    )


def _single_stub_generator(req: TestableRequirement) -> StubFeatureContentGenerator:
    return StubFeatureContentGenerator({req.requirement_id: _clean_content(req)})


@pytest.mark.unit
class TestEndToEndStageRun:
    def test_two_requirements_generate_features_and_package(self, tmp_path: Path) -> None:
        req_a = _requirement(title="User can reset password", component="auth")
        req_b = _requirement(title="User can view profile", component="profile")
        rs = _requirement_set([req_a, req_b])
        features_root = tmp_path / "workspace" / "src" / "test" / "resources" / "features"
        run_dir = tmp_path / "run"
        run_dir.mkdir(parents=True)

        generator = _CountingContentGenerator(
            {
                req_a.requirement_id: _clean_content(req_a),
                req_b.requirement_id: _clean_content(req_b),
            }
        )
        result = run_feature_engineering_stage(
            rs,
            features_root=features_root,
            run_dir=run_dir,
            content_generator=generator,
            remediator=StubFeatureRemediator([]),
        )

        assert len(result.package.records) == 2
        assert generator.calls == [req_a.requirement_id, req_b.requirement_id]
        for record in result.package.records:
            assert record.escalated is False
            assert record.cp2_verdict == "pass"
            assert record.feature_path is not None
            assert (features_root / record.feature_path).exists()

        assert result.package_path.exists()
        assert result.traceability_path.exists()
        assert result.report_path.exists()

    def test_run_state_stage_succeeds_with_correct_artifacts(self, tmp_path: Path) -> None:
        req = _requirement()
        rs = _requirement_set([req])
        features_root = tmp_path / "workspace" / "features"
        run_dir = tmp_path / "run"
        run_dir.mkdir(parents=True)
        trs_path = run_dir / "testable_requirement_set.json"
        trs_path.write_text(
            json.dumps(rs.model_dump(mode="json", by_alias=True)), encoding="utf-8"
        )

        run_state_mgr = _new_run_state_manager(run_dir)
        generator = _CountingContentGenerator({req.requirement_id: _clean_content(req)})
        result = execute_feature_engineering_stage(
            run_state_mgr,
            run_dir,
            rs,
            features_root=features_root,
            content_generator=generator,
            remediator=StubFeatureRemediator([]),
            input_artifacts=[trs_path],
        )

        assert result is not None
        stage = _find_stage(run_state_mgr, "feature_engineering")
        assert stage.status == StageStatus.SUCCEEDED
        assert stage.started_at is not None
        assert stage.ended_at is not None
        assert str(trs_path) in stage.input_artifacts
        for path in result.all_output_paths:
            assert str(path) in stage.output_artifacts

        # run_state.json itself is valid JSON on disk, per the same
        # atomic-write mechanism every other stage uses.
        on_disk = json.loads((run_dir / "run_state.json").read_text())
        fe_record = next(s for s in on_disk["stages"] if s["stageId"] == "feature_engineering")
        assert fe_record["status"] == "succeeded"


@pytest.mark.unit
class TestOutputLocationsAreDistinct:
    def test_workspace_features_and_run_dir_package_are_separate_trees(
        self, tmp_path: Path
    ) -> None:
        req = _requirement()
        rs = _requirement_set([req])
        features_root = tmp_path / "workspace" / "src" / "test" / "resources" / "features"
        run_dir = tmp_path / "run"
        run_dir.mkdir(parents=True)

        result = run_feature_engineering_stage(
            rs,
            features_root=features_root,
            run_dir=run_dir,
            content_generator=_single_stub_generator(req),
            remediator=StubFeatureRemediator([]),
        )

        # The .feature file lives under features_root (ADR-0037/ADR-0041).
        record = result.package.record_for(req.requirement_id)
        assert record is not None and record.feature_path is not None
        feature_file = features_root / record.feature_path
        assert feature_file.exists()
        assert features_root in feature_file.parents

        # The package/traceability/report live in run_dir, never under
        # features_root -- and vice versa.
        assert result.package_path.parent == run_dir
        assert result.traceability_path.parent == run_dir
        assert result.report_path.parent == run_dir
        assert run_dir not in feature_file.parents
        assert features_root not in result.package_path.parents


@pytest.mark.unit
class TestTraceabilityDerivedNotAuthoritative:
    def test_index_is_rebuildable_purely_from_feature_file_tags(self, tmp_path: Path) -> None:
        req = _requirement()
        rs = _requirement_set([req])
        features_root = tmp_path / "features"
        run_dir = tmp_path / "run"
        run_dir.mkdir(parents=True)

        result = run_feature_engineering_stage(
            rs,
            features_root=features_root,
            run_dir=run_dir,
            content_generator=_single_stub_generator(req),
            remediator=StubFeatureRemediator([]),
        )

        original = json.loads(result.traceability_path.read_text())["entries"]
        assert len(original) == 1
        assert original[0]["requirementId"] == req.requirement_id

        # Deleting traceability.json loses no information: rebuilding it
        # purely from the (untouched) .feature file's own tags reproduces
        # the identical index.
        result.traceability_path.unlink()
        assert not result.traceability_path.exists()
        rebuilt = build_traceability_index(result.package.records, features_root=features_root)
        assert rebuilt == original

    def test_index_entries_come_from_tags_not_from_the_package_record(
        self, tmp_path: Path
    ) -> None:
        """If the on-disk .feature file's tags were the only source, editing
        the file (not the package) changes the index -- proving the package
        record itself is not what traceability.json is built from."""
        req = _requirement()
        rs = _requirement_set([req])
        features_root = tmp_path / "features"
        run_dir = tmp_path / "run"
        run_dir.mkdir(parents=True)

        result = run_feature_engineering_stage(
            rs,
            features_root=features_root,
            run_dir=run_dir,
            content_generator=StubFeatureContentGenerator(
                {req.requirement_id: _clean_content(req, scenario_name="Original name")}
            ),
            remediator=StubFeatureRemediator([]),
        )
        record = result.package.record_for(req.requirement_id)
        assert record is not None and record.feature_path is not None
        feature_file = features_root / record.feature_path
        original_index = build_traceability_index(
            result.package.records, features_root=features_root
        )
        assert original_index[0]["scenarioName"] == "Original name"

        # Hand-edit the .feature file's scenario name directly (simulating a
        # human/self-healing edit in the workspace) without touching the
        # package at all.
        edited = feature_file.read_text().replace("Original name", "Edited name")
        feature_file.write_text(edited, encoding="utf-8")

        re_derived = build_traceability_index(result.package.records, features_root=features_root)
        assert re_derived[0]["scenarioName"] == "Edited name"


@pytest.mark.unit
class TestSkipSafety:
    def test_resume_unchanged_is_skipped_and_generator_is_never_called(
        self, tmp_path: Path
    ) -> None:
        req = _requirement()
        rs = _requirement_set([req])
        features_root = tmp_path / "features"
        run_dir = tmp_path / "run"
        run_dir.mkdir(parents=True)
        trs_path = run_dir / "testable_requirement_set.json"
        trs_path.write_text(json.dumps(rs.model_dump(mode="json", by_alias=True)), encoding="utf-8")

        run_state_mgr = _new_run_state_manager(run_dir)
        first = execute_feature_engineering_stage(
            run_state_mgr,
            run_dir,
            rs,
            features_root=features_root,
            content_generator=_CountingContentGenerator({req.requirement_id: _clean_content(req)}),
            remediator=StubFeatureRemediator([]),
            input_artifacts=[trs_path],
        )
        assert first is not None
        assert _find_stage(run_state_mgr, "feature_engineering").status == StageStatus.SUCCEEDED

        resumed_generator = _CountingContentGenerator({req.requirement_id: _clean_content(req)})
        second = execute_feature_engineering_stage(
            run_state_mgr,
            run_dir,
            rs,
            features_root=features_root,
            content_generator=resumed_generator,
            remediator=StubFeatureRemediator([]),
            input_artifacts=[trs_path],
        )

        assert second is None  # SKIPPED, not re-run
        assert _find_stage(run_state_mgr, "feature_engineering").status == StageStatus.SKIPPED
        assert resumed_generator.calls == []  # never invoked -- proves a true skip

    def test_deleting_a_workspace_feature_forces_a_rerun(self, tmp_path: Path) -> None:
        req = _requirement()
        rs = _requirement_set([req])
        features_root = tmp_path / "features"
        run_dir = tmp_path / "run"
        run_dir.mkdir(parents=True)
        trs_path = run_dir / "testable_requirement_set.json"
        trs_path.write_text(json.dumps(rs.model_dump(mode="json", by_alias=True)), encoding="utf-8")

        run_state_mgr = _new_run_state_manager(run_dir)
        first = execute_feature_engineering_stage(
            run_state_mgr,
            run_dir,
            rs,
            features_root=features_root,
            content_generator=_CountingContentGenerator({req.requirement_id: _clean_content(req)}),
            remediator=StubFeatureRemediator([]),
            input_artifacts=[trs_path],
        )
        assert first is not None
        record = first.package.record_for(req.requirement_id)
        assert record is not None and record.feature_path is not None
        (features_root / record.feature_path).unlink()  # simulate loss/self-heal churn

        rerun_generator = _CountingContentGenerator({req.requirement_id: _clean_content(req)})
        second = execute_feature_engineering_stage(
            run_state_mgr,
            run_dir,
            rs,
            features_root=features_root,
            content_generator=rerun_generator,
            remediator=StubFeatureRemediator([]),
            input_artifacts=[trs_path],
        )

        # Hash-match alone never skips: the output is missing, so the whole
        # -stage should_skip returns False and the stage genuinely re-runs.
        assert second is not None
        assert _find_stage(run_state_mgr, "feature_engineering").status == StageStatus.SUCCEEDED
        assert rerun_generator.calls == [req.requirement_id]
        assert (features_root / record.feature_path).exists()  # regenerated


@pytest.mark.unit
class TestAtomicWriteInterruption:
    def test_interrupted_run_state_write_during_stage_14_stays_parseable(
        self, tmp_path: Path
    ) -> None:
        run_dir = tmp_path / "run"
        run_dir.mkdir(parents=True)
        run_state_mgr = _new_run_state_manager(run_dir)
        before = json.loads((run_dir / "run_state.json").read_text())

        trs_path = run_dir / "testable_requirement_set.json"
        with patch("os.replace", side_effect=OSError("simulated crash before rename")):
            with pytest.raises(OSError, match="simulated crash"):
                run_state_mgr.start_stage("feature_engineering", input_artifacts=[trs_path])

        # The file on disk must remain exactly what it was before the crash
        # -- never a torn write -- and it must still parse.
        after_text = (run_dir / "run_state.json").read_text()
        after = json.loads(after_text)  # raises if unparseable
        assert after == before
        fe = next(s for s in after["stages"] if s["stageId"] == "feature_engineering")
        assert fe["status"] == "pending"  # the crashed transition never landed


@pytest.mark.unit
class TestPerRequirementReuse:
    def test_only_the_changed_requirement_regenerates(self, tmp_path: Path) -> None:
        req_a = _requirement(title="User can reset password", component="auth")
        req_b = _requirement(title="User can view profile", component="profile")
        rs1 = _requirement_set([req_a, req_b])
        features_root = tmp_path / "features"
        run_dir = tmp_path / "run"
        run_dir.mkdir(parents=True)

        gen1 = _CountingContentGenerator(
            {
                req_a.requirement_id: _clean_content(req_a),
                req_b.requirement_id: _clean_content(req_b),
            }
        )
        result1 = run_feature_engineering_stage(
            rs1,
            features_root=features_root,
            run_dir=run_dir,
            content_generator=gen1,
            remediator=StubFeatureRemediator([]),
        )
        assert sorted(gen1.calls) == sorted([req_a.requirement_id, req_b.requirement_id])
        record_b_before = result1.package.record_for(req_b.requirement_id)
        assert record_b_before is not None and record_b_before.feature_path is not None
        content_b_before = (features_root / record_b_before.feature_path).read_text()

        # req_a's identity (requirement_id, derived from title + traces_to)
        # is unchanged, but its narrative changes -- a new content_hash for
        # the SAME requirement_id.
        req_a2 = _requirement(
            title="User can reset password", component="auth", narrative="Updated narrative."
        )
        assert req_a2.requirement_id == req_a.requirement_id
        assert req_a2.content_hash != req_a.content_hash

        rs2 = _requirement_set([req_a2, req_b])
        gen2 = _CountingContentGenerator(
            {
                req_a2.requirement_id: _clean_content(req_a2, scenario_name="Updated scenario"),
                req_b.requirement_id: _clean_content(req_b),
            }
        )
        result2 = run_feature_engineering_stage(
            rs2,
            features_root=features_root,
            run_dir=run_dir,
            content_generator=gen2,
            remediator=StubFeatureRemediator([]),
        )

        # Only the changed requirement was regenerated.
        assert gen2.calls == [req_a2.requirement_id]

        record_b_after = result2.package.record_for(req_b.requirement_id)
        assert record_b_after == record_b_before  # byte-identical record, reused verbatim
        assert record_b_after is not None and record_b_after.feature_path is not None
        content_b_after = (features_root / record_b_after.feature_path).read_text()
        assert content_b_after == content_b_before  # workspace file untouched

        record_a_after = result2.package.record_for(req_a2.requirement_id)
        assert record_a_after is not None and record_a_after.content_hash == req_a2.content_hash
        assert record_a_after.content_hash != record_b_before.content_hash


@pytest.mark.unit
class TestEscalationHandling:
    def test_unfixable_feature_is_recorded_escalated_and_stage_still_succeeds(
        self, tmp_path: Path
    ) -> None:
        req = _requirement()
        rs = _requirement_set([req])
        features_root = tmp_path / "features"
        run_dir = tmp_path / "run"
        run_dir.mkdir(parents=True)
        trs_path = run_dir / "testable_requirement_set.json"
        trs_path.write_text(json.dumps(rs.model_dump(mode="json", by_alias=True)), encoding="utf-8")

        raw = _dupe_name_raw_content(req)
        from feature_engineering.generation import generate_feature_file

        with pytest.raises(FeatureGenerationError) as excinfo:
            generate_feature_file(
                req,
                StubFeatureContentGenerator({req.requirement_id: raw}),
                features_root=Path("/tmp/unused"),
            )
        expected_dirty_content = excinfo.value.content
        assert expected_dirty_content is not None

        # StubFeatureRemediator scripted with the SAME dirty content both
        # attempts -- never fixed, so D5 exhausts and escalates.
        remediator = StubFeatureRemediator([expected_dirty_content, expected_dirty_content])

        run_state_mgr = _new_run_state_manager(run_dir)
        result = execute_feature_engineering_stage(
            run_state_mgr,
            run_dir,
            rs,
            features_root=features_root,
            content_generator=StubFeatureContentGenerator({req.requirement_id: raw}),
            remediator=remediator,
            input_artifacts=[trs_path],
        )

        assert result is not None
        record = result.package.record_for(req.requirement_id)
        assert record is not None
        assert record.escalated is True
        assert record.remediated is True
        assert record.cp2_verdict == "fail"
        assert record.escalation_reason is not None
        assert "exhausted" in record.escalation_reason

        # Not silently dropped: the (still-dirty) content is still written
        # to the workspace for a human to review.
        assert record.feature_path is not None
        feature_file = features_root / record.feature_path
        assert feature_file.exists()
        assert feature_file.read_text() == expected_dirty_content

        # The stage's own run-state verdict is SUCCEEDED -- an escalation is
        # a content-level, human-in-the-loop outcome, not a stage failure
        # (mirrors every other Layer 1 tail phase's own non-fatal posture).
        assert _find_stage(run_state_mgr, "feature_engineering").status == StageStatus.SUCCEEDED
        assert result.has_escalations is True


@pytest.mark.unit
class TestNoLlmNoIo:
    def test_stage_package_never_imports_llm_factory(self) -> None:
        import ast

        stage_dir = Path("feature_engineering/stage")
        for py_file in stage_dir.glob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "llm_factory" not in alias.name, f"{py_file}: imports {alias.name}"
                elif isinstance(node, ast.ImportFrom) and node.module:
                    assert "llm_factory" not in node.module, (
                        f"{py_file}: imports from {node.module}"
                    )
