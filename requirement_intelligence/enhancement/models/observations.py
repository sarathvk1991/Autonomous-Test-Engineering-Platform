"""The :class:`RequirementObservation` and the surfaced :class:`EnhancementFinding`.

Recommendation 3 (ADR-0018): observations are produced **first**, and every future
recommendation is derived from an observation — a recommendation engine must never
perform independent analysis. This mirrors the successful Grounding → Classification →
Confidence → Governance layering (ADR-0016) and the Quality Governance Rule Evaluation
→ Assessment → Decision layering (ADR-0017): a raw, deterministic signal layer
(``RequirementObservation``) strictly precedes any interpreted, surfaced layer
(``EnhancementFinding``).

Neither model computes anything. A future observation engine populates
``RequirementObservation`` from the enhanced requirements and the relationship graph;
a future classification step (never Requirement Enhancement's recommendation engine
itself, which does not exist at this milestone) may surface an observation as an
``EnhancementFinding`` by reference — never by copying its content.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.enhancement.identity.enhancement_identity import (
    RequirementObservationId,
)
from requirement_intelligence.enhancement.models.enums import (
    EnhancementSeverity,
    ObservationCategory,
)
from shared.contracts.base import Schema


class RequirementObservation(Schema):
    """One deterministic, un-interpreted signal noticed about the requirement set.

    The raw layer of Recommendation 3: an observation notices something (a gap, a
    conflict, a duplicate) without prescribing what to do about it. It carries no
    recommendation and no release-affecting decision (Requirement Enhancement is
    non-gating, mirroring Grounding — ADR-0016 §D5). ``subject_requirement_ids`` names
    every requirement the observation concerns; it may name one, several, or none (a
    set-level observation).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    observation_id: RequirementObservationId = Field(
        ..., description="Deterministic identity of this observation."
    )
    category: ObservationCategory = Field(..., description="The governed observation category.")
    severity: EnhancementSeverity = Field(..., description="The observation's recorded severity.")
    subject_requirement_ids: tuple[str, ...] = Field(
        default=(), description="Requirement ids this observation concerns."
    )
    message: str = Field(..., min_length=1, description="Human-readable description.")


class EnhancementFinding(Schema):
    """A surfaced enhancement observation — the interpreted layer of Recommendation 3.

    References the :class:`RequirementObservation` it was derived from; it never
    copies the observation's content (reference-not-copy, mirroring
    ``AssessmentFindingReference``, ADR-0017 §D26). No finding is derived here — a
    future classification stage mints these; this model only shapes them.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    finding_id: str = Field(..., min_length=1, description="Identity of this finding.")
    observation_id: RequirementObservationId = Field(
        ..., description="The RequirementObservation this finding was derived from."
    )
    category: ObservationCategory = Field(..., description="The governed observation category.")
    severity: EnhancementSeverity = Field(..., description="Governance severity of the finding.")
    message: str = Field(..., min_length=1, description="Human-readable description.")
