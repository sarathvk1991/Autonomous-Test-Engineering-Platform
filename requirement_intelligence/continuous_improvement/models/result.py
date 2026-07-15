"""The :class:`ContinuousImprovementResult` — the frozen runtime contract of the
Continuous Improvement Framework (CAP-083A architecture freeze; CAP-083B
deterministic engine; CAP-083B.1 permanent runtime-contract certification,
ADR-0022 §D3/§D4/§D10).

CAP-083A froze the architecture before any engine existed. CAP-083B implemented the
first deterministic engine behind that unchanged contract. CAP-083B.1 makes no
behavioural change whatsoever — it permanently certifies ``ContinuousImprovementResult``
as *the complete, deterministic runtime record produced from exactly one execution of*
``ContinuousImprovementService.improve()``, exactly as CAP-082B.1 certified
``RecommendationResult``, CAP-081B.1 certified ``RequirementEnhancementResult``, and
CAP-080B.1.1 certified ``QualityAssessmentResult`` ahead of their own runtime
activations.

It **is**:

* the complete runtime output — the single object that crosses from
  ``DeterministicContinuousImprovementEngine`` into serialization, exactly as
  ``RecommendationResult`` crosses from the Recommendation Framework's runtime
  service;
* the canonical runtime contract — the only Continuous Improvement aggregate, the
  first Layer 2 runtime contract (ADR-0020), a peer to no Layer 1 result (it
  consumes none of them directly, ADR-0021 §Stage 8) and consumed by no other Layer
  2 capability yet;
* independently versioned — ``result_version`` (:class:`ContinuousImprovementResultVersion`)
  evolves on its own axis, never forcing (or forced by) the framework, policy, rule,
  rule-catalogue, or engine versions, and vice versa (ADR-0022 §D10, mirroring
  ADR-0019 §D9);
* deterministic — a pure function of the resolved Historical Dataset and the
  governed policy/rule-catalogue; no randomness, no wall-clock dependence beyond the
  injected clock;
* immutable — ``frozen=True`` (via ``Schema``), tuple-backed collections, no field
  can change after construction;
* self-contained — every finding, trend, opportunity, summary metric, and consumed
  historical-dataset reference already lives here, so the result is reproducible
  with no need to re-run Continuous Improvement or inspect any runtime service
  (Recommendation 8, ADR-0022 §D10);
* explainable — every finding, trend, and opportunity is reconstructable from this
  object alone; no upstream subsystem, engine, provider, policy, or service need
  ever be inspected or re-run;
* serializer-independent — a future serializer projects this object; this object
  never depends on a serializer existing (Recommendation 8);
* execution-package-independent — this object exists and is fully meaningful with no
  Execution Package, CLI phase, or manifest wired to it at all (CAP-083B — none of
  those exist yet);
* historical-storage-independent — this object never depends on a real Historical
  Dataset implementation existing; it references one by id only
  (``HistoricalDatasetReference``, Recommendation 2) and is equally valid whether
  that dataset is backed by the CAP-083B deterministic provider or a future real
  implementation (Recommendation 10);
* engine-independent — this object's shape does not depend on which engine produced
  it; a future statistical, ML, or LLM engine emits the identical contract
  (Recommendation 5).

It is **not**:

* Runtime Truth; Historical Truth; a report; Markdown; JSON formatting; an
  execution artifact; a manifest; a CLI object; a renderer; a serializer; a
  transport object; a projection; an Execution Package object; a scorer; an
  optimizer; a predictor; the Continuous Improvement engine itself; a
  ``HistoricalDatasetProvider``; a service; a policy; a builder; a Historical
  Dataset.

Each of those is a separate, later owner that *consumes* this object (or, for
Historical Dataset, a separate, earlier owner this object *references* — never
embeds); none of them computes anything this object doesn't already carry.

The validators enforce cross-referential integrity only. No finding, trend,
opportunity, or metric is computed here (CAP-083A architecture; CAP-083B
implementation; CAP-083B.1 freeze, ADR-0022).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.continuous_improvement.identity import (
    ContinuousImprovementFrameworkVersion,
    ContinuousImprovementResultId,
    ContinuousImprovementResultVersion,
    ImprovementPolicyId,
    ImprovementPolicyVersion,
)
from requirement_intelligence.continuous_improvement.models.finding import ImprovementFinding
from requirement_intelligence.continuous_improvement.models.historical_dataset_reference import (
    HistoricalDatasetReference,
)
from requirement_intelligence.continuous_improvement.models.opportunity import (
    ImprovementOpportunity,
)
from requirement_intelligence.continuous_improvement.models.summary import (
    ImprovementMetrics,
    ImprovementSummary,
)
from requirement_intelligence.continuous_improvement.models.trend import ImprovementTrend
from shared.contracts.base import Schema

#: Version of the ``ContinuousImprovementResult`` **runtime contract** schema.
#: Independent of every other Continuous Improvement version axis —
#: ``ContinuousImprovementFrameworkVersion``, ``ImprovementPolicyVersion``,
#: ``ImprovementRuleVersion``, ``ImprovementRuleCatalogVersion``,
#: ``ImprovementEngineVersion``, ``ImprovementTrendVersion``, and
#: ``ImprovementAssessmentVersion`` — a change here never forces any of those to
#: change, and vice versa (frozen, CAP-083A, reaffirmed CAP-083B.1, ADR-0022
#: §D4/§D10, mirroring ``RecommendationResultVersion``, ADR-0019 §D4/§D9).
CONTINUOUS_IMPROVEMENT_RESULT_VERSION = ContinuousImprovementResultVersion(1, 0, 0)


class ContinuousImprovementResult(Schema):
    """The complete, deterministic set of improvement observations for one dataset.

    ``ContinuousImprovementResult`` is the **permanent runtime contract** — the
    only Continuous Improvement object that crosses into serialization. It is
    **not** a report, an execution artifact, serialization, a renderer, or a
    calculator: it already contains everything (every finding, every trend, every
    opportunity, the summary, the metrics, the governing policy identity/version,
    and the consumed historical-dataset reference) any downstream projection
    needs.

    **Serialization invariant (frozen, mirrors ADR-0019 §D8).** Every future
    execution artifact concerning Continuous Improvement will be a **pure
    projection** of a ``ContinuousImprovementResult`` — reproducible from it
    alone, computing nothing. A renderer must never call a Continuous Improvement
    engine, ``HistoricalDatasetProvider``, ``PlatformContext``, generate a
    finding, observe a trend, name an opportunity, compute a metric, or invoke a
    policy.

    **Ownership (frozen, CAP-083A, reaffirmed CAP-083B.1, ADR-0022 §D3/§D10).**
    This is the **sole** owner of every finding, trend, opportunity, summary
    metric, policy identity/version, and consumed historical-dataset reference
    produced by the Continuous Improvement Framework. Nothing upstream and
    nothing downstream owns these — no execution artifact, manifest, or other
    subsystem may duplicate that ownership. The engine that assembles this object
    (``DeterministicContinuousImprovementEngine``, CAP-083B) and the
    ``HistoricalDatasetProvider`` it privately consults (Recommendation 10) are
    both engine-internal implementation detail — neither is part of this
    contract, and neither is named by any field here.

    **Explainability (frozen, CAP-083A, Recommendation 6 of ADR-0022).** Every
    finding, trend, and opportunity is explainable entirely from this object's
    contents, traceable through the referenced ``HistoricalDatasetReference`` down
    to Runtime Truth and execution inputs (ADR-0021 §Stage 8) — no downstream
    consumer should ever need to re-run Continuous Improvement or inspect the
    engine, the provider, the service, or ``PlatformContext``.

    **Truth Hierarchy boundary (frozen, ADR-0021 §Stage 3).** This result is
    Derived Knowledge: reproducible from the ``HistoricalDatasetReference`` it
    consumed, but never itself Historical Truth or Runtime Truth. It must never be
    written back into the Historical Dataset it was computed from, and no future
    Continuous Improvement execution may consume a prior ``ContinuousImprovementResult``,
    ``ImprovementFinding``, ``ImprovementTrend``, or ``ImprovementOpportunity`` as
    an input (Recommendation 11: Derived Knowledge must never recursively consume
    Derived Knowledge).

    **Runtime boundary (frozen, CAP-083B.1, ADR-0022 §D10).** Runtime ends at this
    object: ``HistoricalDatasetReference`` → (private ``HistoricalDatasetProvider``
    → engine-internal ``HistoricalDataset``) → ``DeterministicContinuousImprovementEngine``
    → ``ContinuousImprovementResult``. Everything after that — serialization,
    reports, Markdown, JSON, the Execution Package — is projection only.

    **Golden regression boundary (frozen).** A future golden dataset compares this
    object's content, never Markdown or JSON formatting. A presentation change
    must never invalidate a runtime regression baseline; only a change to this
    object's content (or its ``result_version``) is a runtime regression.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    result_id: ContinuousImprovementResultId = Field(..., description="Deterministic result id.")
    historical_dataset: HistoricalDatasetReference = Field(
        ..., description="Provenance of the historical dataset this result was derived from."
    )

    findings: tuple[ImprovementFinding, ...] = Field(
        default=(), description="Every recurring issue observed across this dataset."
    )
    trends: tuple[ImprovementTrend, ...] = Field(
        default=(), description="Every observed trend across this dataset."
    )
    opportunities: tuple[ImprovementOpportunity, ...] = Field(
        default=(), description="Every deterministic opportunity named for this dataset."
    )
    summary: ImprovementSummary = Field(..., description="The headline summary of this run.")
    metrics: ImprovementMetrics = Field(..., description="The deterministic numeric roll-up.")

    policy_id: ImprovementPolicyId = Field(..., description="Identity of the governing policy.")
    policy_version: ImprovementPolicyVersion = Field(
        ..., description="Version of the governing policy."
    )
    framework_version: ContinuousImprovementFrameworkVersion = Field(...)
    result_version: ContinuousImprovementResultVersion = Field(
        default=CONTINUOUS_IMPROVEMENT_RESULT_VERSION,
        description="Version of the ContinuousImprovementResult runtime-contract schema.",
    )
    started_at: datetime = Field(..., description="When this Continuous Improvement run started.")
    completed_at: datetime = Field(
        ..., description="When this Continuous Improvement run completed."
    )

    @model_validator(mode="after")
    def _validate_result(self) -> ContinuousImprovementResult:
        """Cross-references and lifetime must be internally consistent."""
        if self.completed_at < self.started_at:
            raise ValueError("completed_at precedes started_at.")

        finding_ids = [finding.finding_id for finding in self.findings]
        if len(finding_ids) != len(set(finding_ids)):
            raise ValueError("findings must not contain duplicate ids.")

        trend_ids = [trend.trend_id for trend in self.trends]
        if len(trend_ids) != len(set(trend_ids)):
            raise ValueError("trends must not contain duplicate ids.")

        opportunity_ids = [opportunity.opportunity_id for opportunity in self.opportunities]
        if len(opportunity_ids) != len(set(opportunity_ids)):
            raise ValueError("opportunities must not contain duplicate ids.")

        known_finding_ids = set(finding_ids)
        known_trend_ids = set(trend_ids)
        for opportunity in self.opportunities:
            for finding_id in opportunity.source_finding_ids:
                if finding_id not in known_finding_ids:
                    raise ValueError(
                        f"ImprovementOpportunity {opportunity.opportunity_id!r} references "
                        f"finding {finding_id!r}, which is not present in this result's "
                        f"findings."
                    )
            for trend_id in opportunity.source_trend_ids:
                if trend_id not in known_trend_ids:
                    raise ValueError(
                        f"ImprovementOpportunity {opportunity.opportunity_id!r} references "
                        f"trend {trend_id!r}, which is not present in this result's trends."
                    )
        return self
