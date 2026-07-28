"""Tests for requirement_intelligence.run_state (ADR-0036, ADR-0032 carve-out 2).

Covers: stage enumeration completeness, atomic writes (including interruption
safety), the lockfile's acquire/refuse/stale-break behaviour, and the
RunStateManager's skip predicate (both invariants, never hash-alone),
contract_version global invalidation, and resume-point computation.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from requirement_intelligence.run_state import (
    LIVE_STAGE_IDS,
    PLACEHOLDER_STAGE_IDS,
    STAGE_DEFINITIONS,
    RunLock,
    RunLockError,
    RunStateCorruptError,
    RunStateManager,
    StageStatus,
    generate_run_id,
    stage_definition,
)
from requirement_intelligence.run_state.atomic_write import atomic_write_json, read_json_if_valid


@pytest.mark.unit
class TestStageDefinitions:
    def test_total_count_is_twenty(self) -> None:
        assert len(STAGE_DEFINITIONS) == 20

    def test_live_and_placeholder_counts(self) -> None:
        # 13 ADR-0036 L1 stages + TRS emission + stage 14 (Feature Engineering,
        # wired into the live CLI sequence -- see scripts/run_requirement_analysis.py).
        assert len(LIVE_STAGE_IDS) == 15
        assert len(PLACEHOLDER_STAGE_IDS) == 5  # Layers 3-7

    def test_stage_ids_are_unique(self) -> None:
        ids = [d.stage_id for d in STAGE_DEFINITIONS]
        assert len(ids) == len(set(ids))

    def test_adr0036_numbers_1_through_19_all_present_once(self) -> None:
        numbers = [d.stage_number for d in STAGE_DEFINITIONS if d.stage_number is not None]
        assert sorted(numbers) == list(range(1, 20))

    def test_testable_requirement_emission_has_no_adr0036_number(self) -> None:
        d = stage_definition("testable_requirement_emission")
        assert d.stage_number is None

    def test_execution_package_write_is_last_among_live_stages(self) -> None:
        """The reported divergence: numbered 9 in ADR-0036, but the last stage
        to actually execute — array order reflects execution order, not the
        ADR's literal numbering."""
        live_ids = [d.stage_id for d in STAGE_DEFINITIONS if d.layer == "L1"]
        assert live_ids[-1] == "execution_package_write"

    def test_placeholder_layers_cover_l3_through_l7(self) -> None:
        """L2 (Feature Engineering, stage 14) moved into LIVE_STAGE_IDS once
        this task wired it into the CLI's automatic sequence -- only Layers
        3-7 remain reserved, not-yet-implemented placeholders."""
        placeholder_layers = {
            d.layer for d in STAGE_DEFINITIONS if d.stage_id in PLACEHOLDER_STAGE_IDS
        }
        assert placeholder_layers == {"L3", "L4", "L5", "L6", "L7"}

    def test_feature_engineering_is_live_not_placeholder(self) -> None:
        assert "feature_engineering" in LIVE_STAGE_IDS
        assert "feature_engineering" not in PLACEHOLDER_STAGE_IDS

    def test_unknown_stage_id_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown stage_id"):
            stage_definition("not_a_real_stage")


