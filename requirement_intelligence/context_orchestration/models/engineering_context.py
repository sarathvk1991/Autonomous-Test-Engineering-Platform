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
from requirement_intelligence.models.enums import RiskLevel, SourceCategory, SourceSystem
from requirement_intelligence.models.source_artifact import SourceArtifact
from shared.contracts.base import Schema

#: Version of the :class:`EngineeringContext` *shape* — the single source of
#: truth. Advances additively; breaking changes are ADR-gated, matching
#: ``PROMPT_DEFINITION_VERSION``.
#:
#: 1.1 (CAP-076C) reshaped :class:`ContextProvenance` around
#: :class:`ContextContribution`. The 1.0 shape was never serialised by anything —
#: no execution package, baseline, or persisted artifact carries it — so the
#: change invalidates no stored data.
#:
#: 1.2 (CAP-076D) added :class:`ContextRanking`, :class:`ContextCoverage`,
#: :class:`ContextEvidenceBudgetUsage` and :class:`ContextGrounding`. Activating
#: a multi-source policy without them would have hidden the orchestration
#: decisions that policy makes, which is precisely what CAP-076A Invariant 7
#: forbids: a context must explain every group it took *and* every group it left.
ENGINEERING_CONTEXT_VERSION = "1.2"

#: The three engineering evidence domains, in the canonical order every
#: projection of a context uses: the prompt's three sections, the coverage
#: summary, the budget allocation, and the grounding metadata. Fixing the order
#: here — rather than deriving it from set iteration at each call site — is what
#: keeps those four projections mutually consistent and byte-reproducible.
EVIDENCE_DOMAINS: tuple[SourceCategory, ...] = (
    SourceCategory.FUNCTIONAL,
    SourceCategory.SECURITY,
    SourceCategory.QUALITY,
)


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


class RankingScoreComponent(Schema):
    """One candidate group's value for one of the policy's ranking keys.

    A context records the *ordered key values* a group was sorted on rather than
    a single scalar score. There is no scalar: a deterministic ranking is a
    lexicographic comparison of these components in the policy's declared key
    order, and collapsing them into one number would invent a weighting the
    policy never declared.

    ``key`` is the ``RankingKey``'s string value, not the enum. The context model
    must not import the policy package — the policy already imports the identity
    models this module sits beside, and a models→policy edge would close that
    cycle. A context is a *record* of decisions; the vocabulary that produced
    them lives in the policy.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    key: str = Field(..., min_length=1, description="The RankingKey this component scores.")
    value: str = Field(..., description="The group's value for that key, as it was ordered.")


class ContextRankingEntry(Schema):
    """One candidate group's position in the ranking, and its fate.

    Every candidate the orchestrator considered gets an entry — selected or not.
    :attr:`decision_reason` is what makes an exclusion falsifiable: without it a
    reader can see that a group lost but not why, which is indistinguishable
    from a hidden ranking.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    rank: int = Field(..., ge=1, description="1-based position in the policy's ranking.")
    consolidated_id: str = Field(..., min_length=1)
    risk_level: RiskLevel = Field(...)
    candidate_artifact_count: int = Field(..., ge=0, description="Artifacts the group carries.")
    contributed_artifact_count: int = Field(
        default=0, ge=0, description="Artifacts the group contributed to the context."
    )
    score: tuple[RankingScoreComponent, ...] = Field(
        ..., min_length=1, description="The ordered key values this group was ranked on."
    )
    selected: bool = Field(..., description="Whether this group contributed evidence.")
    decision_reason: str = Field(..., min_length=1, description="Why it was admitted or excluded.")

    @model_validator(mode="after")
    def _validate_entry(self) -> ContextRankingEntry:
        """A group that contributed nothing is not selected, and vice versa."""
        if self.selected and self.contributed_artifact_count == 0:
            raise ValueError(
                f"Group '{self.consolidated_id}' is marked selected but contributed no artifacts."
            )
        if not self.selected and self.contributed_artifact_count != 0:
            raise ValueError(
                f"Group '{self.consolidated_id}' is not selected but contributed "
                f"{self.contributed_artifact_count} artifact(s)."
            )
        if self.contributed_artifact_count > self.candidate_artifact_count:
            raise ValueError(
                f"Group '{self.consolidated_id}' contributed "
                f"{self.contributed_artifact_count} of only "
                f"{self.candidate_artifact_count} artifact(s) it carries."
            )
        return self


