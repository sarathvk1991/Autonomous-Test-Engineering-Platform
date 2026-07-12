"""Quality Rule Evaluation (CAP-080A.1).

The layer between the governed ``QualityPolicy`` and the governance decision. It owns
rule evaluation, threshold comparison, policy interpretation, and evaluation
explanation — and nothing else (no orchestration, release decision, serialization,
reporting, Grounding, Validation, or CP1). Its frozen boundary is the
:class:`RuleEvaluationResult`, produced by the :class:`QualityRuleEvaluator`.

**CAP-080A.1 is the architecture freeze only:** canonical models, typed identities,
and the dormant evaluator contract. It performs no rule evaluation and is wired into
no runtime path. Governed by ADR-0017.
"""

from __future__ import annotations

from requirement_intelligence.quality_governance.evaluation.models import (
    RULE_EVALUATION_RESULT_VERSION,
    RULE_EVALUATION_VERSION,
    RuleCategory,
    RuleCategoryCount,
    RuleEvaluation,
    RuleEvaluationResult,
    RuleEvaluationStatistics,
    RuleEvaluationStatus,
    RuleEvaluationSummary,
    RuleSeverityCount,
)
from requirement_intelligence.quality_governance.evaluation.quality_rule_evaluator import (
    DormantQualityRuleEvaluator,
    QualityRuleEvaluator,
)

__all__ = [
    "RULE_EVALUATION_RESULT_VERSION",
    "RULE_EVALUATION_VERSION",
    "DormantQualityRuleEvaluator",
    "QualityRuleEvaluator",
    "RuleCategory",
    "RuleCategoryCount",
    "RuleEvaluation",
    "RuleEvaluationResult",
    "RuleEvaluationStatistics",
    "RuleEvaluationStatus",
    "RuleEvaluationSummary",
    "RuleSeverityCount",
]