@pytest.mark.unit
class TestAtomicWrite:
    def test_writes_valid_json(self, tmp_path: Path) -> None:
        target = tmp_path / "state.json"
        atomic_write_json(target, {"a": 1})
        assert json.loads(target.read_text()) == {"a": 1}

    def test_no_temp_file_left_behind_on_success(self, tmp_path: Path) -> None:
        target = tmp_path / "state.json"
        atomic_write_json(target, {"a": 1})
        leftovers = [p for p in tmp_path.iterdir() if p.name != "state.json"]
        assert leftovers == []

    def test_overwrite_replaces_content_atomically(self, tmp_path: Path) -> None:
        target = tmp_path / "state.json"
        atomic_write_json(target, {"a": 1})
        atomic_write_json(target, {"a": 2})
        assert json.loads(target.read_text()) == {"a": 2}

    def test_interrupted_write_leaves_prior_file_untouched(self, tmp_path: Path) -> None:
        """Simulates a crash mid-write (the rename never happens): the
        original content must survive unmodified, and no temp file lingers
        readable as the target."""
        target = tmp_path / "state.json"
        atomic_write_json(target, {"a": 1})

        with patch("os.replace", side_effect=OSError("simulated crash before rename")):
            with pytest.raises(OSError, match="simulated crash"):
                atomic_write_json(target, {"a": 2})

        assert json.loads(target.read_text()) == {"a": 1}  # untouched
        leftovers = [p for p in tmp_path.iterdir() if p.name != "state.json"]
        assert leftovers == []  # temp file cleaned up

    def test_read_json_if_valid_missing_file(self, tmp_path: Path) -> None:
        assert read_json_if_valid(tmp_path / "missing.json") is None

    def test_read_json_if_valid_corrupt_file(self, tmp_path: Path) -> None:
        target = tmp_path / "corrupt.json"
        target.write_text("{not valid json")
        assert read_json_if_valid(target) is None

    def test_read_json_if_valid_non_object_json(self, tmp_path: Path) -> None:
        target = tmp_path / "array.json"
        target.write_text("[1, 2, 3]")
        assert read_json_if_valid(target) is None

    def test_read_json_if_valid_well_formed(self, tmp_path: Path) -> None:
        target = tmp_path / "ok.json"
        target.write_text('{"a": 1}')
        assert read_json_if_valid(target) == {"a": 1}


@pytest.mark.unit
class TestRunLock:
    def test_acquire_creates_lockfile_with_pid(self, tmp_path: Path) -> None:
        lock = RunLock(tmp_path)
        lock.acquire()
        try:
            assert lock.path.exists()
            assert int(lock.path.read_text()) == os.getpid()
        finally:
            lock.release()

    def test_second_process_refused_while_live(self, tmp_path: Path) -> None:
        lock = RunLock(tmp_path)
        lock.acquire()
        try:
            other = RunLock(tmp_path)
            with pytest.raises(RunLockError, match="locked by another live process"):
                other.acquire()
        finally:
            lock.release()

    def test_release_allows_reacquisition(self, tmp_path: Path) -> None:
        lock = RunLock(tmp_path)
        lock.acquire()
        lock.release()
        assert not lock.path.exists()
        other = RunLock(tmp_path)
        other.acquire()
        other.release()

    def test_release_is_a_noop_if_never_acquired(self, tmp_path: Path) -> None:
        lock = RunLock(tmp_path)
        lock.release()  # must not raise

    def test_stale_lock_dead_pid_is_broken_and_reacquired(self, tmp_path: Path) -> None:
        stale = tmp_path / "run.lock"
        stale.write_text("999999999")  # a pid essentially guaranteed not to exist
        lock = RunLock(tmp_path)
        lock.acquire()
        try:
            assert int(lock.path.read_text()) == os.getpid()
        finally:
            lock.release()

    def test_unparseable_lock_content_is_treated_as_stale(self, tmp_path: Path) -> None:
        garbage = tmp_path / "run.lock"
        garbage.write_text("not-a-pid")
        lock = RunLock(tmp_path)
        lock.acquire()
        lock.release()

    def test_context_manager_acquires_and_releases(self, tmp_path: Path) -> None:
        lock = RunLock(tmp_path)
        with lock:
            assert lock.path.exists()
        assert not lock.path.exists()

    def test_context_manager_releases_on_exception(self, tmp_path: Path) -> None:
        lock = RunLock(tmp_path)
        with pytest.raises(ValueError):
            with lock:
                raise ValueError("boom")
        assert not lock.path.exists()

    def test_permission_error_on_kill_treated_as_live_not_stale(self, tmp_path: Path) -> None:
        """A PID that exists but is owned by another user: os.kill raises
        PermissionError. This must be treated as LIVE (cannot prove absence),
        not stale."""
        holder = tmp_path / "run.lock"
        holder.write_text("1")  # pid 1 (init/launchd) — always exists, unowned by us
        lock = RunLock(tmp_path)
        with patch("os.kill", side_effect=PermissionError):
            with pytest.raises(RunLockError, match="locked by another live process"):
                lock.acquire()


