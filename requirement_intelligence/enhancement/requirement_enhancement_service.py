"""RequirementEnhancementService — the single runtime entry point into Requirement
Intelligence Enhancement.

Architecture (ADR-0018)
------------------------
``RequirementEnhancementService`` is the permanent **orchestration boundary** of the
Requirement Intelligence Enhancement Framework. Everything outside the subsystem will
talk to enhancement through this one contract; nothing else is a public runtime
surface. It mirrors the role the Quality Governance and Grounding runtime services
play for their own subsystems (ADR-0017 §D6, ADR-0016 §D7): a single seam that will
coordinate collaborators and own none of their work.

Consumer only (frozen, Recommendation 5)
------------------------------------------
``enhance`` consumes **only** the two completed upstream inputs — ``EngineeringContext``
and ``AnalysisResult``. Requirement Enhancement never re-runs Engineering Context
Orchestration or Analysis; never re-implements Grounding, Validation, CP1, or Quality
Governance; and never owns any upstream computation. The dependency direction is
one-way:

    EngineeringContext ┐
    AnalysisResult     ├─▶ RequirementEnhancementService.enhance ─▶ RequirementEnhancementResult

What the service will OWN
    orchestration, lifecycle, dependency coordination, execution ordering, and (in a
    later milestone) assembly of the final :class:`RequirementEnhancementResult`.

What the service does NOT own
    Engineering Context Orchestration, Analysis, Grounding, Validation, CP1, Quality
    Governance, and the Execution Package. Each is a separate owner. The future
    enrichment, relationship-detection, and observation engines are **internal
    implementation details** of the service and can be added without changing this
    contract.

Runtime status (CAP-081B)
    ``enhance`` is now implemented: :class:`DeterministicRequirementEnhancementService`
    delegates to a private
    :class:`~requirement_intelligence.enhancement.engine.DeterministicRequirementEnhancementEngine`
    that performs deterministic enrichment, relationship construction, observation
    generation, findings, metrics, and summary end to end. The service is still **not
    wired into the Requirement Intelligence execution pipeline** (nothing calls
    ``enhance`` at runtime) and only ``PlatformContext`` may construct it outside this
    package — so runtime behaviour is byte-identical and the golden baseline is
    unchanged. Runtime integration is future work, exactly as CAP-080B implemented the
    first deterministic Quality Governance rule evaluator years (in capability terms)
    before CAP-080D wired the subsystem in.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from requirement_intelligence.analysis.analysis_models import AnalysisResult
from requirement_intelligence.context_orchestration.models.engineering_context import (
    EngineeringContext,
)
from requirement_intelligence.enhancement.engine import DeterministicRequirementEnhancementEngine
from requirement_intelligence.enhancement.models.result import RequirementEnhancementResult
from requirement_intelligence.enhancement.policy.enhancement_policy import EnhancementPolicy
from requirement_intelligence.enhancement.rules.enhancement_rule_catalog import (
    EnhancementRuleCatalog,
)


class RequirementEnhancementService(ABC):
    """The permanent runtime contract for enhancing one Requirement Intelligence run.

    A single public method, ``enhance``, enriches, relates, and observes the
    generated requirements of a completed analysis under a governed
    :class:`EnhancementPolicy` and returns a :class:`RequirementEnhancementResult`.
    Implementations orchestrate; they delegate enrichment, relationship detection, and
    observation generation to internal collaborators and own no upstream computation
    themselves.
    """

    @abstractmethod
    def enhance(
        self,
        engineering_context: EngineeringContext,
        analysis_result: AnalysisResult,
    ) -> RequirementEnhancementResult:
        """Enhance one run from its completed *engineering_context* and *analysis_result*.

        Parameters
        ----------
        engineering_context:
            The complete reasoning context the analysis was generated from.
        analysis_result:
            The completed, un-validated AI analysis this enhances.

        Returns
        -------
        RequirementEnhancementResult
            The repository-level enhancement aggregate for the run — the complete,
            self-contained record of every enriched requirement, relationship, and
            observation.

        Notes
        -----
        Abstract in CAP-081A; a real engine is wired behind this unchanged signature
        in a later CAP-081 milestone.
        """
        raise NotImplementedError


class DeterministicRequirementEnhancementService(RequirementEnhancementService):
    """The registered default service (CAP-081B) — thin orchestration over the engine.

    Holds a private :class:`DeterministicRequirementEnhancementEngine` and delegates
    ``enhance`` to it, owning only the public boundary and construction. It **computes
    nothing itself**: the engine performs enrichment, relationship construction,
    observation generation, findings, metrics, and summary. Mirrors how the
    registered Quality Governance runtime service delegates to its private pipeline
    (ADR-0017 §D29) — a thin service, real behaviour one layer down.
    """

    def __init__(self, *, policy: EnhancementPolicy, rule_catalog: EnhancementRuleCatalog) -> None:
        """Construct the private deterministic engine this service delegates to."""
        self._engine = DeterministicRequirementEnhancementEngine(
            policy=policy, rule_catalog=rule_catalog
        )

    def enhance(
        self,
        engineering_context: EngineeringContext,
        analysis_result: AnalysisResult,
    ) -> RequirementEnhancementResult:
        """Enhance one run via the deterministic engine — delegation only."""
        return self._engine.enhance(engineering_context, analysis_result)
