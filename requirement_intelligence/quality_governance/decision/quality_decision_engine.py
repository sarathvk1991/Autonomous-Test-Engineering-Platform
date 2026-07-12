"""QualityDecisionEngine — the single owner of the release decision (CAP-080A.3).

Architecture (ADR-0017 D23)
---------------------------
The ``QualityDecisionEngine`` owns the **release decision** — deriving a
:class:`QualityDecision` (``PASS`` / ``PASS_WITH_WARNINGS`` / ``FAIL``) from a
completed :class:`QualityAssessmentResult`. It is the final governed layer before
Governance:

    QualityAssessmentResult ─▶ QualityDecisionEngine.decide ─▶ QualityDecisionResult
                                                                     │
                                       QualityGovernanceService ─▶ QualityGovernanceResult

What the engine owns
    the release decision, governance decision explanation, and decision-policy
    interpretation — and nothing else.

What the engine does NOT own
    rule evaluation, assessment, orchestration, serialization, reporting, the execution
    package, and runtime wiring. The ``QualityGovernanceService`` orchestrates and
    assembles; it never derives ``PASS`` / ``FAIL`` (ADR-0017 Recommendation 6/7).

Consumes only ``QualityAssessmentResult`` (frozen, ADR-0017 §D23, Recommendation 1)
    The engine reads **only** the assessment result — never ``RuleEvaluationResult``,
    ``GroundingResult``, ``ValidationResult``, or ``CP1Result``, and no upstream
    *implementation* class. Those are already interpreted upstream.

Sole owner of the decision (frozen, ADR-0017 Recommendation 2)
    Only this engine derives ``PASS`` / ``PASS_WITH_WARNINGS`` / ``FAIL``. Assessment
    stays observational; the service assembles.

One contract, many future engines (frozen, ADR-0017 Recommendation 5)
    The signature ``decide(quality_assessment_result) -> QualityDecisionResult`` is
    permanent. Deterministic, statistical, regulatory, organization-specific, and
    AI-assisted decision engines all implement it unchanged.

Runtime status (CAP-080A.3)
    ``decide`` is **abstract** and the registered :class:`DormantQualityDecisionEngine`
    raises :class:`NotImplementedError`. The engine is **dormant** — no runtime path
    consumes it, and ``PlatformContext`` constructs it with the governed decision policy
    but no decision logic. Runtime behaviour is byte-identical and the golden baseline is
    unchanged.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from requirement_intelligence.quality_governance.assessment.models import QualityAssessmentResult
from requirement_intelligence.quality_governance.decision.models import QualityDecisionResult
from requirement_intelligence.quality_governance.decision.policy import DecisionPolicy


class QualityDecisionEngine(ABC):
    """The permanent contract for deciding one release from a completed assessment.

    A single public method, ``decide``, derives a :class:`QualityDecision` from a
    :class:`QualityAssessmentResult` under the governed :class:`DecisionPolicy` and
    returns a :class:`QualityDecisionResult`. Implementations own the decision only; they
    make no assessment, own no orchestration, and assemble no governance result.
    """

    @abstractmethod
    def decide(self, quality_assessment_result: QualityAssessmentResult) -> QualityDecisionResult:
        """Decide the release from *quality_assessment_result*.

        Parameters
        ----------
        quality_assessment_result:
            The completed, frozen output of the ``QualityAssessmentEngine`` — the only
            input the decision layer reads.

        Returns
        -------
        QualityDecisionResult
            The self-contained release decision, fully explainable on its own.

        Notes
        -----
        Abstract in CAP-080A.3; the first decision engine is wired behind this unchanged
        signature in a later CAP-080 milestone.
        """
        raise NotImplementedError


class DormantQualityDecisionEngine(QualityDecisionEngine):
    """The registered, dormant decision engine (CAP-080A.3).

    It holds the governed :class:`DecisionPolicy` it will decide under but performs no
    decision: ``decide`` raises :class:`NotImplementedError`. It exists so the boundary
    and its ``PlatformContext`` registration are fixed before any behaviour, exactly as
    the dormant assessment engine was at CAP-080A.2. No runtime path consumes it, so
    runtime is byte-identical.
    """

    def __init__(self, policy: DecisionPolicy) -> None:
        """Store the governed policy the future engine will decide under."""
        self._policy = policy

    @property
    def policy(self) -> DecisionPolicy:
        """The governed decision policy this dormant engine was constructed with."""
        return self._policy

    def decide(self, quality_assessment_result: QualityAssessmentResult) -> QualityDecisionResult:
        """Dormant in CAP-080A.3 — the first decision engine lands in a later milestone."""
        raise NotImplementedError(
            "QualityDecisionEngine.decide is dormant in CAP-080A.3; the first decision "
            "engine is introduced in a later CAP-080 milestone."
        )