@pytest.mark.unit
class TestGenerateRunId:
    def test_starts_with_run_prefix(self) -> None:
        assert generate_run_id().startswith("run-")

    def test_unique_across_calls(self) -> None:
        ids = {generate_run_id() for _ in range(20)}
        assert len(ids) == 20

    def test_filesystem_safe_no_colons(self) -> None:
        run_id = generate_run_id()
        assert ":" not in run_id


@pytest.mark.unit
class TestRunStateManagerCreateAndLoad:
    def test_create_writes_all_stages_pending(self, tmp_path: Path) -> None:
        mgr = RunStateManager.create(
            tmp_path, run_id="run-1", execution_name="demo", contract_version="1.0.0"
        )
        assert all(s.status == StageStatus.PENDING for s in mgr.state.stages)
        assert len(mgr.state.stages) == 20

    def test_create_persists_to_disk(self, tmp_path: Path) -> None:
        RunStateManager.create(
            tmp_path, run_id="run-1", execution_name=None, contract_version="1.0.0"
        )
        assert (tmp_path / "run_state.json").exists()
        on_disk = json.loads((tmp_path / "run_state.json").read_text())
        assert on_disk["runId"] == "run-1"

    def test_try_load_missing_returns_none(self, tmp_path: Path) -> None:
        assert RunStateManager.try_load(tmp_path, current_contract_version="1.0.0") is None

    def test_try_load_corrupt_raises(self, tmp_path: Path) -> None:
        (tmp_path / "run_state.json").write_text("{not valid")
        with pytest.raises(RunStateCorruptError):
            RunStateManager.try_load(tmp_path, current_contract_version="1.0.0")

    def test_try_load_valid_roundtrips(self, tmp_path: Path) -> None:
        created = RunStateManager.create(
            tmp_path, run_id="run-1", execution_name="demo", contract_version="1.0.0"
        )
        created.start_stage("engineering_context_orch")
        created.succeed_stage("engineering_context_orch")

        loaded = RunStateManager.try_load(tmp_path, current_contract_version="1.0.0")
        assert loaded is not None
        assert loaded.state.run_id == "run-1"
        assert loaded.state.execution_name == "demo"
        first = loaded.state.stages[0]
        assert first.status == StageStatus.SUCCEEDED

    def test_contract_version_mismatch_globally_invalidates(self, tmp_path: Path) -> None:
        created = RunStateManager.create(
            tmp_path, run_id="run-1", execution_name="demo", contract_version="1.0.0"
        )
        created.start_stage("engineering_context_orch")
        created.succeed_stage("engineering_context_orch")
        created.start_stage("requirement_analysis")
        created.succeed_stage("requirement_analysis")

        loaded = RunStateManager.try_load(tmp_path, current_contract_version="2.0.0")
        assert loaded is not None
        assert loaded.state.contract_version == "2.0.0"
        assert all(s.status == StageStatus.PENDING for s in loaded.state.stages)

    def test_contract_version_mismatch_preserves_run_identity(self, tmp_path: Path) -> None:
        created = RunStateManager.create(
            tmp_path, run_id="run-1", execution_name="demo", contract_version="1.0.0"
        )
        loaded = RunStateManager.try_load(tmp_path, current_contract_version="2.0.0")
        assert loaded is not None
        assert loaded.state.run_id == "run-1"
        assert loaded.state.execution_name == "demo"
        assert loaded.state.created_at == created.state.created_at

    def test_contract_version_mismatch_invalidation_is_persisted(self, tmp_path: Path) -> None:
        RunStateManager.create(
            tmp_path, run_id="run-1", execution_name=None, contract_version="1.0.0"
        )
        RunStateManager.try_load(tmp_path, current_contract_version="2.0.0")
        on_disk = json.loads((tmp_path / "run_state.json").read_text())
        assert on_disk["contractVersion"] == "2.0.0"
        assert all(s["status"] == "pending" for s in on_disk["stages"])

    def test_contract_version_match_does_not_invalidate(self, tmp_path: Path) -> None:
        created = RunStateManager.create(
            tmp_path, run_id="run-1", execution_name=None, contract_version="1.0.0"
        )
        created.start_stage("engineering_context_orch")
        created.succeed_stage("engineering_context_orch")

        loaded = RunStateManager.try_load(tmp_path, current_contract_version="1.0.0")
        assert loaded is not None
        assert loaded.state.stages[0].status == StageStatus.SUCCEEDED