class ContextRanking(Schema):
    """The complete, ordered ranking the policy produced over every candidate.

    This is the orchestration decision record. Nothing downstream may re-derive
    a rank: :class:`~requirement_intelligence.execution.execution_metrics` reads
    :attr:`entries` rather than re-sorting the consolidated artifacts, because a
    second implementation of the ranking rule is a second ranking rule.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    keys: tuple[str, ...] = Field(..., min_length=1, description="Policy ranking keys, in order.")
    tie_breaker: str = Field(..., min_length=1, description="The final total-order key.")
    entries: tuple[ContextRankingEntry, ...] = Field(..., min_length=1)

    @property
    def selected_consolidated_ids(self) -> tuple[str, ...]:
        """Ids of the ranked groups that contributed, in rank order."""
        return tuple(entry.consolidated_id for entry in self.entries if entry.selected)

    @property
    def excluded_consolidated_ids(self) -> tuple[str, ...]:
        """Ids of the ranked groups that contributed nothing, in rank order."""
        return tuple(entry.consolidated_id for entry in self.entries if not entry.selected)

    def rank_of(self, consolidated_id: str) -> int | None:
        """Return the rank recorded for *consolidated_id*, or ``None`` if unranked."""
        for entry in self.entries:
            if entry.consolidated_id == consolidated_id:
                return entry.rank
        return None

    @model_validator(mode="after")
    def _validate_ranking(self) -> ContextRanking:
        """Ranks must be a contiguous 1..n permutation listed in ascending order."""
        ranks = [entry.rank for entry in self.entries]
        if ranks != list(range(1, len(ranks) + 1)):
            raise ValueError(f"Ranks must be a contiguous ascending 1..n sequence; got {ranks!r}.")
        ids = [entry.consolidated_id for entry in self.entries]
        if len(set(ids)) != len(ids):
            raise ValueError("A consolidated id may appear at most once in the ranking.")
        for entry in self.entries:
            if len(entry.score) != len(self.keys):
                raise ValueError(
                    f"Group '{entry.consolidated_id}' scores {len(entry.score)} component(s) "
                    f"against {len(self.keys)} ranking key(s)."
                )
        return self


class ContextCoverageDomain(Schema):
    """What one evidence domain contributed, and why it did or did not.

    :attr:`evidence_present` is measured over the *candidates*, not the context.
    That is the whole point: a domain that had evidence available and was still
    left out is the CAP-074B defect, and this model is where it becomes visible.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    category: SourceCategory = Field(...)
    evidence_present: bool = Field(..., description="Any candidate group carried this domain.")
    represented: bool = Field(..., description="This domain reached the context.")
    candidate_artifact_count: int = Field(..., ge=0, description="Available across candidates.")
    contributed_artifact_count: int = Field(..., ge=0, description="Present in the context.")
    contributing_group_count: int = Field(..., ge=0)
    truncated: bool = Field(
        ...,
        description=(
            "Less evidence reached the context than the candidates offered. The cause — "
            "the selection strategy, the evidence budget, or both — is stated in 'reason'."
        ),
    )
    reason: str = Field(..., min_length=1, description="Why this domain is represented, or is not.")

    @model_validator(mode="after")
    def _validate_domain(self) -> ContextCoverageDomain:
        """Representation and contribution must agree, and neither may exceed availability."""
        if self.represented != (self.contributed_artifact_count > 0):
            raise ValueError(
                f"Domain '{self.category}' claims represented={self.represented} while "
                f"contributing {self.contributed_artifact_count} artifact(s)."
            )
        if self.contributed_artifact_count > self.candidate_artifact_count:
            raise ValueError(
                f"Domain '{self.category}' contributed {self.contributed_artifact_count} of "
                f"only {self.candidate_artifact_count} available artifact(s)."
            )
        if self.evidence_present != (self.candidate_artifact_count > 0):
            raise ValueError(
                f"Domain '{self.category}' claims evidencePresent={self.evidence_present} with "
                f"{self.candidate_artifact_count} candidate artifact(s)."
            )
        return self


