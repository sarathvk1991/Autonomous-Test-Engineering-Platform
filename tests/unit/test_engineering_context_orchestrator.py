"""CAP-076C — Engineering Context Orchestrator runtime integration.

Covers the orchestrator's four responsibilities — policy execution, evidence
selection, subject derivation, and explanation — and the one claim the whole
milestone rests on: under ``LegacySelectionPolicy`` the orchestrator selects
exactly what ``_select_consolidated`` selected before it existed.

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


def _artifact(index: int, category: SourceCategory, source_type: SourceType) -> SourceArtifact:
    return SourceArtifact(
        artifact_id=f"A{index}",
        source_system=SourceSystem.JIRA,
        source_record_id=f"REC-{index}",
        source_category=category,
        source_type=source_type,
        title=f"Artifact {index}",
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
def test_coverage_guaranteed_strategy_is_not_executed() -> None:
    """DefaultOrchestrationPolicy stays inactive: the orchestrator refuses, never degrades."""
    orchestrator = _orchestrator(DefaultOrchestrationPolicy())
    with pytest.raises(ContextOrchestrationError, match="coverage_guaranteed"):
        orchestrator.orchestrate([_group("cons-component-a", quality=1)])


@pytest.mark.unit
def test_unsupported_evidence_ordering_is_not_executed() -> None:
    """Reordering evidence across sources is CAP-076D; silently ignoring it is not an option."""
    policy = _risk_first_policy().model_copy(
        update={"evidence_ordering": EvidenceOrdering.RISK_THEN_RECORD_ID}
    )
    with pytest.raises(ContextOrchestrationError, match="risk_then_record_id"):
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
def test_platform_context_binds_the_orchestrator_to_the_legacy_policy() -> None:
    """The runtime policy is Legacy; Default is constructible but never bound by default."""
    context = PlatformContext()
    orchestrator = context.create_engineering_context_orchestrator()
    assert isinstance(orchestrator, EngineeringContextOrchestrator)
    assert isinstance(orchestrator.policy, LegacySelectionPolicy)
    assert isinstance(context.create_orchestration_policy(), DefaultOrchestrationPolicy)


@pytest.mark.unit
def test_platform_context_accepts_an_explicit_policy_override() -> None:
    orchestrator = PlatformContext().create_engineering_context_orchestrator(
        DefaultOrchestrationPolicy()
    )
    assert isinstance(orchestrator.policy, DefaultOrchestrationPolicy)


@pytest.mark.unit
def test_platform_context_returns_independent_orchestrators() -> None:
    context = PlatformContext()
    first = context.create_engineering_context_orchestrator()
    second = context.create_engineering_context_orchestrator()
    assert first is not second
