"""The private :class:`QualityGovernancePipeline` — the frozen stage sequencer (CAP-080C).

An internal implementation detail behind :meth:`QualityGovernanceService.evaluate`. It
owns **sequencing only** — ordering and delegation — and computes nothing itself: every
stage is a governed collaborator it invokes. It is **not public**, is **not** in the
package ``__all__``, and is **not** registered as a ``PlatformContext`` factory; the
composition root constructs it inside ``create_quality_governance_service`` and injects it
into the service (ADR-0017 §D29, Recommendation 1).

Frozen execution order (ADR-0017 §D29)::

    GroundingResult + ValidationResult + CP1Result
      → QualityRuleEvaluator.evaluate    → RuleEvaluationResult
      → QualityAssessmentEngine.assess    → QualityAssessmentResult
      → QualityDecisionEngine.decide      → QualityDecisionResult
      → QualityGovernanceResultBuilder.build → QualityGovernanceResult

No stage may be reordered, skipped, or absorb another's responsibility. Processing is
**sequential and deterministic** (no parallelism, no randomness, no UUIDs); the
``started_at`` / ``completed_at`` provenance comes from an injected clock, so a fixed
clock yields a byte-identical result — mirroring the Grounding pipeline (ADR-0016 §D15).

Failure semantics (ADR-0017 §D29): governance is **one aggregate evaluation**. A failure
in any stage (rule evaluation, assessment, or decision) propagates and fails the whole
``evaluate`` call — there is no partial governance result, no recovery, and no fallback.
The only outcomes are exactly one ``QualityGovernanceResult`` or an exception.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from requirement_intelligence.cp1.models.cp1_result import CP1Result
from requirement_intelligence.grounding.models import GroundingResult
from requirement_intelligence.quality_governance.assessment.quality_assessment_engine import (
    QualityAssessmentEngine,
)
from requirement_intelligence.quality_governance.builder import QualityGovernanceResultBuilder
from requirement_intelligence.quality_governance.decision.quality_decision_engine import (
    QualityDecisionEngine,
)
from requirement_intelligence.quality_governance.evaluation.quality_rule_evaluator import (
    QualityRuleEvaluator,
)
from requirement_intelligence.quality_governance.models.result import QualityGovernanceResult
from requirement_intelligence.quality_governance.policy import QualityPolicy
from requirement_intelligence.validation.models.validation_result import ValidationResult


class QualityGovernancePipeline:
    """The private stage sequencer. Sequencing and delegation only — computes nothing."""

    def __init__(
        self,
        *,
        policy: QualityPolicy,
        rule_evaluator: QualityRuleEvaluator,
        assessment_engine: QualityAssessmentEngine,
        decision_engine: QualityDecisionEngine,
        result_builder: QualityGovernanceResultBuilder,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        """Store the governed policy, the injected stage collaborators, and the clock."""
        self._policy = policy
        self._rule_evaluator = rule_evaluator
        self._assessment_engine = assessment_engine
        self._decision_engine = decision_engine
        self._result_builder = result_builder
        self._clock = clock if clock is not None else (lambda: datetime.now(UTC))

    def execute(
        self,
        grounding_result: GroundingResult,
        validation_result: ValidationResult,
        cp1_result: CP1Result,
    ) -> QualityGovernanceResult:
        """Sequence the frozen stages end to end and return the assembled result."""
        started_at = self._clock()

        rule_evaluation_result = self._rule_evaluator.evaluate(
            grounding_result, validation_result, cp1_result
        )
        quality_assessment_result = self._assessment_engine.assess(rule_evaluation_result)
        quality_decision_result = self._decision_engine.decide(quality_assessment_result)

        completed_at = self._clock()
        return self._result_builder.build(
            grounding_result=grounding_result,
            validation_result=validation_result,
            cp1_result=cp1_result,
            rule_evaluation_result=rule_evaluation_result,
            quality_assessment_result=quality_assessment_result,
            quality_decision_result=quality_decision_result,
            policy_id=self._policy.policy_id,
            policy_version=self._policy.policy_version,
            started_at=started_at,
            completed_at=completed_at,
        )
