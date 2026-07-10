"""EngineeringContext — the canonical Engineering Context Orchestration model.

An :class:`EngineeringContext` is *the complete, bounded set of engineering
evidence required to reason about one subject of analysis in a single reasoning
session* (CAP-076A §3).

Relationship to ConsolidatedArtifact
------------------------------------
``EngineeringContext`` **does not replace**
:class:`~requirement_intelligence.models.consolidated_artifact.ConsolidatedArtifact`.
The two are stacked, not substituted:

===================================  =====================================
``ConsolidatedArtifact``             ``EngineeringContext``
===================================  =====================================
Canonical **consolidation** model    Canonical **orchestration** model
Produced by ``ConsolidationEngine``  Produced by the Engineering Context
                                     Orchestrator (CAP-076C)
Answers *"which records share an     Answers *"what does a reasoner need to
attribute?"*                         know about this subject?"*
Grouped by one deterministic         Composed from several groups under a
grouping dimension                   governed ``OrchestrationPolicy``
Owns no policy                       Carries the policy that composed it
===================================  =====================================

An ``EngineeringContext`` **consumes** consolidated artifacts: the orchestrator
selects them, the builder flattens their evidence into this model, and
:class:`ContextProvenance` records exactly which ones contributed. Consolidation
is entirely unaware that this model exists.

Immutability
------------
Every model here derives from :class:`~shared.contracts.base.Schema`, which sets
``frozen=True`` and ``extra="forbid"``. Collections are ``tuple`` rather than
``list`` so immutability is *deep*, not merely surface-level — a frozen pydantic
model with a ``list`` field still permits ``ctx.evidence.functional[0]`` mutation
of the container. This follows the precedent set by
``ValidationProfileDefinition.enabled_layers``.

The builder constructs; consumers read. There is no mutation after construction.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.context_orchestration.models.context_identity import (
    EngineeringContextId,
    OrchestrationPolicyId,
    PolicyVersion,
)
from requirement_intelligence.models.enums import RiskLevel, SourceCategory
from requirement_intelligence.models.source_artifact import SourceArtifact
from shared.contracts.base import Schema

#: Version of the :class:`EngineeringContext` *shape* — the single source of
#: truth. Advances additively; breaking changes are ADR-gated, matching
#: ``PROMPT_DEFINITION_VERSION``.
ENGINEERING_CONTEXT_VERSION = "1.0"


class ContextSubjectBasis(StrEnum):
    """Why a subject was chosen — the dimension the context is organised around.

    Mirrors the vocabulary of the Consolidation grouping cascade without
    importing it, so Consolidation stays free to evolve its own dimensions.
    :attr:`MULTI` records a subject drawn from groups spanning several
    dimensions, which is the case a single ``ConsolidatedArtifact`` cannot
    express and this model exists to represent.
    """

    COMPONENT = "component"
    TAG = "tag"
    ENDPOINT = "endpoint"
    RISK = "risk"
    MULTI = "multi"


class ContextSubject(Schema):
    """What the context is about."""

    model_config = ConfigDict(alias_generator=to_camel)

    label: str = Field(..., min_length=1, description="Human-readable subject name.")
    business_area: str | None = Field(
        default=None, description="Broader business capability the subject sits within."
    )
    basis: ContextSubjectBasis = Field(
        ..., description="The dimension this subject was derived from."
    )


class ContextEvidence(Schema):
    """The reasoning material, partitioned by engineering domain.

    The three domains mirror ``ConsolidatedArtifact``'s split so the context
    projects onto the prompt's existing three-section block with no prompt
    change (CAP-076A Invariant 6). Order within each tuple is significant and
    is fixed by the orchestrator; the builder preserves it verbatim.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    functional_artifacts: tuple[SourceArtifact, ...] = Field(
        default=(), description="Functional evidence (epics, stories, defects)."
    )
    security_artifacts: tuple[SourceArtifact, ...] = Field(
        default=(), description="Security evidence (DAST/SAST findings)."
    )
    quality_artifacts: tuple[SourceArtifact, ...] = Field(
        default=(), description="Code-quality evidence (e.g. SonarQube issues)."
    )

    @property
    def total_count(self) -> int:
        """Total number of evidence artifacts across all three domains."""
        return (
            len(self.functional_artifacts)
            + len(self.security_artifacts)
            + len(self.quality_artifacts)
        )

    @property
    def categories_present(self) -> frozenset[SourceCategory]:
        """The source categories this context actually carries evidence for."""
        present: set[SourceCategory] = set()
        if self.functional_artifacts:
            present.add(SourceCategory.FUNCTIONAL)
        if self.security_artifacts:
            present.add(SourceCategory.SECURITY)
        if self.quality_artifacts:
            present.add(SourceCategory.QUALITY)
        return frozenset(present)


