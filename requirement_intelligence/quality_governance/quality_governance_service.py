"""QualityGovernanceService — the single runtime entry point into Quality Governance.

Architecture (ADR-0017)
-----------------------
``QualityGovernanceService`` is the permanent **orchestration boundary** of the
Quality Governance Framework. Everything outside the subsystem will talk to
governance through this one contract; nothing else is a public runtime surface. It
mirrors the role the Grounding service plays for grounding: a single ``evaluate`` seam
that will coordinate collaborators and own none of their work.

Consumer only (frozen, ADR-0017 Recommendation 1)
-------------------------------------------------
``evaluate`` consumes **only** the three completed, peer runtime results —
``GroundingResult``, ``ValidationResult``, ``CP1Result``. Quality Governance never
re-runs Grounding, Validation, or CP1; never inspects prompts, the Engineering
Context, or Gemini responses; and never owns any upstream computation. The dependency
direction is one-way (ADR-0017 Recommendation 5):

    GroundingResult  ┐
    ValidationResult ├─▶ QualityGovernanceService.evaluate ─▶ QualityGovernanceResult
    CP1Result        ┘

What the service will OWN
    orchestration, lifecycle, dependency coordination, execution ordering, and (in a
    later milestone) assembly of the final :class:`QualityGovernanceResult`.

What the service does NOT own
    Grounding, Validation, CP1, Engineering Context, Analysis, prompt construction,
    Prompt Governance, Reporting, and the Execution Package. Each is a separate owner.
    The future decision layers — policy, rule evaluation, quality assessment, release
    decision (ADR-0017 Recommendation 6) — are **internal implementation details** of
    the service and can be added without changing this contract.

Runtime status (CAP-080C)
    ``evaluate`` is now implemented: :class:`DefaultQualityGovernanceService` delegates
    to a private ``QualityGovernancePipeline`` (``quality_governance.pipeline``)
    that sequences the frozen stages — rule evaluation → assessment → decision →
    assembly — end to end. The service is still **not wired into the Requirement
    Intelligence execution pipeline** (nothing calls ``evaluate`` at runtime), so
    behaviour remains byte-identical and the golden baseline is unchanged;
    execution-package and CLI integration land in CAP-080D behind this unchanged
    ``evaluate`` signature.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from requirement_intelligence.cp1.models.cp1_result import CP1Result
from requirement_intelligence.grounding.models import GroundingResult
from requirement_intelligence.quality_governance.models import QualityGovernanceResult
from requirement_intelligence.quality_governance.pipeline import QualityGovernancePipeline
from requirement_intelligence.validation.models.validation_result import ValidationResult


class QualityGovernanceService(ABC):
    """The permanent runtime contract for governing one Requirement Intelligence run.

    A single public method, ``evaluate``, judges the completed upstream results
    against a governed :class:`QualityPolicy` and returns a
    :class:`QualityGovernanceResult`. Implementations orchestrate; they delegate rule
    evaluation and decision-making to internal collaborators and own no upstream
    computation themselves.
    """

    @abstractmethod
    def evaluate(
        self,
        grounding_result: GroundingResult,
        validation_result: ValidationResult,
        cp1_result: CP1Result,
    ) -> QualityGovernanceResult:
        """Govern one run from its completed *grounding*, *validation*, and *cp1* results.

        Parameters
        ----------
        grounding_result:
            The completed grounding assessment — support classification, confidence,
            and grounding metrics for the run.
        validation_result:
            The completed structural/reasoning validation verdict for the run.
        cp1_result:
            The completed engineering-readiness verdict for the run.

        Returns
        -------
        QualityGovernanceResult
            The repository-level governance aggregate for the run — the complete,
            self-contained audit record of the decision.

        Notes
        -----
        Abstract in CAP-080A; the decision engine is wired behind this unchanged
        signature in a later CAP-080 milestone.
        """
        raise NotImplementedError


class DefaultQualityGovernanceService(QualityGovernanceService):
    """The registered governance service — thin orchestration over the pipeline (CAP-080C).

    It holds a private :class:`QualityGovernancePipeline` and delegates ``evaluate`` to it,
    owning only the public boundary and lifecycle. It **computes nothing**: the pipeline
    sequences the governed stages (rule evaluation → assessment → decision → assembly) and
    the builder assembles the result. Still unwired into the Requirement Intelligence
    execution pipeline, so runtime is byte-identical — exactly mirroring the Grounding
    subsystem's thin service over its private pipeline.
    """

    def __init__(self, pipeline: QualityGovernancePipeline) -> None:
        """Store the private stage-sequencing pipeline to delegate to."""
        self._pipeline = pipeline

    def evaluate(
        self,
        grounding_result: GroundingResult,
        validation_result: ValidationResult,
        cp1_result: CP1Result,
    ) -> QualityGovernanceResult:
        """Govern one run via the frozen pipeline — delegation only, no business logic."""
        return self._pipeline.execute(grounding_result, validation_result, cp1_result)