@pytest.mark.unit
class TestStageTransitions:
    def test_start_marks_running(self, tmp_path: Path) -> None:
        mgr = RunStateManager.create(
            tmp_path, run_id="run-1", execution_name=None, contract_version="1.0.0"
        )
        mgr.start_stage("engineering_context_orch")
        stage = mgr.state.stages[0]
        assert stage.status == StageStatus.RUNNING
        assert stage.started_at is not None
        assert stage.ended_at is None

    def test_succeed_marks_succeeded_with_outputs(self, tmp_path: Path) -> None:
        mgr = RunStateManager.create(
            tmp_path, run_id="run-1", execution_name=None, contract_version="1.0.0"
        )
        out = tmp_path / "out.json"
        out.write_text("{}")
        mgr.start_stage("engineering_context_orch")
        mgr.succeed_stage("engineering_context_orch", output_artifacts=[out])
        stage = mgr.state.stages[0]
        assert stage.status == StageStatus.SUCCEEDED
        assert stage.ended_at is not None
        assert stage.output_artifacts == (str(out),)

    def test_fail_records_error(self, tmp_path: Path) -> None:
        mgr = RunStateManager.create(
            tmp_path, run_id="run-1", execution_name=None, contract_version="1.0.0"
        )
        mgr.start_stage("engineering_context_orch")
        mgr.fail_stage("engineering_context_orch", error=ValueError("boom"))
        stage = mgr.state.stages[0]
        assert stage.status == StageStatus.FAILED
        assert stage.error is not None
        assert stage.error.error_type == "ValueError"
        assert stage.error.message == "boom"

    def test_skip_marks_skipped(self, tmp_path: Path) -> None:
        mgr = RunStateManager.create(
            tmp_path, run_id="run-1", execution_name=None, contract_version="1.0.0"
        )
        mgr.skip_stage("engineering_context_orch")
        assert mgr.state.stages[0].status == StageStatus.SKIPPED

    def test_every_mutation_is_persisted(self, tmp_path: Path) -> None:
        mgr = RunStateManager.create(
            tmp_path, run_id="run-1", execution_name=None, contract_version="1.0.0"
        )
        mgr.start_stage("engineering_context_orch")
        on_disk = json.loads((tmp_path / "run_state.json").read_text())
        assert on_disk["stages"][0]["status"] == "running"


