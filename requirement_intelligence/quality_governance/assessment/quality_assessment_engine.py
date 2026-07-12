"""QualityAssessmentEngine — the single owner of quality assessment (CAP-080A.2).

Architecture (ADR-0017 D21)
---------------------------
The ``QualityAssessmentEngine`` owns **assessment** — interpreting a completed
:class:`RuleEvaluationResult` into a :class:`QualityAssessmentResult`. It sits between
Rule Evaluation and Governance:

    RuleEvaluationResult ─▶ QualityAssessmentEngine.assess ─▶ QualityAssessmentResult
                                                                     │
                                (future Decision layer, ADR-0017 §D22)│
                                                                     ▼
                                       QualityGovernanceService ─▶ QualityGovernanceResult

What the engine owns
    interpretation of a ``RuleEvaluationResult``, assessment logic, assessment
    explanation — and nothing else.

What the engine does NOT own
    rule evaluation, governance orchestration, the release decision (reserved for the
    future Decision layer, ADR-0017 §D22, Recommendation 1/2), serialization,
    reporting, the execution package, and runtime wiring.

Consumes only ``RuleEvaluationResult`` (frozen, ADR-0017 §D21)
    Unlike the rule evaluator, the assessment engine does **not** read
    ``GroundingResult`` / ``ValidationResult`` / ``CP1Result`` — those are already
    interpreted into the ``RuleEvaluationResult``. It re-runs nothing, inspects no
    upstream runtime, and imports no upstream *implementation* class.

One contract, many future engines (frozen, ADR-0017 Recommendation 5)
    The signature ``assess(rule_evaluation_result) -> QualityAssessmentResult`` is
    permanent. Deterministic, risk-weighted, statistical, regulatory, and AI-assisted
    assessment engines all implement it unchanged.

Runtime status (CAP-080A.2)
    ``assess`` is **abstract** and the registered :class:`DormantQualityAssessmentEngine`
    raises :class:`NotImplementedError`. The engine is **dormant** — no runtime path
    consumes it, and ``PlatformContext`` constructs it with the governed assessment
    policy but no interpretation logic. Runtime behaviour is byte-identical and the
    golden baseline is unchanged.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from requirement_intelligence.quality_governance.assessment.models import QualityAssessmentResult
from requirement_intelligence.quality_governance.assessment.policy import AssessmentPolicy
from requirement_intelligence.quality_governance.evaluation.models import RuleEvaluationResult


class QualityAssessmentEngine(ABC):
    """The permanent contract for assessing one completed rule evaluation.

    A single public method, ``assess``, interprets a :class:`RuleEvaluationResult`
    under the governed :class:`AssessmentPolicy` and returns a
    :class:`QualityAssessmentResult` of pure observations. Implementations own
    assessment only; they make no release decision and own no orchestration.
    """

    @abstractmethod
    def assess(self, rule_evaluation_result: RuleEvaluationResult) -> QualityAssessmentResult:
        """Assess *rule_evaluation_result* into a :class:`QualityAssessmentResult`.

        Parameters
        ----------
        rule_evaluation_result:
            The completed, frozen output of the ``QualityRuleEvaluator`` — the only
            input the assessment layer reads.

        Returns
        -------
        QualityAssessmentResult
            The self-contained interpretation — observations only, no release decision.

        Notes
        -----
        Abstract in CAP-080A.2; the first assessment engine is wired behind this
        unchanged signature in a later CAP-080 milestone.
        """
        raise NotImplementedError


class DormantQualityAssessmentEngine(QualityAssessmentEngine):
    """The registered, dormant assessment engine (CAP-080A.2).

    It holds the governed :class:`AssessmentPolicy` it will interpret under but performs
    no assessment: ``assess`` raises :class:`NotImplementedError`. It exists so the
    boundary and its ``PlatformContext`` registration are fixed before any behaviour,
    exactly as the dormant rule evaluator was at CAP-080A.1. No runtime path consumes
    it, so runtime is byte-identical.
    """

    def __init__(self, policy: AssessmentPolicy) -> None:
        """Store the governed policy the future engine will interpret under."""
        self._policy = policy

    @property
    def policy(self) -> AssessmentPolicy:
        """The governed assessment policy this dormant engine was constructed with."""
        return self._policy

    def assess(self, rule_evaluation_result: RuleEvaluationResult) -> QualityAssessmentResult:
        """Dormant in CAP-080A.2 — the first assessment engine lands in a later milestone."""
        raise NotImplementedError(
            "QualityAssessmentEngine.assess is dormant in CAP-080A.2; the first "
            "assessment engine is introduced in a later CAP-080 milestone."
        )
