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
import subprocess
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
from feature_engineering.generation import (
    FeatureGenerationError,
    StubFeatureContentGenerator,
    TransportFailureError,
)
from feature_engineering.remediation import StubFeatureRemediator
from feature_engineering.stage import (
    execute_feature_engineering_stage,
    features_root_for,
    materialize_workspace,
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


def _workspace_features_root(run_dir: Path) -> Path:
    """Where `execute_feature_engineering_stage` (via ADR-0037 Path A
    materialization) actually writes -- inside THIS run's own workspace
    copy, not the shared tracked baseline."""
    return features_root_for(run_dir / "workspace")


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
        assert result.test_data_specifications_path.exists()

    def test_test_data_specifications_json_has_one_entry_per_requirement(
        self, tmp_path: Path
    ) -> None:
        """ADR-0043 D7's own emission, additive to this stage
        (`.test_data_spec`): one specification per requirement,
        unconditionally -- proven here at the actual stage-output level,
        not only against the emitter function directly."""
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

        on_disk = json.loads(result.test_data_specifications_path.read_text(encoding="utf-8"))
        assert {entry["requirementId"] for entry in on_disk["specifications"]} == {
            req_a.requirement_id,
            req_b.requirement_id,
        }
        # Neither of these fixture requirements carries data_fields -- the
        # honest-empty finding, reproduced at the stage-output level.
        for entry in on_disk["specifications"]:
            assert entry["fields"] == []

    def test_run_state_stage_succeeds_with_correct_artifacts(self, tmp_path: Path) -> None:
        req = _requirement()
        rs = _requirement_set([req])
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
        run_dir = tmp_path / "run"
        run_dir.mkdir(parents=True)
        trs_path = run_dir / "testable_requirement_set.json"
        trs_path.write_text(json.dumps(rs.model_dump(mode="json", by_alias=True)), encoding="utf-8")

        run_state_mgr = _new_run_state_manager(run_dir)
        first = execute_feature_engineering_stage(
            run_state_mgr,
            run_dir,
            rs,
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
        run_dir = tmp_path / "run"
        run_dir.mkdir(parents=True)
        trs_path = run_dir / "testable_requirement_set.json"
        trs_path.write_text(json.dumps(rs.model_dump(mode="json", by_alias=True)), encoding="utf-8")

        run_state_mgr = _new_run_state_manager(run_dir)
        first = execute_feature_engineering_stage(
            run_state_mgr,
            run_dir,
            rs,
            content_generator=_CountingContentGenerator({req.requirement_id: _clean_content(req)}),
            remediator=StubFeatureRemediator([]),
            input_artifacts=[trs_path],
        )
        assert first is not None
        record = first.package.record_for(req.requirement_id)
        assert record is not None and record.feature_path is not None
        features_root = _workspace_features_root(run_dir)
        (features_root / record.feature_path).unlink()  # simulate loss/self-heal churn

        rerun_generator = _CountingContentGenerator({req.requirement_id: _clean_content(req)})
        second = execute_feature_engineering_stage(
            run_state_mgr,
            run_dir,
            rs,
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
        feature_file = _workspace_features_root(run_dir) / record.feature_path
        assert feature_file.exists()
        assert feature_file.read_text() == expected_dirty_content

        # The stage's own run-state verdict is SUCCEEDED -- an escalation is
        # a content-level, human-in-the-loop outcome, not a stage failure
        # (mirrors every other Layer 1 tail phase's own non-fatal posture).
        assert _find_stage(run_state_mgr, "feature_engineering").status == StageStatus.SUCCEEDED
        assert result.has_escalations is True


class _TransportFailureContentGenerator:
    """Simulates a live provider's boundary failure (429/quota/timeout) for
    one requirement_id, delegating to `StubFeatureContentGenerator` for
    everything else -- the fake this test suite uses in place of a real
    `LiveFeatureContentGenerator` hitting a real 429, per ADR-0043 D5's own
    stub/live seam discipline (no live call anywhere in this test file)."""

    def __init__(self, canned: dict[str, str], *, fails_for: str) -> None:
        self._stub = StubFeatureContentGenerator(canned)
        self._fails_for = fails_for

    def generate(self, requirement: TestableRequirement) -> str:
        if requirement.requirement_id == self._fails_for:
            raise TransportFailureError(
                f"requirement_id={requirement.requirement_id!r}: LLM provider call failed: "
                "429 RESOURCE_EXHAUSTED"
            )
        return self._stub.generate(requirement)


class _TransportFailureRemediator:
    """Simulates a live remediator's boundary failure -- symmetric to
    `_TransportFailureContentGenerator`, for the D5 remediation call site."""

    def remediate(self, content: str, violations: object) -> str:
        raise TransportFailureError("LLM provider call failed: 429 RESOURCE_EXHAUSTED")


@pytest.mark.unit
class TestTransportFailureEscalation:
    """F1 (2026-08-04, the Layer 1-3 integration run): a transport failure
    (provider/quota/timeout -- `TransportFailureError`, the shared base
    `LiveGenerationError`/`LiveRemediationError` now subclass) at the
    content-generator/remediator boundary is per-requirement recoverable,
    exactly like a content (`FeatureGenerationError`) failure -- it must
    never abort the whole stage. Before this fix, a live 429 on the first
    of 20 requirements failed stage 14 outright with zero requirements
    processed; these tests reproduce that shape deterministically, with a
    fake that raises the same exception a live 429 does, never a real call.
    """

    def test_transport_failure_on_one_requirement_escalates_it_and_stage_continues(
        self, tmp_path: Path
    ) -> None:
        req_ok = _requirement(title="User can reset password")
        req_fails = _requirement(title="User can view order history")
        rs = _requirement_set([req_ok, req_fails])
        run_dir = tmp_path / "run"
        run_dir.mkdir(parents=True)
        trs_path = run_dir / "testable_requirement_set.json"
        trs_path.write_text(json.dumps(rs.model_dump(mode="json", by_alias=True)), encoding="utf-8")

        content_generator = _TransportFailureContentGenerator(
            {req_ok.requirement_id: _clean_content(req_ok)},
            fails_for=req_fails.requirement_id,
        )
        run_state_mgr = _new_run_state_manager(run_dir)
        result = execute_feature_engineering_stage(
            run_state_mgr,
            run_dir,
            rs,
            content_generator=content_generator,
            remediator=StubFeatureRemediator([]),
            input_artifacts=[trs_path],
        )

        # The stage did NOT abort: it produced a result, and it SUCCEEDED,
        # not FAILED -- the whole point of this fix.
        assert result is not None
        assert _find_stage(run_state_mgr, "feature_engineering").status == StageStatus.SUCCEEDED

        ok_record = result.package.record_for(req_ok.requirement_id)
        assert ok_record is not None
        assert ok_record.escalated is False
        assert ok_record.cp2_verdict == "pass"

        failed_record = result.package.record_for(req_fails.requirement_id)
        assert failed_record is not None
        assert failed_record.escalated is True
        assert failed_record.remediated is False
        assert failed_record.feature_path is None
        assert failed_record.escalation_reason is not None
        assert failed_record.escalation_reason.startswith("transport failure (no retry attempted):")
        assert "429 RESOURCE_EXHAUSTED" in failed_record.escalation_reason

        assert result.has_escalations is True

    def test_transport_failure_and_content_failure_escalate_with_different_reasons(
        self, tmp_path: Path
    ) -> None:
        req_transport = _requirement(title="User can view order history")
        req_content = _requirement(title="User can filter search results")
        rs = _requirement_set([req_transport, req_content])
        run_dir = tmp_path / "run"
        run_dir.mkdir(parents=True)
        trs_path = run_dir / "testable_requirement_set.json"
        trs_path.write_text(json.dumps(rs.model_dump(mode="json", by_alias=True)), encoding="utf-8")

        # req_content's raw content carries a forbidden @REQ-* tag -- a
        # pre-assembly tag-contract violation, FeatureGenerationError with
        # content=None (assembler.py), the "unrecoverable" content-failure
        # path, unrelated to any transport condition.
        bad_content = "@REQ-should-never-appear\n" + _clean_content(req_content)
        canned = {req_content.requirement_id: bad_content}
        content_generator = _TransportFailureContentGenerator(
            canned, fails_for=req_transport.requirement_id
        )
        run_state_mgr = _new_run_state_manager(run_dir)
        result = execute_feature_engineering_stage(
            run_state_mgr,
            run_dir,
            rs,
            content_generator=content_generator,
            remediator=StubFeatureRemediator([]),
            input_artifacts=[trs_path],
        )

        assert result is not None
        assert _find_stage(run_state_mgr, "feature_engineering").status == StageStatus.SUCCEEDED

        transport_record = result.package.record_for(req_transport.requirement_id)
        content_record = result.package.record_for(req_content.requirement_id)
        assert transport_record is not None and content_record is not None
        assert transport_record.escalated is True
        assert content_record.escalated is True

        assert transport_record.escalation_reason is not None
        assert content_record.escalation_reason is not None
        # Different escalation REASONS, taxonomy preserved -- a human
        # reviewing an escalation must be able to tell provider/network
        # conditions apart from a generated-content contract violation.
        assert transport_record.escalation_reason.startswith("transport failure")
        assert content_record.escalation_reason.startswith(
            "pre-assembly generation contract violation"
        )
        assert transport_record.escalation_reason != content_record.escalation_reason

    def test_transport_failure_during_remediation_escalates_and_stage_continues(
        self, tmp_path: Path
    ) -> None:
        req = _requirement()
        rs = _requirement_set([req])
        run_dir = tmp_path / "run"
        run_dir.mkdir(parents=True)
        trs_path = run_dir / "testable_requirement_set.json"
        trs_path.write_text(json.dumps(rs.model_dump(mode="json", by_alias=True)), encoding="utf-8")

        # Content that reaches D5 (CP2-fails-after-assembly, not a
        # pre-assembly contract violation): duplicate scenario names.
        raw = _dupe_name_raw_content(req)
        run_state_mgr = _new_run_state_manager(run_dir)
        result = execute_feature_engineering_stage(
            run_state_mgr,
            run_dir,
            rs,
            content_generator=StubFeatureContentGenerator({req.requirement_id: raw}),
            remediator=_TransportFailureRemediator(),
            input_artifacts=[trs_path],
        )

        assert result is not None
        assert _find_stage(run_state_mgr, "feature_engineering").status == StageStatus.SUCCEEDED

        record = result.package.record_for(req.requirement_id)
        assert record is not None
        assert record.escalated is True
        assert record.remediated is False
        assert record.feature_path is None
        assert record.escalation_reason is not None
        assert record.escalation_reason.startswith("transport failure (no retry attempted):")


@pytest.mark.unit
class TestWorkspaceMaterialization:
    """ADR-0037 Path A: each run gets its own isolated copy of the tracked
    baseline; the tracked module itself is never written to."""

    def test_two_runs_get_distinct_workspace_copies_no_collision(self, tmp_path: Path) -> None:
        req_1 = _requirement(title="Run one requirement", component="auth")
        req_2 = _requirement(title="Run two requirement", component="auth")
        run_dir_1 = tmp_path / "run-1"
        run_dir_2 = tmp_path / "run-2"
        run_dir_1.mkdir(parents=True)
        run_dir_2.mkdir(parents=True)

        result_1 = run_feature_engineering_stage(
            _requirement_set([req_1], run_id="run-1"),
            features_root=features_root_for(materialize_workspace(run_dir_1)),
            run_dir=run_dir_1,
            content_generator=_single_stub_generator(req_1),
            remediator=StubFeatureRemediator([]),
        )
        result_2 = run_feature_engineering_stage(
            _requirement_set([req_2], run_id="run-2"),
            features_root=features_root_for(materialize_workspace(run_dir_2)),
            run_dir=run_dir_2,
            content_generator=_single_stub_generator(req_2),
            remediator=StubFeatureRemediator([]),
        )

        record_1 = result_1.package.record_for(req_1.requirement_id)
        record_2 = result_2.package.record_for(req_2.requirement_id)
        assert record_1 is not None and record_1.feature_path is not None
        assert record_2 is not None and record_2.feature_path is not None
        path_1 = _workspace_features_root(run_dir_1) / record_1.feature_path
        path_2 = _workspace_features_root(run_dir_2) / record_2.feature_path

        assert path_1 != path_2
        assert path_1.exists()
        assert path_2.exists()
        # Distinct workspace ROOTS entirely -- run-2's copy never contains
        # run-1's generated feature, and vice versa.
        assert (run_dir_1 / "workspace") != (run_dir_2 / "workspace")
        assert not (run_dir_2 / "workspace" / record_1.feature_path).exists()
        assert not (run_dir_1 / "workspace" / record_2.feature_path).exists()

    def test_tracked_baseline_is_never_written_to(self, tmp_path: Path) -> None:
        req = _requirement()
        run_dir = tmp_path / "run"
        run_dir.mkdir(parents=True)
        baseline_smoke = Path("test-suite-baseline/src/test/resources/features/smoke.feature")
        before_bytes = baseline_smoke.read_bytes()

        run_feature_engineering_stage(
            _requirement_set([req]),
            features_root=features_root_for(materialize_workspace(run_dir)),
            run_dir=run_dir,
            content_generator=_single_stub_generator(req),
            remediator=StubFeatureRemediator([]),
        )

        assert baseline_smoke.read_bytes() == before_bytes  # byte-identical
        status = subprocess.run(
            ["git", "status", "--porcelain", "test-suite-baseline/"],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            check=True,
        )
        assert status.stdout == ""  # tracked module reports clean

    def test_run_copy_is_a_complete_runnable_maven_module(self, tmp_path: Path) -> None:
        req = _requirement()
        run_dir = tmp_path / "run"
        run_dir.mkdir(parents=True)

        workspace_dir = materialize_workspace(run_dir)
        run_feature_engineering_stage(
            _requirement_set([req]),
            features_root=features_root_for(workspace_dir),
            run_dir=run_dir,
            content_generator=_single_stub_generator(req),
            remediator=StubFeatureRemediator([]),
        )

        # Framework files copied verbatim from the tracked baseline.
        assert (workspace_dir / "pom.xml").exists()
        runner_java = "src/test/java/com/automation/runners/RunCucumberTest.java"
        assert (workspace_dir / runner_java).exists()
        assert (workspace_dir / "src/test/java/com/automation/base/ConfigReader.java").exists()
        assert (workspace_dir / "src/test/java/com/automation/base/BasePage.java").exists()
        assert (workspace_dir / "src/test/resources/junit-platform.properties").exists()
        assert (workspace_dir / "src/test/resources/config.properties").exists()
        # The tracked smoke feature travels with the copy...
        assert (workspace_dir / "src/test/resources/features/smoke.feature").exists()
        # ...alongside the newly generated feature -- both resolvable by
        # @SelectClasspathResource("features") within this one copy.
        generated = list((workspace_dir / "src/test/resources/features").rglob("*.feature"))
        assert any(p.name == "smoke.feature" for p in generated)
        assert any(p.name != "smoke.feature" for p in generated)
        # Build output is NOT copied -- it is Maven's to regenerate.
        assert not (workspace_dir / "target").exists()

    def test_resume_safety_materialization_never_wipes_prior_generation(
        self, tmp_path: Path
    ) -> None:
        """The one hazard Path A introduces: resuming a run must find its
        existing workspace intact, never a fresh baseline copy that
        destroys already-generated features."""
        run_dir = tmp_path / "run"
        run_dir.mkdir(parents=True)

        workspace_dir = materialize_workspace(run_dir)
        marker = workspace_dir / "src/test/resources/features/auth/marker.feature"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("# simulates prior generation", encoding="utf-8")

        # A second materialize_workspace call -- e.g. a resumed run, or a
        # retried stage-14 attempt within the same run -- must return the
        # SAME directory, untouched.
        again = materialize_workspace(run_dir)
        assert again == workspace_dir
        assert marker.exists()
        assert marker.read_text(encoding="utf-8") == "# simulates prior generation"

    def test_resume_via_execute_feature_engineering_stage_preserves_workspace(
        self, tmp_path: Path
    ) -> None:
        """End-to-end version of the resume-safety proof, through the
        actual stage-14 wiring: SKIP on resume must not touch the
        workspace at all (materialization only happens on a genuine run)."""
        req = _requirement()
        rs = _requirement_set([req])
        run_dir = tmp_path / "run"
        run_dir.mkdir(parents=True)
        trs_path = run_dir / "testable_requirement_set.json"
        trs_path.write_text(json.dumps(rs.model_dump(mode="json", by_alias=True)), encoding="utf-8")

        run_state_mgr = _new_run_state_manager(run_dir)
        first = execute_feature_engineering_stage(
            run_state_mgr,
            run_dir,
            rs,
            content_generator=_single_stub_generator(req),
            remediator=StubFeatureRemediator([]),
            input_artifacts=[trs_path],
        )
        assert first is not None
        record = first.package.record_for(req.requirement_id)
        assert record is not None and record.feature_path is not None
        feature_file = _workspace_features_root(run_dir) / record.feature_path
        content_before = feature_file.read_text(encoding="utf-8")

        second = execute_feature_engineering_stage(
            run_state_mgr,
            run_dir,
            rs,
            content_generator=_single_stub_generator(req),
            remediator=StubFeatureRemediator([]),
            input_artifacts=[trs_path],
        )

        assert second is None  # SKIPPED
        assert feature_file.read_text(encoding="utf-8") == content_before  # untouched


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
