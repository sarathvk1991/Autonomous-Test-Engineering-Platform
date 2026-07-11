"""Unit tests for the construction-only Grounding Framework builders."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from requirement_intelligence.grounding.builders import (
    GroundedRequirementBuilder,
    GroundingAssessmentBuilder,
    GroundingResultBuilder,
)
from requirement_intelligence.grounding.identity import GroundedRequirementId
from requirement_intelligence.grounding.models import SupportClassification
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


@pytest.mark.unit
class TestGroundedRequirementBuilder:
    def test_mints_deterministic_id(self) -> None:
        builder = GroundedRequirementBuilder()
        text = "Set the X-Content-Type-Options header to nosniff."
        req = builder.build(
            domain=SourceCategory.SECURITY,
            text=text,
            position=0,
            classification=SupportClassification.SUPPORTED,
            confidence=make_confidence(),
            explanation=make_explanation(),
            evidence_links=(make_link(),),
        )
        assert req.requirement_id == GroundedRequirementId.for_requirement(
            SourceCategory.SECURITY, text
        )

    def test_rejects_invalid_construction(self) -> None:
        builder = GroundedRequirementBuilder()
        with pytest.raises(ValidationError):
            builder.build(
                domain=SourceCategory.SECURITY,
                text="unsupported claim",
                position=0,
                classification=SupportClassification.SUPPORTED,
                confidence=make_confidence(),
                explanation=make_explanation(),
                evidence_links=(),  # SUPPORTED requires ≥1 supporting link
            )


@pytest.mark.unit
class TestAssessmentAndResultBuilders:
    def _requirement(self):  # type: ignore[no-untyped-def]
        return GroundedRequirementBuilder().build(
            domain=SourceCategory.SECURITY,
            text="Set nosniff header.",
            position=0,
            classification=SupportClassification.SUPPORTED,
            confidence=make_confidence(),
            explanation=make_explanation(),
            evidence_links=(make_link(),),
        )

    def test_assessment_builder_mints_id_and_validates(self) -> None:
        req = self._requirement()
        assessment = GroundingAssessmentBuilder().build(
            context_id="ctx-authentication-abc",
            grounded_requirements=(req,),
            metrics=make_metrics(),
            summary=make_summary(),
        )
        assert str(assessment.assessment_id).startswith("grnd-ctx-authentication-abc-")
        assert assessment.grounded_requirements == (req,)

    def test_assessment_builder_id_is_deterministic(self) -> None:
        req = self._requirement()
        one = GroundingAssessmentBuilder().build(
            context_id="ctx-x",
            grounded_requirements=(req,),
            metrics=make_metrics(),
            summary=make_summary(),
        )
        two = GroundingAssessmentBuilder().build(
            context_id="ctx-x",
            grounded_requirements=(req,),
            metrics=make_metrics(),
            summary=make_summary(),
        )
        assert one.assessment_id == two.assessment_id

    def test_result_builder_builds_carrier(self) -> None:
        req = self._requirement()
        assessment = GroundingAssessmentBuilder().build(
            context_id="ctx-x",
            grounded_requirements=(req,),
            metrics=make_metrics(),
            summary=make_summary(),
        )
        result = GroundingResultBuilder().build(
            analysis_id="a-1",
            execution_id="e-1",
            assessment=assessment,
            started_at=STARTED,
            completed_at=COMPLETED,
        )
        assert result.assessment is assessment
        assert result.analysis_id == "a-1"
