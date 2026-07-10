"""CAP-076D — Engineering Context Orchestrator, multi-source and coverage-guaranteed.

Covers the orchestrator's responsibilities — policy execution, ranking, coverage,
evidence budgeting, ordering, subject derivation, and explanation — and the two
claims the milestone rests on:

* ``DefaultOrchestrationPolicy`` composes one context from several consolidation
  groups so that every evidence domain the candidates carry reaches the reasoner.
* ``LegacySelectionPolicy`` still selects exactly what ``_select_consolidated``
  selected before the orchestrator existed, so a behaviour change can be
  attributed to the policy rather than to the code that executes it.

No LLM call is made and no file is written.
"""

from __future__ import annotations

import pytest

from requirement_intelligence.context_orchestration import (
    ContextOrchestrationError,
    ContextSubjectBasis,
    CoverageMode,
    CoverageRule,
    DefaultOrchestrationPolicy,
    EngineeringContextBuilder,
    EngineeringContextOrchestrator,
    EvidenceBudget,
    EvidenceOrdering,
    LegacySelectionPolicy,
    OrchestrationPolicy,
    OrchestrationPolicyId,
    PolicyVersion,
    RankingKey,
    RankingRule,
    SelectionStrategy,
    TieBreaker,
)
from requirement_intelligence.models.consolidated_artifact import ConsolidatedArtifact
from requirement_intelligence.models.enums import (
    RiskLevel,
    SourceCategory,
    SourceSystem,
    SourceType,
)
from requirement_intelligence.models.source_artifact import SourceArtifact
from requirement_intelligence.platform import PlatformContext

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _artifact(
    index: int,
    category: SourceCategory,
    source_type: SourceType,
    *,
    severity: str | None = None,
) -> SourceArtifact:
    return SourceArtifact(
        artifact_id=f"A{index}",
        source_system=SourceSystem.JIRA,
        source_record_id=f"REC-{index:03d}",
        source_category=category,
        source_type=source_type,
        title=f"Artifact {index}",
        severity=severity,
    )


def _group(
    consolidated_id: str,
    *,
    functional: int = 0,
    security: int = 0,
    quality: int = 0,
    module: str = "auth",
    risk: RiskLevel = RiskLevel.LOW,
) -> ConsolidatedArtifact:
    return ConsolidatedArtifact(
        consolidated_id=consolidated_id,
        module=module,
        risk_level=risk,
        consolidation_reason=f"Grouped by component {module}",
        functional_artifacts=[
            _artifact(i, SourceCategory.FUNCTIONAL, SourceType.STORY) for i in range(functional)
        ],
        security_artifacts=[
            _artifact(100 + i, SourceCategory.SECURITY, SourceType.DAST) for i in range(security)
        ],
        quality_artifacts=[
            _artifact(200 + i, SourceCategory.QUALITY, SourceType.SAST) for i in range(quality)
        ],
    )


def _orchestrator(policy: OrchestrationPolicy | None = None) -> EngineeringContextOrchestrator:
    return EngineeringContextOrchestrator(
        policy=policy or LegacySelectionPolicy(),
        builder=EngineeringContextBuilder(),
    )


def _default() -> EngineeringContextOrchestrator:
    """The orchestrator the runtime binds."""
    return _orchestrator(DefaultOrchestrationPolicy())


def _coverage_of(context: object, category: SourceCategory) -> object:
    """The coverage record for one evidence domain."""
    return next(d for d in context.coverage.domains if d.category == category)  # type: ignore[attr-defined]


def _legacy_selection(groups: list[ConsolidatedArtifact]) -> ConsolidatedArtifact:
    """The rule ``scripts/run_requirement_analysis.py:_select_consolidated`` applied."""

    def key(group: ConsolidatedArtifact) -> tuple[int, str]:
        total = (
            len(group.functional_artifacts)
            + len(group.security_artifacts)
            + len(group.quality_artifacts)
        )
        return (-total, group.consolidated_id)

    return sorted(groups, key=key)[0]


