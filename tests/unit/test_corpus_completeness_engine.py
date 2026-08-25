"""Unit tests for :class:`CorpusCompletenessEngine` (CAP-091 piece 2 — ADR-0052 D1/D2).

Every test builds its own tiny, real-shaped ``output/executions/``-style
corpus under ``tmp_path`` and reads it through a real
:class:`CorpusExecutionReader` — never the actual (gitignored, machine-local)
``output/executions/`` directory — mirroring
``tests/unit/test_corpus_execution_reader.py``'s own discipline.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from requirement_intelligence.corpus_completeness.engine import (
    MIN_SAMPLE_SIZE_FOR_ASSESSMENT,
    AssessmentStatus,
    CompletenessAssessment,
    CorpusCompletenessEngine,
)
from requirement_intelligence.corpus_completeness.reader import CorpusExecutionReader


def _write_run(run_dir: Path, *, execution_id: str, completed: str, count: int) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "manifest.json").write_text(
        json.dumps({"executionId": execution_id, "executionCompletedTimestamp": completed}),
        encoding="utf-8",
    )
    (run_dir / "testable_requirement_set.json").write_text(
        json.dumps({"requirements": [{"requirementId": f"REQ-{i}"} for i in range(count)]}),
        encoding="utf-8",
    )


def _seed_real_shaped_corpus(root: Path) -> None:
    """13 runs, clustered 15 (x3) / 20 (x7) / 30 (x3) — mirrors the real corpus."""
    counts = [15, 15, 15, 20, 20, 20, 20, 20, 20, 20, 30, 30, 30]
    for index, count in enumerate(counts):
        _write_run(
            root / f"run-{index}",
            execution_id=f"ex-{index}",
            completed=f"2026-08-{index + 1:02d}T00:00:00+00:00",
            count=count,
        )


def _engine(root: Path) -> CorpusCompletenessEngine:
    return CorpusCompletenessEngine(CorpusExecutionReader(root))


@pytest.mark.unit
class TestContract:
    def test_engine_constructs_with_default_reader(self) -> None:
        CorpusCompletenessEngine()

    def test_assess_returns_a_completeness_assessment(self, tmp_path: Path) -> None:
        _seed_real_shaped_corpus(tmp_path)
        assessment = _engine(tmp_path).assess(execution_id="ex-new", requirement_count=20)
        assert isinstance(assessment, CompletenessAssessment)


@pytest.mark.unit
class TestAssessmentAgainstRealShapedClusters:
    def test_count_matching_a_cluster_is_not_flagged(self, tmp_path: Path) -> None:
        _seed_real_shaped_corpus(tmp_path)
        assessment = _engine(tmp_path).assess(execution_id="ex-new", requirement_count=20)

        assert assessment.status == AssessmentStatus.ASSESSED
        assert assessment.flagged is False
        assert "at or above the historical minimum of 15" in assessment.reason

    def test_count_at_the_historical_minimum_is_not_flagged(self, tmp_path: Path) -> None:
        """The real, three-times-repeated 15-cluster must never itself be
        flagged — the whole reason below-minimum was chosen over z-score."""
        _seed_real_shaped_corpus(tmp_path)
        assessment = _engine(tmp_path).assess(execution_id="ex-new", requirement_count=15)

        assert assessment.flagged is False

    def test_count_below_the_historical_minimum_is_flagged(self, tmp_path: Path) -> None:
        _seed_real_shaped_corpus(tmp_path)
        assessment = _engine(tmp_path).assess(execution_id="ex-new", requirement_count=5)

        assert assessment.status == AssessmentStatus.ASSESSED
        assert assessment.flagged is True
        assert "below the historical minimum of 15" in assessment.reason
        assert "count 5" in assessment.reason

    def test_count_above_the_historical_maximum_is_not_flagged(self, tmp_path: Path) -> None:
        """Scope is incompleteness (low counts) only — a run with MORE
        requirements than ever seen is not this capability's concern (D1)."""
        _seed_real_shaped_corpus(tmp_path)
        assessment = _engine(tmp_path).assess(execution_id="ex-new", requirement_count=100)

        assert assessment.flagged is False

    def test_distribution_summary_matches_the_real_shaped_corpus(self, tmp_path: Path) -> None:
        _seed_real_shaped_corpus(tmp_path)
        assessment = _engine(tmp_path).assess(execution_id="ex-new", requirement_count=20)

        distribution = assessment.distribution
        assert distribution is not None
        assert distribution.sample_size == 13
        assert distribution.minimum == 15
        assert distribution.maximum == 30
        assert distribution.median == 20
        assert len(distribution.contributing_execution_ids) == 13