class ContextCoverage(Schema):
    """Whether the policy's coverage rule was satisfied, and what was covered.

    Two distinct booleans, deliberately not merged:

    * :attr:`rule_satisfied` — did the context meet the coverage rule the policy
      *declared*? ``LegacySelectionPolicy`` declares ``single_largest_group``,
      and satisfies it, while showing a reasoner one domain out of three.
    * :attr:`all_present_categories_represented` — did every domain that had
      evidence actually reach the reasoner?

    Collapsing these would let a satisfied policy report "covered" over the exact
    defect CAP-074B identified. Legacy runs are expected to report
    ``ruleSatisfied=true`` alongside ``allPresentCategoriesRepresented=false``.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    mode: str = Field(..., min_length=1, description="The CoverageMode the policy declared.")
    selection_strategy: str = Field(..., min_length=1)
    domains: tuple[ContextCoverageDomain, ...] = Field(..., min_length=1)
    rule_satisfied: bool = Field(...)
    all_present_categories_represented: bool = Field(...)

    @property
    def represented_categories(self) -> tuple[SourceCategory, ...]:
        """Domains that reached the context, in canonical order."""
        return tuple(domain.category for domain in self.domains if domain.represented)

    @property
    def present_categories(self) -> tuple[SourceCategory, ...]:
        """Domains any candidate group carried, in canonical order."""
        return tuple(domain.category for domain in self.domains if domain.evidence_present)

    @model_validator(mode="after")
    def _validate_coverage(self) -> ContextCoverage:
        """The observational flag is derived, never asserted independently."""
        observed = all(
            domain.represented for domain in self.domains if domain.evidence_present
        ) and any(domain.evidence_present for domain in self.domains)
        if self.all_present_categories_represented != observed:
            raise ValueError(
                f"allPresentCategoriesRepresented={self.all_present_categories_represented} "
                f"contradicts the per-domain record, which shows {observed}."
            )
        return self


class DomainBudgetUsage(Schema):
    """One domain's slice of the evidence budget, and how much of it was spent."""

    model_config = ConfigDict(alias_generator=to_camel)

    category: SourceCategory = Field(...)
    available: int = Field(..., ge=0, description="Artifacts the candidates offered this domain.")
    allocated: int = Field(..., ge=0, description="Artifacts the budget permitted this domain.")
    used: int = Field(..., ge=0, description="Artifacts this domain contributed.")

    @property
    def truncated(self) -> bool:
        """The budget bound this domain: it offered more than it was permitted.

        Distinct from :attr:`ContextCoverageDomain.truncated`, which asks whether
        less evidence reached the context than was offered — true whenever the
        *strategy* left a group behind, budget or no budget. This asks only
        whether the **budget** was the constraint, so a run that lost evidence to
        single-group selection does not report a budget it never came near.
        """
        return self.available > self.allocated

    @model_validator(mode="after")
    def _validate_usage(self) -> DomainBudgetUsage:
        """Spend may never exceed the allocation, nor the available evidence."""
        if self.used > self.allocated:
            raise ValueError(
                f"Domain '{self.category}' used {self.used} artifact(s) against an "
                f"allocation of {self.allocated}."
            )
        if self.used > self.available:
            raise ValueError(
                f"Domain '{self.category}' used {self.used} of only {self.available} available."
            )
        return self


