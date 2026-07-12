"""Quality Decision (CAP-080A.3).

The final governed layer before Governance. It owns the release decision, governance
decision explanation, and decision-policy interpretation — and nothing else (no rule
evaluation, assessment, orchestration, serialization, reporting, or execution package).
Its frozen boundary is the :class:`QualityDecisionResult`, produced by the
:class:`QualityDecisionEngine`, which is the **sole owner** of ``PASS`` /
``PASS_WITH_WARNINGS`` / ``FAIL``.

**CAP-080A.3 is the architecture freeze only:** canonical models, the governed
:class:`DecisionPolicy`, and the dormant engine contract. It performs no decision and is
wired into no runtime path. Governed by ADR-0017.
"""

from __future__ import annotations

from requirement_intelligence.quality_governance.decision.models import (
    DECISION_VERSION,
    QUALITY_DECISION_RESULT_VERSION,
    DecisionExplanation,
    DecisionStatistics,
    DecisionSummary,
    QualityDecisionResult,
)
from requirement_intelligence.quality_governance.decision.policy import (
    DECISION_POLICY_VERSION,
    DEFAULT_DECISION_POLICY_ID,
    DecisionPolicy,
    DecisionRule,
)
from requirement_intelligence.quality_governance.decision.policy_builder import (
    DecisionPolicyBuilder,
    default_decision_policy,
)
from requirement_intelligence.quality_governance.decision.quality_decision_engine import (
    DeterministicQualityDecisionEngine,
    QualityDecisionEngine,
)

__all__ = [
    "DECISION_POLICY_VERSION",
    "DECISION_VERSION",
    "DEFAULT_DECISION_POLICY_ID",
    "QUALITY_DECISION_RESULT_VERSION",
    "DecisionExplanation",
    "DecisionPolicy",
    "DecisionPolicyBuilder",
    "DecisionRule",
    "DecisionStatistics",
    "DecisionSummary",
    "DeterministicQualityDecisionEngine",
    "QualityDecisionEngine",
    "QualityDecisionResult",
    "default_decision_policy",
]