# ---------------------------------------------------------------------------
# Behavioural equivalence — the central CAP-076C claim
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "groups",
    [
        pytest.param(
            [_group("cons-component-a", quality=1)],
            id="single-candidate",
        ),
        pytest.param(
            [
                _group("cons-component-small", quality=1),
                _group("cons-component-big", quality=9),
                _group("cons-component-mid", quality=4),
            ],
            id="largest-wins",
        ),
        pytest.param(
            [
                _group("cons-tag-zeta", quality=3),
                _group("cons-tag-alpha", quality=3),
            ],
            id="tie-broken-by-id-ascending",
        ),
        pytest.param(
            [
                _group("cons-component-mixed", functional=2, security=2, quality=1),
                _group("cons-component-quality", quality=4),
            ],
            id="counts-span-every-domain",
        ),
        pytest.param(
            [
                _group("cons-risk-critical", quality=1, risk=RiskLevel.CRITICAL),
                _group("cons-endpoint-login", quality=5, risk=RiskLevel.LOW),
            ],
            id="legacy-ignores-risk-and-ranks-by-size",
        ),
    ],
)
def test_legacy_policy_selects_exactly_what_the_retired_rule_selected(
    groups: list[ConsolidatedArtifact],
) -> None:
    """LegacySelectionPolicy is behaviour-preserving: same group, every time."""
    result = _orchestrator().orchestrate(groups)
    assert result.selected_groups == (_legacy_selection(groups),)


@pytest.mark.unit
def test_legacy_policy_composes_a_single_group_context() -> None:
    """``single_largest`` means one group reaches the reasoner — today's behaviour."""
    groups = [_group("cons-component-a", quality=9), _group("cons-component-b", security=2)]
    context = _orchestrator().orchestrate(groups).context
    assert context.provenance.contributing_group_count == 1
    assert context.provenance.contributing_consolidated_ids == ("cons-component-a",)


@pytest.mark.unit
def test_evidence_is_the_selected_group_in_group_order() -> None:
    """The orchestrator neither drops nor reorders the selected group's evidence."""
    group = _group("cons-component-a", functional=2, security=1, quality=3)
    context = _orchestrator().orchestrate([group]).context
    assert list(context.evidence.functional_artifacts) == group.functional_artifacts
    assert list(context.evidence.security_artifacts) == group.security_artifacts
    assert list(context.evidence.quality_artifacts) == group.quality_artifacts


@pytest.mark.unit
def test_orchestration_is_deterministic() -> None:
    """Two runs over the same candidates mint the same context identity."""
    groups = [_group("cons-component-b", quality=4), _group("cons-component-a", quality=4)]
    first = _orchestrator().orchestrate(groups).context
    second = _orchestrator().orchestrate(groups).context
    assert first.context_id == second.context_id


@pytest.mark.unit
def test_candidate_order_does_not_affect_selection() -> None:
    """Ranking is a total order, so the input ordering cannot change the outcome."""
    groups = [_group("cons-component-a", quality=4), _group("cons-component-b", quality=4)]
    forward = _orchestrator().orchestrate(groups).context
    reverse = _orchestrator().orchestrate(list(reversed(groups))).context
    assert forward.context_id == reverse.context_id


# ---------------------------------------------------------------------------
# Policy execution
# ---------------------------------------------------------------------------


def _risk_first_policy() -> OrchestrationPolicy:
    """A governed policy that ranks by risk before size, still selecting one group."""
    return OrchestrationPolicy(
        policy_id=OrchestrationPolicyId("risk-first-test"),
        policy_version=PolicyVersion(1, 0, 0),
        description="Ranks by rolled-up risk before size.",
        coverage=CoverageRule(mode=CoverageMode.SINGLE_LARGEST_GROUP),
        ranking=RankingRule(
            keys=(RankingKey.RISK_LEVEL_DESC, RankingKey.ARTIFACT_COUNT_DESC),
            tie_breaker=TieBreaker.CONSOLIDATED_ID_ASC,
        ),
        evidence_budget=EvidenceBudget(max_artifacts_per_domain=100, max_artifacts_total=100),
        evidence_ordering=EvidenceOrdering.GROUP_ORDER,
        selection_strategy=SelectionStrategy.SINGLE_LARGEST,
        reason_template="Composed for {subject} from {groups} group(s) covering {categories}.",
    )


@pytest.mark.unit
def test_ranking_keys_are_applied_in_the_order_the_policy_declares() -> None:
    """A CRITICAL group outranks a larger LOW group when risk ranks first."""
    groups = [
        _group("cons-component-noisy", quality=9, risk=RiskLevel.LOW),
        _group("cons-component-severe", security=1, risk=RiskLevel.CRITICAL),
    ]
    result = _orchestrator(_risk_first_policy()).orchestrate(groups)
    assert result.selected_groups[0].consolidated_id == "cons-component-severe"


