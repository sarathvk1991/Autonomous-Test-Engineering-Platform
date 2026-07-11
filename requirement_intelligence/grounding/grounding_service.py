"""GroundingService — the single runtime entry point into the Grounding subsystem.

Architecture (ADR-0016)
-----------------------
``GroundingService`` is the permanent **orchestration boundary** of the Grounding
Framework. Everything outside the subsystem talks to grounding through this one
contract; nothing else is a public runtime surface. It mirrors the role
``RequirementAnalysisService`` plays for AI execution: a single ``assess`` seam
that coordinates collaborators and owns none of their work.

    GroundingService              (orchestration — this contract, stable)
            │  builds a canonical MatchingContext, fans out to MatchingRequests,
            │  delegates each to
            ▼
    GroundingStrategy             (matching — the replaceable extension point)

Future internal flow (CAP-077B onward; not implemented here)
------------------------------------------------------------
``assess`` keeps its signature ``(engineering_context, analysis_result)``. Inside,
it will:

1. build a canonical :class:`MatchingContext` from those runtime inputs via the
   ``MatchingContextBuilder`` — the one boundary that touches runtime models;
2. fan it out into N :class:`MatchingRequest`\\ s (``MatchingContext.to_requests``);
3. delegate each to the configured :class:`GroundingStrategy`, collecting one
   ``MatchResult`` per requirement (links + match statistics + matcher explanation);
4. classify, score confidence, explain (at requirement scope), and assemble the
   ``GroundingResult`` from those ``MatchResult``\\ s via its internal collaborators.

The strategy sees only canonical matching models — never ``EngineeringContext`` or
``AnalysisResult``.

What the service OWNS
    orchestration, lifecycle, dependency coordination, execution ordering, and
    (in a later milestone) assembly of the final :class:`GroundingResult`.

What the service does NOT own
    evidence matching (``GroundingStrategy``), support classification, confidence
    calculation, metrics calculation, explanation generation, execution-package
    writing, Validation, CP1, and the Prompt Builder. Each is a separate owner.

Dependency inversion
    The service depends on the :class:`GroundingStrategy` **abstraction**, never on
    a concrete strategy (``DeterministicTextMatchingStrategy``,
    ``SemanticSimilarityStrategy``, ``EvidenceCitationStrategy``, ``HybridStrategy``
    — all future). No runtime code references a concrete strategy. Future
    collaborators (a classification engine, a confidence calculator, metrics and
    explanation assemblers, the result builder) are **internal implementation
    details** of the service and can be added without changing this contract.

Runtime status (CAP-077E)
    ``assess`` is now implemented: ``DefaultGroundingService`` delegates to a private
    :class:`~requirement_intelligence.grounding.pipeline.GroundingPipeline` that sequences
    the frozen stages end to end. The service is still **not wired into the execution
    pipeline** (nothing calls ``assess`` at runtime), so behaviour remains byte-identical;
    execution-package integration lands in CAP-077F.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from requirement_intelligence.analysis.analysis_models import AnalysisResult
from requirement_intelligence.context_orchestration.models.engineering_context import (
    EngineeringContext,
)
from requirement_intelligence.grounding.models import GroundingResult
from requirement_intelligence.grounding.pipeline import GroundingPipeline


class GroundingService(ABC):
    """The permanent runtime contract for grounding one analysis.

    A single public method, ``assess``, grades a completed analysis against the
    evidence that produced it and returns a :class:`GroundingResult`. Implementations
    orchestrate; they delegate matching to a :class:`GroundingStrategy` and own no
    matching, scoring, or classification logic themselves.
    """

    @abstractmethod
    def assess(
        self,
        engineering_context: EngineeringContext,
        analysis_result: AnalysisResult,
    ) -> GroundingResult:
        """Grade *analysis_result* against the evidence in *engineering_context*.

        Parameters
        ----------
        engineering_context:
            The complete, bounded evidence the reasoning session received — the
            corpus grounding traces requirements back to.
        analysis_result:
            The raw, un-validated AI analysis to be grounded.

        Returns
        -------
        GroundingResult
            The repository-level grounding aggregate for the run.

        Notes
        -----
        The full pipeline is wired in CAP-077E behind this unchanged signature.
        """
        raise NotImplementedError


class DefaultGroundingService(GroundingService):
    """The registered grounding service — thin orchestration over the pipeline (CAP-077E).

    It holds a private :class:`GroundingPipeline` and delegates ``assess`` to it, owning
    only the public boundary and lifecycle. It computes nothing; the pipeline sequences the
    governed stages. Still unwired into the execution pipeline, so runtime is byte-identical.
    """

    def __init__(self, pipeline: GroundingPipeline) -> None:
        """Store the private stage-sequencing pipeline to delegate to."""
        self._pipeline = pipeline

    def assess(
        self,
        engineering_context: EngineeringContext,
        analysis_result: AnalysisResult,
    ) -> GroundingResult:
        """Ground *analysis_result* against *engineering_context* via the frozen pipeline."""
        return self._pipeline.execute(engineering_context, analysis_result)
