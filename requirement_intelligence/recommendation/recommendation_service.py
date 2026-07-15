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

Runtime status (CAP-082B)
    ``recommend`` is now implemented: :class:`DeterministicRecommendationService`
    delegates to a private
    :class:`~requirement_intelligence.recommendation.engine.DeterministicRecommendationEngine`
    that performs deterministic candidate collection, confidence surfacing, priority
    resolution, grouping, metrics, and summary end to end. The service is still **not
    wired into the Requirement Intelligence execution pipeline** (nothing calls
    ``recommend`` at runtime) and only ``PlatformContext`` may construct it outside
    this package — so runtime behaviour is byte-identical and the golden baseline is
    unchanged. Runtime integration is future work, exactly as CAP-080B implemented the
    first deterministic Quality Governance rule evaluator before CAP-080D wired the
    subsystem in, and CAP-081B implemented the first deterministic Requirement
    Enhancement engine before CAP-081C activated it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from requirement_intelligence.cp1.models.cp1_result import CP1Result
from requirement_intelligence.enhancement.models.result import RequirementEnhancementResult
from requirement_intelligence.grounding.models.assessment import GroundingResult
from requirement_intelligence.quality_governance.models.result import QualityGovernanceResult
from requirement_intelligence.recommendation.engine import DeterministicRecommendationEngine
from requirement_intelligence.recommendation.models.result import RecommendationResult
from requirement_intelligence.recommendation.policy.recommendation_policy import (
    RecommendationPolicy,
)
from requirement_intelligence.recommendation.rules.recommendation_rule_catalog import (
    RecommendationRuleCatalog,
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
        Abstract in CAP-082A; :class:`DeterministicRecommendationService` (CAP-082B)
        implements it behind this unchanged signature.
        """
        raise NotImplementedError


class DeterministicRecommendationService(RecommendationService):
    """The registered default service (CAP-082B) — thin orchestration over the engine.

    Holds a private :class:`~requirement_intelligence.recommendation.engine.
    DeterministicRecommendationEngine` and delegates ``recommend`` to it, owning only
    the public boundary and construction. It **computes nothing itself**: the engine
    performs candidate collection, confidence surfacing, priority resolution,
    grouping, metrics, and summary. Mirrors how the Requirement Enhancement
    subsystem's own deterministic runtime service delegates to its private engine
    (ADR-0018) — a thin service, real behaviour one layer down.
    """

    def __init__(
        self,
        *,
        policy: RecommendationPolicy,
        rule_catalog: RecommendationRuleCatalog | None = None,
    ) -> None:
        """Construct the private deterministic engine this service delegates to."""
        self._engine = DeterministicRecommendationEngine(policy=policy, rule_catalog=rule_catalog)

    def recommend(
        self,
        enhancement_result: RequirementEnhancementResult,
        grounding_result: GroundingResult,
        validation_result: ValidationResult,
        cp1_result: CP1Result,
        quality_governance_result: QualityGovernanceResult,
    ) -> RecommendationResult:
        """Recommend actions for one run via the deterministic engine — delegation only."""
        return self._engine.recommend(
            enhancement_result,
            grounding_result,
            validation_result,
            cp1_result,
            quality_governance_result,
        )
