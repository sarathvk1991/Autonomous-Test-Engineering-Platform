"""Unit tests for the declarative Orchestration Policy framework.

A policy is inert data. These tests assert its defaults, its self-validation,
its metadata, and — most importantly — that a non-deterministic policy is
*unrepresentable*, discharging CAP-076A Invariant 7 structurally.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from requirement_intelligence.context_orchestration.models.context_identity import (
    OrchestrationPolicyId,
    PolicyVersion,
)
from requirement_intelligence.context_orchestration.policy import (
    REASON_TEMPLATE_FIELDS,
    CoverageMode,
    CoverageRule,
    DefaultOrchestrationPolicy,
    EvidenceBudget,
    EvidenceOrdering,
    LegacySelectionPolicy,
    OrchestrationPolicy,
    RankingKey,
    RankingRule,
    SelectionStrategy,
    TieBreaker,
)

# ---------------------------------------------------------------------------
# Defaults & metadata
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_default_policy_is_an_orchestration_policy() -> None:
    assert isinstance(DefaultOrchestrationPolicy(), OrchestrationPolicy)


@pytest.mark.unit
def test_default_policy_metadata_is_governed() -> None:
    policy = DefaultOrchestrationPolicy()
    assert policy.policy_id == OrchestrationPolicyId("coverage")
    assert policy.policy_version == PolicyVersion(1, 0, 0)
    assert policy.description


@pytest.mark.unit
def test_default_policy_guarantees_coverage_and_ranks_risk_before_size() -> None:
    """The two rules that repair the CAP-074B defect."""
    policy = DefaultOrchestrationPolicy()
    assert policy.coverage.mode == CoverageMode.ALL_PRESENT_CATEGORIES
    assert policy.selection_strategy == SelectionStrategy.COVERAGE_GUARANTEED
    assert policy.ranking.keys[0] == RankingKey.RISK_LEVEL_DESC
    assert policy.ranking.keys.index(RankingKey.RISK_LEVEL_DESC) < policy.ranking.keys.index(
        RankingKey.ARTIFACT_COUNT_DESC
    )


@pytest.mark.unit
def test_default_policy_budgets_per_domain_not_only_in_total() -> None:
    """CAP-076A R8: a global cap alone still yields an all-Sonar context."""
    budget = DefaultOrchestrationPolicy().evidence_budget
    assert budget.max_artifacts_per_domain < budget.max_artifacts_total


@pytest.mark.unit
def test_legacy_policy_restates_todays_selection_rule() -> None:
    policy = LegacySelectionPolicy()
    assert policy.selection_strategy == SelectionStrategy.SINGLE_LARGEST
    assert policy.coverage.mode == CoverageMode.SINGLE_LARGEST_GROUP
    assert policy.ranking.keys == (RankingKey.ARTIFACT_COUNT_DESC, RankingKey.CONSOLIDATED_ID_ASC)


@pytest.mark.unit
def test_policies_are_immutable() -> None:
    with pytest.raises(ValidationError):
        DefaultOrchestrationPolicy().description = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Invariant 7 — reproducibility is enforced by the type system
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_every_ranking_key_is_a_deterministic_data_derived_key() -> None:
    """No enum member exists that a probabilistic or learned score could inhabit."""
    assert set(RankingKey) == {
        RankingKey.RISK_LEVEL_DESC,
        RankingKey.ARTIFACT_COUNT_DESC,
        RankingKey.CONSOLIDATED_ID_ASC,
    }


@pytest.mark.unit
def test_tie_breaker_admits_only_a_total_order() -> None:
    assert set(TieBreaker) == {TieBreaker.CONSOLIDATED_ID_ASC}


@pytest.mark.unit
def test_ranking_rejects_duplicate_keys() -> None:
    """A repeated key can never break a tie the first occurrence did not."""
    with pytest.raises(ValidationError):
        RankingRule(keys=(RankingKey.RISK_LEVEL_DESC, RankingKey.RISK_LEVEL_DESC))


@pytest.mark.unit
def test_ranking_requires_at_least_one_key() -> None:
    with pytest.raises(ValidationError):
        RankingRule(keys=())


# ---------------------------------------------------------------------------
# Self-validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_budget_rejects_unsatisfiable_bounds() -> None:
    with pytest.raises(ValidationError):
        EvidenceBudget(max_artifacts_per_domain=10, max_artifacts_total=5)


@pytest.mark.unit
@pytest.mark.parametrize("field", ["max_artifacts_per_domain", "max_artifacts_total"])
def test_budget_rejects_non_positive_bounds(field: str) -> None:
    values = {"max_artifacts_per_domain": 5, "max_artifacts_total": 5, field: 0}
    with pytest.raises(ValidationError):
        EvidenceBudget(**values)  # type: ignore[arg-type]


@pytest.mark.unit
def test_policy_rejects_coverage_strategy_contradiction() -> None:
    """A single group cannot guarantee coverage; the policy must say so."""
    with pytest.raises(ValidationError):
        DefaultOrchestrationPolicy(coverage=CoverageRule(mode=CoverageMode.SINGLE_LARGEST_GROUP))


@pytest.mark.unit
def test_policy_rejects_reason_template_with_unknown_placeholder() -> None:
    with pytest.raises(ValidationError):
        DefaultOrchestrationPolicy(reason_template="composed from {bogus}")


@pytest.mark.unit
def test_policy_accepts_reason_template_using_only_known_placeholders() -> None:
    template = " ".join(f"{{{field}}}" for field in sorted(REASON_TEMPLATE_FIELDS))
    assert DefaultOrchestrationPolicy(reason_template=template).reason_template == template


@pytest.mark.unit
def test_policy_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        DefaultOrchestrationPolicy(unexpected="x")


# ---------------------------------------------------------------------------
# Explainability
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_render_reason_substitutes_supplied_fields() -> None:
    policy = DefaultOrchestrationPolicy(
        reason_template="{subject}/{strategy}/{groups}/{categories}"
    )
    assert policy.render_reason(subject="Auth", strategy="s", groups=2, categories="a, b") == (
        "Auth/s/2/a, b"
    )


@pytest.mark.unit
def test_render_reason_raises_when_a_placeholder_is_missing() -> None:
    policy = DefaultOrchestrationPolicy(reason_template="{subject}")
    with pytest.raises(ValueError, match="subject"):
        policy.render_reason(groups=1)


@pytest.mark.unit
def test_default_reason_asserts_co_selection_not_correlation() -> None:
    """CAP-076A Invariant 2, discharged where a reader will actually see it."""
    assert "no correlation" in DefaultOrchestrationPolicy().reason_template.lower()


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_policy_serialises_with_string_identifiers_and_camel_case() -> None:
    dumped = DefaultOrchestrationPolicy().model_dump(mode="json", by_alias=True)
    assert dumped["policyId"] == "coverage"
    assert dumped["policyVersion"] == "1.0.0"
    assert dumped["evidenceBudget"]["maxArtifactsPerDomain"] == 25
    assert dumped["selectionStrategy"] == "coverage_guaranteed"


@pytest.mark.unit
def test_policy_survives_a_json_round_trip() -> None:
    policy = DefaultOrchestrationPolicy()
    restored = OrchestrationPolicy.model_validate_json(policy.model_dump_json())
    assert restored.policy_id == policy.policy_id
    assert restored.ranking.keys == policy.ranking.keys
    assert restored.evidence_budget == policy.evidence_budget


@pytest.mark.unit
def test_policy_is_constructible_from_scratch_without_defaults() -> None:
    """A future governed policy file must be expressible as plain data."""
    policy = OrchestrationPolicy(
        policy_id=OrchestrationPolicyId("custom"),
        policy_version=PolicyVersion(1, 0, 0),
        description="custom",
        coverage=CoverageRule(mode=CoverageMode.ALL_PRESENT_CATEGORIES),
        ranking=RankingRule(keys=(RankingKey.CONSOLIDATED_ID_ASC,)),
        evidence_budget=EvidenceBudget(max_artifacts_per_domain=1, max_artifacts_total=1),
        evidence_ordering=EvidenceOrdering.GROUP_ORDER,
        selection_strategy=SelectionStrategy.COVERAGE_GUARANTEED,
        reason_template="{subject}",
    )
    assert policy.policy_id == OrchestrationPolicyId("custom")
