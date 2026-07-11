"""GroundingService — the single runtime entry point into the Grounding subsystem.

Architecture (ADR-0016)
-----------------------
``GroundingService`` is the permanent **orchestration boundary** of the Grounding
Framework. Everything outside the subsystem talks to grounding through this one
contract; nothing else is a public runtime surface. It mirrors the role
``RequirementAnalysisService`` plays for AI execution: a single ``assess`` seam
that coordinates collaborators and owns none of their work.

    GroundingService              (orchestration — this contract, stable)
            │  delegates matching to
            ▼
    GroundingStrategy             (matching — the replaceable extension point)

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

This milestone (CAP-077A.1)
    Establishes the boundary only. ``assess`` is abstract, and the registered
    default implementation raises :class:`NotImplementedError`: no matching, no
    classification, no confidence, no metrics, no runtime integration. The service
    exists but is **dormant**, exactly as the Engineering Context Orchestrator did
    before its own runtime activation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from requirement_intelligence.analysis.analysis_models import AnalysisResult
from requirement_intelligence.context_orchestration.models.engineering_context import (
    EngineeringContext,
)
from requirement_intelligence.grounding.config import GroundingConfiguration
from requirement_intelligence.grounding.contracts import GroundingStrategy
from requirement_intelligence.grounding.models import GroundingResult


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
        Unimplemented in CAP-077A.1: this contract exists to fix the runtime API.
        Matching (CAP-077B), classification (CAP-077C), confidence and metrics
        (CAP-077D), and runtime integration (CAP-077E) fill it in behind this
        unchanged signature.
        """
        raise NotImplementedError


class DefaultGroundingService(GroundingService):
    """The registered, construction-only grounding service.

    Holds the governed :class:`GroundingConfiguration` and — once a matcher exists
    — a :class:`GroundingStrategy`. It depends only on the strategy *abstraction*;
    no concrete strategy is injected yet, so ``strategy`` defaults to ``None``.
    ``assess`` deliberately raises :class:`NotImplementedError`: the boundary is
    live, the behaviour is not.
    """

    def __init__(
        self,
        configuration: GroundingConfiguration,
        strategy: GroundingStrategy | None = None,
    ) -> None:
        """Store the governed configuration and (future) matching strategy."""
        self._configuration = configuration
        self._strategy = strategy

    @property
    def configuration(self) -> GroundingConfiguration:
        """The governed grounding configuration this service was built with."""
        return self._configuration

    @property
    def strategy(self) -> GroundingStrategy | None:
        """The matching strategy, or ``None`` until one is injected (CAP-077B)."""
        return self._strategy

    def assess(
        self,
        engineering_context: EngineeringContext,
        analysis_result: AnalysisResult,
    ) -> GroundingResult:
        """Not yet implemented — the boundary is dormant until CAP-077B onward."""
        raise NotImplementedError(
            "GroundingService.assess is not implemented in CAP-077A.1. The Grounding "
            "subsystem exposes its runtime boundary here; matching, classification, "
            "confidence, metrics, and runtime integration land in CAP-077B onward."
        )
