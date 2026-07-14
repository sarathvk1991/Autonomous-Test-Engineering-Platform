"""The :class:`RecommendationResult` — the frozen runtime contract of the
Recommendation Framework (CAP-082A, ADR-0019 §D3/§D4).

CAP-082A is a pure architecture milestone: no recommendation is generated, no
heuristic runs, no scoring is performed. ``RecommendationResult`` is nonetheless
frozen now, before any engine exists, exactly as CAP-081A froze
``RequirementEnhancementResult`` and CAP-080A froze ``QualityAssessmentResult`` ahead
of their own first implementations.

It **is**:

* the runtime contract — the single object that will cross from a future runtime
  into serialization, exactly as ``RequirementEnhancementResult`` crosses from the
  Requirement Enhancement runtime service's ``enhance`` method today;
* the only recommendation aggregate — a peer to ``RequirementEnhancementResult`` /
  ``GroundingResult`` / ``ValidationResult`` / ``CP1Result`` /
  ``QualityGovernanceResult``;
* the canonical recommendation boundary — every recommendation, group, summary,
  metric, and consumed-input reference already lives here, so the result is
  self-contained and reproducible with no need to re-run recommendation generation
  or inspect any runtime service (Recommendation 7).

It is **not**:

* a report; Markdown; an execution artifact; a renderer; a serializer; an Execution
  Package object; a scorer; a prioritizer; a grouping engine; the recommendation
  engine itself; a service; a policy; a builder.

Each of those is a separate, later owner that *consumes* this object; none of them
computes anything this object doesn't already carry.

The validators enforce cross-referential integrity only. No recommendation, group,
score, or metric is computed here (CAP-082A, ADR-0019).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.recommendation.identity.recommendation_identity import (
    RecommendationFrameworkVersion,
    RecommendationPolicyId,
    RecommendationPolicyVersion,
    RecommendationResultId,
    RecommendationResultVersion,
)
from requirement_intelligence.recommendation.models.enums import RecommendationSource
from requirement_intelligence.recommendation.models.group import RecommendationGroup
from requirement_intelligence.recommendation.models.recommendation import Recommendation
from requirement_intelligence.recommendation.models.summary import (
    RecommendationMetrics,
    RecommendationSummary,
)
from shared.contracts.base import Schema

#: Version of the ``RecommendationResult`` **runtime contract** schema. Independent
#: of every other recommendation version axis — ``RecommendationFrameworkVersion``,
#: ``RecommendationPolicyVersion``, and ``RecommendationVersion`` — a change here
#: never forces any of those to change, and vice versa (frozen, CAP-082A, ADR-0019
#: §D4). A future recommendation engine (``RecommendationEngineVersion``, should one
#: be introduced) would evolve without forcing this schema to change either — the
#: same independence ``EnhancementResultVersion`` gives Requirement Enhancement
#: (ADR-0018 §D8) and ``GroundingResultVersion`` gives Grounding (ADR-0016 §D16).
RECOMMENDATION_RESULT_VERSION = RecommendationResultVersion(1, 0, 0)


class RecommendationInputReference(Schema):
    """The identity and version of one upstream result the recommendation run consumed.

    Records provenance only — which upstream result (``RecommendationSource``), which
    id, and which contract version — never the result's contents. This mirrors
    ``EnhancementInputReference`` (ADR-0018) and ``ConsumedResultReference``
    (ADR-0017 §D3), and is what makes the dependency graph of Recommendation 1
    legible on the audit record without embedding (or coupling to) the upstream
    aggregates.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    source: RecommendationSource = Field(..., description="Which upstream result this names.")
    input_id: str = Field(..., min_length=1, description="Identity of the consumed input.")
    input_version: str = Field(
        ..., min_length=1, description="Contract/schema version of the consumed input."
    )


