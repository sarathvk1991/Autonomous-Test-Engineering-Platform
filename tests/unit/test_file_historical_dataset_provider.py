"""Unit tests for :class:`FileHistoricalDatasetProvider` (Historical Dataset arc,
piece 2 — ADR-0021 §Stage 6).

Every test builds its own tiny, real-shaped ``output/executions/``-style corpus under
``tmp_path`` — never the actual (gitignored, machine-local) ``output/executions/``
directory, mirroring how every other test in this suite avoids depending on real,
uncommitted local run output.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from requirement_intelligence.knowledge_graph.engine.file_historical_dataset_provider import (
    FileHistoricalDatasetProvider,
)
from requirement_intelligence.knowledge_graph.engine.historical_dataset import (
    HistoricalDataset,
    HistoricalDatasetProvider,
)
from requirement_intelligence.knowledge_graph.models.historical_dataset_reference import (
    HistoricalDatasetReference,
)


def _reference(**overrides: object) -> HistoricalDatasetReference:
    defaults: dict[str, object] = dict(
        dataset_id="ds-real",
        dataset_version="1.0.0",
        first_execution_id="ex-1",
        last_execution_id="ex-1",
        execution_count=1,
        history_window=25,
        generated_at=datetime(2026, 8, 24, tzinfo=UTC),
    )
    defaults.update(overrides)
    return HistoricalDatasetReference(**defaults)


def _write_manifest(run_dir: Path, *, execution_id: str, completed: str) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "manifest.json").write_text(
        json.dumps({"executionId": execution_id, "executionCompletedTimestamp": completed}),
        encoding="utf-8",
    )


def _write_trs(run_dir: Path, *, requirement_ids: tuple[str, ...]) -> None:
    (run_dir / "testable_requirement_set.json").write_text(
        json.dumps({"requirements": [{"requirementId": rid} for rid in requirement_ids]}),
        encoding="utf-8",
    )


def _write_recommendations(run_dir: Path, *, recommendation_ids: tuple[str, ...]) -> None:
    (run_dir / "recommendation_result.json").write_text(
        json.dumps({"recommendations": [{"recommendationId": rid} for rid in recommendation_ids]}),
        encoding="utf-8",
    )


def _real_shaped_cp1_result_json(*, finding_ids: tuple[str, ...]) -> str:
    """A ``cp1_result.json`` payload shaped exactly like ``CP1Result.model_dump(mode=
    "json", by_alias=True)`` (piece 1) — the real camelCase field names
    (``findingId`` etc.) this provider's dict-level reader must key against. The
    ``cp1Input``/``frameworkMetadata`` subtrees are omitted: this provider never
    touches them (it reads only ``findings[].findingId``, at the dict level), and
    constructing a full real ``CP1Input`` tree here would duplicate
    ``test_run_requirement_analysis.py``'s own heavy helper for no additional
    proof — the real end-to-end write path (a genuine ``CP1Result`` through the
    real ``ExecutionWriter``) is exercised separately, not duplicated per test.
    """
    return json.dumps(
        {
            "cp1Id": "CP1-1",
            "overallVerdict": "pass",
            "findings": [{"findingId": fid, "criterionId": "CP1-0001"} for fid in finding_ids],
        }
    )


@pytest.mark.unit
class TestContract:
    def test_provider_is_a_historical_dataset_provider(self, tmp_path: Path) -> None:
        assert isinstance(FileHistoricalDatasetProvider(tmp_path), HistoricalDatasetProvider)

    def test_resolved_dataset_is_a_plain_historical_dataset(self, tmp_path: Path) -> None:
        dataset = FileHistoricalDatasetProvider(tmp_path).resolve(_reference())
        assert isinstance(dataset, HistoricalDataset)

    def test_dataset_id_matches_reference(self, tmp_path: Path) -> None:
        dataset = FileHistoricalDatasetProvider(tmp_path).resolve(_reference(dataset_id="ds-x"))
        assert dataset.dataset_id == "ds-x"


@pytest.mark.unit
class TestSingleExecutionResolution:
    """The only window shape the live CLI mints today: first == last, count == 1."""

    def test_resolves_real_execution_id_and_requirement_id(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-a"
        _write_manifest(run_dir, execution_id="ex-1", completed="2026-08-01T00:00:00+00:00")
        _write_trs(run_dir, requirement_ids=("REQ-a", "REQ-b", "REQ-c"))

        dataset = FileHistoricalDatasetProvider(tmp_path).resolve(
            _reference(first_execution_id="ex-1", last_execution_id="ex-1")
        )

        assert len(dataset.executions) == 1
        record = dataset.executions[0]
        assert record.execution_id == "ex-1"
        assert record.requirement_id == "REQ-a"  # representative — the first of the full set
        assert record.requirement_ids == ("REQ-a", "REQ-b", "REQ-c")  # piece 3: the full set
        assert record.ordinal == 0
        assert record.depends_on_previous is False

    def test_unfound_execution_resolves_to_empty_not_fabricated(self, tmp_path: Path) -> None:
        """The current, in-flight execution: minted before ExecutionWriter has run.

        This is the real, live shape today — the reference always names the run's
        own not-yet-persisted execution_id. No crash, no synthesized stand-in.
        """
        dataset = FileHistoricalDatasetProvider(tmp_path).resolve(
            _reference(first_execution_id="ex-not-on-disk", last_execution_id="ex-not-on-disk")
        )
        assert dataset.executions == ()

    def test_empty_corpus_root_resolves_to_empty(self, tmp_path: Path) -> None:
        missing_root = tmp_path / "does-not-exist"
        dataset = FileHistoricalDatasetProvider(missing_root).resolve(_reference())
        assert dataset.executions == ()


@pytest.mark.unit
class TestMultiExecutionWindow:
    def test_resolves_chronological_window_with_correct_ordinals(self, tmp_path: Path) -> None:
        for name, execution_id, completed, req in (
            ("run-a", "ex-a", "2026-08-01T00:00:00+00:00", "REQ-a"),
            ("run-b", "ex-b", "2026-08-02T00:00:00+00:00", "REQ-b"),
            ("run-c", "ex-c", "2026-08-03T00:00:00+00:00", "REQ-c"),
        ):
            run_dir = tmp_path / name
            _write_manifest(run_dir, execution_id=execution_id, completed=completed)
            _write_trs(run_dir, requirement_ids=(req,))

        dataset = FileHistoricalDatasetProvider(tmp_path).resolve(
            _reference(first_execution_id="ex-a", last_execution_id="ex-c", execution_count=3)
        )

        assert [r.execution_id for r in dataset.executions] == ["ex-a", "ex-b", "ex-c"]
        assert [r.ordinal for r in dataset.executions] == [0, 1, 2]
        assert [r.depends_on_previous for r in dataset.executions] == [False, True, True]

    def test_reversed_first_last_resolves_to_empty(self, tmp_path: Path) -> None:
        for name, execution_id, completed in (
            ("run-a", "ex-a", "2026-08-01T00:00:00+00:00"),
            ("run-b", "ex-b", "2026-08-02T00:00:00+00:00"),
        ):
            run_dir = tmp_path / name
            _write_manifest(run_dir, execution_id=execution_id, completed=completed)
            _write_trs(run_dir, requirement_ids=("REQ-x",))

        dataset = FileHistoricalDatasetProvider(tmp_path).resolve(
            _reference(first_execution_id="ex-b", last_execution_id="ex-a", execution_count=2)
        )
        assert dataset.executions == ()

    def test_caps_at_execution_count(self, tmp_path: Path) -> None:
        for name, execution_id, completed in (
            ("run-a", "ex-a", "2026-08-01T00:00:00+00:00"),
            ("run-b", "ex-b", "2026-08-02T00:00:00+00:00"),
            ("run-c", "ex-c", "2026-08-03T00:00:00+00:00"),
        ):
            run_dir = tmp_path / name
            _write_manifest(run_dir, execution_id=execution_id, completed=completed)
            _write_trs(run_dir, requirement_ids=("REQ-x",))

        dataset = FileHistoricalDatasetProvider(tmp_path).resolve(
            _reference(first_execution_id="ex-a", last_execution_id="ex-c", execution_count=2)
        )
        assert len(dataset.executions) == 2


@pytest.mark.unit
class TestGracefulToleranceOfMixedDirectories:
    """Finding 2, carried forward: a run missing a contract is served, not crashed on."""

    def test_run_missing_manifest_is_skipped(self, tmp_path: Path) -> None:
        good = tmp_path / "run-good"
        _write_manifest(good, execution_id="ex-good", completed="2026-08-01T00:00:00+00:00")
        _write_trs(good, requirement_ids=("REQ-good",))
        (tmp_path / "run-no-manifest").mkdir()

        dataset = FileHistoricalDatasetProvider(tmp_path).resolve(
            _reference(first_execution_id="ex-good", last_execution_id="ex-good")
        )
        assert len(dataset.executions) == 1
        assert dataset.executions[0].execution_id == "ex-good"

    def test_run_missing_testable_requirement_set_is_excluded_from_window(
        self, tmp_path: Path
    ) -> None:
        """A run with no requirement data (required field, no honest placeholder)
        is excluded from a multi-execution window, never padded with a fake id."""
        no_trs = tmp_path / "run-no-trs"
        _write_manifest(no_trs, execution_id="ex-no-trs", completed="2026-08-01T00:00:00+00:00")
        # No testable_requirement_set.json written — the real "7-of-8" older-run shape.
        has_trs = tmp_path / "run-has-trs"
        _write_manifest(has_trs, execution_id="ex-has-trs", completed="2026-08-02T00:00:00+00:00")
        _write_trs(has_trs, requirement_ids=("REQ-x",))

        dataset = FileHistoricalDatasetProvider(tmp_path).resolve(
            _reference(
                first_execution_id="ex-no-trs", last_execution_id="ex-has-trs", execution_count=2
            )
        )
        assert [r.execution_id for r in dataset.executions] == ["ex-has-trs"]

    def test_run_with_empty_requirements_list_is_excluded(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-empty-trs"
        _write_manifest(run_dir, execution_id="ex-empty", completed="2026-08-01T00:00:00+00:00")
        _write_trs(run_dir, requirement_ids=())

        dataset = FileHistoricalDatasetProvider(tmp_path).resolve(
            _reference(first_execution_id="ex-empty", last_execution_id="ex-empty")
        )
        assert dataset.executions == ()

    def test_malformed_json_treated_as_absent_not_a_crash(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-bad-json"
        run_dir.mkdir()
        (run_dir / "manifest.json").write_text("{not valid json", encoding="utf-8")

        dataset = FileHistoricalDatasetProvider(tmp_path).resolve(
            _reference(first_execution_id="ex-anything", last_execution_id="ex-anything")
        )
        assert dataset.executions == ()

    def test_run_missing_cp1_json_yields_none_finding_id(self, tmp_path: Path) -> None:
        """Piece 1 is going-forward-only — every existing real run lacks
        cp1_result.json. That must resolve to ``finding_id=None``, not a crash."""
        run_dir = tmp_path / "run-pre-piece1"
        _write_manifest(run_dir, execution_id="ex-1", completed="2026-08-01T00:00:00+00:00")
        _write_trs(run_dir, requirement_ids=("REQ-a",))
        # No cp1_result.json written — the real shape of all pre-piece-1 runs.

        dataset = FileHistoricalDatasetProvider(tmp_path).resolve(
            _reference(first_execution_id="ex-1", last_execution_id="ex-1")
        )
        assert dataset.executions[0].finding_id is None

    def test_mixed_7_of_8_and_8_of_8_runs_in_one_window(self, tmp_path: Path) -> None:
        """A pre-piece-1 (7-of-8) run and a post-piece-1 (8-of-8, has cp1_result.json)
        run resolved in the SAME window: both included, only the latter carries a
        finding_id."""
        old = tmp_path / "run-old"
        _write_manifest(old, execution_id="ex-old", completed="2026-08-01T00:00:00+00:00")
        _write_trs(old, requirement_ids=("REQ-old",))

        new = tmp_path / "run-new"
        _write_manifest(new, execution_id="ex-new", completed="2026-08-02T00:00:00+00:00")
        _write_trs(new, requirement_ids=("REQ-new",))
        (new / "cp1_result.json").write_text(
            _real_shaped_cp1_result_json(finding_ids=("CP1-FIND-1",)), encoding="utf-8"
        )

        dataset = FileHistoricalDatasetProvider(tmp_path).resolve(
            _reference(first_execution_id="ex-old", last_execution_id="ex-new", execution_count=2)
        )

        by_id = {r.execution_id: r for r in dataset.executions}
        assert by_id["ex-old"].finding_id is None
        assert by_id["ex-new"].finding_id == "CP1-FIND-1"


@pytest.mark.unit
class TestRealCp1JsonReadAtDictLevel:
    """Finding 1, proven directly: reading CP1Result's own real JSON shape (the
    deeply-nested contract) works at the dict level, never via model_validate."""

    def test_reads_real_cp1_result_json_finding_id(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-a"
        _write_manifest(run_dir, execution_id="ex-1", completed="2026-08-01T00:00:00+00:00")
        _write_trs(run_dir, requirement_ids=("REQ-a",))
        (run_dir / "cp1_result.json").write_text(
            _real_shaped_cp1_result_json(finding_ids=("CP1-FIND-1", "CP1-FIND-2")), encoding="utf-8"
        )

        dataset = FileHistoricalDatasetProvider(tmp_path).resolve(
            _reference(first_execution_id="ex-1", last_execution_id="ex-1")
        )
        # First finding is the representative — same "first-of-many" discipline as
        # requirement_id/recommendation_id.
        assert dataset.executions[0].finding_id == "CP1-FIND-1"

    def test_reads_real_recommendation_result_json(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-a"
        _write_manifest(run_dir, execution_id="ex-1", completed="2026-08-01T00:00:00+00:00")
        _write_trs(run_dir, requirement_ids=("REQ-a",))
        _write_recommendations(run_dir, recommendation_ids=("rc-1", "rc-2"))

        dataset = FileHistoricalDatasetProvider(tmp_path).resolve(
            _reference(first_execution_id="ex-1", last_execution_id="ex-1")
        )
        assert dataset.executions[0].recommendation_id == "rc-1"


@pytest.mark.unit
class TestScalarShapeHonesty:
    """capability_id/document_id are always None — no real per-execution equivalent
    exists; requirement_id stays the representative-first id, unchanged."""

    def test_capability_id_and_document_id_are_always_none(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-a"
        _write_manifest(run_dir, execution_id="ex-1", completed="2026-08-01T00:00:00+00:00")
        _write_trs(run_dir, requirement_ids=("REQ-a",))

        dataset = FileHistoricalDatasetProvider(tmp_path).resolve(
            _reference(first_execution_id="ex-1", last_execution_id="ex-1")
        )
        assert dataset.executions[0].capability_id is None
        assert dataset.executions[0].document_id is None

    def test_one_record_per_execution_not_per_requirement(self, tmp_path: Path) -> None:
        """Execution-granularity is unchanged: a real execution's 20 requirements
        still yield exactly ONE record — but (piece 3) the record itself is no
        longer requirement-blind: requirement_ids now carries all 20, in file
        order, while requirement_id stays the representative-first id."""
        run_dir = tmp_path / "run-a"
        all_ids = tuple(f"REQ-{i}" for i in range(20))
        _write_manifest(run_dir, execution_id="ex-1", completed="2026-08-01T00:00:00+00:00")
        _write_trs(run_dir, requirement_ids=all_ids)

        dataset = FileHistoricalDatasetProvider(tmp_path).resolve(
            _reference(first_execution_id="ex-1", last_execution_id="ex-1")
        )
        assert len(dataset.executions) == 1
        record = dataset.executions[0]
        assert record.requirement_id == "REQ-0"
        assert record.requirement_ids == all_ids


@pytest.mark.unit
class TestRequirementIdsFullSet:
    """Piece 3: the record's additive ``requirement_ids`` field."""

    def test_requirement_ids_carries_the_full_set_in_file_order(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-a"
        _write_manifest(run_dir, execution_id="ex-1", completed="2026-08-01T00:00:00+00:00")
        _write_trs(run_dir, requirement_ids=("REQ-a", "REQ-b", "REQ-c"))

        dataset = FileHistoricalDatasetProvider(tmp_path).resolve(
            _reference(first_execution_id="ex-1", last_execution_id="ex-1")
        )
        assert dataset.executions[0].requirement_ids == ("REQ-a", "REQ-b", "REQ-c")

    def test_requirement_ids_first_element_matches_the_representative(
        self, tmp_path: Path
    ) -> None:
        run_dir = tmp_path / "run-a"
        _write_manifest(run_dir, execution_id="ex-1", completed="2026-08-01T00:00:00+00:00")
        _write_trs(run_dir, requirement_ids=("REQ-a", "REQ-b"))

        dataset = FileHistoricalDatasetProvider(tmp_path).resolve(
            _reference(first_execution_id="ex-1", last_execution_id="ex-1")
        )
        record = dataset.executions[0]
        assert record.requirement_ids[0] == record.requirement_id

    def test_entries_missing_requirement_id_are_skipped_not_fabricated(
        self, tmp_path: Path
    ) -> None:
        """Dict-level tolerance (piece 1/2's finding, carried forward): a
        malformed requirement entry is silently skipped, never guessed."""
        run_dir = tmp_path / "run-a"
        _write_manifest(run_dir, execution_id="ex-1", completed="2026-08-01T00:00:00+00:00")
        (run_dir / "testable_requirement_set.json").write_text(
            json.dumps(
                {
                    "requirements": [
                        {"requirementId": "REQ-a"},
                        {"title": "no requirementId key at all"},
                        {"requirementId": None},
                        {"requirementId": ""},
                        "not-even-a-dict",
                        {"requirementId": "REQ-b"},
                    ]
                }
            ),
            encoding="utf-8",
        )

        dataset = FileHistoricalDatasetProvider(tmp_path).resolve(
            _reference(first_execution_id="ex-1", last_execution_id="ex-1")
        )
        assert dataset.executions[0].requirement_ids == ("REQ-a", "REQ-b")

    def test_mixed_directory_missing_cp1_result_still_populates_requirement_ids(
        self, tmp_path: Path
    ) -> None:
        """A real, pre-piece-1 run (no cp1_result.json) still yields its full
        requirement set — requirement_ids reads only testable_requirement_set.json,
        independent of cp1_result.json's presence."""
        run_dir = tmp_path / "run-a"
        _write_manifest(run_dir, execution_id="ex-1", completed="2026-08-01T00:00:00+00:00")
        _write_trs(run_dir, requirement_ids=("REQ-a", "REQ-b", "REQ-c"))
        # No cp1_result.json written — mirrors the real corpus's pre-piece-1 runs.

        dataset = FileHistoricalDatasetProvider(tmp_path).resolve(
            _reference(first_execution_id="ex-1", last_execution_id="ex-1")
        )
        record = dataset.executions[0]
        assert record.requirement_ids == ("REQ-a", "REQ-b", "REQ-c")
        assert record.finding_id is None


@pytest.mark.unit
class TestDeterminism:
    def test_resolve_is_a_pure_function_of_disk_state(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-a"
        _write_manifest(run_dir, execution_id="ex-1", completed="2026-08-01T00:00:00+00:00")
        _write_trs(run_dir, requirement_ids=("REQ-a",))
        provider = FileHistoricalDatasetProvider(tmp_path)
        reference = _reference(first_execution_id="ex-1", last_execution_id="ex-1")

        assert provider.resolve(reference) == provider.resolve(reference)
