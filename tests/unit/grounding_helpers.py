"""Shared construction helpers for Grounding Framework foundation tests.

Not a test module (no ``test_`` prefix, so pytest does not collect it). It builds
valid canonical instances so each test asserts one thing without re-stating the
whole object graph.
"""

from __future__ import annotations

from datetime import UTC, datetime

from requirement_intelligence.grounding.models import (
    ConfidenceBand,
    ConfidenceComponent,
    EvidenceReference,
    EvidenceRelation,
    GroundingConfidence,
    GroundingExplanation,
    GroundingMetrics,
    GroundingSummary,
    RequirementEvidenceLink,
    SupportClassification,
)
from requirement_intelligence.grounding.version import (
    GROUNDING_CONFIGURATION_VERSION,
    GROUNDING_FRAMEWORK_VERSION,
)
from requirement_intelligence.models.enums import (
    SourceCategory,
    SourceSystem,
    SourceType,
)


def make_evidence_reference(
    *,
    source_system: SourceSystem = SourceSystem.OWASP_ZAP,
    source_record_id: str = "10021",
    source_category: SourceCategory = SourceCategory.SECURITY,
    source_type: SourceType = SourceType.DAST,
) -> EvidenceReference:
    """A valid evidence reference (defaults to a ZAP security finding)."""
    return EvidenceReference(
        source_system=source_system,
        source_record_id=source_record_id,
        source_category=source_category,
        source_type=source_type,
    )


def make_link(
    *,
    relation: EvidenceRelation = EvidenceRelation.DIRECT,
    match_score: int = 90,
    evidence: EvidenceReference | None = None,
) -> RequirementEvidenceLink:
    """A valid requirement-to-evidence link."""
    return RequirementEvidenceLink(
        evidence=evidence or make_evidence_reference(),
        relation=relation,
        match_score=match_score,
        matched_terms=("nosniff", "content-type-options"),
        rationale="Requirement names the header the alert reports missing.",
    )


def make_confidence(
    *, score: int = 88, band: ConfidenceBand = ConfidenceBand.HIGH
) -> GroundingConfidence:
    """A valid grounding confidence carrying its versions."""
    return GroundingConfidence(
        score=score,
        band=band,
        components=(
            ConfidenceComponent(factor="direct_match", delta=8, reason="one strong match"),
        ),
        configuration_version=GROUNDING_CONFIGURATION_VERSION,
        framework_version=GROUNDING_FRAMEWORK_VERSION,
    )


def make_explanation(
    *, summary: str = "Supported by a direct ZAP finding."
) -> GroundingExplanation:
    """A valid structured explanation."""
    return GroundingExplanation(
        summary=summary,
        supporting_evidence=(make_evidence_reference(),),
        recommendations=("accept",),
    )


def make_metrics(*, total: int = 1, grounded: int = 1, score: int = 100) -> GroundingMetrics:
    """Valid metrics for a small assessment (values supplied, not computed)."""
    return GroundingMetrics(
        total_requirements=total,
        grounded_requirements=grounded,
        unsupported_requirements=total - grounded,
        grounding_coverage=1.0,
        evidence_coverage=1.0,
        requirement_coverage=1.0,
        evidence_utilization=1.0,
        traceability_completeness=1.0,
        average_confidence=88.0,
        cross_source_support=0.0,
        single_source_support=1.0,
        unsupported_rate=0.0,
        hallucination_rate=0.0,
        average_evidence_per_requirement=1.0,
        average_sources_per_requirement=1.0,
        evidence_reuse_ratio=1.0,
        grounding_score=score,
    )


def make_summary(*, total: int = 1, supported: int = 1, score: int = 100) -> GroundingSummary:
    """A valid headline summary."""
    return GroundingSummary(
        total_requirements=total,
        supported=supported,
        partially_supported=0,
        unsupported=total - supported,
        grounding_score=score,
        verdict="All requirements grounded.",
    )


SUPPORTED = SupportClassification.SUPPORTED
STARTED = datetime(2026, 7, 11, 12, 0, 0, tzinfo=UTC)
COMPLETED = datetime(2026, 7, 11, 12, 0, 1, tzinfo=UTC)


def make_classification_result(
    *,
    text: str = "Set nosniff header.",
    classification: SupportClassification = SupportClassification.SUPPORTED,
    supporting_links: tuple[RequirementEvidenceLink, ...] | None = None,
):  # type: ignore[no-untyped-def]
    """A valid ClassificationResult (defaults to SUPPORTED with one direct link)."""
    from requirement_intelligence.grounding.classification import ClassificationResult
    from requirement_intelligence.grounding.identity import GroundedRequirementId

    links = (make_link(),) if supporting_links is None else supporting_links
    return ClassificationResult(
        requirement_id=GroundedRequirementId.for_requirement(SourceCategory.SECURITY, text),
        support_classification=classification,
        supporting_links=links,
        classification_reason="test",
    )
