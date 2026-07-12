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

Runtime status (CAP-080A)
    ``evaluate`` is **abstract** and the registered :class:`DormantQualityGovernanceService`
    raises :class:`NotImplementedError`. The service is **dormant** — no pipeline
    stage, execution builder, or CLI path consumes it, and ``PlatformContext``
    constructs it with the governed policy but **no decision engine**. Runtime
    behaviour is byte-identical and the golden baseline is unchanged. The decision
    engine and runtime activation land in a later CAP-080 milestone, behind this
    unchanged ``evaluate`` signature.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from requirement_intelligence.cp1.models.cp1_result import CP1Result
from requirement_intelligence.grounding.models import GroundingResult
from requirement_intelligence.quality_governance.models import QualityGovernanceResult
from requirement_intelligence.quality_governance.policy import QualityPolicy
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


class DormantQualityGovernanceService(QualityGovernanceService):
    """The registered, dormant governance service (CAP-080A).

    It holds the governed :class:`QualityPolicy` it will evaluate but performs no
    governance: ``evaluate`` raises :class:`NotImplementedError`. It exists so the
    boundary and its ``PlatformContext`` registration are fixed before any behaviour,
    exactly as the default Grounding service was dormant at CAP-077A.1. No pipeline
    stage consumes it, so runtime is byte-identical.
    """

    def __init__(self, policy: QualityPolicy) -> None:
        """Store the governed policy the future decision engine will evaluate."""
        self._policy = policy

    @property
    def policy(self) -> QualityPolicy:
        """The governed quality policy this dormant service was constructed with."""
        return self._policy

    def evaluate(
        self,
        grounding_result: GroundingResult,
        validation_result: ValidationResult,
        cp1_result: CP1Result,
    ) -> QualityGovernanceResult:
        """Dormant in CAP-080A — the decision engine lands in a later milestone."""
        raise NotImplementedError(
            "QualityGovernanceService.evaluate is dormant in CAP-080A; the decision "
            "engine is introduced in a later CAP-080 milestone."
        )