@pytest.mark.unit
class TestSkipPredicate:
    def test_never_skip_a_stage_that_has_not_succeeded(self, tmp_path: Path) -> None:
        mgr = RunStateManager.create(
            tmp_path, run_id="run-1", execution_name=None, contract_version="1.0.0"
        )
        assert not mgr.should_skip("engineering_context_orch")

    def test_skip_when_both_invariants_hold(self, tmp_path: Path) -> None:
        mgr = RunStateManager.create(
            tmp_path, run_id="run-1", execution_name=None, contract_version="1.0.0"
        )
        inp = tmp_path / "in.txt"
        inp.write_text("data")
        out = tmp_path / "out.json"
        mgr.start_stage("engineering_context_orch", input_artifacts=[inp])
        out.write_text("{}")
        mgr.succeed_stage("engineering_context_orch", output_artifacts=[out])

        assert mgr.should_skip(
            "engineering_context_orch", input_artifacts=[inp], output_artifacts=[out]
        )

    def test_no_skip_when_input_hash_changed_even_though_succeeded(self, tmp_path: Path) -> None:
        """Invariant (a) alone failing must block skip, regardless of (b)."""
        mgr = RunStateManager.create(
            tmp_path, run_id="run-1", execution_name=None, contract_version="1.0.0"
        )
        inp = tmp_path / "in.txt"
        inp.write_text("data")
        out = tmp_path / "out.json"
        mgr.start_stage("engineering_context_orch", input_artifacts=[inp])
        out.write_text("{}")
        mgr.succeed_stage("engineering_context_orch", output_artifacts=[out])

        inp.write_text("changed data")  # input drifted since the stage ran
        assert not mgr.should_skip(
            "engineering_context_orch", input_artifacts=[inp], output_artifacts=[out]
        )

    def test_no_skip_when_output_missing_even_though_hash_matches(self, tmp_path: Path) -> None:
        """The core invariant this task exists to enforce: hash-match alone is
        never sufficient. Output physically missing -> must re-run."""
        mgr = RunStateManager.create(
            tmp_path, run_id="run-1", execution_name=None, contract_version="1.0.0"
        )
        inp = tmp_path / "in.txt"
        inp.write_text("data")
        out = tmp_path / "out.json"
        mgr.start_stage("engineering_context_orch", input_artifacts=[inp])
        out.write_text("{}")
        mgr.succeed_stage("engineering_context_orch", output_artifacts=[out])

        out.unlink()  # output vanished after the stage succeeded
        assert not mgr.should_skip(
            "engineering_context_orch", input_artifacts=[inp], output_artifacts=[out]
        )

    def test_no_skip_when_output_is_corrupt_json(self, tmp_path: Path) -> None:
        """Present-but-invalid must be treated exactly like missing."""
        mgr = RunStateManager.create(
            tmp_path, run_id="run-1", execution_name=None, contract_version="1.0.0"
        )
        inp = tmp_path / "in.txt"
        inp.write_text("data")
        out = tmp_path / "out.json"
        mgr.start_stage("engineering_context_orch", input_artifacts=[inp])
        out.write_text("{}")
        mgr.succeed_stage("engineering_context_orch", output_artifacts=[out])

        out.write_text("{not valid json, truncated")  # corrupted after success
        assert not mgr.should_skip(
            "engineering_context_orch", input_artifacts=[inp], output_artifacts=[out]
        )

    def test_non_json_output_only_needs_to_exist(self, tmp_path: Path) -> None:
        mgr = RunStateManager.create(
            tmp_path, run_id="run-1", execution_name=None, contract_version="1.0.0"
        )
        out = tmp_path / "out.txt"
        mgr.start_stage("engineering_context_orch")
        out.write_text("plain text, not json")
        mgr.succeed_stage("engineering_context_orch", output_artifacts=[out])

        assert mgr.should_skip("engineering_context_orch", output_artifacts=[out])

    def test_no_declared_inputs_hashes_to_none_and_still_requires_output(
        self, tmp_path: Path
    ) -> None:
        mgr = RunStateManager.create(
            tmp_path, run_id="run-1", execution_name=None, contract_version="1.0.0"
        )
        out = tmp_path / "out.json"
        mgr.start_stage("engineering_context_orch")  # no inputs declared
        assert not mgr.should_skip("engineering_context_orch", output_artifacts=[out])
        out.write_text("{}")
        mgr.succeed_stage("engineering_context_orch", output_artifacts=[out])
        assert mgr.should_skip("engineering_context_orch", output_artifacts=[out])


@pytest.mark.unit
class TestResumePoint:
    def test_all_pending_resumes_from_first_stage(self, tmp_path: Path) -> None:
        mgr = RunStateManager.create(
            tmp_path, run_id="run-1", execution_name=None, contract_version="1.0.0"
        )
        assert mgr.first_non_succeeded_stage_id() == STAGE_DEFINITIONS[0].stage_id

    def test_resumes_from_first_non_succeeded(self, tmp_path: Path) -> None:
        mgr = RunStateManager.create(
            tmp_path, run_id="run-1", execution_name=None, contract_version="1.0.0"
        )
        mgr.start_stage("engineering_context_orch")
        mgr.succeed_stage("engineering_context_orch")
        mgr.start_stage("requirement_analysis")
        mgr.succeed_stage("requirement_analysis")
        mgr.start_stage("requirement_enhancement")
        mgr.fail_stage("requirement_enhancement", error=RuntimeError("x"))

        assert mgr.first_non_succeeded_stage_id() == "requirement_enhancement"

    def test_none_when_every_stage_succeeded(self, tmp_path: Path) -> None:
        mgr = RunStateManager.create(
            tmp_path, run_id="run-1", execution_name=None, contract_version="1.0.0"
        )
        for definition in STAGE_DEFINITIONS:
            mgr.start_stage(definition.stage_id)
            mgr.succeed_stage(definition.stage_id)
        assert mgr.first_non_succeeded_stage_id() is None
