"""QualityRuleEvaluator — the single owner of governance rule evaluation (CAP-080A.1).

Architecture (ADR-0017 D17-D20)
-------------------------------
The ``QualityRuleEvaluator`` owns **behaviour**; the ``QualityGovernanceService``
owns **sequencing**. This is the deliberate split frozen by CAP-080A.1:

    GroundingResult ┐
    ValidationResult├─▶ QualityRuleEvaluator.evaluate ─▶ RuleEvaluationResult
    CP1Result       ┘                                          │
                                                               ▼
                              QualityGovernanceService.evaluate ─▶ QualityGovernanceResult

The evaluator reads the three completed peer results and the governed
:class:`QualityPolicy`, evaluates each governed rule (threshold comparison,
mandatory-rule evaluation), and produces a :class:`RuleEvaluationResult` of pure
observations. It owns **only** that.

What the evaluator does NOT own
    governance orchestration, the release decision, quality scoring, serialization,
    reporting, the execution package, builders, Grounding, Validation, and CP1. Each
    is a separate owner (ADR-0017 D18).

Consumer only (frozen, ADR-0017 Recommendation 1/5)
    ``evaluate`` consumes only ``GroundingResult`` / ``ValidationResult`` /
    ``CP1Result`` — never re-running the subsystems that produce them, never inspecting
    prompts, the Engineering Context, or Gemini responses, and never importing an
    upstream *implementation* class.

One contract, many future evaluators (frozen, ADR-0017 Recommendation 5)
    The signature ``evaluate(grounding_result, validation_result, cp1_result) ->
    RuleEvaluationResult`` is permanent. Deterministic (CAP-080B), statistical,
    organization-specific, regulatory, risk-weighted, and hybrid evaluators all
    implement it unchanged.

Runtime status (CAP-080A.1)
    ``evaluate`` is **abstract** and the registered :class:`DormantQualityRuleEvaluator`
    raises :class:`NotImplementedError`. The evaluator is **dormant** — no runtime
    path consumes it, and ``PlatformContext`` constructs it with the governed policy
    but no rule set. Runtime behaviour is byte-identical and the golden baseline is
    unchanged. The first real evaluator lands in CAP-080B behind this unchanged
    signature.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from requirement_intelligence.cp1.models.cp1_result import CP1Result
from requirement_intelligence.grounding.models import GroundingResult
from requirement_intelligence.quality_governance.evaluation.models import RuleEvaluationResult
from requirement_intelligence.quality_governance.policy import QualityPolicy
from requirement_intelligence.validation.models.validation_result import ValidationResult


class QualityRuleEvaluator(ABC):
    """The permanent contract for evaluating governed quality rules over one run.

    A single public method, ``evaluate``, judges the completed upstream results against
    the governed :class:`QualityPolicy` and returns a :class:`RuleEvaluationResult` of
    pure observations. Implementations own rule evaluation only; they make no release
    decision, compute no quality score, and own no orchestration.
    """

    @abstractmethod
    def evaluate(
        self,
        grounding_result: GroundingResult,
        validation_result: ValidationResult,
        cp1_result: CP1Result,
    ) -> RuleEvaluationResult:
        """Evaluate the governed rules over the completed *grounding*/*validation*/*cp1* results.

        Parameters
        ----------
        grounding_result:
            The completed grounding assessment for the run.
        validation_result:
            The completed structural/reasoning validation verdict for the run.
        cp1_result:
            The completed engineering-readiness verdict for the run.

        Returns
        -------
        RuleEvaluationResult
            The self-contained record of every evaluated rule — observations only, no
            score and no decision.

        Notes
        -----
        Abstract in CAP-080A.1; the first evaluator is wired behind this unchanged
        signature in CAP-080B.
        """
        raise NotImplementedError


class DormantQualityRuleEvaluator(QualityRuleEvaluator):
    """The registered, dormant rule evaluator (CAP-080A.1).

    It holds the governed :class:`QualityPolicy` whose rules it will evaluate but
    performs no evaluation: ``evaluate`` raises :class:`NotImplementedError`. It exists
    so the boundary and its ``PlatformContext`` registration are fixed before any
    behaviour, exactly as the dormant governance service was at CAP-080A. No runtime
    path consumes it, so runtime is byte-identical.
    """

    def __init__(self, policy: QualityPolicy) -> None:
        """Store the governed policy whose rules the future evaluator will evaluate."""
        self._policy = policy

    @property
    def policy(self) -> QualityPolicy:
        """The governed quality policy this dormant evaluator was constructed with."""
        return self._policy

    def evaluate(
        self,
        grounding_result: GroundingResult,
        validation_result: ValidationResult,
        cp1_result: CP1Result,
    ) -> RuleEvaluationResult:
        """Dormant in CAP-080A.1 — the first rule evaluator lands in CAP-080B."""
        raise NotImplementedError(
            "QualityRuleEvaluator.evaluate is dormant in CAP-080A.1; the first rule "
            "evaluator is introduced in CAP-080B."
        )
