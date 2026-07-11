"""Unit tests for Grounding Framework canonical models.

Covers construction, immutability, camelCase serialization round-trips, and the
contract invariants each model enforces at construction.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from requirement_intelligence.grounding.identity import (
    GroundedRequirementId,
    GroundingAssessmentId,
)
from requirement_intelligence.grounding.models import (
    ConfidenceBand,
    EvidenceRelation,
    GroundedRequirement,
    GroundingAssessment,
    GroundingFinding,
    GroundingResult,
    GroundingSeverity,
    SupportClassification,
)
from requirement_intelligence.grounding.version import (
    GROUNDING_CONFIGURATION_VERSION,
    GROUNDING_FRAMEWORK_VERSION,
)
from requirement_intelligence.models.enums import SourceCategory
from tests.unit.grounding_helpers import (
    COMPLETED,
    STARTED,
    make_confidence,
    make_explanation,
    make_link,
    make_metrics,
    make_summary,
)


def _supported_requirement(text: str = "Set nosniff header.") -> GroundedRequirement:
    return GroundedRequirement(
        requirement_id=GroundedRequirementId.for_requirement(SourceCategory.SECURITY, text),
        domain=SourceCategory.SECURITY,
        text=text,
        position=0,
        classification=SupportClassification.SUPPORTED,
        confidence=make_confidence(),
        evidence_links=(make_link(),),
        explanation=make_explanation(),
    )


@pytest.mark.unit
class TestGroundedRequirement:
    def test_constructs_and_exposes_source_systems(self) -> None:
        req = _supported_requirement()
        assert req.source_systems == frozenset({"owasp_zap"})

    def test_is_immutable(self) -> None:
        req = _supported_requirement()
        with pytest.raises(ValidationError):
            req.text = "changed"  # type: ignore[misc]

    def test_supported_without_evidence_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GroundedRequirement(
                requirement_id=GroundedRequirementId.for_requirement(SourceCategory.SECURITY, "x"),
                domain=SourceCategory.SECURITY,
                text="x",
                position=0,
                classification=SupportClassification.SUPPORTED,
                confidence=make_confidence(),
                evidence_links=(),
                explanation=make_explanation(),
            )

    def test_unsupported_with_supporting_link_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GroundedRequirement(
                requirement_id=GroundedRequirementId.for_requirement(SourceCategory.SECURITY, "y"),
                domain=SourceCategory.SECURITY,
                text="y",
                position=0,
                classification=SupportClassification.UNSUPPORTED,
                confidence=make_confidence(score=5, band=ConfidenceBand.LOW),
                evidence_links=(make_link(relation=EvidenceRelation.DIRECT),),
                explanation=make_explanation(),
            )

    def test_serialises_camel_case_and_round_trips(self) -> None:
        req = _supported_requirement()
        dumped = req.model_dump(mode="json", by_alias=True)
        assert "requirementId" in dumped
        assert "evidenceLinks" in dumped
        assert GroundedRequirement.model_validate(dumped) == req


@pytest.mark.unit
class TestGroundingFinding:
    def _finding(self, classification: SupportClassification) -> GroundingFinding:
        req = _supported_requirement()
        return GroundingFinding(
            finding_id="gf-1",
            requirement_id=req.requirement_id,
            classification=classification,
            severity=GroundingSeverity.WARNING,
            message="unsupported requirement",
        )

    def test_hallucination_classification_is_accepted(self) -> None:
        finding = self._finding(SupportClassification.UNSUPPORTED)
        assert finding.classification == SupportClassification.UNSUPPORTED

    def test_non_hallucination_classification_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            self._finding(SupportClassification.SUPPORTED)


@pytest.mark.unit
class TestGroundingAssessmentAndResult:
    def _assessment(self, *, with_finding: bool) -> GroundingAssessment:
        req = _supported_requirement()
        findings: tuple[GroundingFinding, ...] = ()
        if with_finding:
            findings = (
                GroundingFinding(
                    finding_id="gf-1",
                    requirement_id=req.requirement_id,
                    classification=SupportClassification.UNSUPPORTED,
                    severity=GroundingSeverity.WARNING,
                    message="x",
                ),
            )
        return GroundingAssessment(
            assessment_id=GroundingAssessmentId.for_run("ctx-x", "c"),
            context_id="ctx-x",
            grounded_requirements=(req,),
            findings=findings,
            metrics=make_metrics(),
            summary=make_summary(),
            framework_version=GROUNDING_FRAMEWORK_VERSION,
            configuration_version=GROUNDING_CONFIGURATION_VERSION,
        )

    def test_supported_assessment_has_no_findings(self) -> None:
        assessment = self._assessment(with_finding=False)
        assert assessment.findings == ()

    def test_finding_for_supported_requirement_is_rejected(self) -> None:
        # The one requirement is SUPPORTED, so a finding over-covers it.
        with pytest.raises(ValidationError):
            self._assessment(with_finding=True)

    def test_result_rejects_completed_before_started(self) -> None:
        assessment = self._assessment(with_finding=False)
        with pytest.raises(ValidationError):
            GroundingResult(
                analysis_id="a-1",
                execution_id="e-1",
                assessment=assessment,
                framework_version=GROUNDING_FRAMEWORK_VERSION,
                configuration_version=GROUNDING_CONFIGURATION_VERSION,
                started_at=COMPLETED,
                completed_at=STARTED,
            )

    def test_result_round_trips(self) -> None:
        assessment = self._assessment(with_finding=False)
        result = GroundingResult(
            analysis_id="a-1",
            execution_id="e-1",
            assessment=assessment,
            framework_version=GROUNDING_FRAMEWORK_VERSION,
            configuration_version=GROUNDING_CONFIGURATION_VERSION,
            started_at=STARTED,
            completed_at=COMPLETED,
        )
        dumped = result.model_dump(mode="json", by_alias=True)
        assert dumped["frameworkVersion"] == "1.0.0"
        assert GroundingResult.model_validate(dumped) == result
