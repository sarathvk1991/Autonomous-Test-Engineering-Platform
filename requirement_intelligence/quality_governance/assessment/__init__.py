"""Quality Assessment (CAP-080A.2).

The layer between Rule Evaluation and Quality Governance. It owns interpretation of a
``RuleEvaluationResult``, assessment logic, and assessment explanation — and nothing
else (no rule evaluation, governance orchestration, release decision, serialization,
reporting, or execution package). Its frozen boundary is the
:class:`QualityAssessmentResult`, produced by the :class:`QualityAssessmentEngine`.

**CAP-080A.2 is the architecture freeze only:** canonical models, the governed
:class:`AssessmentPolicy`, and the dormant engine contract. It performs no assessment
and is wired into no runtime path. Governed by ADR-0017.
"""

from __future__ import annotations

from requirement_intelligence.quality_governance.assessment.models import (
    ASSESSMENT_OUTCOME_VERSION,
    QUALITY_ASSESSMENT_RESULT_VERSION,
    AssessmentDistributionEntry,
    AssessmentFindingReference,
    AssessmentLevel,
    AssessmentOutcome,
    AssessmentStatistics,
    AssessmentSummary,
    QualityAssessmentResult,
)
from requirement_intelligence.quality_governance.assessment.policy import (
    ASSESSMENT_POLICY_VERSION,
    DEFAULT_ASSESSMENT_POLICY_ID,
    AssessmentConflictPolicy,
    AssessmentPolicy,
    AssessmentWeights,
)
from requirement_intelligence.quality_governance.assessment.policy_builder import (
    AssessmentPolicyBuilder,
    default_assessment_policy,
)
from requirement_intelligence.quality_governance.assessment.quality_assessment_engine import (
    DeterministicQualityAssessmentEngine,
    QualityAssessmentEngine,
)

__all__ = [
    "ASSESSMENT_OUTCOME_VERSION",
    "ASSESSMENT_POLICY_VERSION",
    "DEFAULT_ASSESSMENT_POLICY_ID",
    "QUALITY_ASSESSMENT_RESULT_VERSION",
    "AssessmentConflictPolicy",
    "AssessmentDistributionEntry",
    "AssessmentFindingReference",
    "AssessmentLevel",
    "AssessmentOutcome",
    "AssessmentPolicy",
    "AssessmentPolicyBuilder",
    "AssessmentStatistics",
    "AssessmentSummary",
    "AssessmentWeights",
    "DeterministicQualityAssessmentEngine",
    "QualityAssessmentEngine",
    "QualityAssessmentResult",
    "default_assessment_policy",
]