class ContextEvidenceBudgetUsage(Schema):
    """The policy's evidence budget as it was actually allocated and spent.

    Allocation is a deterministic function of the policy's bounds and the
    evidence the candidates offered; it is computed once, by the orchestrator,
    and recorded here. Nothing downstream recomputes it.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    max_artifacts_per_domain: int = Field(..., ge=1)
    max_artifacts_total: int = Field(..., ge=1)
    domains: tuple[DomainBudgetUsage, ...] = Field(..., min_length=1)

    @property
    def total_allocated(self) -> int:
        """Artifacts the budget permitted across every domain."""
        return sum(domain.allocated for domain in self.domains)

    @property
    def total_used(self) -> int:
        """Artifacts the context actually carries."""
        return sum(domain.used for domain in self.domains)

    @property
    def total_available(self) -> int:
        """Artifacts the candidate groups offered across every domain."""
        return sum(domain.available for domain in self.domains)

    @property
    def truncated(self) -> bool:
        """The budget bound at least one domain."""
        return any(domain.truncated for domain in self.domains)

    @model_validator(mode="after")
    def _validate_budget(self) -> ContextEvidenceBudgetUsage:
        """Allocation must respect both the per-domain and the total bound."""
        for domain in self.domains:
            if domain.allocated > self.max_artifacts_per_domain:
                raise ValueError(
                    f"Domain '{domain.category}' was allocated {domain.allocated} artifact(s), "
                    f"above the per-domain bound of {self.max_artifacts_per_domain}."
                )
        if self.total_allocated > self.max_artifacts_total:
            raise ValueError(
                f"Allocation totals {self.total_allocated} artifact(s), above the total "
                f"bound of {self.max_artifacts_total}."
            )
        return self


class SourceDistributionEntry(Schema):
    """How many of a context's evidence artifacts came from one source system."""

    model_config = ConfigDict(alias_generator=to_camel)

    source_system: SourceSystem = Field(...)
    artifact_count: int = Field(..., ge=1)


class ContextGrounding(Schema):
    """Observational metadata describing what the context is grounded in.

    Grounding is a *measurement* of the assembled evidence, taken after every
    orchestration decision has been made. It changes nothing: Validation and CP1
    never read it (CAP-076D Stage 7). It exists so a reader can answer "what did
    this reasoning session actually stand on?" without re-reading the evidence.

    It deliberately does not restate coverage or budget facts — those live in
    :class:`ContextCoverage` and :class:`ContextEvidenceBudgetUsage`, and a
    second copy would be a second source of truth.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    evidence_domains: tuple[SourceCategory, ...] = Field(
        ..., min_length=1, description="Domains the context carries, in canonical order."
    )
    functional_count: int = Field(..., ge=0)
    security_count: int = Field(..., ge=0)
    quality_count: int = Field(..., ge=0)
    total_count: int = Field(..., ge=1)
    source_distribution: tuple[SourceDistributionEntry, ...] = Field(
        ..., min_length=1, description="Evidence per origin system, sorted by system."
    )

    @model_validator(mode="after")
    def _validate_grounding(self) -> ContextGrounding:
        """Counts must agree with each other and with the distribution."""
        if self.functional_count + self.security_count + self.quality_count != self.total_count:
            raise ValueError(
                f"Grounding domain counts sum to "
                f"{self.functional_count + self.security_count + self.quality_count}, "
                f"not the declared total of {self.total_count}."
            )
        distributed = sum(entry.artifact_count for entry in self.source_distribution)
        if distributed != self.total_count:
            raise ValueError(
                f"Source distribution accounts for {distributed} artifact(s), "
                f"not the declared total of {self.total_count}."
            )
        return self


class ContextContribution(Schema):
    """One :class:`ConsolidatedArtifact`'s documented contribution to a context.

    Carries the group's own identity and grouping facts alongside the
    orchestrator's :attr:`inclusion_reason` — the explicit answer to *"why is
    this group in this context?"*. Nothing about a contributing group is left
    implicit, so a context needs no access to Consolidation to be explained
    (CAP-076C Stage 9).

    ``module`` and ``consolidation_reason`` are recorded rather than re-derived
    because they are Consolidation's outputs, not Orchestration's, and only the
    contributing group knows them.

    ``artifact_count`` counts what the group *contributed*, which under an
    evidence budget can be fewer than the ``candidate_artifact_count`` it
    carries. Recording both is what makes truncation visible; recording only the
    first would silently misreport the group as small (CAP-076D Stage 4).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    consolidated_id: str = Field(..., min_length=1, description="The contributing group's id.")
    module: str = Field(..., min_length=1, description="The group's module / component.")
    business_area: str | None = Field(default=None)
    consolidation_reason: str | None = Field(
        default=None, description="Why Consolidation grouped these records together."
    )
    rank: int = Field(..., ge=1, description="The group's position in the policy's ranking.")
    artifact_count: int = Field(..., ge=1, description="Source artifacts the group contributed.")
    candidate_artifact_count: int = Field(..., ge=1, description="Source artifacts it carries.")
    functional_count: int = Field(default=0, ge=0)
    security_count: int = Field(default=0, ge=0)
    quality_count: int = Field(default=0, ge=0)
    inclusion_reason: str = Field(
        ...,
        min_length=1,
        description="Why the orchestrator's policy admitted this group into the context.",
    )

    @property
    def truncated(self) -> bool:
        """The evidence budget admitted only part of what this group carries."""
        return self.artifact_count < self.candidate_artifact_count

    @model_validator(mode="after")
    def _validate_contribution(self) -> ContextContribution:
        """Per-domain counts must reconstruct the contribution, which must fit the group."""
        domains = self.functional_count + self.security_count + self.quality_count
        if domains != self.artifact_count:
            raise ValueError(
                f"Group '{self.consolidated_id}' declares {self.artifact_count} contributed "
                f"artifact(s) but its domain counts sum to {domains}."
            )
        if self.artifact_count > self.candidate_artifact_count:
            raise ValueError(
                f"Group '{self.consolidated_id}' contributed {self.artifact_count} of only "
                f"{self.candidate_artifact_count} artifact(s) it carries."
            )
        return self


