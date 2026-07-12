"""The governed Quality Rule Catalogue (CAP-080B).

The canonical, metadata-only declaration of *which* quality rules the framework
governs. It owns rule metadata, ordering, lookup, and grouping — and nothing else: no
threshold value, no comparison, no evaluation. The
:class:`~requirement_intelligence.quality_governance.evaluation.quality_rule_evaluator.DeterministicQualityRuleEvaluator`
iterates the catalogue and owns all behaviour (ADR-0017 §D25).

Adding, removing, or retuning a rule is a versioned catalogue change (a
:class:`QualityRuleBuilder` edit), never an evaluator code change (ADR-0017
Recommendation 2).
"""

from __future__ import annotations

from requirement_intelligence.quality_governance.rules.quality_rule import (
    QUALITY_RULE_VERSION,
    QualityMetric,
    QualityMetricSubsystem,
    QualityReleaseToggle,
    QualityRule,
    QualityThresholdRef,
    RuleComparator,
    RuleType,
)
from requirement_intelligence.quality_governance.rules.quality_rule_builder import (
    QualityRuleBuilder,
    default_quality_rule_catalog,
)
from requirement_intelligence.quality_governance.rules.quality_rule_catalog import (
    QUALITY_RULE_CATALOG_VERSION,
    QualityRuleCatalog,
)

__all__ = [
    "QUALITY_RULE_CATALOG_VERSION",
    "QUALITY_RULE_VERSION",
    "QualityMetric",
    "QualityMetricSubsystem",
    "QualityReleaseToggle",
    "QualityRule",
    "QualityRuleBuilder",
    "QualityRuleCatalog",
    "QualityThresholdRef",
    "RuleComparator",
    "RuleType",
    "default_quality_rule_catalog",
]
