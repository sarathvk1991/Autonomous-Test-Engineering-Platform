"""The governed default Orchestration Policy, and the behaviour-preserving policy.

Two policies are provided. Neither is applied by anything at CAP-076B.

:class:`DefaultOrchestrationPolicy`
    The governed default: coverage-guaranteed, risk-ranked, domain-budgeted.
    This is the policy that repairs the CAP-074B defect.

:class:`LegacySelectionPolicy`
    A faithful, declarative restatement of the selection rule that
    ``scripts/run_requirement_analysis.py:_select_consolidated`` implements
    today: rank by artifact count descending, tie-break on ``consolidated_id``,
    take one group. It exists because CAP-076A §9 Stage 3 requires the runtime
    to be wired with *behaviour-identical* rules before the policy is flipped in
    Stage 4 — separating a plumbing bug from a policy change in the golden diff.
    Without it, CAP-076C would have to invent it.
"""

from __future__ import annotations

from requirement_intelligence.context_orchestration.models.context_identity import (
    OrchestrationPolicyId,
    PolicyVersion,
)
from requirement_intelligence.context_orchestration.policy.orchestration_policy import (
    CoverageMode,
    CoverageRule,
    EvidenceBudget,
    EvidenceOrdering,
    OrchestrationPolicy,
    RankingKey,
    RankingRule,
    SelectionStrategy,
    TieBreaker,
)

#: Per-domain artifact cap. Chosen against CAP-076A §6.3: today's 71-artifact
#: single-domain context renders ~5.3k tokens, so 25 per domain keeps a
#: three-domain context comparable in size to the one-domain context it replaces.
_MAX_ARTIFACTS_PER_DOMAIN = 25

#: Total artifact cap across all three domains.
_MAX_ARTIFACTS_TOTAL = 60


class DefaultOrchestrationPolicy(OrchestrationPolicy):
    """The governed default policy — coverage-guaranteed, risk-ranked, budgeted.

    Every field carries a governed default, so ``DefaultOrchestrationPolicy()``
    is the canonical policy instance. It remains an ``OrchestrationPolicy`` and
    is inert: it describes rules and applies none.

    The reason template asserts *co-selection*, not correlation, discharging
    CAP-076A Invariant 2 (correlation is asserted, never implied) in the one
    place a reader will actually see it.
    """

    policy_id: OrchestrationPolicyId = OrchestrationPolicyId("coverage")
    policy_version: PolicyVersion = PolicyVersion(1, 0, 0)
    description: str = (
        "Guarantees every source category that produced evidence is represented, "
        "ranks candidate groups by rolled-up risk before size, and bounds evidence "
        "per domain so no single verbose source can crowd out the others."
    )

    coverage: CoverageRule = CoverageRule(mode=CoverageMode.ALL_PRESENT_CATEGORIES)
    ranking: RankingRule = RankingRule(
        keys=(
            RankingKey.RISK_LEVEL_DESC,
            RankingKey.ARTIFACT_COUNT_DESC,
            RankingKey.CONSOLIDATED_ID_ASC,
        ),
        tie_breaker=TieBreaker.CONSOLIDATED_ID_ASC,
    )
    evidence_budget: EvidenceBudget = EvidenceBudget(
        max_artifacts_per_domain=_MAX_ARTIFACTS_PER_DOMAIN,
        max_artifacts_total=_MAX_ARTIFACTS_TOTAL,
    )
    evidence_ordering: EvidenceOrdering = EvidenceOrdering.RISK_THEN_RECORD_ID
    selection_strategy: SelectionStrategy = SelectionStrategy.COVERAGE_GUARANTEED

    reason_template: str = (
        "Composed for {subject} under the {strategy} strategy from {groups} "
        "consolidation group(s), covering {categories}. Evidence is co-selected "
        "for coverage; no correlation between sources is asserted."
    )


class LegacySelectionPolicy(OrchestrationPolicy):
    """Declarative restatement of today's selection rule. Behaviour-preserving.

    Equivalent to ``_select_consolidated``: ``sorted(key=(-total, consolidated_id))[0]``.
    The budget is set above the largest observed group (71 artifacts in the repo's
    own fixtures) so this policy never truncates evidence that today's runtime
    would have included — the point of the policy is to change nothing.
    """

    policy_id: OrchestrationPolicyId = OrchestrationPolicyId("legacy-single-largest")
    policy_version: PolicyVersion = PolicyVersion(1, 0, 0)
    description: str = (
        "Reproduces the pre-CAP-076 selection rule exactly: the single consolidation "
        "group with the most artifacts, ties broken by consolidated id ascending. "
        "Retained solely so runtime integration can be proven behaviour-identical."
    )

    coverage: CoverageRule = CoverageRule(mode=CoverageMode.SINGLE_LARGEST_GROUP)
    ranking: RankingRule = RankingRule(
        keys=(RankingKey.ARTIFACT_COUNT_DESC, RankingKey.CONSOLIDATED_ID_ASC),
        tie_breaker=TieBreaker.CONSOLIDATED_ID_ASC,
    )
    evidence_budget: EvidenceBudget = EvidenceBudget(
        max_artifacts_per_domain=1000,
        max_artifacts_total=1000,
    )
    evidence_ordering: EvidenceOrdering = EvidenceOrdering.GROUP_ORDER
    selection_strategy: SelectionStrategy = SelectionStrategy.SINGLE_LARGEST

    reason_template: str = (
        "Selected {subject} as the largest of {candidates} consolidation group(s)."
    )