@pytest.mark.unit
def test_an_unimplemented_selection_strategy_raises_rather_than_degrading() -> None:
    """A policy that is silently half-applied is worse than no policy at all."""
    policy = _risk_first_policy().model_copy(update={"selection_strategy": "fanciful"})
    with pytest.raises(ContextOrchestrationError, match="does not execute"):
        _orchestrator(policy).orchestrate([_group("cons-component-a", quality=1)])


@pytest.mark.unit
def test_an_unimplemented_evidence_ordering_raises_rather_than_degrading() -> None:
    policy = _risk_first_policy().model_copy(update={"evidence_ordering": "alphabetical"})
    with pytest.raises(ContextOrchestrationError, match="not implemented"):
        _orchestrator(policy).orchestrate([_group("cons-component-a", quality=1)])


# ---------------------------------------------------------------------------
# Subject derivation
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    ("consolidated_id", "expected"),
    [
        ("cons-component-authentication", ContextSubjectBasis.COMPONENT),
        ("cons-tag-xss", ContextSubjectBasis.TAG),
        ("cons-endpoint-login", ContextSubjectBasis.ENDPOINT),
        ("cons-risk-critical", ContextSubjectBasis.RISK),
        ("CONS-1", ContextSubjectBasis.MULTI),
    ],
)
def test_subject_basis_is_recovered_from_the_group_id(
    consolidated_id: str, expected: ContextSubjectBasis
) -> None:
    """A group does not retain its grouping dimension; the id encodes it."""
    context = _orchestrator().orchestrate([_group(consolidated_id, quality=1)]).context
    assert context.subject.basis == expected


@pytest.mark.unit
def test_subject_label_is_the_selected_group_module() -> None:
    group = _group("cons-component-payments", quality=1, module="payments")
    context = _orchestrator().orchestrate([group]).context
    assert context.subject.label == "payments"


# ---------------------------------------------------------------------------
# Explainability (Stage 9)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_every_contribution_records_its_rank_and_the_policy_that_admitted_it() -> None:
    groups = [
        _group("cons-component-a", quality=9),
        _group("cons-component-b", quality=1),
        _group("cons-component-c", quality=1),
    ]
    context = _orchestrator().orchestrate(groups).context
    (contribution,) = context.provenance.contributions
    assert "Ranked 1 of 3 candidate group(s)" in contribution.inclusion_reason
    assert "legacy-single-largest" in contribution.inclusion_reason
    assert "single_largest" in contribution.inclusion_reason


@pytest.mark.unit
def test_provenance_records_the_candidates_that_were_not_selected() -> None:
    """Selection is falsifiable only if the context records what it chose *from*."""
    groups = [_group("cons-component-a", quality=9), _group("cons-component-b", quality=1)]
    context = _orchestrator().orchestrate(groups).context
    assert context.provenance.candidate_group_count == 2
    assert context.provenance.contributing_group_count == 1


@pytest.mark.unit
def test_contribution_carries_the_groups_own_consolidation_reason() -> None:
    """Consolidation's explanation survives into the context; it is not re-derived."""
    group = _group("cons-component-a", quality=1)
    context = _orchestrator().orchestrate([group]).context
    (contribution,) = context.provenance.contributions
    assert contribution.consolidation_reason == group.consolidation_reason
    assert contribution.module == group.module
    assert contribution.artifact_count == 1


@pytest.mark.unit
def test_orchestration_reason_is_rendered_from_the_policy_template() -> None:
    context = _orchestrator().orchestrate([_group("cons-component-auth", quality=1)]).context
    assert context.orchestration_reason == (
        "Selected auth as the largest of 1 consolidation group(s)."
    )


@pytest.mark.unit
def test_orchestration_reason_counts_the_candidates_not_the_contributors() -> None:
    """ "Largest of N" must name what the group beat, or the ranking stays hidden."""
    groups = [
        _group("cons-component-auth", quality=9),
        _group("cons-component-b", quality=1),
        _group("cons-component-c", quality=1),
    ]
    context = _orchestrator().orchestrate(groups).context
    assert context.orchestration_reason == (
        "Selected auth as the largest of 3 consolidation group(s)."
    )


# ---------------------------------------------------------------------------
# Input contract
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_orchestrate_rejects_an_empty_candidate_set() -> None:
    with pytest.raises(ContextOrchestrationError, match="At least one ConsolidatedArtifact"):
        _orchestrator().orchestrate([])


