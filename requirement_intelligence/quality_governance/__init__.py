"""Quality Governance Framework (CAP-080).

The governed subsystem that owns Quality Governance for a Requirement Intelligence
run: policy evaluation, quality assessment, release decisions, and governance
findings. It is a **consumer only** of the three completed peer results —
``GroundingResult``, ``ValidationResult``, ``CP1Result`` — and owns none of the
Engineering Context, Analysis, Grounding, Validation, CP1, Execution Package,
Reporting, or Serialization upstream of it (ADR-0017).

**CAP-080A is the architecture freeze only:** canonical models, typed identities,
enumerations, the governed :class:`QualityPolicy` and its builder, and the dormant
:class:`QualityGovernanceService` contract. It performs no policy evaluation, no
quality calculation, and no release decision, and it is wired into no runtime path.
Governed by ADR-0017.
"""

from __future__ import annotations

from requirement_intelligence.quality_governance.evaluation import (
    RULE_EVALUATION_RESULT_VERSION,
    RULE_EVALUATION_VERSION,
    DormantQualityRuleEvaluator,
    QualityRuleEvaluator,
    RuleCategory,
    RuleCategoryCount,
    RuleEvaluation,
    RuleEvaluationResult,
    RuleEvaluationStatistics,
    RuleEvaluationStatus,
    RuleEvaluationSummary,
    RuleSeverityCount,
)
from requirement_intelligence.quality_governance.identity import (
    QualityAssessmentId,
    QualityAssessmentVersion,
    QualityGovernanceResultId,
    QualityGovernanceResultVersion,
    QualityGovernanceVersion,
    QualityPolicyId,
    QualityPolicyVersion,
    RuleEvaluationId,
    RuleEvaluationResultId,
    RuleEvaluationResultVersion,
    RuleEvaluationVersion,
)
from requirement_intelligence.quality_governance.models import (
    QUALITY_ASSESSMENT_VERSION,
    QUALITY_GOVERNANCE_RESULT_VERSION,
    ConsumedResultReference,
    QualityAssessment,
    QualityDecision,
    QualityFinding,
    QualityFindingCategory,
    QualityFindingCategoryCount,
    QualityGovernanceResult,
    QualityInputSource,
    QualitySeverity,
    QualitySummary,
)
from requirement_intelligence.quality_governance.policy import (
    DEFAULT_QUALITY_POLICY_ID,
    QualityPolicy,
    QualityPolicyBuilder,
    QualityReleaseRules,
    QualitySeverityThresholds,
    QualityThresholds,
    default_quality_policy,
)
from requirement_intelligence.quality_governance.quality_governance_service import (
    DormantQualityGovernanceService,
    QualityGovernanceService,
)
from requirement_intelligence.quality_governance.version import (
    QUALITY_GOVERNANCE_FRAMEWORK_VERSION,
    QUALITY_POLICY_VERSION,
)

__all__ = [
    "DEFAULT_QUALITY_POLICY_ID",
    "QUALITY_ASSESSMENT_VERSION",
    "QUALITY_GOVERNANCE_FRAMEWORK_VERSION",
    "QUALITY_GOVERNANCE_RESULT_VERSION",
    "QUALITY_POLICY_VERSION",
    "RULE_EVALUATION_RESULT_VERSION",
    "RULE_EVALUATION_VERSION",
    "ConsumedResultReference",
    "DormantQualityGovernanceService",
    "DormantQualityRuleEvaluator",
    "QualityAssessment",
    "QualityAssessmentId",
    "QualityAssessmentVersion",
    "QualityDecision",
    "QualityFinding",
    "QualityFindingCategory",
    "QualityFindingCategoryCount",
    "QualityGovernanceResult",
    "QualityGovernanceResultId",
    "QualityGovernanceResultVersion",
    "QualityGovernanceService",
    "QualityGovernanceVersion",
    "QualityInputSource",
    "QualityPolicy",
    "QualityPolicyBuilder",
    "QualityPolicyId",
    "QualityPolicyVersion",
    "QualityReleaseRules",
    "QualityRuleEvaluator",
    "QualitySeverity",
    "QualitySeverityThresholds",
    "QualitySummary",
    "QualityThresholds",
    "RuleCategory",
    "RuleCategoryCount",
    "RuleEvaluation",
    "RuleEvaluationId",
    "RuleEvaluationResult",
    "RuleEvaluationResultId",
    "RuleEvaluationResultVersion",
    "RuleEvaluationStatistics",
    "RuleEvaluationStatus",
    "RuleEvaluationSummary",
    "RuleEvaluationVersion",
    "RuleSeverityCount",
    "default_quality_policy",
]