class RecommendationResult(Schema):
    """The complete, deterministic set of recommendations for one run.

    ``RecommendationResult`` is the **runtime contract** — the only recommendation
    object that will cross into serialization. It is **not** a report, an execution
    artifact, serialization, a renderer, or a calculator: it already contains
    everything (every recommendation, every group, the summary, the metrics, the
    governing policy identity/version, and the consumed-input provenance) any
    downstream projection needs.

    **Serialization invariant (frozen, mirrors ADR-0018 §D8 / ADR-0017 §D3/CAP-080A).**
    Every future execution artifact concerning recommendations will be a **pure
    projection** of a ``RecommendationResult`` — reproducible from it alone, computing
    nothing. A renderer must never call a recommendation engine, ``PlatformContext``,
    generate a recommendation, form a group, compute a metric, or invoke a policy.

    **Ownership (frozen, CAP-082A, ADR-0019 §D3).** This is the **sole** owner of
    every recommendation, group, summary metric, policy identity/version, and
    consumed-input provenance produced by the Recommendation Framework. Nothing
    upstream and nothing downstream owns these — no execution artifact, manifest, or
    other subsystem may duplicate that ownership (mirroring ADR-0017 §D31's
    manifest-purity rule, applied here from the outset rather than retrofitted).

    **Explainability (frozen, CAP-082A, Recommendation 7).** Every recommendation is
    explainable entirely from this object's ``recommendations``, ``groups``,
    ``summary``, and ``metrics`` — no downstream consumer should ever need to re-run
    recommendation generation or inspect the engine, the service, or
    ``PlatformContext``.

    **Runtime/Execution Package boundary (frozen, one-way, Recommendation 8).**
    ``Enhancement/Grounding/Validation/CP1/Quality Governance results →
    RecommendationService.recommend → RecommendationResult → Execution Package →
    JSON / Markdown / reports``. The Execution Package formats only; the runtime
    computes only; neither depends on the other. This milestone freezes the contract
    before any serializer, Execution Package integration, dashboard, or reporting
    work exists (Recommendation 8).

    **Golden regression boundary (frozen).** A future golden dataset compares this
    object's content, never Markdown or JSON formatting. A presentation change must
    never invalidate a runtime regression baseline; only a change to this object's
    content (or its ``result_version``) is a runtime regression.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    result_id: RecommendationResultId = Field(..., description="Deterministic result id.")
    analysis_id: str = Field(..., min_length=1, description="The analysis these recommend on.")
    execution_id: str = Field(
        ..., min_length=1, description="The AI invocation these recommend on."
    )

    recommendations: tuple[Recommendation, ...] = Field(
        default=(), description="Every recommendation produced by this run."
    )
    groups: tuple[RecommendationGroup, ...] = Field(
        default=(), description="Every recommendation group produced by this run."
    )
    summary: RecommendationSummary = Field(..., description="The headline summary of this run.")
    metrics: RecommendationMetrics = Field(..., description="The deterministic numeric roll-up.")

    consumed_inputs: tuple[RecommendationInputReference, ...] = Field(
        default=(), description="The upstream results this run consumed (provenance only)."
    )

    policy_id: RecommendationPolicyId = Field(..., description="Identity of the governing policy.")
    policy_version: RecommendationPolicyVersion = Field(
        ..., description="Version of the governing policy."
    )
    framework_version: RecommendationFrameworkVersion = Field(...)
    result_version: RecommendationResultVersion = Field(
        default=RECOMMENDATION_RESULT_VERSION,
        description="Version of the RecommendationResult runtime-contract schema.",
    )
    started_at: datetime = Field(..., description="When recommendation generation started.")
    completed_at: datetime = Field(..., description="When recommendation generation completed.")

    @model_validator(mode="after")
    def _validate_result(self) -> RecommendationResult:
        """Provenance, cross-references, and lifetime must be internally consistent."""
        if self.completed_at < self.started_at:
            raise ValueError("completed_at precedes started_at.")

        sources = [reference.source for reference in self.consumed_inputs]
        if len(sources) != len(set(sources)):
            raise ValueError("consumed_inputs must not name the same source twice.")

        recommendation_ids = [
            recommendation.recommendation_id for recommendation in self.recommendations
        ]
        if len(recommendation_ids) != len(set(recommendation_ids)):
            raise ValueError("recommendations must not contain duplicate ids.")

        group_ids = [group.group_id for group in self.groups]
        if len(group_ids) != len(set(group_ids)):
            raise ValueError("groups must not contain duplicate ids.")

        known_recommendation_ids = set(recommendation_ids)
        for group in self.groups:
            for recommendation_id in group.recommendation_ids:
                if recommendation_id not in known_recommendation_ids:
                    raise ValueError(
                        f"RecommendationGroup {group.group_id!r} references recommendation "
                        f"{recommendation_id!r}, which is not present in this result's "
                        f"recommendations."
                    )
        return self
