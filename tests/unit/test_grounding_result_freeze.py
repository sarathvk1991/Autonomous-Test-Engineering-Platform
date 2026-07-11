"""Unit tests for the CAP-077E.1 GroundingResult runtime-contract freeze.

Covers the GroundingResult schema version (default, serialization, immutability,
independence) and the frozen runtime/artifact boundary: the Execution Package imports no
grounding runtime component, and GroundingResult imports no Execution Package.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from requirement_intelligence.grounding import (
    GROUNDING_RESULT_VERSION,
    ClassificationVersion,
    ConfidenceVersion,
    GroundingAssessmentBuilder,
    GroundingFrameworkVersion,
    GroundingMetricsBuilder,
    GroundingResult,
    GroundingResultBuilder,
    GroundingResultVersion,
    MatchResultVersion,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FIXED = datetime(2026, 7, 11, 12, 0, 0, tzinfo=UTC)


def _result() -> GroundingResult:
    metrics = GroundingMetricsBuilder().build([], evidence_available=0)
    summary = GroundingMetricsBuilder().build_summary([], metrics)
    assessment = GroundingAssessmentBuilder().build(
        context_id="ctx-x",
        grounded_requirements=(),
        metrics=metrics,
        summary=summary,
    )
    return GroundingResultBuilder().build(
        analysis_id="a-1",
        execution_id="e-1",
        assessment=assessment,
        started_at=_FIXED,
        completed_at=_FIXED,
    )


@pytest.mark.unit
class TestGroundingResultVersion:
    def test_default_result_version(self) -> None:
        assert _result().result_version == GROUNDING_RESULT_VERSION
        assert isinstance(_result().result_version, GroundingResultVersion)

    def test_serialises_and_round_trips(self) -> None:
        dumped = _result().model_dump(mode="json", by_alias=True)
        assert dumped["resultVersion"] == str(GROUNDING_RESULT_VERSION)
        assert GroundingResult.model_validate(dumped) == _result()

    def test_is_immutable(self) -> None:
        with pytest.raises(ValidationError):
            _result().result_version = GroundingResultVersion(2, 0, 0)  # type: ignore[misc]

    def test_version_is_independent_of_other_versions(self) -> None:
        one = GroundingResultVersion(1, 0, 0)
        assert one != GroundingFrameworkVersion(1, 0, 0)
        assert one != MatchResultVersion(1, 0, 0)
        assert one != ClassificationVersion(1, 0, 0)
        assert one != ConfidenceVersion(1, 0, 0)


@pytest.mark.unit
class TestRuntimeArtifactBoundary:
    def test_execution_package_imports_no_grounding_runtime(self) -> None:
        """Execution Package may consume GroundingResult but never a runtime component."""
        execution_dir = _REPO_ROOT / "requirement_intelligence" / "execution"
        forbidden = (
            "grounding.strategies",
            "grounding.normalization",
            "grounding.matching",
            "grounding.classification",
            "grounding.confidence",
            "grounding.pipeline",
            "grounding.metrics_builder",
            "grounding.grounding_service",
            "GroundingService",
            "GroundingPipeline",
            "SupportClassificationEngine",
            "ConfidenceCalculator",
        )
        for module in execution_dir.glob("*.py"):
            for line in module.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in forbidden:
                        assert token not in line, f"{module.name} imports {token}"

    def test_grounding_result_imports_no_execution_package(self) -> None:
        """The runtime contract never depends on the Execution Package (one-way)."""
        source = (
            _REPO_ROOT / "requirement_intelligence" / "grounding" / "models" / "assessment.py"
        ).read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                assert "execution" not in line.lower()