@pytest.mark.unit
def test_orchestrate_rejects_a_non_consolidated_artifact() -> None:
    with pytest.raises(ContextOrchestrationError, match="Expected ConsolidatedArtifact"):
        _orchestrator().orchestrate([object()])  # type: ignore[list-item]


@pytest.mark.unit
def test_construction_rejects_a_non_policy() -> None:
    with pytest.raises(ContextOrchestrationError, match="Expected an OrchestrationPolicy"):
        EngineeringContextOrchestrator(policy=object(), builder=EngineeringContextBuilder())  # type: ignore[arg-type]


@pytest.mark.unit
def test_construction_rejects_a_non_builder() -> None:
    with pytest.raises(ContextOrchestrationError, match="Expected an EngineeringContextBuilder"):
        EngineeringContextOrchestrator(policy=LegacySelectionPolicy(), builder=object())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# PlatformContext ownership (Stage 7)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_platform_context_binds_the_orchestrator_to_the_default_policy() -> None:
    """CAP-076D: the runtime policy is Default. Legacy remains constructible."""
    context = PlatformContext()
    orchestrator = context.create_engineering_context_orchestrator()
    assert isinstance(orchestrator, EngineeringContextOrchestrator)
    assert isinstance(orchestrator.policy, DefaultOrchestrationPolicy)
    assert isinstance(context.create_orchestration_policy(), DefaultOrchestrationPolicy)


@pytest.mark.unit
def test_legacy_selection_policy_remains_available_as_the_control_arm() -> None:
    """Legacy is retained, not deprecated: it is how a policy change is attributed."""
    context = PlatformContext()
    assert isinstance(context.create_legacy_selection_policy(), LegacySelectionPolicy)
    orchestrator = context.create_engineering_context_orchestrator(
        context.create_legacy_selection_policy()
    )
    assert isinstance(orchestrator.policy, LegacySelectionPolicy)


@pytest.mark.unit
def test_platform_context_accepts_an_explicit_policy_override() -> None:
    orchestrator = PlatformContext().create_engineering_context_orchestrator(
        LegacySelectionPolicy()
    )
    assert isinstance(orchestrator.policy, LegacySelectionPolicy)


@pytest.mark.unit
def test_platform_context_returns_independent_orchestrators() -> None:
    context = PlatformContext()
    first = context.create_engineering_context_orchestrator()
    second = context.create_engineering_context_orchestrator()
    assert first is not second


# ---------------------------------------------------------------------------
# Multi-source assembly (Stage 2) and coverage guarantee (Stage 3)
# ---------------------------------------------------------------------------


def _three_domain_candidates() -> list[ConsolidatedArtifact]:
    """The CAP-074B shape: single-domain groups, quality the largest and most severe."""
    return [
        _group("cons-component-noisy", quality=9, risk=RiskLevel.CRITICAL),
        _group("cons-tag-xss", security=3, risk=RiskLevel.HIGH),
        _group("cons-endpoint-login", functional=2, risk=RiskLevel.MEDIUM),
    ]


@pytest.mark.unit
def test_default_policy_composes_a_context_from_several_groups() -> None:
    """The orchestrator no longer terminates after selecting one group."""
    context = _default().orchestrate(_three_domain_candidates()).context
    assert context.provenance.contributing_group_count == 3
    assert set(context.provenance.contributing_consolidated_ids) == {
        "cons-component-noisy",
        "cons-tag-xss",
        "cons-endpoint-login",
    }


@pytest.mark.unit
def test_default_policy_delivers_every_evidence_domain_that_exists() -> None:
    """The CAP-074B repair, stated as an assertion: all three domains reach the reasoner."""
    context = _default().orchestrate(_three_domain_candidates()).context
    assert context.evidence.categories_present == frozenset(
        {SourceCategory.FUNCTIONAL, SourceCategory.SECURITY, SourceCategory.QUALITY}
    )
    assert context.coverage.all_present_categories_represented is True
    assert context.coverage.rule_satisfied is True


@pytest.mark.unit
def test_legacy_policy_leaves_available_domains_uncovered() -> None:
    """The defect, made legible: the rule is satisfied while two domains are lost."""
    context = _orchestrator().orchestrate(_three_domain_candidates()).context
    assert context.coverage.rule_satisfied is True
    assert context.coverage.all_present_categories_represented is False
    assert context.coverage.represented_categories == (SourceCategory.QUALITY,)

    functional = _coverage_of(context, SourceCategory.FUNCTIONAL)
    assert functional.evidence_present is True
    assert functional.represented is False
    assert "single_largest" in functional.reason


