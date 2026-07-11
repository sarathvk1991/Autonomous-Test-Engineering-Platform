"""Canonical matching input models.

These are the **contract between the Grounding Service and every Grounding
Strategy**. A strategy consumes only these models — never ``EngineeringContext``,
``AnalysisResult``, ``ParsedResponse``, ``PlatformContext``, or any other runtime
object. Fixing a small, canonical, immutable input is what makes matching
deterministic, unit-testable in isolation, and reusable by every future strategy
(deterministic, semantic, citation, hybrid) without change.

Model roles
-----------
* :class:`MatchingRequirement` — one normalized generated requirement, *before*
  grading. It is deliberately **not** a ``GroundedRequirement``: a grounded
  requirement carries a classification, confidence, and explanation that only
  exist *after* matching, and its validators reject an ungraded instance. The two
  share one identity, though — ``requirement_id`` is minted the same deterministic
  way — so a link produced here names the requirement by the id it will keep.
* :class:`MatchingEvidence` — one evidence artifact reduced to its stable identity
  plus the text fields a matcher reads. Self-contained: no ``SourceArtifact`` import
  leaks into a strategy.
* :class:`MatchingRequest` — one requirement against the whole corpus. The service
  fans a context out into N requests so a strategy can evaluate each independently
  (and, later, in parallel) behind an unchanged contract.
* :class:`MatchingContext` — the complete, deterministic matching input for one run.

Determinism
-----------
No timestamps, no UUIDs, no mutable runtime objects, no service or builder
references. The only execution identifier carried is ``context_id``, which is itself
a deterministic function of the engineering context. Two runs over identical inputs
build equal contexts.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.grounding.config import GroundingConfiguration
from requirement_intelligence.grounding.identity import (
    GroundedRequirementId,
    GroundingConfigurationVersion,
    GroundingFrameworkVersion,
)
from requirement_intelligence.grounding.models.evidence import EvidenceReference
from requirement_intelligence.models.enums import SourceCategory
from shared.contracts.base import Schema


class MatchingRequirement(Schema):
    """One normalized generated requirement, before grounding grades it."""

    model_config = ConfigDict(alias_generator=to_camel)

    requirement_id: GroundedRequirementId = Field(..., description="Deterministic requirement id.")
    domain: SourceCategory = Field(..., description="The requirement's evidence domain.")
    text: str = Field(..., min_length=1, description="The generated requirement text.")
    position: int = Field(..., ge=0, description="Index within its category array in the response.")


class MatchingEvidence(Schema):
    """One evidence artifact reduced to its identity and matchable text fields.

    Carries everything a text matcher reads and nothing it does not. The stable
    identity lives in :attr:`reference`; ``artifact_id`` (a per-run uuid) is
    deliberately excluded so a context is reproducible.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    reference: EvidenceReference = Field(..., description="Stable identity of the evidence.")
    title: str = Field(..., min_length=1, description="Short human-readable summary.")
    description: str | None = Field(default=None, description="Full body text, when present.")
    tags: tuple[str, ...] = Field(default=(), description="Free-form labels carried from source.")
    severity: str | None = Field(default=None, description="Source severity string, when present.")
    status: str | None = Field(default=None, description="Source status string, when present.")
    component: str | None = Field(default=None, description="Owning component/module/project.")
    location: str | None = Field(default=None, description="Physical location (e.g. file:line).")


class MatchingRequest(Schema):
    """One requirement to be matched against the evidence corpus.

    The atomic unit a :class:`GroundingStrategy` evaluates. Immutable and complete:
    a strategy needs nothing beyond this to produce links.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    context_id: str = Field(..., min_length=1, description="Id of the context this belongs to.")
    requirement: MatchingRequirement = Field(..., description="The requirement to match.")
    evidence: tuple[MatchingEvidence, ...] = Field(
        default=(), description="The full evidence corpus, in canonical order."
    )
    configuration: GroundingConfiguration = Field(
        ..., description="Governed grounding configuration."
    )
    framework_version: GroundingFrameworkVersion = Field(...)
    configuration_version: GroundingConfigurationVersion = Field(...)

    @model_validator(mode="after")
    def _validate_request(self) -> MatchingRequest:
        """Declared versions must match the configuration that was supplied."""
        if self.configuration.version != self.configuration_version:
            raise ValueError("configuration_version disagrees with the supplied configuration.")
        if self.configuration.framework_version != self.framework_version:
            raise ValueError("framework_version disagrees with the supplied configuration.")
        return self


class MatchingContext(Schema):
    """The complete, deterministic matching input for one grounding run.

    The canonical contract between :class:`GroundingService` and every
    :class:`GroundingStrategy`. It carries the requirements to grade, the evidence
    corpus to grade them against, the governed configuration, and the versions that
    make the result interpretable — and nothing else.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    context_id: str = Field(..., min_length=1, description="Deterministic engineering-context id.")
    requirements: tuple[MatchingRequirement, ...] = Field(
        default=(), description="Normalized generated requirements, in response order."
    )
    evidence: tuple[MatchingEvidence, ...] = Field(
        default=(), description="The engineering-context evidence corpus, in canonical order."
    )
    configuration: GroundingConfiguration = Field(
        ..., description="Governed grounding configuration."
    )
    framework_version: GroundingFrameworkVersion = Field(...)
    configuration_version: GroundingConfigurationVersion = Field(...)

    @model_validator(mode="after")
    def _validate_context(self) -> MatchingContext:
        """Declared versions must match the configuration that was supplied."""
        if self.configuration.version != self.configuration_version:
            raise ValueError("configuration_version disagrees with the supplied configuration.")
        if self.configuration.framework_version != self.framework_version:
            raise ValueError("framework_version disagrees with the supplied configuration.")
        return self

    def to_requests(self) -> tuple[MatchingRequest, ...]:
        """Fan the context out into one :class:`MatchingRequest` per requirement.

        A pure structural projection — no matching, no scoring, no filtering,
        deterministic in requirement order. It exists so the Grounding Service can
        prepare N independent requests without a strategy ever seeing the whole
        context object.
        """
        return tuple(
            MatchingRequest(
                context_id=self.context_id,
                requirement=requirement,
                evidence=self.evidence,
                configuration=self.configuration,
                framework_version=self.framework_version,
                configuration_version=self.configuration_version,
            )
            for requirement in self.requirements
        )
