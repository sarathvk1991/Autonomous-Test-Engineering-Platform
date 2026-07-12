"""The :class:`QualityGovernanceResult` — the frozen runtime contract of the subsystem.

``QualityGovernanceResult`` is the canonical repository-level aggregate the Quality
Governance runtime will produce and ``QualityGovernanceService.evaluate`` will return
— a peer to ``GroundingResult`` / ``ValidationResult`` / ``CP1Result``. It ties the
governance assessment to the run it graded and **names the exact upstream results it
consumed** (:class:`ConsumedResultReference`), so the verdict is a complete,
self-contained audit record: every ``PASS`` / ``PASS_WITH_WARNINGS`` / ``FAIL`` is
explainable from this object alone, with no need to re-run governance or inspect any
runtime service (ADR-0017 Recommendation 3).

The validators enforce cross-referential integrity only. No score, decision, or
metric is computed here.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.quality_governance.identity.quality_identity import (
    QualityGovernanceResultId,
    QualityGovernanceResultVersion,
    QualityGovernanceVersion,
    QualityPolicyId,
    QualityPolicyVersion,
)
from requirement_intelligence.quality_governance.models.assessment import QualityAssessment
from requirement_intelligence.quality_governance.models.enums import QualityInputSource
from shared.contracts.base import Schema

#: Version of the ``QualityGovernanceResult`` **runtime contract** schema. Independent
#: of the framework, policy, and assessment versions; a change here never forces any
#: of those to change, and vice versa.
QUALITY_GOVERNANCE_RESULT_VERSION = QualityGovernanceResultVersion(1, 0, 0)


class ConsumedResultReference(Schema):
    """The identity and version of one upstream result the governance verdict consumed.

    Records provenance only — which peer result (Grounding / Validation / CP1), which
    id, and which contract version — never the result's contents. This is what makes
    the dependency graph of ADR-0017 Recommendation 5 legible on the audit record
    without embedding (or coupling to) the upstream aggregates.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    source: QualityInputSource = Field(..., description="Which peer subsystem produced the result.")
    result_id: str = Field(..., min_length=1, description="Identity of the consumed result.")
    result_version: str = Field(
        ..., min_length=1, description="Contract/schema version of the consumed result."
    )


class QualityGovernanceResult(Schema):
    """The complete, deterministic quality governance verdict for one run.

    ``QualityGovernanceResult`` is the **runtime contract** — the only governance
    object that will cross into serialization. It is **not** a report, an execution
    artifact, serialization, a renderer, or a calculator: it already contains
    everything (the assessment, its findings, the summary, the governing policy
    identity/version, and the consumed-input provenance) any downstream projection
    needs.

    **Serialization invariant (frozen, CAP-080A).** Every future execution artifact
    (``quality_governance.json``, ``quality_report.md``, ``quality_score.md``) will be
    a **pure projection** of a ``QualityGovernanceResult`` — reproducible from it
    alone, computing nothing (ADR-0017 Recommendation 4), exactly as the Grounding
    artifacts project ``GroundingResult``.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    result_id: QualityGovernanceResultId = Field(..., description="Deterministic result id.")
    analysis_id: str = Field(..., min_length=1, description="The analysis this governs.")
    execution_id: str = Field(..., min_length=1, description="The AI invocation this governs.")

    assessment: QualityAssessment = Field(..., description="The governance assessment.")
    consumed_inputs: tuple[ConsumedResultReference, ...] = Field(
        default=(), description="The upstream results this verdict consumed (provenance only)."
    )

    policy_id: QualityPolicyId = Field(..., description="Identity of the governing policy.")
    policy_version: QualityPolicyVersion = Field(
        ..., description="Version of the governing policy."
    )
    framework_version: QualityGovernanceVersion = Field(...)
    result_version: QualityGovernanceResultVersion = Field(
        default=QUALITY_GOVERNANCE_RESULT_VERSION,
        description="Version of the QualityGovernanceResult runtime-contract schema.",
    )
    started_at: datetime = Field(..., description="When governance evaluation started.")
    completed_at: datetime = Field(..., description="When governance evaluation completed.")

    @model_validator(mode="after")
    def _validate_result(self) -> QualityGovernanceResult:
        """Provenance, identity, and lifetime must be internally consistent."""
        if self.completed_at < self.started_at:
            raise ValueError("completed_at precedes started_at.")
        if self.assessment.analysis_id != self.analysis_id:
            raise ValueError("Assessment analysis_id does not match the result's.")
        if self.assessment.execution_id != self.execution_id:
            raise ValueError("Assessment execution_id does not match the result's.")
        if self.assessment.policy_id != self.policy_id or self.assessment.policy_version != (
            self.policy_version
        ):
            raise ValueError("Assessment policy identity/version does not match the result's.")

        sources = [ref.source for ref in self.consumed_inputs]
        if len(sources) != len(set(sources)):
            raise ValueError("consumed_inputs must not name the same source twice.")
        return self
