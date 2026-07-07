"""Unit tests for CP1ReportBuilder — ``cp1_report.md`` rendering (CAP-068).

The builder is **pure presentation**: it reads a ``CP1Result`` and formats Markdown.
It never evaluates criteria, aggregates findings, derives a verdict, scores, or
applies any engineering-readiness logic. These tests construct **real** canonical
models (``CP1Result`` / ``CP1Finding`` / ``CP1FrameworkMetadata`` / ``CP1Input``)
directly — no engine, no pipeline — so findings and ordering are fully controlled
(the one real governed criterion, ``CP1-0001``, emits at most one finding).

Covers: zero findings message, PASS/FAIL rendering, finding + recommendation
rendering, multiple findings with preserved ordering, all required sections,
determinism, and thread safety.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pytest

from requirement_intelligence.analysis.analysis_models import AnalysisResult
from requirement_intelligence.cp1.models import (
    CP1Finding,
    CP1FrameworkMetadata,
    CP1Input,
    CP1Result,
)
from requirement_intelligence.execution.cp1_report_builder import CP1ReportBuilder
from requirement_intelligence.llm.llm_models import LLMResponse
from requirement_intelligence.normalization.framework.normalization_pipeline import (
    NormalizationPipeline,
)
from requirement_intelligence.normalization.framework.normalization_registry import (
    NormalizationRegistry,
)
from requirement_intelligence.normalization.models.normalization_configuration import (
    NormalizationConfiguration,
)
from requirement_intelligence.normalization.response import ResponseNormalizer
from requirement_intelligence.validation.models import (
    DEFAULT_VALIDATION_CONTRACT_VERSION,
    FRAMEWORK_VERSION,
    PIPELINE_VERSION,
    REGISTRY_VERSION,
    ValidationConfiguration,
    ValidationFrameworkMetadata,
    ValidationHealth,
    ValidationResult,
    ValidationStatistics,
    ValidationSummary,
)
from requirement_intelligence.validation.models import (
    ValidationVerdict as ValidationSubsystemVerdict,
)
from shared.enums.base import ValidationVerdict

_TS = datetime(2026, 7, 6, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Local builders — real canonical models, no engine/pipeline/criteria
# ---------------------------------------------------------------------------


def _analysis_result() -> AnalysisResult:
    return AnalysisResult(
        analysis_id="AN-1",
        execution_id="EX-1",
        source_consolidated_id="C-1",
        prompt_version="1.0",
        reasoning_contract_version="1.0",
        provider="gemini",
        model="model",
        started_at=_TS,
        completed_at=_TS,
        duration_ms=1.0,
        llm_response=LLMResponse(provider="gemini", model="model", generated_text="x"),
    )


def _cp1_input() -> CP1Input:
    analysis = _analysis_result()
    registry = NormalizationRegistry()
    normalization = ResponseNormalizer(
        registry, NormalizationPipeline(registry), NormalizationConfiguration()
    ).normalize(analysis.llm_response)
    validation = ValidationResult(
        validation_id="VAL-1",
        execution_id="EX-1",
        analysis_id="AN-1",
        analysis_result=analysis,
        validation_summary=ValidationSummary(
            total_issues=0,
            info_count=0,
            warning_count=0,
            error_count=0,
            critical_count=0,
            blocking_issue_count=0,
            overall_health=ValidationHealth.HEALTHY,
        ),
        validation_statistics=ValidationStatistics(
            validation_duration_ms=1.5,
            rules_executed=1,
            rules_passed=1,
            rules_failed=0,
            started_at=_TS,
            completed_at=_TS,
            validator_version=FRAMEWORK_VERSION,
            validation_contract_version=DEFAULT_VALIDATION_CONTRACT_VERSION,
            execution_id="EX-1",
        ),
        validation_configuration=ValidationConfiguration(),
        validation_framework_metadata=ValidationFrameworkMetadata(
            framework_version=FRAMEWORK_VERSION,
            validation_contract_version=DEFAULT_VALIDATION_CONTRACT_VERSION,
            pipeline_version=PIPELINE_VERSION,
            registry_version=REGISTRY_VERSION,
        ),
        overall_verdict=ValidationSubsystemVerdict.PASSED,
        started_at=_TS,
        completed_at=_TS,
    )
    return CP1Input(validation_result=validation, normalization_result=normalization)


def _finding(
    finding_id: str = "F-1",
    *,
    criterion_id: str = "CP1-0001",
    message: str = "No engineering input exists.",
    recommendation: str = "Add at least one requirement.",
    evidence: str | None = "pooled requirement count: 0",
) -> CP1Finding:
    return CP1Finding(
        finding_id=finding_id,
        criterion_id=criterion_id,
        criterion_version="1.0.0",
        verdict_contribution=ValidationVerdict.FAIL,
        message=message,
        location="functional_requirements+security_requirements+quality_requirements",
        evidence=evidence,
        recommendation=recommendation,
        correlation_id="EX-1",
        created_at=_TS,
    )


def _framework_metadata() -> CP1FrameworkMetadata:
    return CP1FrameworkMetadata(
        framework_version="1.0.0",
        criteria_contract_version="1.0",
        pipeline_version="1.0.0",
        registry_version="1.0.0",
    )


def _cp1_result(
    *,
    findings: tuple[CP1Finding, ...] = (),
    verdict: ValidationVerdict = ValidationVerdict.PASS,
) -> CP1Result:
    return CP1Result(
        cp1_id="CP1-RUN-1",
        validation_id="VAL-1",
        execution_id="EX-1",
        analysis_id="AN-1",
        cp1_input=_cp1_input(),
        findings=findings,
        framework_metadata=_framework_metadata(),
        overall_verdict=verdict,
        started_at=_TS,
        completed_at=_TS,
    )


@dataclass(frozen=True)
class _Data:
    """Minimal ExecutionData stand-in exposing only ``cp1_result``."""

    cp1_result: Any


def _build(result: CP1Result) -> str:
    return CP1ReportBuilder().build(_Data(cp1_result=result))


# ---------------------------------------------------------------------------
# Structure / header
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStructure:
    def test_has_all_required_sections(self) -> None:
        report = _build(_cp1_result())
        for heading in (
            "# CP1 Engineering Readiness Report",
            "## Overall Verdict",
            "## Framework",
            "## Criteria Executed",
            "## Findings",
            "## Recommendations",
            "## Execution Metadata",
        ):
            assert heading in report

    def test_framework_version_rendered(self) -> None:
        report = _build(_cp1_result())
        assert "| Framework Version | 1.0.0 |" in report

    def test_execution_metadata_rendered(self) -> None:
        report = _build(_cp1_result())
        assert "| CP1 Id | CP1-RUN-1 |" in report
        assert "| Execution Id | EX-1 |" in report
        assert "| Analysis Id | AN-1 |" in report

    def test_trailing_newline(self) -> None:
        assert _build(_cp1_result()).endswith("\n")


# ---------------------------------------------------------------------------
# Zero findings (PASS)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNoFindings:
    def test_pass_verdict_rendered(self) -> None:
        assert "**PASS**" in _build(_cp1_result(verdict=ValidationVerdict.PASS))

    def test_no_findings_message(self) -> None:
        report = _build(_cp1_result())
        assert "No engineering readiness findings." in report

    def test_no_recommendations_message(self) -> None:
        assert "_No recommendations._" in _build(_cp1_result())

    def test_criteria_executed_empty_note(self) -> None:
        assert "_No criteria reported findings" in _build(_cp1_result())

    def test_findings_count_zero(self) -> None:
        assert "| Findings | 0 |" in _build(_cp1_result())


# ---------------------------------------------------------------------------
# One finding (FAIL)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSingleFinding:
    def test_fail_verdict_rendered(self) -> None:
        report = _build(_cp1_result(findings=(_finding(),), verdict=ValidationVerdict.FAIL))
        assert "**FAIL**" in report

    def test_finding_rendered(self) -> None:
        report = _build(_cp1_result(findings=(_finding(),), verdict=ValidationVerdict.FAIL))
        assert "### CP1-0001 — FAIL" in report
        assert "No engineering input exists." in report
        assert "| Finding Id | F-1 |" in report

    def test_recommendation_rendered(self) -> None:
        report = _build(_cp1_result(findings=(_finding(),), verdict=ValidationVerdict.FAIL))
        assert "Add at least one requirement." in report
        assert "- CP1-0001: Add at least one requirement." in report

    def test_criteria_executed_lists_criterion(self) -> None:
        report = _build(_cp1_result(findings=(_finding(),), verdict=ValidationVerdict.FAIL))
        assert "- CP1-0001" in report

    def test_no_findings_message_absent(self) -> None:
        report = _build(_cp1_result(findings=(_finding(),), verdict=ValidationVerdict.FAIL))
        assert "No engineering readiness findings." not in report

    def test_findings_count_one(self) -> None:
        report = _build(_cp1_result(findings=(_finding(),), verdict=ValidationVerdict.FAIL))
        assert "| Findings | 1 |" in report


# ---------------------------------------------------------------------------
# Multiple findings — ordering preserved
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMultipleFindings:
    def _multi(self) -> CP1Result:
        findings = (
            _finding("F-1", message="first finding", recommendation="fix first"),
            _finding("F-2", message="second finding", recommendation="fix second"),
            _finding("F-3", message="third finding", recommendation="fix third"),
        )
        return _cp1_result(findings=findings, verdict=ValidationVerdict.FAIL)

    def test_all_findings_rendered(self) -> None:
        report = _build(self._multi())
        assert "first finding" in report
        assert "second finding" in report
        assert "third finding" in report

    def test_finding_ordering_preserved(self) -> None:
        report = _build(self._multi())
        assert report.index("first finding") < report.index("second finding")
        assert report.index("second finding") < report.index("third finding")

    def test_recommendation_ordering_preserved(self) -> None:
        report = _build(self._multi())
        assert report.index("fix first") < report.index("fix second")
        assert report.index("fix second") < report.index("fix third")

    def test_findings_count_three(self) -> None:
        assert "| Findings | 3 |" in _build(self._multi())

    def test_distinct_criteria_deduplicated_in_order(self) -> None:
        findings = (
            _finding("F-1", criterion_id="CP1-0001"),
            _finding("F-2", criterion_id="CP1-0002"),
            _finding("F-3", criterion_id="CP1-0001"),
        )
        report = _build(_cp1_result(findings=findings, verdict=ValidationVerdict.FAIL))
        criteria_block = report.split("## Criteria Executed")[1].split("## Findings")[0]
        assert criteria_block.count("- CP1-0001") == 1  # deduplicated
        assert "- CP1-0002" in criteria_block
        assert criteria_block.index("- CP1-0001") < criteria_block.index("- CP1-0002")


# ---------------------------------------------------------------------------
# Safety: markdown escaping, optional evidence
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSafety:
    def test_pipes_and_newlines_escaped(self) -> None:
        finding = _finding(message="a | b\nc")
        report = _build(_cp1_result(findings=(finding,), verdict=ValidationVerdict.FAIL))
        assert "a \\| b c" in report  # pipe escaped, newline flattened

    def test_absent_evidence_renders_dash(self) -> None:
        finding = _finding(evidence=None)
        report = _build(_cp1_result(findings=(finding,), verdict=ValidationVerdict.FAIL))
        assert "| Evidence | - |" in report


# ---------------------------------------------------------------------------
# Determinism & thread safety
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDeterminismAndThreadSafety:
    def test_deterministic_repeated_build(self) -> None:
        result = _cp1_result(findings=(_finding(),), verdict=ValidationVerdict.FAIL)
        assert _build(result) == _build(result)

    def test_thread_safe(self) -> None:
        result = _cp1_result(findings=(_finding(),), verdict=ValidationVerdict.FAIL)
        expected = _build(result)
        builder = CP1ReportBuilder()
        data = _Data(cp1_result=result)
        with ThreadPoolExecutor(max_workers=8) as pool:
            outputs = list(pool.map(lambda _: builder.build(data), range(32)))
        assert all(o == expected for o in outputs)
