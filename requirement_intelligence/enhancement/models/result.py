"""The :class:`RequirementEnhancementResult` — the frozen runtime contract of the
Requirement Intelligence Enhancement Framework.

``RequirementEnhancementResult`` is the canonical repository-level aggregate the
Requirement Enhancement runtime will produce and
``RequirementEnhancementService.enhance`` will return — a peer to ``GroundingResult`` /
``ValidationResult`` / ``CP1Result`` / ``QualityGovernanceResult``. It ties the
enhancement to the run it enriched and **names the exact upstream inputs it consumed**
(:class:`EnhancementInputReference`), so the result is a complete, self-contained
record: every enriched requirement, relationship, and observation is explainable from
this object alone, with no need to re-run enhancement or inspect any runtime service
(Recommendation 5).

The validators enforce cross-referential integrity only. No enrichment, relationship,
observation, or metric is computed here (Stage 2/3, ADR-0018).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.enhancement.identity.enhancement_identity import (
    EnhancementFrameworkVersion,
    EnhancementPolicyId,
    EnhancementPolicyVersion,
    EnhancementResultVersion,
    RequirementEnhancementResultId,
)
from requirement_intelligence.enhancement.models.enums import EnhancementInputSource
from requirement_intelligence.enhancement.models.observations import (
    EnhancementFinding,
    RequirementObservation,
)
from requirement_intelligence.enhancement.models.relationships import RelationshipGraph
from requirement_intelligence.enhancement.models.requirements import EnhancedRequirement
from requirement_intelligence.enhancement.models.summary import (
    EnhancementMetrics,
    EnhancementSummary,
)
from shared.contracts.base import Schema

#: Version of the ``RequirementEnhancementResult`` **runtime contract** schema.
#: Independent of the framework, policy, relationship, and observation versions; a
#: change here never forces any of those to change, and vice versa.
ENHANCEMENT_RESULT_VERSION = EnhancementResultVersion(1, 0, 0)


class EnhancementInputReference(Schema):
    """The identity and version of one upstream input the enhancement run consumed.

    Records provenance only — which input (Engineering Context / Analysis Result),
    which id, and which contract version — never the input's contents. This mirrors
    ``ConsumedResultReference`` (ADR-0017 §D3) and is what makes the dependency graph
    of Recommendation 5 legible on the audit record without embedding (or coupling to)
    the upstream aggregates.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    source: EnhancementInputSource = Field(..., description="Which upstream input this names.")
    input_id: str = Field(..., min_length=1, description="Identity of the consumed input.")
    input_version: str = Field(
        ..., min_length=1, description="Contract/schema version of the consumed input."
    )


class RequirementEnhancementResult(Schema):
    """The complete, deterministic enhancement of one Requirement Intelligence run.

    ``RequirementEnhancementResult`` is the **runtime contract** — the only
    enhancement object that will cross into serialization. It is **not** a report, an
    execution artifact, serialization, a renderer, or a calculator: it already
    contains everything (enriched requirements, the relationship graph, observations,
    surfaced findings, the summary, the metrics, the governing policy identity/
    version, and the consumed-input provenance) any downstream projection needs.

    **Serialization invariant (frozen, mirrors ADR-0017 §D3/CAP-080A).** Every future
    execution artifact concerning Requirement Enhancement will be a **pure
    projection** of a ``RequirementEnhancementResult`` — reproducible from it alone,
    computing nothing.

    Ownership (frozen, Stage 3). This is the **sole** owner of every enriched
    requirement, relationship, observation, finding, summary, and metric produced by
    Requirement Enhancement. No execution artifact, manifest, or downstream subsystem
    may duplicate that ownership (mirroring ADR-0017 §D31's manifest-purity rule,
    applied here from the outset rather than retrofitted).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    result_id: RequirementEnhancementResultId = Field(..., description="Deterministic result id.")
    analysis_id: str = Field(..., min_length=1, description="The analysis this enhances.")
    execution_id: str = Field(..., min_length=1, description="The AI invocation this enhances.")

    enhanced_requirements: tuple[EnhancedRequirement, ...] = Field(
        default=(), description="Every enriched requirement produced by this run."
    )
    relationship_graph: RelationshipGraph = Field(
        ..., description="The single canonical requirement-relationship graph (Recommendation 6)."
    )
    observations: tuple[RequirementObservation, ...] = Field(
        default=(), description="Every raw observation produced by this run (Recommendation 3)."
    )
    findings: tuple[EnhancementFinding, ...] = Field(
        default=(), description="Every observation surfaced as a finding."
    )
    summary: EnhancementSummary = Field(..., description="The headline summary of this run.")
    metrics: EnhancementMetrics = Field(..., description="The deterministic numeric roll-up.")

    consumed_inputs: tuple[EnhancementInputReference, ...] = Field(
        default=(), description="The upstream inputs this result consumed (provenance only)."
    )

    policy_id: EnhancementPolicyId = Field(..., description="Identity of the governing policy.")
    policy_version: EnhancementPolicyVersion = Field(
        ..., description="Version of the governing policy."
    )
    framework_version: EnhancementFrameworkVersion = Field(...)
    result_version: EnhancementResultVersion = Field(
        default=ENHANCEMENT_RESULT_VERSION,
        description="Version of the RequirementEnhancementResult runtime-contract schema.",
    )
    started_at: datetime = Field(..., description="When enhancement started.")
    completed_at: datetime = Field(..., description="When enhancement completed.")

    @model_validator(mode="after")
    def _validate_result(self) -> RequirementEnhancementResult:
        """Provenance, cross-references, and lifetime must be internally consistent."""
        if self.completed_at < self.started_at:
            raise ValueError("completed_at precedes started_at.")

        sources = [reference.source for reference in self.consumed_inputs]
        if len(sources) != len(set(sources)):
            raise ValueError("consumed_inputs must not name the same source twice.")

        enhanced_ids = [item.enhanced_requirement_id for item in self.enhanced_requirements]
        if len(enhanced_ids) != len(set(enhanced_ids)):
            raise ValueError("enhanced_requirements must not contain duplicate ids.")

        observation_ids = {observation.observation_id for observation in self.observations}
        for finding in self.findings:
            if finding.observation_id not in observation_ids:
                raise ValueError(
                    f"Finding {finding.finding_id!r} references observation "
                    f"{finding.observation_id!r}, which is not present in this result's "
                    f"observations."
                )

        finding_ids = [finding.finding_id for finding in self.findings]
        if len(finding_ids) != len(set(finding_ids)):
            raise ValueError("findings must not contain duplicate ids.")

        relationship_ids = {
            relationship.relationship_id for relationship in self.relationship_graph.relationships
        }
        for enhanced in self.enhanced_requirements:
            for relationship_id in enhanced.relationship_ids:
                if relationship_id not in relationship_ids:
                    raise ValueError(
                        f"EnhancedRequirement {enhanced.enhanced_requirement_id!r} references "
                        f"relationship {relationship_id!r}, which is not present in this "
                        f"result's relationship graph."
                    )
            for observation_id in enhanced.observation_ids:
                if observation_id not in observation_ids:
                    raise ValueError(
                        f"EnhancedRequirement {enhanced.enhanced_requirement_id!r} references "
                        f"observation {observation_id!r}, which is not present in this "
                        f"result's observations."
                    )
        return self
