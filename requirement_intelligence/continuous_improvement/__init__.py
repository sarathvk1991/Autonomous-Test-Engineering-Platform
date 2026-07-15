"""Continuous Improvement Framework (CAP-083A architecture; CAP-083B deterministic engine).

The first Layer 2 capability defined by ADR-0020 (Platform Evolution Roadmap) and
governed by ADR-0021 (Cross-Execution Data Architecture & Historical Intelligence
Constitution). It observes recurrence — recurring findings, trends, and
opportunities — across a **Historical Dataset**, never a single execution. It is
a **consumer of Historical Truth only** (ADR-0021 §Stage 8): it never imports a
Layer 1 subsystem, never re-runs Requirement Enhancement, Grounding, Validation,
CP1, Quality Governance, or Recommendation, and never reaches into the Execution
Package.

**Runtime status (CAP-083B):** ``DeterministicContinuousImprovementEngine``
detects recurring findings, observes trends, and generates opportunities entirely
from the governed ``ImprovementRuleCatalog`` and ``ImprovementPolicy`` —
deterministic, no AI, no heuristics beyond governed data. It resolves each
``HistoricalDatasetReference`` through a private, replaceable
``HistoricalDatasetProvider`` (the Historical Dataset Resolution Principle,
ADR-0022 §D9) and never recursively consumes a prior ``ContinuousImprovementResult``
or any of its constituents (Recommendation 11). The subsystem is still **not wired
into** any execution pipeline — nothing calls ``improve`` at runtime — so runtime
behaviour is byte-identical and the golden baseline is unchanged. Governed by
ADR-0022.
"""

from __future__ import annotations

from requirement_intelligence.continuous_improvement.continuous_improvement_service import (
    ContinuousImprovementService,
    DeterministicContinuousImprovementService,
)
from requirement_intelligence.continuous_improvement.engine import (
    DeterministicContinuousImprovementEngine,
    DeterministicHistoricalDatasetProvider,
    HistoricalDataset,
    HistoricalDatasetProvider,
    HistoricalExecutionRecord,
)
from requirement_intelligence.continuous_improvement.identity import (
    ContinuousImprovementFrameworkVersion,
    ContinuousImprovementResultId,
    ContinuousImprovementResultVersion,
    ImprovementAssessmentId,
    ImprovementAssessmentVersion,
    ImprovementEngineVersion,
    ImprovementFindingId,
    ImprovementOpportunityId,
    ImprovementPolicyId,
    ImprovementPolicyVersion,
    ImprovementRuleCatalogVersion,
    ImprovementRuleVersion,
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
from requirement_intelligence.continuous_improvement.rules import (
    IMPROVEMENT_RULE_CATALOG_VERSION,
    IMPROVEMENT_RULE_VERSION,
    ImprovementPolicyToggle,
    ImprovementRule,
    ImprovementRuleBuilder,
    ImprovementRuleCatalog,
    ImprovementRuleFamily,
    default_improvement_rule_catalog,
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
    "IMPROVEMENT_RULE_CATALOG_VERSION",
    "IMPROVEMENT_RULE_VERSION",
    "ContinuousImprovementFrameworkVersion",
    "ContinuousImprovementResult",
    "ContinuousImprovementResultId",
    "ContinuousImprovementResultVersion",
    "ContinuousImprovementService",
    "DeterministicContinuousImprovementEngine",
    "DeterministicContinuousImprovementService",
    "DeterministicHistoricalDatasetProvider",
    "HistoricalDataset",
    "HistoricalDatasetProvider",
    "HistoricalDatasetReference",
    "HistoricalExecutionRecord",
    "ImprovementAssessmentId",
    "ImprovementAssessmentVersion",
    "ImprovementCapabilitySwitches",
    "ImprovementEngineVersion",
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
    "ImprovementPolicyToggle",
    "ImprovementPolicyVersion",
    "ImprovementRule",
    "ImprovementRuleBuilder",
    "ImprovementRuleCatalog",
    "ImprovementRuleCatalogVersion",
    "ImprovementRuleFamily",
    "ImprovementRuleVersion",
    "ImprovementSeverity",
    "ImprovementSourceLayer",
    "ImprovementSummary",
    "ImprovementThresholds",
    "ImprovementTrend",
    "ImprovementTrendDirection",
    "ImprovementTrendId",
    "ImprovementTrendVersion",
    "default_improvement_policy",
    "default_improvement_rule_catalog",
]
