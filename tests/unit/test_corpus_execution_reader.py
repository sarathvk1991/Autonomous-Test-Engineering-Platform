"""Unit tests for :class:`CorpusExecutionReader` (CAP-091 piece 1 — ADR-0052 D3).

Every test builds its own tiny, real-shaped ``output/executions/``-style
corpus under ``tmp_path`` — never the actual (gitignored, machine-local)
``output/executions/`` directory — mirroring
``tests/unit/test_file_historical_dataset_provider.py``'s own discipline.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from requirement_intelligence.corpus_completeness.reader import (
    CorpusExecutionReader,
    CorpusExecutionRecord,
)


def _write_manifest(run_dir: Path, *, execution_id: str, completed: str) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "manifest.json").write_text(
        json.dumps({"executionId": execution_id, "executionCompletedTimestamp": completed}),
        encoding="utf-8",
    )


def _write_trs(
    run_dir: Path,
    *,
    requirement_ids: tuple[str, ...],
    component: str | None = None,
    functional_tag: str | None = None,
) -> None:
    requirements = []
    for rid in requirement_ids:
        entry: dict[str, object] = {"requirementId": rid}
        if component is not None:
            entry["component"] = component
        if functional_tag is not None:
            entry["functionalTag"] = functional_tag
        requirements.append(entry)
    (run_dir / "testable_requirement_set.json").write_text(
        json.dumps({"requirements": requirements}), encoding="utf-8"
    )


@pytest.mark.unit
class TestContract:
    def test_reader_constructs_with_default_root(self) -> None:
        CorpusExecutionReader()

    def test_read_returns_a_tuple_of_corpus_execution_records(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-a"
        _write_manifest(run_dir, execution_id="ex-1", completed="2026-08-01T00:00:00+00:00")
        _write_trs(run_dir, requirement_ids=("REQ-a",))

        records = CorpusExecutionReader(tmp_path).read()

        assert isinstance(records, tuple)
        assert isinstance(records[0], CorpusExecutionRecord)


@pytest.mark.unit
class TestExtraction:
    def test_extracts_requirement_count(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-a"
        _write_manifest(run_dir, execution_id="ex-1", completed="2026-08-01T00:00:00+00:00")
        _write_trs(run_dir, requirement_ids=("REQ-a", "REQ-b", "REQ-c"))

        records = CorpusExecutionReader(tmp_path).read()

        assert len(records) == 1
        assert records[0].execution_id == "ex-1"
        assert records[0].completed_timestamp == "2026-08-01T00:00:00+00:00"
        assert records[0].requirement_count == 3

    def test_extracts_representative_component_and_functional_tag(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-a"
        _write_manifest(run_dir, execution_id="ex-1", completed="2026-08-01T00:00:00+00:00")
        _write_trs(
            run_dir,
            requirement_ids=("REQ-a", "REQ-b"),
            component="pkg/Foo.java",
            functional_tag="@foo",
        )

        records = CorpusExecutionReader(tmp_path).read()

        assert records[0].component == "pkg/Foo.java"
        assert records[0].functional_tag == "@foo"

    def test_component_and_functional_tag_absent_resolve_to_none(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-a"
        _write_manifest(run_dir, execution_id="ex-1", completed="2026-08-01T00:00:00+00:00")
        _write_trs(run_dir, requirement_ids=("REQ-a",))

        records = CorpusExecutionReader(tmp_path).read()

        assert records[0].component is None
        assert records[0].functional_tag is None

    def test_one_record_per_execution_not_per_requirement(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-a"
        all_ids = tuple(f"REQ-{i}" for i in range(20))
        _write_manifest(run_dir, execution_id="ex-1", completed="2026-08-01T00:00:00+00:00")
        _write_trs(run_dir, requirement_ids=all_ids)

        records = CorpusExecutionReader(tmp_path).read()

        assert len(records) == 1
        assert records[0].requirement_count == 20


@pytest.mark.unit
class TestMultiExecutionEnumeration:
    def test_enumerates_every_qualifying_run_in_chronological_order(self, tmp_path: Path) -> None:
        for name, execution_id, completed, req in (
            ("run-c", "ex-c", "2026-08-03T00:00:00+00:00", "REQ-c"),
            ("run-a", "ex-a", "2026-08-01T00:00:00+00:00", "REQ-a"),
            ("run-b", "ex-b", "2026-08-02T00:00:00+00:00", "REQ-b"),
        ):
            run_dir = tmp_path / name
            _write_manifest(run_dir, execution_id=execution_id, completed=completed)
            _write_trs(run_dir, requirement_ids=(req,))

        records = CorpusExecutionReader(tmp_path).read()

        assert [r.execution_id for r in records] == ["ex-a", "ex-b", "ex-c"]

    def test_real_corpus_shaped_cluster_of_counts(self, tmp_path: Path) -> None:
        """Mirrors the real corpus's own signal (ADR-0052 D1): counts cluster
        at distinct values (15/20/30 in the real data), never a single
        constant."""
        for name, execution_id, completed, count in (
            ("run-a", "ex-a", "2026-08-01T00:00:00+00:00", 15),
            ("run-b", "ex-b", "2026-08-02T00:00:00+00:00", 20),
            ("run-c", "ex-c", "2026-08-03T00:00:00+00:00", 30),
        ):
            run_dir = tmp_path / name
            _write_manifest(run_dir, execution_id=execution_id, completed=completed)
            _write_trs(run_dir, requirement_ids=tuple(f"REQ-{i}" for i in range(count)))

        records = CorpusExecutionReader(tmp_path).read()

        assert [r.requirement_count for r in records] == [15, 20, 30]


@pytest.mark.unit
class TestGracefulToleranceOfMixedDirectories:
    """Mirrors the Historical Dataset arc's own file-based provider (piece
    2/3) tolerance discipline: a run missing a contract is skipped, not
    crashed on."""

    def test_run_missing_manifest_is_skipped(self, tmp_path: Path) -> None:
        good = tmp_path / "run-good"
        _write_manifest(good, execution_id="ex-good", completed="2026-08-01T00:00:00+00:00")
        _write_trs(good, requirement_ids=("REQ-good",))
        (tmp_path / "run-no-manifest").mkdir()

        records = CorpusExecutionReader(tmp_path).read()

        assert [r.execution_id for r in records] == ["ex-good"]

    def test_run_missing_testable_requirement_set_is_skipped(self, tmp_path: Path) -> None:
        no_trs = tmp_path / "run-no-trs"
        _write_manifest(no_trs, execution_id="ex-no-trs", completed="2026-08-01T00:00:00+00:00")
        # No testable_requirement_set.json written — the real "dry run" shape.
        has_trs = tmp_path / "run-has-trs"
        _write_manifest(has_trs, execution_id="ex-has-trs", completed="2026-08-02T00:00:00+00:00")
        _write_trs(has_trs, requirement_ids=("REQ-x",))

        records = CorpusExecutionReader(tmp_path).read()

        assert [r.execution_id for r in records] == ["ex-has-trs"]

    def test_run_with_empty_requirements_list_is_skipped(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-empty-trs"
        _write_manifest(run_dir, execution_id="ex-empty", completed="2026-08-01T00:00:00+00:00")
        _write_trs(run_dir, requirement_ids=())

        records = CorpusExecutionReader(tmp_path).read()

        assert records == ()

    def test_malformed_manifest_json_treated_as_absent_not_a_crash(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-bad-json"
        run_dir.mkdir()
        (run_dir / "manifest.json").write_text("{not valid json", encoding="utf-8")

        records = CorpusExecutionReader(tmp_path).read()

        assert records == ()

    def test_malformed_requirement_set_json_treated_as_absent_not_a_crash(
        self, tmp_path: Path
    ) -> None:
        run_dir = tmp_path / "run-bad-trs"
        _write_manifest(run_dir, execution_id="ex-1", completed="2026-08-01T00:00:00+00:00")
        (run_dir / "testable_requirement_set.json").write_text(
            "{not valid json", encoding="utf-8"
        )

        records = CorpusExecutionReader(tmp_path).read()

        assert records == ()

    def test_manifest_missing_execution_id_is_skipped(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-a"
        run_dir.mkdir()
        (run_dir / "manifest.json").write_text(
            json.dumps({"executionCompletedTimestamp": "2026-08-01T00:00:00+00:00"}),
            encoding="utf-8",
        )
        _write_trs(run_dir, requirement_ids=("REQ-a",))

        records = CorpusExecutionReader(tmp_path).read()

        assert records == ()

    def test_manifest_missing_completed_timestamp_is_skipped(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-a"
        run_dir.mkdir()
        (run_dir / "manifest.json").write_text(
            json.dumps({"executionId": "ex-1"}), encoding="utf-8"
        )
        _write_trs(run_dir, requirement_ids=("REQ-a",))

        records = CorpusExecutionReader(tmp_path).read()

        assert records == ()

    def test_malformed_requirement_entries_are_skipped_not_counted(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-a"
        _write_manifest(run_dir, execution_id="ex-1", completed="2026-08-01T00:00:00+00:00")
        (run_dir / "testable_requirement_set.json").write_text(
            json.dumps(
                {
                    "requirements": [
                        {"requirementId": "REQ-a"},
                        "not-even-a-dict",
                        {"requirementId": "REQ-b"},
                    ]
                }
            ),
            encoding="utf-8",
        )

        records = CorpusExecutionReader(tmp_path).read()

        assert records[0].requirement_count == 2

    def test_mixed_qualifying_and_nonqualifying_dirs_in_the_same_corpus(
        self, tmp_path: Path
    ) -> None:
        good = tmp_path / "run-good"
        _write_manifest(good, execution_id="ex-good", completed="2026-08-01T00:00:00+00:00")
        _write_trs(good, requirement_ids=("REQ-a",))

        (tmp_path / "run-no-manifest").mkdir()

        dry_run = tmp_path / "run-dry"
        _write_manifest(dry_run, execution_id="ex-dry", completed="2026-08-02T00:00:00+00:00")

        empty_trs = tmp_path / "run-empty"
        _write_manifest(empty_trs, execution_id="ex-empty", completed="2026-08-03T00:00:00+00:00")
        _write_trs(empty_trs, requirement_ids=())

        records = CorpusExecutionReader(tmp_path).read()

        assert [r.execution_id for r in records] == ["ex-good"]


@pytest.mark.unit
class TestEmptyOrMissingRoot:
    def test_empty_corpus_root_resolves_to_empty(self, tmp_path: Path) -> None:
        records = CorpusExecutionReader(tmp_path).read()
        assert records == ()

    def test_missing_root_directory_resolves_to_empty(self, tmp_path: Path) -> None:
        missing_root = tmp_path / "does-not-exist"
        records = CorpusExecutionReader(missing_root).read()
        assert records == ()

    def test_non_directory_entries_in_root_are_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "a-stray-file.txt").write_text("not a run dir", encoding="utf-8")
        run_dir = tmp_path / "run-a"
        _write_manifest(run_dir, execution_id="ex-1", completed="2026-08-01T00:00:00+00:00")
        _write_trs(run_dir, requirement_ids=("REQ-a",))

        records = CorpusExecutionReader(tmp_path).read()

        assert [r.execution_id for r in records] == ["ex-1"]


@pytest.mark.unit
class TestDisjointBoundary:
    """ADR-0052 D3 / ADR-0023 §D9/§D10: never imports from ``knowledge_graph``."""

    def test_reader_module_imports_nothing_from_knowledge_graph(self) -> None:
        import ast
        import inspect

        from requirement_intelligence.corpus_completeness import reader as reader_module

        source = inspect.getsource(reader_module)
        tree = ast.parse(source)
        from_imports = [
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        ]
        plain_imports = [
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        ]

        assert not any("knowledge_graph" in module for module in from_imports + plain_imports)


@pytest.mark.unit
class TestDeterminism:
    def test_read_is_a_pure_function_of_disk_state(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-a"
        _write_manifest(run_dir, execution_id="ex-1", completed="2026-08-01T00:00:00+00:00")
        _write_trs(run_dir, requirement_ids=("REQ-a",))
        reader = CorpusExecutionReader(tmp_path)

        assert reader.read() == reader.read()
