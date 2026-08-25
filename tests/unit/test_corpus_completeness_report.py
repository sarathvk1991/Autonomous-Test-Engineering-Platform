"""Unit tests for :class:`CorpusCompletenessReport` (CAP-091 piece 3 — ADR-0052 D5).

Builds on fixture ``CompletenessAssessment`` values (piece 2's own type) —
never the actual (gitignored, machine-local) ``output/executions/``
directory in committed tests — mirroring
``tests/unit/test_corpus_completeness_engine.py``'s own discipline.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from requirement_intelligence.corpus_completeness.engine import (
    AssessmentStatus,
    CompletenessAssessment,
    CorpusCompletenessEngine,
    HistoricalDistributionSummary,
)
from requirement_intelligence.corpus_completeness.reader import CorpusExecutionReader
from requirement_intelligence.corpus_completeness.report import (
    CorpusCompletenessReport,
    build_corpus_completeness_report,
)


def _distribution(**overrides: object) -> HistoricalDistributionSummary:
    defaults: dict[str, object] = dict(
        sample_size=13,
        minimum=15,
        median=20,
        maximum=30,
        contributing_execution_ids=tuple(f"ex-{i}" for i in range(13)),
    )
    defaults.update(overrides)
    return HistoricalDistributionSummary(**defaults)  # type: ignore[arg-type]


def _assessment(**overrides: object) -> CompletenessAssessment:
    defaults: dict[str, object] = dict(
        execution_id="ex-new",
        requirement_count=20,
        status=AssessmentStatus.ASSESSED,
        distribution=_distribution(),
        flagged=False,
        reason="count 20 is at or above the historical minimum of 15 (n=13, median=20, max=30)",
    )
    defaults.update(overrides)
    return CompletenessAssessment(**defaults)  # type: ignore[arg-type]


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
    counts = [15, 15, 15, 20, 20, 20, 20, 20, 20, 20, 30, 30, 30]
    for index, count in enumerate(counts):
        _write_run(
            root / f"run-{index}",
            execution_id=f"ex-{index}",
            completed=f"2026-08-{index + 1:02d}T00:00:00+00:00",
            count=count,
        )


@pytest.mark.unit
class TestContract:
    def test_build_report_returns_a_corpus_completeness_report(self) -> None:
        report = build_corpus_completeness_report(_assessment())
        assert isinstance(report, CorpusCompletenessReport)


@pytest.mark.unit
class TestSurfacesTheAssessment:
    def test_flagged_run_surfaces_outlier_true_with_the_transparent_rationale(self) -> None:
        assessment = _assessment(
            requirement_count=5,
            flagged=True,
            reason="count 5 is below the historical minimum of 15 (n=13, median=20, max=30)",
        )

        report = build_corpus_completeness_report(assessment)

        assert report.execution_id == "ex-new"
        assert report.requirement_count == 5
        assert report.status == AssessmentStatus.ASSESSED
        assert report.outlier is True
        assert report.rationale == (
            "count 5 is below the historical minimum of 15 (n=13, median=20, max=30)"
        )
        assert report.distribution is not None
        assert report.distribution.minimum == 15
        assert report.distribution.median == 20
        assert report.distribution.maximum == 30

    def test_normal_run_surfaces_outlier_false(self) -> None:
        report = build_corpus_completeness_report(_assessment())

        assert report.outlier is False
        assert report.status == AssessmentStatus.ASSESSED
        assert "at or above the historical minimum" in report.rationale

    def test_count_above_the_maximum_still_surfaces_outlier_false(self) -> None:
        """D1's scope is incompleteness only — the report never widens the
        engine's one-sided signal into general outlier detection."""
        assessment = _assessment(
            requirement_count=100,
            flagged=False,
            reason=(
                "count 100 is at or above the historical minimum of 15 "
                "(n=13, median=20, max=30)"
            ),
        )
        report = build_corpus_completeness_report(assessment)
        assert report.outlier is False


@pytest.mark.unit
class TestInsufficientHistorySurfacedHonestly:
    def test_thin_corpus_assessment_surfaces_as_insufficient_history_not_a_verdict(self) -> None:
        assessment = _assessment(
            status=AssessmentStatus.INSUFFICIENT_HISTORY,
            distribution=_distribution(
                sample_size=1,
                minimum=20,
                median=20,
                maximum=20,
                contributing_execution_ids=("ex-0",),
            ),
            flagged=False,
            reason=(
                "only 1 historical execution(s) available (need at least 3); "
                "cannot assess completeness"
            ),
        )

        report = build_corpus_completeness_report(assessment)

        assert report.status == AssessmentStatus.INSUFFICIENT_HISTORY
        assert report.outlier is False  # never a fabricated flagged verdict
        assert "cannot assess completeness" in report.rationale

    def test_zero_historical_runs_surfaces_with_no_distribution(self) -> None:
        assessment = _assessment(
            status=AssessmentStatus.INSUFFICIENT_HISTORY,
            distribution=None,
            flagged=False,
            reason=(
                "only 0 historical execution(s) available (need at least 3); "
                "cannot assess completeness"
            ),
        )

        report = build_corpus_completeness_report(assessment)

        assert report.distribution is None
        assert report.status == AssessmentStatus.INSUFFICIENT_HISTORY


@pytest.mark.unit
class TestReportOnlyStructurally:
    """Mirrors CP7's own structural report-only proof: no verdict/passed/gate
    field, asserted directly via ``__dataclass_fields__``, not merely
    "the report happens to never fail" behaviorally."""

    def test_the_report_has_no_verdict_or_passed_or_gate_field(self) -> None:
        report = build_corpus_completeness_report(_assessment())

        assert not hasattr(report, "overall_verdict")
        assert not hasattr(report, "passed")
        assert not hasattr(report, "gate")
        assert set(CorpusCompletenessReport.__dataclass_fields__) == {
            "execution_id",
            "requirement_count",
            "status",
            "distribution",
            "outlier",
            "rationale",
        }

    def test_no_gating_shaped_method_exists_on_the_report_type(self) -> None:
        gating_like_names = {
            name
            for name in dir(CorpusCompletenessReport)
            if any(token in name.lower() for token in ("gate", "block", "fail", "raise"))
        }
        assert gating_like_names == set()


@pytest.mark.unit
class TestDeterminism:
    def test_same_assessment_yields_the_same_report(self) -> None:
        assessment = _assessment()
        assert build_corpus_completeness_report(assessment) == build_corpus_completeness_report(
            assessment
        )


@pytest.mark.unit
class TestDisjointBoundary:
    """ADR-0052 D3 / ADR-0023 §D9/§D10: never imports from ``knowledge_graph``."""

    def test_report_module_imports_nothing_from_knowledge_graph(self) -> None:
        import ast
        import inspect

        from requirement_intelligence.corpus_completeness import report as report_module

        source = inspect.getsource(report_module)
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
class TestEndToEndChainOverFixtureCorpus:
    """reader -> engine -> report, wired together, over a fixture corpus
    shaped like the real cluster distribution."""

    def test_full_chain_produces_a_sensible_report(self, tmp_path: Path) -> None:
        _seed_real_shaped_corpus(tmp_path)
        engine = CorpusCompletenessEngine(CorpusExecutionReader(tmp_path))

        assessment = engine.assess(execution_id="ex-current", requirement_count=8)
        report = build_corpus_completeness_report(assessment)

        assert report.outlier is True
        assert report.distribution is not None
        assert report.distribution.sample_size == 13
        assert "below the historical minimum of 15" in report.rationale
