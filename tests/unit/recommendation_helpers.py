"""Shared construction helpers for Recommendation engine tests (CAP-082B).

Not a test module (no ``test_`` prefix, so pytest does not collect it). It builds
valid, tunable ``RequirementEnhancementResult`` / ``GroundingResult`` /
``ValidationResult`` / ``CP1Result`` / ``QualityGovernanceResult`` carriers so each
engine test states only the finding(s) it cares about. Mirrors
``tests/unit/quality_governance_helpers.py``, extended to also expose the actual
finding/issue objects the Recommendation engine reads (not just aggregate counts).
"""

from __future__ import annotations

from datetime import UTC, datetime

from requirement_intelligence.cp1.models import (
    CP1Finding,
    CP1FrameworkMetadata,
    CP1Input,
    CP1Result,
)
from requirement_intelligence.enhancement.identity.enhancement_identity import (
    RelationshipGraphId,
    RequirementEnhancementResultId,
)
from requirement_intelligence.enhancement.models.enums import (
    EnhancementSeverity,
    ObservationCategory,
)
from requirement_intelligence.enhancement.models.observations import (
    EnhancementFinding,
    RequirementObservation,
)
from requirement_intelligence.enhancement.models.relationships import RelationshipGraph
from requirement_intelligence.enhancement.models.result import RequirementEnhancementResult
from requirement_intelligence.enhancement.models.summary import (
    EnhancementMetrics,
    EnhancementSummary,
)
from requirement_intelligence.enhancement.policy import default_enhancement_policy
from requirement_intelligence.enhancement.version import ENHANCEMENT_FRAMEWORK_VERSION
from requirement_intelligence.grounding.identity import GroundedRequirementId, GroundingAssessmentId
from requirement_intelligence.grounding.models import (
    GroundingAssessment,
    GroundingMetrics,
    GroundingResult,
    GroundingSummary,
)
from requirement_intelligence.grounding.models.confidence import GroundingConfidence
from requirement_intelligence.grounding.models.enums import (
    ConfidenceBand,
    EvidenceRelation,
    SupportClassification,
)
from requirement_intelligence.grounding.models.evidence import (
    EvidenceReference,
    RequirementEvidenceLink,
)
from requirement_intelligence.grounding.models.explanation import GroundingExplanation
from requirement_intelligence.grounding.models.findings import GroundingFinding
from requirement_intelligence.grounding.models.grounded_requirement import GroundedRequirement
from requirement_intelligence.grounding.version import (
    GROUNDING_CONFIGURATION_VERSION,
    GROUNDING_FRAMEWORK_VERSION,
)
from requirement_intelligence.models.enums import SourceCategory
from requirement_intelligence.quality_governance.identity.quality_identity import (
    QualityAssessmentId,
    QualityGovernanceResultId,
)
from requirement_intelligence.quality_governance.models.assessment import QualityAssessment
from requirement_intelligence.quality_governance.models.enums import (
    QualityDecision,
    QualitySeverity,
)
from requirement_intelligence.quality_governance.models.findings import QualityFinding
from requirement_intelligence.quality_governance.models.result import QualityGovernanceResult
from requirement_intelligence.quality_governance.models.summary import QualitySummary
from requirement_intelligence.quality_governance.policy import default_quality_policy
from requirement_intelligence.quality_governance.version import QUALITY_GOVERNANCE_FRAMEWORK_VERSION
from requirement_intelligence.validation.models import (
    DEFAULT_VALIDATION_CONTRACT_VERSION,
    FRAMEWORK_VERSION,
    PIPELINE_VERSION,
    REGISTRY_VERSION,
    ValidationConfiguration,
    ValidationFrameworkMetadata,
    ValidationHealth,
    ValidationIssue,
    ValidationResult,
    ValidationStatistics,
    ValidationSummary,
)
from requirement_intelligence.validation.models import (
    ValidationVerdict as ValidationSubsystemVerdict,
)
from requirement_intelligence.validation.validation_rule_layer import ValidationLayer
from shared.enums.base import ValidationVerdict as CP1Verdict
from tests.unit.quality_governance_helpers import _analysis_result, _normalization_result

_TS = datetime(2026, 7, 14, 12, 0, 0, tzinfo=UTC)
_TS_END = datetime(2026, 7, 14, 12, 0, 1, tzinfo=UTC)

