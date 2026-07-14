"""RecommendationService — the single runtime entry point into the Recommendation
Framework.

Architecture (ADR-0019)
------------------------
``RecommendationService`` is the permanent **orchestration boundary** of the
Recommendation Framework. Everything outside the subsystem will talk to
recommendation generation through this one contract; nothing else is a public
runtime surface. It mirrors the role the Requirement Enhancement, Quality
Governance, and Grounding runtime services play for their own subsystems (ADR-0018
§D6, ADR-0017 §D6, ADR-0016 §D7): a single seam that will coordinate collaborators
and own none of their work.

Consumer only (frozen, Recommendation 1)
------------------------------------------
``recommend`` consumes **only** the five completed upstream results —
``RequirementEnhancementResult``, ``GroundingResult``, ``ValidationResult``,
``CP1Result``, and ``QualityGovernanceResult``. The Recommendation Framework never
re-runs Requirement Enhancement, Grounding, Validation, CP1, or Quality Governance,
and never owns any of their computation. The dependency direction is one-way:

    RequirementEnhancementResult  ┐
    GroundingResult               │
    ValidationResult              ├─▶ RecommendationService.recommend ─▶ RecommendationResult
    CP1Result                     │
    QualityGovernanceResult       ┘

What the service will OWN
    orchestration, lifecycle, dependency coordination, execution ordering, and (in a
    later milestone) assembly of the final :class:`RecommendationResult`.

What the service does NOT own
    Requirement Enhancement, Grounding, Validation, CP1, Quality Governance, and the
    Execution Package. Each is a separate owner. A future deterministic, ML, LLM, or
    hybrid recommendation engine is an **internal implementation detail** of the
    service and can be added without changing this contract.

Runtime status (CAP-082A)
    ``recommend`` is **abstract**. The registered
    :class:`DormantRecommendationService` raises :class:`NotImplementedError`. It is
    dormant — no runtime path consumes it, and only ``PlatformContext`` may
    construct it outside this package — so runtime behaviour is byte-identical and
    the golden baseline is unchanged. Runtime integration is future work
    (CAP-082B onward), exactly as CAP-081A froze the Requirement Enhancement service
    boundary before CAP-081B implemented the first deterministic engine.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from requirement_intelligence.cp1.models.cp1_result import CP1Result
from requirement_intelligence.enhancement.models.result import RequirementEnhancementResult
from requirement_intelligence.grounding.models.assessment import GroundingResult
from requirement_intelligence.quality_governance.models.result import QualityGovernanceResult
from requirement_intelligence.recommendation.models.result import RecommendationResult
from requirement_intelligence.recommendation.policy.recommendation_policy import (
    RecommendationPolicy,
)
from requirement_intelligence.validation.models.validation_result import ValidationResult


class RecommendationService(ABC):
    """The permanent runtime contract for recommending actions for one run.

    A single public method, ``recommend``, derives recommendations from the five
    completed upstream results under a governed :class:`RecommendationPolicy` and
    returns a :class:`RecommendationResult`. Implementations orchestrate; they
    delegate generation, prioritization, grouping, and confidence scoring to internal
    collaborators and own no upstream computation themselves.
    """

    @abstractmethod
    def recommend(
        self,
        enhancement_result: RequirementEnhancementResult,
        grounding_result: GroundingResult,
        validation_result: ValidationResult,
        cp1_result: CP1Result,
        quality_governance_result: QualityGovernanceResult,
    ) -> RecommendationResult:
        """Recommend actions from the five completed upstream results.

        Parameters
        ----------
        enhancement_result:
            The completed Requirement Enhancement result for this run.
        grounding_result:
            The completed Grounding result for this run.
        validation_result:
            The completed Validation result for this run.
        cp1_result:
            The completed CP1 result for this run.
        quality_governance_result:
            The completed Quality Governance result for this run.

        Returns
        -------
        RecommendationResult
            The repository-level recommendation aggregate for the run — the
            complete, self-contained record of every recommendation and group.

        Notes
        -----
        Abstract in CAP-082A; a real engine is wired behind this unchanged signature
        in a later CAP-082 milestone (CAP-082B: Deterministic Recommendation Engine).
        """
        raise NotImplementedError


class DormantRecommendationService(RecommendationService):
    """The registered, dormant service (CAP-082A). Raises on every call.

    Exists so :meth:`PlatformContext.create_recommendation_service` has a concrete
    class to construct — proving the composition root and the frozen signature are
    wired — without performing any recommendation generation. Mirrors the pattern
    ADR-0016 §D7, ADR-0017 §D6, and ADR-0018 §D6 established for the dormant
    Grounding, Quality Governance, and Requirement Enhancement runtime services
    before their first real engines landed.
    """

    def __init__(self, policy: RecommendationPolicy) -> None:
        """Store the governed policy a future engine will read."""
        self._policy = policy

    def recommend(
        self,
        enhancement_result: RequirementEnhancementResult,
        grounding_result: GroundingResult,
        validation_result: ValidationResult,
        cp1_result: CP1Result,
        quality_governance_result: QualityGovernanceResult,
    ) -> RecommendationResult:
        """Raise: no recommendation engine exists yet (CAP-082A is architecture only)."""
        raise NotImplementedError(
            "RecommendationService.recommend has no implementation yet (CAP-082A "
            "froze the architecture only); a later CAP-082 milestone wires a real "
            "engine behind this unchanged signature."
        )
