"""Continuous Improvement Framework (CAP-083A).

The first Layer 2 capability defined by ADR-0020 (Platform Evolution Roadmap) and
governed by ADR-0021 (Cross-Execution Data Architecture & Historical Intelligence
Constitution). It observes recurrence — recurring findings, trends, and
opportunities — across a **Historical Dataset**, never a single execution. It is
a **consumer of Historical Truth only** (ADR-0021 §Stage 8): it never imports a
Layer 1 subsystem, never re-runs Requirement Enhancement, Grounding, Validation,
CP1, Quality Governance, or Recommendation, and never reaches into the Execution
Package.

**Runtime status (CAP-083A):** architecture and governance freeze only. No
finding is derived, no trend is observed, no opportunity is generated, and
nothing is wired into a runtime path. ``DormantContinuousImprovementService``
raises ``NotImplementedError`` on every call. The subsystem is not wired into any
execution pipeline — nothing calls ``improve`` at runtime — so runtime behaviour
is byte-identical and the golden baseline is unchanged. Governed by ADR-0022.
"""

from __future__ import annotations

from requirement_intelligence.continuous_improvement.continuous_improvement_service import (
    ContinuousImprovementService,
    DormantContinuousImprovementService,
)
from requirement_intelligence.continuous_improvement.identity import (
    ContinuousImprovementFrameworkVersion,
    ContinuousImprovementResultId,
    ContinuousImprovementResultVersion,
    ImprovementAssessmentId,
    ImprovementAssessmentVersion,
    ImprovementFindingId,
    ImprovementOpportunityId,
    ImprovementPolicyId,
    ImprovementPolicyVersion,
    ImprovementTrendId,
    ImprovementTrendVersion,
)
from requirement_intelligence.continuous_improvement.models import (
    CONTINUOUS_IMPROVEMENT_RESULT_VERSION,
    ContinuousImprovementResult,
    HistoricalDatasetReference,
    ImprovementFinding,
    ImprovementFindingCategory,
    ImprovementMetrics,
    ImprovementOpportunity,
    ImprovementOpportunityCategory,
    ImprovementSeverity,
    ImprovementSourceLayer,
    ImprovementSummary,
    ImprovementTrend,
    ImprovementTrendDirection,
)
from requirement_intelligence.continuous_improvement.policy import (
    DEFAULT_IMPROVEMENT_POLICY_ID,
    ImprovementCapabilitySwitches,
    ImprovementPolicy,
    ImprovementPolicyBuilder,
    ImprovementThresholds,
    default_improvement_policy,
)
from requirement_intelligence.continuous_improvement.version import (
    CONTINUOUS_IMPROVEMENT_FRAMEWORK_VERSION,
    IMPROVEMENT_POLICY_VERSION,
)

__all__ = [
    "CONTINUOUS_IMPROVEMENT_FRAMEWORK_VERSION",
    "CONTINUOUS_IMPROVEMENT_RESULT_VERSION",
    "DEFAULT_IMPROVEMENT_POLICY_ID",
    "IMPROVEMENT_POLICY_VERSION",
    "ContinuousImprovementFrameworkVersion",
    "ContinuousImprovementResult",
    "ContinuousImprovementResultId",
    "ContinuousImprovementResultVersion",
    "ContinuousImprovementService",
    "DormantContinuousImprovementService",
    "HistoricalDatasetReference",
    "ImprovementAssessmentId",
    "ImprovementAssessmentVersion",
    "ImprovementCapabilitySwitches",
    "ImprovementFinding",
    "ImprovementFindingCategory",
    "ImprovementFindingId",
    "ImprovementMetrics",
    "ImprovementOpportunity",
    "ImprovementOpportunityCategory",
    "ImprovementOpportunityId",
    "ImprovementPolicy",
    "ImprovementPolicyBuilder",
    "ImprovementPolicyId",
    "ImprovementPolicyVersion",
    "ImprovementSeverity",
    "ImprovementSourceLayer",
    "ImprovementSummary",
    "ImprovementThresholds",
    "ImprovementTrend",
    "ImprovementTrendDirection",
    "ImprovementTrendId",
    "ImprovementTrendVersion",
    "default_improvement_policy",
]