class ContextMetadata(Schema):
    """The engineering surface the evidence sits on."""

    model_config = ConfigDict(alias_generator=to_camel)

    risk_level: RiskLevel = Field(..., description="Risk rolled up across all evidence.")
    components: tuple[str, ...] = Field(
        default=(), description="Distinct components the evidence touches, sorted."
    )
    endpoints: tuple[str, ...] = Field(
        default=(), description="Distinct endpoints the evidence touches, sorted."
    )


class ContextCorrelation(Schema):
    """An **asserted** relationship between two evidence artifacts.

    CAP-076A Invariant 2: *correlation is asserted, never implied*. Co-presence
    in a context is not co-reference. A correlation may only be recorded when a
    concrete ``basis`` justifies it; an empty correlation tuple therefore means
    "no relationship is claimed", not "no relationship exists".
    """

    model_config = ConfigDict(alias_generator=to_camel)

    from_artifact_id: str = Field(..., min_length=1)
    to_artifact_id: str = Field(..., min_length=1)
    basis: str = Field(..., min_length=1, description="Why the two are related.")


class ContextDependencies(Schema):
    """What links the evidence together, and to other contexts.

    Empty at CAP-076B. Correlation inference is a later milestone; this model
    reserves its home so that landing it requires no change to Consolidation.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    correlations: tuple[ContextCorrelation, ...] = Field(default=())
    related_context_ids: tuple[EngineeringContextId, ...] = Field(default=())


class ContextProvenance(Schema):
    """How this context came to exist — which groups fed it, and how much.

    Traceability of individual evidence is not duplicated here: every
    ``SourceArtifact`` already carries ``(source_system, source_record_id)``.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    contributing_consolidated_ids: tuple[str, ...] = Field(
        ...,
        min_length=1,
        description="Ids of the ConsolidatedArtifacts that contributed, in order.",
    )
    contributing_group_count: int = Field(..., ge=1)
    source_artifact_count: int = Field(..., ge=1)


class OrchestrationMetadata(Schema):
    """Which governed policy composed this context, and against which model shape.

    Recording the policy identity *inside* the context is what makes a historical
    execution package interpretable: without it, a result cannot be attributed to
    the rules that produced it.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    policy_id: OrchestrationPolicyId = Field(...)
    policy_version: PolicyVersion = Field(...)
    context_model_version: str = Field(default=ENGINEERING_CONTEXT_VERSION)


class EngineeringContext(Schema):
    """The canonical, immutable orchestration model.

    Constructed exclusively by
    :class:`~requirement_intelligence.context_orchestration.engineering_context_builder.EngineeringContextBuilder`.
    Nothing consumes this model at CAP-076B; runtime integration is CAP-076C.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    context_id: EngineeringContextId = Field(..., description="Deterministic context identity.")
    subject: ContextSubject = Field(...)
    evidence: ContextEvidence = Field(...)
    context_metadata: ContextMetadata = Field(...)
    dependencies: ContextDependencies = Field(default_factory=ContextDependencies)
    provenance: ContextProvenance = Field(...)
    orchestration: OrchestrationMetadata = Field(...)
    orchestration_reason: str = Field(
        ...,
        min_length=1,
        description="The single explainable sentence recording why this context was composed.",
    )

    @model_validator(mode="after")
    def _validate_context(self) -> EngineeringContext:
        """Enforce the invariants a context must satisfy to be well-formed."""
        if self.evidence.total_count == 0:
            raise ValueError(
                "An EngineeringContext must carry at least one evidence artifact; "
                "an empty context is not a context."
            )
        if self.evidence.total_count != self.provenance.source_artifact_count:
            raise ValueError(
                f"Provenance disagrees with evidence: "
                f"sourceArtifactCount={self.provenance.source_artifact_count} but "
                f"{self.evidence.total_count} evidence artifacts are present."
            )
        if self.provenance.contributing_group_count != len(
            self.provenance.contributing_consolidated_ids
        ):
            raise ValueError(
                f"Provenance disagrees with itself: "
                f"contributingGroupCount={self.provenance.contributing_group_count} but "
                f"{len(self.provenance.contributing_consolidated_ids)} contributing ids "
                f"are recorded."
            )
        return self
