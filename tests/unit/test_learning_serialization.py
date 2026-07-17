"""Unit tests for the Learning serialization layer (CAP-086C).

Covers the JSON round-trip invariant, deterministic Markdown/metrics rendering, the
ExecutionWriter integration (conditional artifacts + manifest registration + absence
when no LearningResult), the manifest purity boundary (the manifest references the
Learning artifacts but never duplicates their content, ADR-0029 §D28/§D29), and the
frozen boundaries (serializer imports no Learning runtime; the runtime contract
imports no execution package). Mirrors ``test_organizational_memory_serialization.py``
(CAP-085C).
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from requirement_intelligence.execution.execution_writer import ExecutionWriter
from requirement_intelligence.learning.identity import (
    LearningCandidateId,
    LearningConfidenceId,
    LearningFrameworkVersion,
    LearningId,
    LearningLifecycleId,
    LearningPolicyId,
    LearningPolicyVersion,
    LearningResultId,
    LearningValidationId,
)
from requirement_intelligence.learning.models import (
    Learning,
    LearningCandidate,
    LearningConfidence,
    LearningConfidenceLevel,
    LearningLifecycle,
    LearningMaturity,
    LearningMetrics,
    LearningResult,
    LearningSummary,
    LearningValidation,
    LearningValidationGate,
)
from requirement_intelligence.learning.serialization import LearningSerializer
from tests.productization.conftest import _run_golden_pipeline

_REPO_ROOT = Path(__file__).resolve().parents[2]

_LEARNING_ARTIFACTS = (
    "learning_result.json",
    "learning_report.md",
    "learning_metrics.md",
)

_NOW = datetime(2026, 7, 16, tzinfo=UTC)


def _with_content() -> LearningResult:
    """A hand-built result carrying one of every knowledge object, for report
    content assertions.

    Hand-building the result directly (the same discipline the CAP-086B.1
    freeze test used) keeps this test focused on rendering, not on the
    floor-gated validation/generation conditions the engine's own tests
    already cover.
    """
    candidate = LearningCandidate(
        candidate_id=LearningCandidateId.for_source("bp-1"),
        source_best_practice_ids=("bp-1",),
        proposed_change="Adopt the practice organization-wide.",
        confidence=LearningConfidenceLevel.LOW,
    )
    validation = LearningValidation(
        validation_id=LearningValidationId.for_ordinal("learning-serialization", 0),
        candidate_id=candidate.candidate_id,
        gates_cleared=tuple(LearningValidationGate),
        rationale="Cleared every governed gate.",
        validated_at=_NOW,
        confidence=LearningConfidenceLevel.VERIFIED,
        policy_version=LearningPolicyVersion(1, 0, 0),
    )
    learning = Learning(
        learning_id=LearningId.for_ordinal("learning-serialization", 0),
        candidate_id=candidate.candidate_id,
        validation_id=validation.validation_id,
        message="Adopt the practice organization-wide.",
        maturity=LearningMaturity.VALIDATED,
        confidence=LearningConfidenceLevel.VERIFIED,
    )
    confidence = LearningConfidence(
        confidence_id=LearningConfidenceId.for_ordinal("learning-serialization", 0),
        subject_id=str(learning.learning_id),
        level=LearningConfidenceLevel.VERIFIED,
        evidence_count=2,
        rationale="Two corroborating best practices.",
        recorded_at=_NOW,
    )
    lifecycle = LearningLifecycle(
        lifecycle_id=LearningLifecycleId.for_ordinal("learning-serialization", 0),
        subject_id=str(learning.learning_id),
        maturity=LearningMaturity.VALIDATED,
        maturity_reason="newly validated",
    )
    return LearningResult(
        result_id=LearningResultId.for_source("omr-serialization"),
        organizational_memory_result_id="omr-serialization",
        candidates=(candidate,),
        learnings=(learning,),
        validations=(validation,),
        confidences=(confidence,),
        lifecycles=(lifecycle,),
        summary=LearningSummary(
            policy_id=LearningPolicyId("default-learning-policy"),
            policy_version=LearningPolicyVersion(1, 0, 0),
            total_candidates=1,
            total_learnings=1,
            total_validations=1,
            headline="1 candidate, 1 learning.",
        ),
        metrics=LearningMetrics(
            candidate_count=1,
            learning_count=1,
            validation_count=1,
            observed_count=0,
            validated_count=1,
            trusted_count=0,
            institutional_count=0,
            standard_count=0,
            retired_count=0,
        ),
        policy_id=LearningPolicyId("default-learning-policy"),
        policy_version=LearningPolicyVersion(1, 0, 0),
        framework_version=LearningFrameworkVersion(1, 0, 0),
        started_at=_NOW,
        completed_at=_NOW,
    )


def _empty_result() -> LearningResult:
    """A result carrying no candidates, validations, learnings, confidences, or
    lifecycles — the policy-disabled / corpus-floor-gated shape."""
    return LearningResult(
        result_id=LearningResultId.for_source("omr-serialization-empty"),
        organizational_memory_result_id="omr-serialization-empty",
        candidates=(),
        learnings=(),
        validations=(),
        confidences=(),
        lifecycles=(),
        summary=LearningSummary(
            policy_id=LearningPolicyId("default-learning-policy"),
            policy_version=LearningPolicyVersion(1, 0, 0),
            total_candidates=0,
            total_learnings=0,
            total_validations=0,
            headline="Learning is disabled by policy (enable_candidate_proposal=False).",
        ),
        metrics=LearningMetrics(
            candidate_count=0,
            learning_count=0,
            validation_count=0,
            observed_count=0,
            validated_count=0,
            trusted_count=0,
            institutional_count=0,
            standard_count=0,
            retired_count=0,
        ),
        policy_id=LearningPolicyId("default-learning-policy"),
        policy_version=LearningPolicyVersion(1, 0, 0),
        framework_version=LearningFrameworkVersion(1, 0, 0),
        started_at=_NOW,
        completed_at=_NOW,
    )


@pytest.mark.unit
class TestJsonProjection:
    def test_round_trip_equals_original(self) -> None:
        result = _with_content()
        dumped = LearningSerializer().render_json(result)
        assert LearningResult.model_validate(dumped) == result

    def test_json_is_camel_case_and_carries_versions(self) -> None:
        dumped = LearningSerializer().render_json(_with_content())
        assert "resultVersion" in dumped
        assert "frameworkVersion" in dumped
        assert "policyVersion" in dumped
        assert "organizationalMemoryResultId" in dumped

    def test_json_is_deterministic_for_the_same_result(self) -> None:
        serializer = LearningSerializer()
        result = _with_content()
        assert json.dumps(serializer.render_json(result)) == json.dumps(
            serializer.render_json(result)
        )


@pytest.mark.unit
class TestMarkdownProjection:
    def test_report_is_deterministic_and_has_sections(self) -> None:
        serializer = LearningSerializer()
        result = _with_content()
        report = serializer.render_report(result)
        assert report == serializer.render_report(result)
        for section in (
            "# Learning Report",
            "## Summary",
            "## Consumed Layer 2 Result",
            "## Learning Candidates",
            "## Validations",
            "## Learnings",
            "## Confidences",
            "## Lifecycles",
        ):
            assert section in report

    def test_metrics_is_deterministic_and_has_headline(self) -> None:
        serializer = LearningSerializer()
        result = _with_content()
        rendered = serializer.render_metrics(result)
        assert rendered == serializer.render_metrics(result)
        assert "# Learning Metrics" in rendered
        assert "Lifecycle Maturity Distribution" in rendered

    def test_report_surfaces_a_learning_verbatim(self) -> None:
        # The projection never derives a Learning — it renders exactly what
        # the LearningResult already recorded.
        serializer = LearningSerializer()
        result = _with_content()
        assert result.learnings
        report = serializer.render_report(result)
        assert str(result.learnings[0].learning_id) in report
        assert result.learnings[0].message in report

    def test_result_with_no_content_still_renders_valid_sections(self) -> None:
        serializer = LearningSerializer()
        result = _empty_result()
        assert result.candidates == ()
        report = serializer.render_report(result)
        assert "_None_" in report
        metrics = serializer.render_metrics(result)
        assert "_None_" in metrics or "0" in metrics


@pytest.mark.unit
class TestExecutionWriterIntegration:
    def test_no_learning_result_produces_no_artifacts(self, tmp_path: Path) -> None:
        pipeline = _run_golden_pipeline(tmp_path / "golden")
        data = replace(pipeline.execution_data, learning_result=None)
        target = tmp_path / "no_learning"
        target.mkdir()
        write_result = ExecutionWriter().write(target, data)
        for name in _LEARNING_ARTIFACTS:
            assert not (target / name).exists()
        assert all("learning" not in n for n in write_result.generated_artifacts)
        manifest = write_result.manifest
        assert "learningExecuted" not in manifest
        assert "learningReport" not in manifest

    def test_learning_result_produces_three_artifacts_and_manifest_entries(
        self, tmp_path: Path
    ) -> None:
        result = _with_content()
        pipeline = _run_golden_pipeline(tmp_path / "golden")
        data = replace(pipeline.execution_data, learning_result=result)
        target = tmp_path / "with_learning"
        target.mkdir()
        write_result = ExecutionWriter().write(target, data)
        for name in _LEARNING_ARTIFACTS:
            assert (target / name).exists()
            assert name in write_result.generated_artifacts
        manifest_names = {a["name"] for a in write_result.manifest["generatedArtifacts"]}
        assert set(_LEARNING_ARTIFACTS) <= manifest_names
        # Manifest purity (ADR-0029 §D28/§D29): the manifest is package
        # metadata only — it names the artifact, it never carries Learning
        # content. The canonical candidates/validations/learnings/confidences/
        # lifecycles live exclusively in learning_result.json / LearningResult.
        assert write_result.manifest["learningExecuted"] is True
        assert "learningSummary" not in write_result.manifest
        assert "learningCandidates" not in write_result.manifest
        result_path = target / "learning_result.json"
        on_disk = json.loads(result_path.read_text(encoding="utf-8"))
        assert on_disk["summary"]["totalCandidates"] == result.summary.total_candidates

    def test_artifacts_are_reproducible_from_learning_result_alone(
        self, tmp_path: Path
    ) -> None:
        result = _with_content()
        pipeline = _run_golden_pipeline(tmp_path / "golden")
        data = replace(pipeline.execution_data, learning_result=result)
        target = tmp_path / "repro"
        target.mkdir()
        ExecutionWriter().write(target, data)
        serializer = LearningSerializer()
        assert (target / "learning_report.md").read_text(encoding="utf-8") == (
            serializer.render_report(result)
        )
        assert (target / "learning_metrics.md").read_text(encoding="utf-8") == (
            serializer.render_metrics(result)
        )
        assert json.loads(
            (target / "learning_result.json").read_text(encoding="utf-8")
        ) == serializer.render_json(result)


@pytest.mark.unit
class TestSerializationBoundary:
    def test_serializer_imports_no_learning_runtime(self) -> None:
        source = (
            _REPO_ROOT
            / "requirement_intelligence"
            / "learning"
            / "serialization"
            / "learning_serializer.py"
        ).read_text(encoding="utf-8")
        forbidden = (
            "learning.engine",
            "learning_service",
            "learning.policy",
            "learning.rules",
            "DeterministicLearningEngine",
            "DeterministicLearningService",
            "LearningService",
            "LearningPolicy",
            "LearningRuleCatalog",
            "PlatformContext",
        )
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                for token in forbidden:
                    assert token not in line, f"serializer must not import {token!r}"

    def test_runtime_contract_imports_no_execution_package(self) -> None:
        """LearningResult must never depend on the Execution Package."""
        source = (
            _REPO_ROOT / "requirement_intelligence" / "learning" / "models" / "result.py"
        ).read_text(encoding="utf-8")
        assert "requirement_intelligence.execution" not in source
