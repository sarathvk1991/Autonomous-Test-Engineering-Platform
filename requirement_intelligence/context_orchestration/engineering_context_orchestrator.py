"""EngineeringContextOrchestrator — the runtime's single orchestration point.

Sits between Consolidation and Analysis and answers the one question no other
component may answer: *which evidence does this reasoning session receive?*

    list[ConsolidatedArtifact]  ->  EngineeringContextOrchestrator  ->  EngineeringContext

Responsibilities
----------------
* Consume the ``ConsolidatedArtifact``s Consolidation produced.
* Execute the governed :class:`OrchestrationPolicy` — rank, select, cover, budget, order.
* Derive the :class:`ContextSubject` the context is about.
* Invoke :class:`EngineeringContextBuilder` to construct the context.
* Record every decision: the full ranking, the coverage outcome per domain, the
  budget allocation, and one reason per group — admitted *and* excluded.

It does **not** own grouping (Consolidation), connectors, prompt rendering,
analysis, validation, or execution writing. It reads consolidated artifacts and
returns a context; it never mutates either.

Policy support at CAP-076D
--------------------------
Both governed policies are now executable, and
:class:`~...policy.default_policy.DefaultOrchestrationPolicy` is the one the
runtime binds. The two differ only in the rules they declare:

===========================  =========================  ==============================
Rule                         ``LegacySelectionPolicy``  ``DefaultOrchestrationPolicy``
===========================  =========================  ==============================
Selection                    ``single_largest``         ``coverage_guaranteed``
Ranking                      size, then id              risk, size, then id
Evidence ordering            ``group_order``            ``risk_then_record_id``
Domains a reasoner receives  one                        every domain with evidence
===========================  =========================  ==============================

Legacy is retained, not deprecated: it is the control arm. Running both over the
same candidates is what proves a difference in output came from the policy and
not from the code that executes it.

The order of operations is not incidental
-----------------------------------------
Rank, then select per domain, then apply the budget, then order the assembled
evidence. Ranking before selection is what lets coverage draw the *best* group
per domain rather than the first. Budgeting during selection — rather than by
truncating afterwards — is what lets a 71-artifact group contribute its 25 most
severe findings instead of being dropped whole for not fitting.

Determinism (CAP-076A Invariant 7)
----------------------------------
Every ranking key is a total order over data the groups already carry, and the
policy's tie-breaker terminates every comparison. Budget allocation is integer
water-filling over a fixed domain order. Evidence ordering is a stable sort on
``(-risk, source_record_id)``. Two runs over the same consolidated artifacts
select the same groups, take the same artifacts, and order them identically.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from requirement_intelligence.context_orchestration.context_exceptions import (
    ContextBudgetExceededError,
    ContextOrchestrationError,
)
from requirement_intelligence.context_orchestration.engineering_context_builder import (
    EngineeringContextBuilder,
)
from requirement_intelligence.context_orchestration.evidence_budget import (
    allocate_evidence_budget,
)
from requirement_intelligence.context_orchestration.evidence_ordering import order_evidence
from requirement_intelligence.context_orchestration.evidence_selection import GroupContribution
from requirement_intelligence.context_orchestration.models.engineering_context import (
    EVIDENCE_DOMAINS,
    ContextCoverage,
    ContextCoverageDomain,
    ContextEvidence,
    ContextEvidenceBudgetUsage,
    ContextRanking,
    ContextRankingEntry,
    ContextSubject,
    ContextSubjectBasis,
    DomainBudgetUsage,
    EngineeringContext,
    RankingScoreComponent,
)
from requirement_intelligence.context_orchestration.policy.orchestration_policy import (
    CoverageMode,
    OrchestrationPolicy,
    RankingKey,
    SelectionStrategy,
    TieBreaker,
)
from requirement_intelligence.models.consolidated_artifact import ConsolidatedArtifact
from requirement_intelligence.models.enums import RiskLevel, SourceCategory
from requirement_intelligence.models.source_artifact import SourceArtifact

#: Severity ladder used by ``RISK_LEVEL_DESC``. Deliberately a local constant
#: rather than an import of ``consolidation_rules._RISK_ORDER``: orchestration
#: must not reach into Consolidation's private module, and ranking severity is
#: an orchestration concern (ADR-0015 §D3).
_RISK_RANK: dict[RiskLevel, int] = {
    RiskLevel.LOW: 0,
    RiskLevel.MEDIUM: 1,
    RiskLevel.HIGH: 2,
    RiskLevel.CRITICAL: 3,
}

#: Maps the grouping dimension encoded in a ``consolidated_id`` onto the subject
#: basis. ``build_consolidated_id`` mints ``cons-<dimension>-<slug>``; a group
#: does not otherwise retain the dimension it was formed on.
_BASIS_BY_DIMENSION: dict[str, ContextSubjectBasis] = {
    "component": ContextSubjectBasis.COMPONENT,
    "tag": ContextSubjectBasis.TAG,
    "endpoint": ContextSubjectBasis.ENDPOINT,
    "risk": ContextSubjectBasis.RISK,
}

_CONSOLIDATED_ID_PREFIX = "cons-"

#: Reads a group's artifacts for one evidence domain. The three domains are
#: separate attributes on ``ConsolidatedArtifact``, so a domain-generic
#: orchestrator needs this indirection exactly once.
_DOMAIN_ARTIFACTS = {
    SourceCategory.FUNCTIONAL: lambda group: group.functional_artifacts,
    SourceCategory.SECURITY: lambda group: group.security_artifacts,
    SourceCategory.QUALITY: lambda group: group.quality_artifacts,
}


@dataclass(frozen=True)
class ContextOrchestrationResult:
    """The orchestrator's output: the context, and the groups that composed it.

    ``context`` is the product. ``selected_groups`` is returned alongside it
    because the execution package still persists one ``ConsolidatedArtifact``
    verbatim (``consolidated_artifact.json``), and a context — which flattens and
    reorders evidence across its groups — cannot reconstitute one. The groups are
    in rank order, so ``selected_groups[0]`` is always :attr:`primary_group`.
    Callers read the groups; they never re-select.
    """

    context: EngineeringContext
    selected_groups: tuple[ConsolidatedArtifact, ...]

    @property
    def primary_group(self) -> ConsolidatedArtifact:
        """The highest-ranked contributing group — the context's subject.

        Under ``single_largest`` this is the only group. Under
        ``coverage_guaranteed`` it is the group the ranking put first, which is
        the group ``single_largest`` would also have chosen when the two policies
        rank alike. Naming it explicitly keeps the execution package's
        ``selectedArtifactId`` meaningful across the policy flip.
        """
        return self.selected_groups[0]


@dataclass(frozen=True)
class _Ranked:
    """One candidate group with the rank and score the policy gave it."""

    rank: int
    group: ConsolidatedArtifact
    score: tuple[RankingScoreComponent, ...]


def _total_artifacts(group: ConsolidatedArtifact) -> int:
    """Total source artifacts a group carries across all three domains."""
    return (
        len(group.functional_artifacts)
        + len(group.security_artifacts)
        + len(group.quality_artifacts)
    )


#: One sort-key function per ranking key. Each returns a value whose natural
#: ascending order is the key's declared order, so a tuple of them sorts
#: correctly under a single ``sorted(..., key=...)`` with no ``reverse``.
_RANKING_KEY_FUNCTIONS = {
    RankingKey.RISK_LEVEL_DESC: lambda g: -_RISK_RANK[g.risk_level],
    RankingKey.ARTIFACT_COUNT_DESC: lambda g: -_total_artifacts(g),
    RankingKey.CONSOLIDATED_ID_ASC: lambda g: g.consolidated_id,
}

#: The value each ranking key ordered a group on, rendered for the audit record.
#: Separate from the sort functions above because ``-3`` explains nothing to a
#: reader while ``critical`` does.
_RANKING_KEY_VALUES = {
    RankingKey.RISK_LEVEL_DESC: lambda g: str(g.risk_level),
    RankingKey.ARTIFACT_COUNT_DESC: lambda g: str(_total_artifacts(g)),
    RankingKey.CONSOLIDATED_ID_ASC: lambda g: g.consolidated_id,
}

_TIE_BREAKER_FUNCTIONS = {
    TieBreaker.CONSOLIDATED_ID_ASC: lambda g: g.consolidated_id,
}


class EngineeringContextOrchestrator:
    """Applies one governed :class:`OrchestrationPolicy` to produce one context.

    Stateless and deterministic; a single instance is safe to reuse across runs.
    """

    def __init__(
        self,
        policy: OrchestrationPolicy,
        builder: EngineeringContextBuilder,
    ) -> None:
        """Bind the orchestrator to the policy it executes and the builder it calls."""
        if not isinstance(policy, OrchestrationPolicy):
            raise ContextOrchestrationError(
                f"Expected an OrchestrationPolicy, got: {type(policy).__name__}"
            )
        if not isinstance(builder, EngineeringContextBuilder):
            raise ContextOrchestrationError(
                f"Expected an EngineeringContextBuilder, got: {type(builder).__name__}"
            )
        self._policy = policy
        self._builder = builder

    @property
    def policy(self) -> OrchestrationPolicy:
        """The governed policy this orchestrator executes."""
        return self._policy

    def orchestrate(self, candidates: Sequence[ConsolidatedArtifact]) -> ContextOrchestrationResult:
        """Rank *candidates*, select under the policy, and build the context.

        Args:
            candidates: Every consolidation group eligible for this run, in the
                order Consolidation produced them.

        Returns:
            ContextOrchestrationResult: The composed context and the groups that
            composed it, in rank order.

        Raises:
            ContextOrchestrationError: If *candidates* is empty or wrongly typed,
                or if the policy declares a rule this orchestrator cannot execute.
            ContextConstructionError: Propagated from the builder.
            ContextBudgetExceededError: Propagated from the builder. Reaching it
                would mean this orchestrator applied the budget incorrectly; the
                builder's check is the backstop, not the mechanism.
        """
        self._validate_candidates(candidates)

        ranked = self._rank(candidates)
        available = self._available_evidence(candidates)
        allocation = allocate_evidence_budget(self._policy.evidence_budget, available)

        contributions, evidence = self._select(ranked, allocation)

        subject = self._derive_subject(contributions)
        selected_groups = tuple(contribution.group for contribution in contributions)

        context = self._builder.build(
            subject=subject,
            evidence=evidence,
            contributions=contributions,
            policy=self._policy,
            ranking=self._build_ranking(ranked, contributions),
            coverage=self._build_coverage(contributions, available, evidence, allocation),
            evidence_budget=self._build_budget_usage(available, allocation, evidence),
            candidate_group_count=len(candidates),
        )
        return ContextOrchestrationResult(context=context, selected_groups=selected_groups)

    # ------------------------------------------------------------------
    # Policy execution
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_candidates(candidates: Sequence[ConsolidatedArtifact]) -> None:
        """Reject an empty or wrongly-typed candidate set."""
        if not candidates:
            raise ContextOrchestrationError(
                "At least one ConsolidatedArtifact is required to orchestrate a context."
            )
        for candidate in candidates:
            if not isinstance(candidate, ConsolidatedArtifact):
                raise ContextOrchestrationError(
                    f"Expected ConsolidatedArtifact, got: {type(candidate).__name__}"
                )

    @staticmethod
    def _available_evidence(
        candidates: Sequence[ConsolidatedArtifact],
    ) -> dict[SourceCategory, int]:
        """Count what each domain could contribute, summed across every candidate.

        This is the *demand* the budget is allocated against. Measuring it over
        the candidates rather than the selection is what makes a truncation
        visible: a domain that offered 300 artifacts and contributed 25 has been
        bounded, and the coverage record says so.
        """
        return {
            domain: sum(len(_DOMAIN_ARTIFACTS[domain](group)) for group in candidates)
            for domain in EVIDENCE_DOMAINS
        }

    def _rank(self, candidates: Sequence[ConsolidatedArtifact]) -> tuple[_Ranked, ...]:
        """Sort candidates by the policy's ranking keys, then its tie-breaker."""
        ranking = self._policy.ranking
        key_functions = [_RANKING_KEY_FUNCTIONS[key] for key in ranking.keys]
        key_functions.append(_TIE_BREAKER_FUNCTIONS[ranking.tie_breaker])

        def sort_key(group: ConsolidatedArtifact) -> tuple[object, ...]:
            return tuple(function(group) for function in key_functions)

        ordered = sorted(candidates, key=sort_key)
        return tuple(
            _Ranked(rank=rank, group=group, score=self._score(group))
            for rank, group in enumerate(ordered, start=1)
        )

    def _score(self, group: ConsolidatedArtifact) -> tuple[RankingScoreComponent, ...]:
        """Render the values this group was ranked on, in the policy's key order."""
        return tuple(
            RankingScoreComponent(key=str(key), value=_RANKING_KEY_VALUES[key](group))
            for key in self._policy.ranking.keys
        )

    def _select(
        self, ranked: Sequence[_Ranked], allocation: dict[SourceCategory, int]
    ) -> tuple[tuple[GroupContribution, ...], ContextEvidence]:
        """Draw the contributing groups and their evidence, per the policy's strategy."""
        strategy = self._policy.selection_strategy
        if strategy == SelectionStrategy.SINGLE_LARGEST:
            return self._select_single_largest(ranked)
        if strategy == SelectionStrategy.COVERAGE_GUARANTEED:
            return self._select_coverage_guaranteed(ranked, allocation)
        raise ContextOrchestrationError(
            f"Policy '{self._policy.policy_id}' declares selection strategy "
            f"'{strategy}', which this orchestrator does not execute."
        )

    def _select_single_largest(
        self, ranked: Sequence[_Ranked]
    ) -> tuple[tuple[GroupContribution, ...], ContextEvidence]:
        """Take the top-ranked group whole. Reproduces the pre-CAP-076 runtime.

        No budget is applied: the strategy takes one group or nothing, so there
        is no allocation to spend and nothing to truncate. The builder still
        enforces the policy's bound, which is why ``LegacySelectionPolicy`` sets
        it above the largest group the repository's own fixtures produce.
        """
        top = ranked[0]
        contribution = GroupContribution.whole(
            group=top.group,
            rank=top.rank,
            inclusion_reason=self._inclusion_reason(top, len(ranked), ()),
        )
        evidence = self._order_domains(
            {
                SourceCategory.FUNCTIONAL: list(top.group.functional_artifacts),
                SourceCategory.SECURITY: list(top.group.security_artifacts),
                SourceCategory.QUALITY: list(top.group.quality_artifacts),
            }
        )
        return (contribution,), evidence

    def _select_coverage_guaranteed(
        self, ranked: Sequence[_Ranked], allocation: dict[SourceCategory, int]
    ) -> tuple[tuple[GroupContribution, ...], ContextEvidence]:
        """Draw the best-ranked evidence from every domain, up to each domain's budget.

        Each domain is filled independently: the ranking is walked in order, and
        every group carrying that domain contributes as much as the remaining
        allocation permits. A group too large to fit entirely contributes its
        highest-ordered artifacts rather than being skipped — dropping a CRITICAL
        71-finding group because 71 exceeds a 25-artifact budget would let the
        budget silently override the ranking.
        """
        taken: dict[SourceCategory, list[SourceArtifact]] = {d: [] for d in EVIDENCE_DOMAINS}
        counts: dict[str, dict[SourceCategory, int]] = {}
        covered: dict[str, list[SourceCategory]] = {}

        for domain in EVIDENCE_DOMAINS:
            remaining = allocation[domain]
            for entry in ranked:
                if remaining == 0:
                    break
                pool = _DOMAIN_ARTIFACTS[domain](entry.group)
                if not pool:
                    continue
                admitted = order_evidence(self._policy.evidence_ordering, pool)[:remaining]
                remaining -= len(admitted)
                taken[domain].extend(admitted)
                identifier = entry.group.consolidated_id
                counts.setdefault(identifier, dict.fromkeys(EVIDENCE_DOMAINS, 0))
                counts[identifier][domain] = len(admitted)
                covered.setdefault(identifier, []).append(domain)

        if not counts:
            raise ContextOrchestrationError(
                f"Policy '{self._policy.policy_id}' admitted no evidence from "
                f"{len(ranked)} candidate group(s); an empty context is not a context."
            )

        contributions = tuple(
            GroupContribution(
                group=entry.group,
                rank=entry.rank,
                inclusion_reason=self._inclusion_reason(
                    entry, len(ranked), tuple(covered[entry.group.consolidated_id])
                ),
                functional_count=counts[entry.group.consolidated_id][SourceCategory.FUNCTIONAL],
                security_count=counts[entry.group.consolidated_id][SourceCategory.SECURITY],
                quality_count=counts[entry.group.consolidated_id][SourceCategory.QUALITY],
            )
            for entry in ranked
            if entry.group.consolidated_id in counts
        )
        return contributions, self._order_domains(taken)

    def _order_domains(self, taken: dict[SourceCategory, list[SourceArtifact]]) -> ContextEvidence:
        """Order each domain's assembled evidence under the policy's ordering rule.

        Ordering is applied once, across all contributing groups, so the section a
        reasoner reads is globally ordered rather than ordered within each group.
        """
        ordering = self._policy.evidence_ordering
        return ContextEvidence(
            functional_artifacts=order_evidence(ordering, taken[SourceCategory.FUNCTIONAL]),
            security_artifacts=order_evidence(ordering, taken[SourceCategory.SECURITY]),
            quality_artifacts=order_evidence(ordering, taken[SourceCategory.QUALITY]),
        )

    # ------------------------------------------------------------------
    # Subject derivation
    # ------------------------------------------------------------------

    @staticmethod
    def _derive_subject(contributions: Sequence[GroupContribution]) -> ContextSubject:
        """Derive what the context is about from the group that ranked first.

        A multi-source context takes its subject from its highest-ranked
        contributing group, not from a concatenation of every group's module. Two
        reasons. Joining ten modules with ``" + "`` yields a label no reader can
        use and a context id slug no manifest can display. And under a ranking
        that both policies share, the rank-1 group is the one ``single_largest``
        would also have chosen — so activating coverage adds evidence to a context
        without moving its subject, which is exactly the claim CAP-076D makes.

        The basis is :attr:`ContextSubjectBasis.MULTI` whenever several groups
        contribute: the evidence then spans grouping dimensions, and attributing
        the subject to any one of them would be false.
        """
        primary = contributions[0].group
        if len(contributions) == 1:
            return ContextSubject(
                label=primary.module,
                business_area=primary.business_area,
                basis=_basis_of(primary),
            )
        return ContextSubject(
            label=primary.module,
            business_area=primary.business_area,
            basis=ContextSubjectBasis.MULTI,
        )

    # ------------------------------------------------------------------
    # Explainability (Stage 6)
    # ------------------------------------------------------------------

    def _inclusion_reason(
        self,
        entry: _Ranked,
        candidate_count: int,
        domains: Sequence[SourceCategory],
    ) -> str:
        """Explain the rank a group achieved and the rule that admitted it."""
        coverage = f" to cover {', '.join(str(domain) for domain in domains)}" if domains else ""
        return (
            f"Ranked {entry.rank} of {candidate_count} candidate group(s) by "
            f"[{self._ranking_keys()}], tie-broken by {self._policy.ranking.tie_breaker}, "
            f"and admitted{coverage} by the '{self._policy.selection_strategy}' strategy of "
            f"policy '{self._policy.policy_id}' v{self._policy.policy_version}."
        )

    def _exclusion_reason(self, entry: _Ranked, candidate_count: int) -> str:
        """Explain why a ranked group contributed nothing.

        An exclusion without a reason is indistinguishable from a hidden ranking,
        so the two strategies each name the rule that shut the group out.
        """
        prefix = f"Ranked {entry.rank} of {candidate_count} candidate group(s) and excluded: "
        if self._policy.selection_strategy == SelectionStrategy.SINGLE_LARGEST:
            return (
                f"{prefix}the 'single_largest' strategy of policy "
                f"'{self._policy.policy_id}' admits only the top-ranked group."
            )
        return (
            f"{prefix}every evidence domain this group carries had exhausted its "
            f"allocation of the {self._policy.evidence_budget.max_artifacts_total}-artifact "
            f"evidence budget before this rank was reached."
        )

    def _ranking_keys(self) -> str:
        """The policy's ranking keys, rendered for a reason string."""
        return ", ".join(str(key) for key in self._policy.ranking.keys)

    def _build_ranking(
        self, ranked: Sequence[_Ranked], contributions: Sequence[GroupContribution]
    ) -> ContextRanking:
        """Record every candidate's rank, score, and fate — admitted or not."""
        contributed = {c.consolidated_id: c for c in contributions}
        entries = tuple(
            ContextRankingEntry(
                rank=entry.rank,
                consolidated_id=entry.group.consolidated_id,
                risk_level=entry.group.risk_level,
                candidate_artifact_count=_total_artifacts(entry.group),
                contributed_artifact_count=(
                    contributed[entry.group.consolidated_id].contributed_count
                    if entry.group.consolidated_id in contributed
                    else 0
                ),
                score=entry.score,
                selected=entry.group.consolidated_id in contributed,
                decision_reason=(
                    contributed[entry.group.consolidated_id].inclusion_reason
                    if entry.group.consolidated_id in contributed
                    else self._exclusion_reason(entry, len(ranked))
                ),
            )
            for entry in ranked
        )
        return ContextRanking(
            keys=tuple(str(key) for key in self._policy.ranking.keys),
            tie_breaker=str(self._policy.ranking.tie_breaker),
            entries=entries,
        )

    def _build_coverage(
        self,
        contributions: Sequence[GroupContribution],
        available: dict[SourceCategory, int],
        evidence: ContextEvidence,
        allocation: dict[SourceCategory, int],
    ) -> ContextCoverage:
        """Record, per domain, whether evidence existed and whether it was represented."""
        contributed = self._contributed_counts(evidence)
        domains = tuple(
            self._coverage_domain(domain, contributions, available, contributed, allocation)
            for domain in EVIDENCE_DOMAINS
        )
        all_represented = all(d.represented for d in domains if d.evidence_present) and any(
            d.evidence_present for d in domains
        )
        return ContextCoverage(
            mode=str(self._policy.coverage.mode),
            selection_strategy=str(self._policy.selection_strategy),
            domains=domains,
            rule_satisfied=self._coverage_rule_satisfied(domains, contributions),
            all_present_categories_represented=all_represented,
        )

    def _coverage_domain(
        self,
        domain: SourceCategory,
        contributions: Sequence[GroupContribution],
        available: dict[SourceCategory, int],
        contributed: dict[SourceCategory, int],
        allocation: dict[SourceCategory, int],
    ) -> ContextCoverageDomain:
        """Build one domain's coverage record, with the reason it holds."""
        present = available[domain] > 0
        count = contributed[domain]
        groups = sum(1 for c in contributions if self._domain_count(c, domain) > 0)
        return ContextCoverageDomain(
            category=domain,
            evidence_present=present,
            represented=count > 0,
            candidate_artifact_count=available[domain],
            contributed_artifact_count=count,
            contributing_group_count=groups,
            truncated=count < available[domain],
            reason=self._coverage_reason(domain, present, count, groups, available, allocation),
        )

    def _coverage_reason(
        self,
        domain: SourceCategory,
        present: bool,
        contributed: int,
        groups: int,
        available: dict[SourceCategory, int],
        allocation: dict[SourceCategory, int],
    ) -> str:
        """State why a domain is represented, or why it is not."""
        if not present:
            return f"No candidate group carried {domain} evidence."
        if contributed == 0:
            return (
                f"{available[domain]} {domain} artifact(s) were available across the candidate "
                f"groups but none reached the context: "
                f"{self._exclusion_cause(domain, allocation)}"
            )
        truncation = (
            f", bounded by an allocation of {allocation[domain]}"
            if contributed < available[domain]
            else ""
        )
        return (
            f"Represented by {groups} contributing group(s) supplying {contributed} of the "
            f"{available[domain]} available {domain} artifact(s){truncation}."
        )

    def _exclusion_cause(
        self, domain: SourceCategory, allocation: dict[SourceCategory, int]
    ) -> str:
        """Name the rule that kept an available domain out of the context.

        The strategy and the budget are different causes with different remedies,
        and a reader repairing a thin context needs to know which one applied.
        """
        if self._policy.selection_strategy == SelectionStrategy.SINGLE_LARGEST:
            return (
                f"the 'single_largest' strategy of policy '{self._policy.policy_id}' admits "
                f"only the top-ranked group, and that group carries no {domain} evidence."
            )
        if allocation[domain] == 0:
            return (
                f"the {self._policy.evidence_budget.max_artifacts_total}-artifact evidence "
                f"budget allocated this domain no artifacts."
            )
        return (
            f"no group carrying {domain} evidence was admitted by the "
            f"'{self._policy.selection_strategy}' strategy of policy "
            f"'{self._policy.policy_id}'."
        )

    def _coverage_rule_satisfied(
        self,
        domains: Sequence[ContextCoverageDomain],
        contributions: Sequence[GroupContribution],
    ) -> bool:
        """Did the context satisfy the coverage rule the policy *declared*?

        Distinct from whether every available domain was represented.
        ``single_largest_group`` is satisfied by one group, and satisfying it is
        precisely how the CAP-074B defect passed unnoticed — which is why both
        facts are recorded separately.
        """
        required = self._policy.coverage.required_categories
        missing_required = [
            domain.category
            for domain in domains
            if SourceCategory(domain.category) in required and not domain.represented
        ]
        if missing_required:
            return False
        if self._policy.coverage.mode == CoverageMode.SINGLE_LARGEST_GROUP:
            return len(contributions) == 1
        return all(domain.represented for domain in domains if domain.evidence_present)

    def _build_budget_usage(
        self,
        available: dict[SourceCategory, int],
        allocation: dict[SourceCategory, int],
        evidence: ContextEvidence,
    ) -> ContextEvidenceBudgetUsage:
        """Record the allocation the budget produced and the spend against it.

        ``coverage_guaranteed`` fills each domain up to its allocation, so a spend
        above it is unreachable. ``single_largest`` never consults the allocation
        — it takes one group whole — so a group larger than the policy permits is
        caught here, as a budget error rather than a model validation error. This
        is why ``LegacySelectionPolicy`` sets a bound above the largest group the
        repository's fixtures produce.
        """
        contributed = self._contributed_counts(evidence)
        budget = self._policy.evidence_budget
        for domain in EVIDENCE_DOMAINS:
            if contributed[domain] > allocation[domain]:
                raise ContextBudgetExceededError(
                    f"Policy '{self._policy.policy_id}' allocated {allocation[domain]} "
                    f"{domain} artifact(s) under its "
                    f"{budget.max_artifacts_per_domain}-per-domain bound, but the "
                    f"'{self._policy.selection_strategy}' strategy selected "
                    f"{contributed[domain]}."
                )
        return ContextEvidenceBudgetUsage(
            max_artifacts_per_domain=budget.max_artifacts_per_domain,
            max_artifacts_total=budget.max_artifacts_total,
            domains=tuple(
                DomainBudgetUsage(
                    category=domain,
                    available=available[domain],
                    allocated=allocation[domain],
                    used=contributed[domain],
                )
                for domain in EVIDENCE_DOMAINS
            ),
        )

    @staticmethod
    def _contributed_counts(evidence: ContextEvidence) -> dict[SourceCategory, int]:
        """The context's artifact count per domain."""
        return {
            SourceCategory.FUNCTIONAL: len(evidence.functional_artifacts),
            SourceCategory.SECURITY: len(evidence.security_artifacts),
            SourceCategory.QUALITY: len(evidence.quality_artifacts),
        }

    @staticmethod
    def _domain_count(contribution: GroupContribution, domain: SourceCategory) -> int:
        """How many artifacts *contribution* supplied to *domain*."""
        if domain == SourceCategory.FUNCTIONAL:
            return contribution.functional_count
        if domain == SourceCategory.SECURITY:
            return contribution.security_count
        return contribution.quality_count


def _basis_of(group: ConsolidatedArtifact) -> ContextSubjectBasis:
    """Recover the grouping dimension a group was formed on, from its id.

    Returns :attr:`ContextSubjectBasis.MULTI` when the id does not carry a
    recognisable dimension — the honest answer for a group whose subject cannot
    be attributed to any single dimension this model knows about.
    """
    identifier = group.consolidated_id.lower()
    if not identifier.startswith(_CONSOLIDATED_ID_PREFIX):
        return ContextSubjectBasis.MULTI
    remainder = identifier[len(_CONSOLIDATED_ID_PREFIX) :]
    dimension = remainder.split("-", 1)[0]
    return _BASIS_BY_DIMENSION.get(dimension, ContextSubjectBasis.MULTI)
