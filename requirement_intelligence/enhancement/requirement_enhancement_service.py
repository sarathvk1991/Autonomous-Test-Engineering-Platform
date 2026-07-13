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

Runtime status (CAP-081A)
    ``enhance`` is **abstract**. The registered :class:`DormantRequirementEnhancementService`
    raises :class:`NotImplementedError`. It is dormant — no runtime path consumes it,
    and only ``PlatformContext`` may construct it outside this package — so runtime
    behaviour is byte-identical and the golden baseline is unchanged. Runtime
    integration is future work, exactly as CAP-080A froze the Quality Governance
    service boundary years (in capability terms) before CAP-080D wired it in.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from requirement_intelligence.analysis.analysis_models import AnalysisResult
from requirement_intelligence.context_orchestration.models.engineering_context import (
    EngineeringContext,
)
from requirement_intelligence.enhancement.models.result import RequirementEnhancementResult
from requirement_intelligence.enhancement.policy.enhancement_policy import EnhancementPolicy


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


class DormantRequirementEnhancementService(RequirementEnhancementService):
    """The registered, dormant service (CAP-081A). Raises on every call.

    Exists so :meth:`PlatformContext.create_requirement_enhancement_service` has a
    concrete class to construct — proving the composition root and the frozen
    signature are wired — without performing any enhancement. Mirrors the pattern
    ADR-0016 §D7 and ADR-0017 §D6 established for the dormant Grounding and Quality
    Governance runtime services before their first real engines landed.
    """

    def __init__(self, policy: EnhancementPolicy) -> None:
        """Store the governed policy a future engine will read."""
        self._policy = policy

    def enhance(
        self,
        engineering_context: EngineeringContext,
        analysis_result: AnalysisResult,
    ) -> RequirementEnhancementResult:
        """Raise: no enhancement engine exists yet (CAP-081A is architecture only)."""
        raise NotImplementedError(
            "RequirementEnhancementService.enhance has no implementation yet "
            "(CAP-081A froze the architecture only); a later CAP-081 milestone wires "
            "a real engine behind this unchanged signature."
        )