ANALYSIS_ID = "AN-REC-1"
EXECUTION_ID = "EX-REC-1"


# ---------------------------------------------------------------------------
# Requirement Enhancement
# ---------------------------------------------------------------------------


def make_enhancement_finding(
    finding_id: str,
    *,
    category: ObservationCategory,
    severity: EnhancementSeverity = EnhancementSeverity.WARNING,
) -> EnhancementFinding:
    """One surfaced enhancement finding, for engine dispatch tests."""
    return EnhancementFinding(
        finding_id=finding_id,
        observation_id=f"eo-{finding_id}",
        category=category,
        severity=severity,
        message=f"synthetic finding {finding_id}",
    )


def make_enhancement_result(
    *,
    findings: tuple[EnhancementFinding, ...] = (),
    analysis_id: str = ANALYSIS_ID,
    execution_id: str = EXECUTION_ID,
) -> RequirementEnhancementResult:
    """A minimal, valid enhancement result carrying exactly the given findings."""
    policy = default_enhancement_policy()
    summary = EnhancementSummary(
        policy_id=policy.policy_id,
        policy_version=policy.policy_version,
        total_requirements_enhanced=0,
        total_relationships=0,
        total_observations=len(findings),
        total_findings=len(findings),
        headline=f"{len(findings)} finding(s).",
    )
    metrics = EnhancementMetrics(
        enrichment_coverage=0.0, relationship_density=0.0, observation_rate=0.0
    )
    observations = tuple(
        RequirementObservation(
            observation_id=finding.observation_id,
            category=finding.category,
            severity=finding.severity,
            message=finding.message,
        )
        for finding in findings
    )
    return RequirementEnhancementResult(
        result_id=RequirementEnhancementResultId.for_enhancement(f"{analysis_id}:{execution_id}"),
        analysis_id=analysis_id,
        execution_id=execution_id,
        relationship_graph=RelationshipGraph(
            graph_id=RelationshipGraphId.for_enhancement(f"{analysis_id}:{execution_id}")
        ),
        observations=observations,
        findings=findings,
        summary=summary,
        metrics=metrics,
        policy_id=policy.policy_id,
        policy_version=policy.policy_version,
        framework_version=ENHANCEMENT_FRAMEWORK_VERSION,
        started_at=_TS,
        completed_at=_TS_END,
    )


# ---------------------------------------------------------------------------
# Grounding
# ---------------------------------------------------------------------------


def _grounded_requirement(
    requirement_id: str, classification: SupportClassification
) -> GroundedRequirement:
    evidence_links: tuple[RequirementEvidenceLink, ...] = ()
    if classification == SupportClassification.CONTRADICTED:
        evidence_links = (
            RequirementEvidenceLink(
                evidence=EvidenceReference(
                    source_system="jira",
                    source_record_id="SRC-1",
                    source_category=SourceCategory.FUNCTIONAL,
                    source_type="story",
                ),
                relation=EvidenceRelation.CONTRADICTING,
                match_score=50,
                rationale="synthetic contradiction",
            ),
        )
    return GroundedRequirement(
        requirement_id=GroundedRequirementId.for_requirement(
            SourceCategory.FUNCTIONAL, requirement_id
        ),
        domain=SourceCategory.FUNCTIONAL,
        text=requirement_id,
        position=0,
        classification=classification,
        confidence=GroundingConfidence(
            score=10,
            band=ConfidenceBand.LOW,
            configuration_version=GROUNDING_CONFIGURATION_VERSION,
            framework_version=GROUNDING_FRAMEWORK_VERSION,
        ),
        evidence_links=evidence_links,
        explanation=GroundingExplanation(summary=f"synthetic explanation for {requirement_id}"),
    )


def make_grounding_finding(
    finding_id: str, *, classification: SupportClassification
) -> tuple[GroundingFinding, GroundedRequirement]:
    """One grounding finding plus the grounded requirement it must reference."""
    requirement = _grounded_requirement(finding_id, classification)
    finding = GroundingFinding(
        finding_id=finding_id,
        requirement_id=requirement.requirement_id,
        classification=classification,
        severity="critical" if classification == SupportClassification.CONTRADICTED else "warning",
        message=f"synthetic finding {finding_id}",
    )
    return finding, requirement