@pytest.mark.unit
class TestColdStartHonesty:
    """ADR-0052 D1: never fabricate a verdict when history is too thin."""

    def test_zero_historical_runs_is_insufficient_history(self, tmp_path: Path) -> None:
        assessment = _engine(tmp_path).assess(execution_id="ex-new", requirement_count=20)

        assert assessment.status == AssessmentStatus.INSUFFICIENT_HISTORY
        assert assessment.flagged is False
        assert assessment.distribution is None
        assert "0 historical execution" in assessment.reason

    def test_one_historical_run_is_insufficient_history(self, tmp_path: Path) -> None:
        _write_run(
            tmp_path / "run-0", execution_id="ex-0", completed="2026-08-01T00:00:00+00:00", count=20
        )
        assessment = _engine(tmp_path).assess(execution_id="ex-new", requirement_count=5)

        assert assessment.status == AssessmentStatus.INSUFFICIENT_HISTORY
        assert assessment.flagged is False
        # Honest partial data, even though insufficient to assess against.
        assert assessment.distribution is not None
        assert assessment.distribution.sample_size == 1

    def test_two_historical_runs_is_still_insufficient_history(self, tmp_path: Path) -> None:
        for index, count in enumerate((15, 20)):
            _write_run(
                tmp_path / f"run-{index}",
                execution_id=f"ex-{index}",
                completed=f"2026-08-0{index + 1}T00:00:00+00:00",
                count=count,
            )
        assessment = _engine(tmp_path).assess(execution_id="ex-new", requirement_count=5)

        assert assessment.status == AssessmentStatus.INSUFFICIENT_HISTORY
        assert assessment.distribution is not None
        assert assessment.distribution.sample_size == 2

    def test_three_historical_runs_is_sufficient_to_assess(self, tmp_path: Path) -> None:
        for index, count in enumerate((15, 20, 30)):
            _write_run(
                tmp_path / f"run-{index}",
                execution_id=f"ex-{index}",
                completed=f"2026-08-0{index + 1}T00:00:00+00:00",
                count=count,
            )
        assert MIN_SAMPLE_SIZE_FOR_ASSESSMENT == 3
        assessment = _engine(tmp_path).assess(execution_id="ex-new", requirement_count=5)

        assert assessment.status == AssessmentStatus.ASSESSED
        assert assessment.flagged is True


@pytest.mark.unit
class TestGranularity:
    """ADR-0052 D2: per-run-total count vs the distribution — not per-component."""

    def test_assess_takes_a_plain_requirement_count_not_a_requirement_object(
        self, tmp_path: Path
    ) -> None:
        _seed_real_shaped_corpus(tmp_path)
        # The public signature itself proves the granularity: a bare int, no
        # component/functionalTag parameter exists to assess by.
        assessment = _engine(tmp_path).assess(execution_id="ex-new", requirement_count=15)
        assert assessment.requirement_count == 15


@pytest.mark.unit
class TestReportOnlyNeverGates:
    """ADR-0052 D5: an assessment is a signal, never a gate."""

    def test_flagged_assessment_raises_nothing_and_returns_normally(self, tmp_path: Path) -> None:
        _seed_real_shaped_corpus(tmp_path)
        assessment = _engine(tmp_path).assess(execution_id="ex-new", requirement_count=1)
        assert assessment.flagged is True  # no exception, no process exit — just a value

    def test_assessment_type_has_no_gating_method(self) -> None:
        """Structural proof: nothing on the assessment can be used to block —
        no ``raise_if_failed``/``should_fail``/``is_gate`` style method."""
        gating_like_names = {
            name
            for name in dir(CompletenessAssessment)
            if any(token in name.lower() for token in ("gate", "block", "fail", "raise"))
        }
        assert gating_like_names == set()


@pytest.mark.unit
class TestDisjointBoundary:
    """ADR-0052 D3 / ADR-0023 §D9/§D10: never imports from ``knowledge_graph``."""

    def test_engine_module_imports_nothing_from_knowledge_graph(self) -> None:
        import ast
        import inspect

        from requirement_intelligence.corpus_completeness import engine as engine_module

        source = inspect.getsource(engine_module)
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
    def test_assess_is_a_pure_function_of_disk_state_and_input(self, tmp_path: Path) -> None:
        _seed_real_shaped_corpus(tmp_path)
        engine = _engine(tmp_path)

        first = engine.assess(execution_id="ex-new", requirement_count=15)
        second = engine.assess(execution_id="ex-new", requirement_count=15)

        assert first == second