@pytest.mark.unit
def test_a_domain_with_no_evidence_is_not_reported_as_missing() -> None:
    """Coverage is measured against what the candidates carried, not against three."""
    context = _default().orchestrate([_group("cons-component-a", quality=2)]).context
    security = _coverage_of(context, SourceCategory.SECURITY)
    assert security.evidence_present is False
    assert security.represented is False
    assert security.reason == "No candidate group carried security evidence."
    assert context.coverage.all_present_categories_represented is True


@pytest.mark.unit
def test_coverage_draws_the_best_ranked_group_from_each_domain() -> None:
    """Within a domain the ranking decides, so a CRITICAL group is filled before a LOW one."""
    policy = DefaultOrchestrationPolicy(
        evidence_budget=EvidenceBudget(max_artifacts_per_domain=2, max_artifacts_total=6)
    )
    groups = [
        _group("cons-tag-mild", security=5, risk=RiskLevel.LOW),
        _group("cons-tag-severe", security=2, risk=RiskLevel.CRITICAL),
    ]
    context = _orchestrator(policy).orchestrate(groups).context
    assert context.provenance.contributing_consolidated_ids == ("cons-tag-severe",)
    assert len(context.evidence.security_artifacts) == 2


# ---------------------------------------------------------------------------
# Evidence budget (Stage 4)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_the_budget_bounds_each_domain_independently() -> None:
    """A verbose domain cannot crowd out a sparse one — the CAP-076A R8 risk."""
    policy = DefaultOrchestrationPolicy(
        evidence_budget=EvidenceBudget(max_artifacts_per_domain=3, max_artifacts_total=9)
    )
    groups = [
        _group("cons-component-noisy", quality=50, risk=RiskLevel.CRITICAL),
        _group("cons-endpoint-login", functional=1, risk=RiskLevel.LOW),
    ]
    context = _orchestrator(policy).orchestrate(groups).context
    assert len(context.evidence.quality_artifacts) == 3
    assert len(context.evidence.functional_artifacts) == 1


@pytest.mark.unit
def test_a_group_too_large_for_its_budget_contributes_rather_than_being_dropped() -> None:
    """Dropping a CRITICAL group for not fitting would let the budget override the ranking."""
    policy = DefaultOrchestrationPolicy(
        evidence_budget=EvidenceBudget(max_artifacts_per_domain=4, max_artifacts_total=12)
    )
    context = _orchestrator(policy).orchestrate([_group("cons-component-a", quality=40)]).context
    (contribution,) = context.provenance.contributions
    assert contribution.artifact_count == 4
    assert contribution.candidate_artifact_count == 40
    assert contribution.truncated is True


@pytest.mark.unit
def test_budget_usage_records_the_allocation_and_the_spend() -> None:
    policy = DefaultOrchestrationPolicy(
        evidence_budget=EvidenceBudget(max_artifacts_per_domain=2, max_artifacts_total=6)
    )
    context = _orchestrator(policy).orchestrate(_three_domain_candidates()).context
    budget = context.evidence_budget
    assert budget.max_artifacts_per_domain == 2
    assert budget.total_used == budget.total_allocated == 6
    assert budget.truncated is True

    quality = next(d for d in budget.domains if d.category == SourceCategory.QUALITY)
    assert (quality.available, quality.allocated, quality.used) == (9, 2, 2)


@pytest.mark.unit
def test_the_budget_is_not_reported_as_binding_when_it_did_not_bind() -> None:
    """Legacy loses evidence to its strategy, not to a budget it never approached."""
    context = _orchestrator().orchestrate(_three_domain_candidates()).context
    assert context.evidence_budget.truncated is False