class ContextProvenance(Schema):
    """How this context came to exist — which groups fed it, and how much.

    Traceability of individual evidence is not duplicated here: every
    ``SourceArtifact`` already carries ``(source_system, source_record_id)``.

    :attr:`candidate_group_count` records how many groups the orchestrator
    *considered*, not merely how many it chose. Without it, "selected the
    largest group" is unfalsifiable — a reader cannot tell a policy that
    discarded four candidates from one that had no choice to make.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    contributions: tuple[ContextContribution, ...] = Field(
        ...,
        min_length=1,
        description="The contributing groups, in the order the orchestrator selected them.",
    )
    candidate_group_count: int = Field(
        ..., ge=1, description="Groups the policy ranked, including those not selected."
    )
    source_artifact_count: int = Field(..., ge=1)

    @property
    def contributing_consolidated_ids(self) -> tuple[str, ...]:
        """Ids of the ConsolidatedArtifacts that contributed, in selection order."""
        return tuple(contribution.consolidated_id for contribution in self.contributions)

    @property
    def contributing_group_count(self) -> int:
        """How many groups contributed evidence to this context."""
        return len(self.contributions)

    @model_validator(mode="after")
    def _validate_provenance(self) -> ContextProvenance:
        """A context cannot draw on more groups than the policy ever considered."""
        if self.candidate_group_count < self.contributing_group_count:
            raise ValueError(
                f"candidateGroupCount ({self.candidate_group_count}) is below the "
                f"{self.contributing_group_count} group(s) that contributed."
            )
        return self


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
    It is the complete reasoning input a session receives, and — through
    :attr:`ranking`, :attr:`coverage` and :attr:`evidence_budget` — the complete
    record of how that input was chosen.

    The validator below is the reason those four sections can be trusted: every
    projection of a context (the prompt, ``engineering_context.json``, the
    manifest, the execution metrics) reads one of them, and they are checked
    against the evidence they claim to describe rather than against each other's
    good intentions.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    context_id: EngineeringContextId = Field(..., description="Deterministic context identity.")
    subject: ContextSubject = Field(...)
    evidence: ContextEvidence = Field(...)
    context_metadata: ContextMetadata = Field(...)
    dependencies: ContextDependencies = Field(default_factory=ContextDependencies)
    provenance: ContextProvenance = Field(...)
    orchestration: OrchestrationMetadata = Field(...)
    ranking: ContextRanking = Field(..., description="Every candidate group, ranked and decided.")
    coverage: ContextCoverage = Field(..., description="Which evidence domains were covered.")
    evidence_budget: ContextEvidenceBudgetUsage = Field(
        ..., description="How the policy's budget was allocated and spent."
    )
    grounding: ContextGrounding = Field(
        ..., description="Observational measurement of the assembled evidence."
    )
    orchestration_reason: str = Field(
        ...,
        min_length=1,
        description="The single explainable sentence recording why this context was composed.",
    )

    @model_validator(mode="after")
    def _validate_context(self) -> EngineeringContext:
        """Enforce the invariants a context must satisfy to be well-formed."""
        evidence = self.evidence
        if evidence.total_count == 0:
            raise ValueError(
                "An EngineeringContext must carry at least one evidence artifact; "
                "an empty context is not a context."
            )
        if evidence.total_count != self.provenance.source_artifact_count:
            raise ValueError(
                f"Provenance disagrees with evidence: "
                f"sourceArtifactCount={self.provenance.source_artifact_count} but "
                f"{evidence.total_count} evidence artifacts are present."
            )
        contributed = sum(c.artifact_count for c in self.provenance.contributions)
        if contributed != evidence.total_count:
            raise ValueError(
                f"Contributions disagree with evidence: the contributing groups declare "
                f"{contributed} artifacts but {evidence.total_count} are present."
            )
        self._validate_ranking_agrees_with_provenance()
        self._validate_domain_counts_agree_with_evidence()
        return self

    def _validate_ranking_agrees_with_provenance(self) -> None:
        """The groups the ranking says it selected are exactly the ones that contributed."""
        if self.ranking.selected_consolidated_ids != self.provenance.contributing_consolidated_ids:
            raise ValueError(
                f"Ranking selected {list(self.ranking.selected_consolidated_ids)!r} but "
                f"provenance records {list(self.provenance.contributing_consolidated_ids)!r} "
                f"as contributing."
            )
        if len(self.ranking.entries) != self.provenance.candidate_group_count:
            raise ValueError(
                f"Ranking holds {len(self.ranking.entries)} entries against "
                f"{self.provenance.candidate_group_count} candidate group(s)."
            )

    def _validate_domain_counts_agree_with_evidence(self) -> None:
        """Coverage, budget and grounding must each count the evidence that is present."""
        actual = {
            SourceCategory.FUNCTIONAL: len(self.evidence.functional_artifacts),
            SourceCategory.SECURITY: len(self.evidence.security_artifacts),
            SourceCategory.QUALITY: len(self.evidence.quality_artifacts),
        }
        for domain in self.coverage.domains:
            if domain.contributed_artifact_count != actual[SourceCategory(domain.category)]:
                raise ValueError(
                    f"Coverage claims {domain.contributed_artifact_count} '{domain.category}' "
                    f"artifact(s); the evidence carries "
                    f"{actual[SourceCategory(domain.category)]}."
                )
        for usage in self.evidence_budget.domains:
            if usage.used != actual[SourceCategory(usage.category)]:
                raise ValueError(
                    f"Budget records {usage.used} '{usage.category}' artifact(s) used; the "
                    f"evidence carries {actual[SourceCategory(usage.category)]}."
                )
        grounded = (
            self.grounding.functional_count,
            self.grounding.security_count,
            self.grounding.quality_count,
        )
        if grounded != tuple(actual[domain] for domain in EVIDENCE_DOMAINS):
            raise ValueError(
                f"Grounding counts {grounded} disagree with the evidence "
                f"{tuple(actual[domain] for domain in EVIDENCE_DOMAINS)}."
            )