def make_grounding_result(
    *,
    findings: tuple[GroundingFinding, ...] = (),
    grounded_requirements: tuple[GroundedRequirement, ...] = (),
    analysis_id: str = ANALYSIS_ID,
    execution_id: str = EXECUTION_ID,
) -> GroundingResult:
    """A minimal, valid grounding result carrying exactly the given findings."""
    metrics = GroundingMetrics(
        total_requirements=len(grounded_requirements),
        grounded_requirements=len(grounded_requirements),
        unsupported_requirements=len(findings),
        grounding_coverage=1.0,
        evidence_coverage=0.9,
        requirement_coverage=1.0,
        evidence_utilization=1.0,
        traceability_completeness=1.0,
        average_confidence=85.0,
        cross_source_support=0.0,
        single_source_support=0.0,
        unsupported_rate=0.0,
        hallucination_rate=0.0,
        average_evidence_per_requirement=0.0,
        average_sources_per_requirement=0.0,
        evidence_reuse_ratio=0.0,
        grounding_score=90,
    )
    summary = GroundingSummary(
        total_requirements=len(grounded_requirements),
        supported=len(grounded_requirements) - len(findings),
        partially_supported=0,
        unsupported=len(findings),
        grounding_score=90,
        verdict="synthetic run",
    )
    assessment = GroundingAssessment(
        assessment_id=GroundingAssessmentId.for_run("ctx-rec-1", f"{analysis_id}:{execution_id}"),
        context_id="ctx-rec-1",
        grounded_requirements=grounded_requirements,
        findings=findings,
        metrics=metrics,
        summary=summary,
        framework_version=GROUNDING_FRAMEWORK_VERSION,
        configuration_version=GROUNDING_CONFIGURATION_VERSION,
    )
    return GroundingResult(
        analysis_id=analysis_id,
        execution_id=execution_id,
        assessment=assessment,
        framework_version=GROUNDING_FRAMEWORK_VERSION,
        configuration_version=GROUNDING_CONFIGURATION_VERSION,
        started_at=_TS,
        completed_at=_TS_END,
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def make_validation_issue(issue_id: str, *, severity: str = "warning") -> ValidationIssue:
    """One validation issue, for engine dispatch tests."""
    return ValidationIssue(
        issue_id=issue_id,
        category="structure",
        severity=severity,
        validation_layer=ValidationLayer.CONTENT,
        rule_id="RULE-1",
        rule_version="1.0",
        message=f"synthetic issue {issue_id}",
        location="functionalRequirements[0]",
        recommendation="fix it",
        blocking=False,
        correlation_id=EXECUTION_ID,
        created_at=_TS,
    )


def make_validation_result(
    *,
    issues: tuple[ValidationIssue, ...] = (),
    verdict: ValidationSubsystemVerdict = ValidationSubsystemVerdict.PASSED,
    analysis_id: str = ANALYSIS_ID,
    execution_id: str = EXECUTION_ID,
) -> ValidationResult:
    """A minimal, valid validation result carrying exactly the given issues."""
    summary = ValidationSummary(
        total_issues=len(issues),
        info_count=0,
        warning_count=0,
        error_count=0,
        critical_count=0,
        blocking_issue_count=0,
        overall_health=ValidationHealth.HEALTHY,
    )
    statistics = ValidationStatistics(
        validation_duration_ms=1.0,
        rules_executed=1,
        rules_passed=1,
        rules_failed=0,
        started_at=_TS,
        completed_at=_TS,
        validator_version=FRAMEWORK_VERSION,
        validation_contract_version=DEFAULT_VALIDATION_CONTRACT_VERSION,
        execution_id=execution_id,
    )
    framework_metadata = ValidationFrameworkMetadata(
        framework_version=FRAMEWORK_VERSION,
        validation_contract_version=DEFAULT_VALIDATION_CONTRACT_VERSION,
        pipeline_version=PIPELINE_VERSION,
        registry_version=REGISTRY_VERSION,
    )
    return ValidationResult(
        validation_id="VAL-REC-1",
        execution_id=execution_id,
        analysis_id=analysis_id,
        analysis_result=_analysis_result(execution_id, analysis_id),
        validation_summary=summary,
        validation_statistics=statistics,
        validation_issues=issues,
        validation_configuration=ValidationConfiguration(),
        validation_framework_metadata=framework_metadata,
        overall_verdict=verdict,
        started_at=_TS,
        completed_at=_TS,
    )


# ---------------------------------------------------------------------------
# CP1
# ---------------------------------------------------------------------------


def make_cp1_finding(finding_id: str, *, verdict: CP1Verdict) -> CP1Finding:
    """One CP1 finding, for engine dispatch tests."""
    return CP1Finding(
        finding_id=finding_id,
        criterion_id="CP1-0001",
        criterion_version="1.0",
        verdict_contribution=verdict,
        message=f"synthetic finding {finding_id}",
        location="functionalRequirements[0]",
        recommendation="fix it",
        correlation_id=EXECUTION_ID,
        created_at=_TS,
    )


def make_cp1_result(
    *,
    findings: tuple[CP1Finding, ...] = (),
    verdict: CP1Verdict = CP1Verdict.PASS,
    analysis_id: str = ANALYSIS_ID,
    execution_id: str = EXECUTION_ID,
) -> CP1Result:
    """A minimal, valid CP1 result carrying exactly the given findings."""
    analysis = _analysis_result(execution_id, analysis_id)
    cp1_input = CP1Input(
        validation_result=make_validation_result(
            analysis_id=analysis_id, execution_id=execution_id
        ),
        normalization_result=_normalization_result(analysis),
    )
    return CP1Result(
        cp1_id="CP1-REC-1",
        validation_id="VAL-REC-1",
        execution_id=execution_id,
        analysis_id=analysis_id,
        cp1_input=cp1_input,
        findings=findings,
        framework_metadata=CP1FrameworkMetadata(
            framework_version="1.0.0",
            criteria_contract_version="1.0",
            pipeline_version="1.0.0",
            registry_version="1.0.0",
        ),
        overall_verdict=verdict,
        started_at=_TS,
        completed_at=_TS_END,
    )


# ---------------------------------------------------------------------------
# Quality Governance
# ---------------------------------------------------------------------------


def make_quality_finding(
    finding_id: str, *, severity: QualitySeverity = QualitySeverity.WARNING
) -> QualityFinding:
    """One quality finding, for engine dispatch tests."""
    return QualityFinding(
        finding_id=finding_id,
        category="hallucination_rate_exceeded",
        severity=severity,
        source="grounding",
        message=f"synthetic finding {finding_id}",
    )


def make_quality_governance_result(
    *,
    findings: tuple[QualityFinding, ...] = (),
    decision: QualityDecision = QualityDecision.PASS,
    analysis_id: str = ANALYSIS_ID,
    execution_id: str = EXECUTION_ID,
) -> QualityGovernanceResult:
    """A minimal, valid quality governance result with the given findings/decision.

    The decision and findings must satisfy ``QualityAssessment``'s explainability
    invariant: PASS carries no WARNING/FAILURE findings, PASS_WITH_WARNINGS requires
    at least one WARNING and no FAILURE, and FAIL requires at least one FAILURE.
    """
    policy = default_quality_policy()
    warnings = sum(1 for f in findings if QualitySeverity(f.severity) == QualitySeverity.WARNING)
    failures = sum(1 for f in findings if QualitySeverity(f.severity) == QualitySeverity.FAILURE)
    assessment_id = QualityAssessmentId.for_run(analysis_id, execution_id)
    summary = QualitySummary(
        decision=decision,
        overall_quality_score=100 if decision == QualityDecision.PASS else 60,
        policy_id=policy.policy_id,
        policy_version=policy.policy_version,
        total_findings=len(findings),
        warning_count=warnings,
        failure_count=failures,
        verdict=f"{len(findings)} finding(s), decision={decision}.",
    )
    assessment = QualityAssessment(
        assessment_id=assessment_id,
        analysis_id=analysis_id,
        execution_id=execution_id,
        decision=decision,
        findings=findings,
        summary=summary,
        policy_id=policy.policy_id,
        policy_version=policy.policy_version,
        framework_version=QUALITY_GOVERNANCE_FRAMEWORK_VERSION,
    )
    return QualityGovernanceResult(
        result_id=QualityGovernanceResultId.for_assessment(str(assessment_id)),
        analysis_id=analysis_id,
        execution_id=execution_id,
        assessment=assessment,
        policy_id=policy.policy_id,
        policy_version=policy.policy_version,
        framework_version=QUALITY_GOVERNANCE_FRAMEWORK_VERSION,
        started_at=_TS,
        completed_at=_TS_END,
    )