@pytest.mark.unit
def test_budget_allocation_is_reproducible() -> None:
    """Same bounds, same demand, same allocation — every time."""
    policy = DefaultOrchestrationPolicy(
        evidence_budget=EvidenceBudget(max_artifacts_per_domain=25, max_artifacts_total=60)
    )
    groups = [
        _group("cons-component-a", quality=100, risk=RiskLevel.CRITICAL),
        _group("cons-tag-b", security=100, risk=RiskLevel.HIGH),
        _group("cons-endpoint-c", functional=100, risk=RiskLevel.MEDIUM),
    ]
    first = _orchestrator(policy).orchestrate(groups).context
    second = _orchestrator(policy).orchestrate(list(reversed(groups))).context
    assert first.model_dump_json() == second.model_dump_json()
    # Three contested domains, 25 each, capped by a 60 total: 20 apiece.
    assert (first.grounding.functional_count, first.grounding.security_count) == (20, 20)
    assert first.grounding.quality_count == 20


# ---------------------------------------------------------------------------
# Ranking and evidence ordering (Stage 5)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_risk_then_record_id_ordering_admits_the_most_severe_evidence() -> None:
    """The ordering rule decides which artifacts survive the budget, not just how they read."""
    policy = DefaultOrchestrationPolicy(
        evidence_budget=EvidenceBudget(max_artifacts_per_domain=2, max_artifacts_total=6)
    )
    group = ConsolidatedArtifact(
        consolidated_id="cons-component-a",
        module="auth",
        risk_level=RiskLevel.CRITICAL,
        quality_artifacts=[
            _artifact(1, SourceCategory.QUALITY, SourceType.SAST, severity="Low"),
            _artifact(2, SourceCategory.QUALITY, SourceType.SAST, severity="Blocker"),
            _artifact(3, SourceCategory.QUALITY, SourceType.SAST, severity="Major"),
        ],
    )
    context = _orchestrator(policy).orchestrate([group]).context
    assert [a.source_record_id for a in context.evidence.quality_artifacts] == [
        "REC-002",  # Blocker -> CRITICAL
        "REC-003",  # Major   -> HIGH
    ]


@pytest.mark.unit
def test_evidence_ordering_ties_break_on_record_id_ascending() -> None:
    policy = DefaultOrchestrationPolicy()
    group = ConsolidatedArtifact(
        consolidated_id="cons-component-a",
        module="auth",
        risk_level=RiskLevel.LOW,
        security_artifacts=[
            _artifact(9, SourceCategory.SECURITY, SourceType.DAST, severity="High"),
            _artifact(2, SourceCategory.SECURITY, SourceType.DAST, severity="High"),
        ],
    )
    context = _orchestrator(policy).orchestrate([group]).context
    assert [a.source_record_id for a in context.evidence.security_artifacts] == [
        "REC-002",
        "REC-009",
    ]


@pytest.mark.unit
def test_the_ranking_records_every_candidate_with_its_score() -> None:
    context = _default().orchestrate(_three_domain_candidates()).context
    ranking = context.ranking
    assert len(ranking.entries) == 3
    assert [e.rank for e in ranking.entries] == [1, 2, 3]
    assert ranking.keys == ("risk_level_desc", "artifact_count_desc", "consolidated_id_asc")
    assert ranking.tie_breaker == "consolidated_id_asc"

    top = ranking.entries[0]
    assert top.consolidated_id == "cons-component-noisy"
    assert [(c.key, c.value) for c in top.score] == [
        ("risk_level_desc", "critical"),
        ("artifact_count_desc", "9"),
        ("consolidated_id_asc", "cons-component-noisy"),
    ]


@pytest.mark.unit
def test_risk_outranks_size_under_the_default_policy() -> None:
    """A CRITICAL defect outranks 71 code smells, which is why risk ranks first."""
    groups = [
        _group("cons-component-noisy", quality=71, risk=RiskLevel.LOW),
        _group("cons-tag-severe", security=1, risk=RiskLevel.CRITICAL),
    ]
    context = _default().orchestrate(groups).context
    assert context.ranking.entries[0].consolidated_id == "cons-tag-severe"
    assert context.ranking.rank_of("cons-component-noisy") == 2


# ---------------------------------------------------------------------------
# Explainability (Stage 6)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_every_excluded_group_records_why_it_was_excluded() -> None:
    """An exclusion without a reason is indistinguishable from a hidden ranking."""
    context = _orchestrator().orchestrate(_three_domain_candidates()).context
    excluded = [e for e in context.ranking.entries if not e.selected]
    assert len(excluded) == 2
    for entry in excluded:
        assert entry.contributed_artifact_count == 0
        assert "single_largest" in entry.decision_reason
        assert f"Ranked {entry.rank} of 3" in entry.decision_reason


