"""Unit tests for the Quality Governance serialization layer (CAP-080D).

Covers the JSON round-trip invariant, deterministic Markdown/summary rendering, the
ExecutionWriter integration (conditional artifacts + manifest registration + absence when no
QualityGovernanceResult), the release-authority manifest field, and the frozen boundaries
(serializer imports no governance runtime; the runtime contract imports no execution package).
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from requirement_intelligence.execution.execution_writer import ExecutionWriter
from requirement_intelligence.platform.platform_context import PlatformContext
from requirement_intelligence.quality_governance import (
    QualityDecision,
    QualityGovernanceResult,
)
from requirement_intelligence.quality_governance.serialization import (
    QualityGovernanceSerializer,
)
from shared.enums.base import ValidationVerdict as CP1Verdict
from tests.productization.conftest import _run_golden_pipeline
from tests.unit.quality_governance_helpers import (
    make_cp1_result,
    make_grounding_result,
    make_validation_result,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]

_QUALITY_GOVERNANCE_ARTIFACTS = (
    "quality_governance_result.json",
    "quality_governance_report.md",
    "quality_governance_summary.md",
)


def _governance_result(**kwargs: object) -> QualityGovernanceResult:
    """Evaluate a real QualityGovernanceResult from tunable peer results (no runtime redesign).

    Uses the registered ``QualityGovernanceService`` — the same composition root the runtime
    uses — so the serializer is exercised against a genuine runtime contract, never a hand-rolled
    stand-in. A single ``evaluate`` call fixes the provenance timestamps, so the same object can
    be serialised twice for byte-for-byte determinism assertions.
    """
    service = PlatformContext().create_quality_governance_service()
    return service.evaluate(
        make_grounding_result(**kwargs.get("grounding", {})),  # type: ignore[arg-type]
        make_validation_result(**kwargs.get("validation", {})),  # type: ignore[arg-type]
        make_cp1_result(**kwargs.get("cp1", {})),  # type: ignore[arg-type]
    )


@pytest.mark.unit
class TestJsonProjection:
    def test_round_trip_equals_original(self) -> None:
        result = _governance_result()
        dumped = QualityGovernanceSerializer().render_json(result)
        assert QualityGovernanceResult.model_validate(dumped) == result

    def test_json_is_camel_case_and_carries_versions(self) -> None:
        dumped = QualityGovernanceSerializer().render_json(_governance_result())
        assert "resultVersion" in dumped
        assert "frameworkVersion" in dumped
        assert "consumedInputs" in dumped

    def test_json_is_deterministic_for_the_same_result(self) -> None:
        serializer = QualityGovernanceSerializer()
        result = _governance_result()
        assert json.dumps(serializer.render_json(result)) == json.dumps(
            serializer.render_json(result)
        )


@pytest.mark.unit
class TestMarkdownProjection:
    def test_report_is_deterministic_and_has_sections(self) -> None:
        serializer = QualityGovernanceSerializer()
        result = _governance_result()
        report = serializer.render_report(result)
        assert report == serializer.render_report(result)
        for section in (
            "# Quality Governance Report",
            "## Release Decision",
            "## Finding Distribution",
            "## Findings",
            "## Consumed Results",
        ):
            assert section in report

    def test_summary_is_deterministic_and_has_headline(self) -> None:
        serializer = QualityGovernanceSerializer()
        result = _governance_result()
        rendered = serializer.render_summary(result)
        assert rendered == serializer.render_summary(result)
        assert "# Quality Governance Summary" in rendered
        assert "Release decision" in rendered

    def test_report_surfaces_the_decision_verbatim(self) -> None:
        # A clean run PASSes; a failed CP1 verdict trips the mandatory release gate and FAILs.
        # The projection never derives the decision — it renders exactly what the
        # QualityGovernanceResult already recorded.
        serializer = QualityGovernanceSerializer()
        passing = _governance_result()
        assert passing.assessment.decision == QualityDecision.PASS
        assert "PASS" in serializer.render_summary(passing)

        failing = _governance_result(cp1={"verdict": CP1Verdict.FAIL})
        assert failing.assessment.decision == QualityDecision.FAIL
        assert "FAIL" in serializer.render_summary(failing)
        # The failing run surfaces at least one governance finding in its report.
        assert failing.assessment.findings
        report = serializer.render_report(failing)
        assert failing.assessment.findings[0].finding_id in report


@pytest.mark.unit
class TestExecutionWriterIntegration:
    def test_no_governance_result_produces_no_artifacts(self, tmp_path: Path) -> None:
        pipeline = _run_golden_pipeline(tmp_path / "golden")
        data = replace(pipeline.execution_data, quality_governance_result=None)
        target = tmp_path / "no_governance"
        target.mkdir()
        write_result = ExecutionWriter().write(target, data)
        for name in _QUALITY_GOVERNANCE_ARTIFACTS:
            assert not (target / name).exists()
        assert all("quality_governance" not in n for n in write_result.generated_artifacts)
        manifest = write_result.manifest
        assert "qualityGovernanceExecuted" not in manifest
        assert "qualityGovernanceDecision" not in manifest

    def test_governance_result_produces_three_artifacts_and_manifest_entries(
        self, tmp_path: Path
    ) -> None:
        pipeline = _run_golden_pipeline(tmp_path / "golden")
        result = pipeline.quality_governance_result
        data = replace(pipeline.execution_data, quality_governance_result=result)
        target = tmp_path / "with_governance"
        target.mkdir()
        write_result = ExecutionWriter().write(target, data)
        for name in _QUALITY_GOVERNANCE_ARTIFACTS:
            assert (target / name).exists()
            assert name in write_result.generated_artifacts
        manifest_names = {a["name"] for a in write_result.manifest["generatedArtifacts"]}
        assert set(_QUALITY_GOVERNANCE_ARTIFACTS) <= manifest_names
        # Release authority: the manifest records the canonical decision, read verbatim.
        decision = result.assessment.decision
        assert write_result.manifest["qualityGovernanceExecuted"] is True
        assert write_result.manifest["qualityGovernanceDecision"] == str(
            getattr(decision, "value", decision)
        )

    def test_artifacts_are_reproducible_from_governance_result_alone(
        self, tmp_path: Path
    ) -> None:
        pipeline = _run_golden_pipeline(tmp_path / "golden")
        result = pipeline.quality_governance_result
        data = replace(pipeline.execution_data, quality_governance_result=result)
        target = tmp_path / "repro"
        target.mkdir()
        ExecutionWriter().write(target, data)
        serializer = QualityGovernanceSerializer()
        assert (target / "quality_governance_report.md").read_text(encoding="utf-8") == (
            serializer.render_report(result)
        )
        assert (target / "quality_governance_summary.md").read_text(encoding="utf-8") == (
            serializer.render_summary(result)
        )
        assert json.loads(
            (target / "quality_governance_result.json").read_text(encoding="utf-8")
        ) == serializer.render_json(result)


@pytest.mark.unit
class TestSerializationBoundary:
    def test_serializer_imports_no_governance_runtime(self) -> None:
        source = (
            _REPO_ROOT
            / "requirement_intelligence"
            / "quality_governance"
            / "serialization"
            / "quality_governance_serializer.py"
        ).read_text(encoding="utf-8")
        forbidden = (
            "quality_governance.evaluation",
            "quality_governance.assessment",
            "quality_governance.decision",
            "quality_governance.pipeline",
            "quality_governance.builder",
            "quality_governance.policy",
            "quality_governance.rules",
            "quality_governance_service",
            "QualityGovernancePipeline",
            "QualityRuleEvaluator",
            "QualityAssessmentEngine",
            "QualityDecisionEngine",
            "QualityGovernanceService",
        )
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                for token in forbidden:
                    assert token not in line, f"serializer must not import {token!r}"

    def test_runtime_contract_imports_no_execution_package(self) -> None:
        """QualityGovernanceResult must never depend on the Execution Package."""
        source = (
            _REPO_ROOT
            / "requirement_intelligence"
            / "quality_governance"
            / "models"
            / "result.py"
        ).read_text(encoding="utf-8")
        assert "requirement_intelligence.execution" not in source