@pytest.mark.unit
def test_an_admitted_group_records_the_domains_it_was_admitted_to_cover() -> None:
    context = _default().orchestrate(_three_domain_candidates()).context
    reasons = {c.consolidated_id: c.inclusion_reason for c in context.provenance.contributions}
    assert "to cover security" in reasons["cons-tag-xss"]
    assert "to cover functional" in reasons["cons-endpoint-login"]
    assert "coverage_guaranteed" in reasons["cons-component-noisy"]


@pytest.mark.unit
def test_excluded_groups_under_coverage_cite_the_exhausted_budget() -> None:
    policy = DefaultOrchestrationPolicy(
        evidence_budget=EvidenceBudget(max_artifacts_per_domain=1, max_artifacts_total=3)
    )
    groups = [
        _group("cons-component-a", quality=5, risk=RiskLevel.CRITICAL),
        _group("cons-component-b", quality=5, risk=RiskLevel.LOW),
    ]
    context = _orchestrator(policy).orchestrate(groups).context
    (excluded,) = [e for e in context.ranking.entries if not e.selected]
    assert excluded.consolidated_id == "cons-component-b"
    assert "exhausted its allocation" in excluded.decision_reason


@pytest.mark.unit
def test_the_ranking_and_the_provenance_name_the_same_groups() -> None:
    """The model refuses to hold a ranking that disagrees with what contributed."""
    context = _default().orchestrate(_three_domain_candidates()).context
    assert (
        context.ranking.selected_consolidated_ids
        == context.provenance.contributing_consolidated_ids
    )


# ---------------------------------------------------------------------------
# Grounding metadata (Stage 7)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_grounding_reports_the_domains_and_counts_of_the_assembled_evidence() -> None:
    context = _default().orchestrate(_three_domain_candidates()).context
    grounding = context.grounding
    assert grounding.evidence_domains == (
        SourceCategory.FUNCTIONAL,
        SourceCategory.SECURITY,
        SourceCategory.QUALITY,
    )
    assert (grounding.functional_count, grounding.security_count, grounding.quality_count) == (
        2,
        3,
        9,
    )
    assert grounding.total_count == 14


@pytest.mark.unit
def test_grounding_reports_the_source_distribution() -> None:
    context = _default().orchestrate(_three_domain_candidates()).context
    distribution = context.grounding.source_distribution
    assert [(str(e.source_system), e.artifact_count) for e in distribution] == [("jira", 14)]


# ---------------------------------------------------------------------------
# Subject derivation under a multi-source policy
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_a_multi_group_context_takes_its_subject_from_the_top_ranked_group() -> None:
    """Coverage adds evidence to a context without moving its subject."""
    groups = _three_domain_candidates()
    context = _default().orchestrate(groups).context
    assert context.subject.label == "auth"
    assert context.subject.basis == ContextSubjectBasis.MULTI


@pytest.mark.unit
def test_the_primary_group_is_the_top_ranked_contributor() -> None:
    result = _default().orchestrate(_three_domain_candidates())
    assert result.primary_group.consolidated_id == "cons-component-noisy"
    assert result.selected_groups[0] is result.primary_group


# ---------------------------------------------------------------------------
# Policy comparison (Stage 9)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_activating_the_default_policy_widens_the_evidence_without_moving_the_subject() -> None:
    """The single claim CAP-076D makes, tested directly."""
    groups = _three_domain_candidates()
    legacy = _orchestrator().orchestrate(groups).context
    default = _default().orchestrate(groups).context

    assert legacy.subject.label == default.subject.label
    assert legacy.evidence.total_count == 9
    assert default.evidence.total_count == 14
    assert legacy.provenance.contributing_group_count == 1
    assert default.provenance.contributing_group_count == 3
    assert legacy.provenance.candidate_group_count == default.provenance.candidate_group_count


@pytest.mark.unit
def test_both_policies_rank_the_same_candidate_set() -> None:
    """The candidates are Consolidation's output; no policy may narrow them."""
    groups = _three_domain_candidates()
    legacy = _orchestrator().orchestrate(groups).context
    default = _default().orchestrate(groups).context
    assert len(legacy.ranking.entries) == len(default.ranking.entries) == 3


@pytest.mark.unit
def test_the_default_policy_is_deterministic_over_a_multi_group_context() -> None:
    groups = _three_domain_candidates()
    first = _default().orchestrate(groups).context
    second = _default().orchestrate(list(reversed(groups))).context
    assert first.model_dump_json() == second.model_dump_json()
