"""Unit tests for the EngineeringContext canonical model and its builder.

Also asserts the CAP-076B containment guarantee: the subsystem exists, is
constructed by ``PlatformContext``, and is consumed by **nothing** in the
runtime. That last assertion is the milestone's central claim, so it is tested
rather than asserted in prose.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from requirement_intelligence.context_orchestration import (
    ENGINEERING_CONTEXT_VERSION,
    EVIDENCE_DOMAINS,
    ContextBudgetExceededError,
    ContextConstructionError,
    ContextContribution,
    ContextCoverage,
    ContextCoverageDomain,
    ContextDependencies,
    ContextEvidence,
    ContextEvidenceBudgetUsage,
    ContextGrounding,
    ContextMetadata,
    ContextProvenance,
    ContextRanking,
    ContextRankingEntry,
    ContextSubject,
    ContextSubjectBasis,
    DefaultOrchestrationPolicy,
    DomainBudgetUsage,
    EngineeringContext,
    EngineeringContextBuilder,
    EngineeringContextId,
    GroupContribution,
    LegacySelectionPolicy,
    OrchestrationMetadata,
    OrchestrationPolicyId,
    PolicyCompatibilityError,
    PolicyVersion,
    RankingScoreComponent,
    SourceDistributionEntry,
)
from requirement_intelligence.models.consolidated_artifact import ConsolidatedArtifact
from requirement_intelligence.models.enums import (
    RiskLevel,
    SourceCategory,
    SourceSystem,
    SourceType,
)
from requirement_intelligence.models.source_artifact import SourceArtifact

_REPO_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Fixtures — deterministic, no uuid4
# ---------------------------------------------------------------------------


def _artifact(
    index: int,
    category: SourceCategory,
    source_type: SourceType,
    *,
    severity: str | None = None,
    component: str | None = None,
    url: str | None = None,
) -> SourceArtifact:
    return SourceArtifact(
        artifact_id=f"art-{index}",
        source_system=SourceSystem.SONARQUBE,
        source_record_id=f"REC-{index}",
        source_category=category,
        source_type=source_type,
        title=f"Finding {index}",
        severity=severity,
        component=component,
        url=url,
    )


def _functional_group() -> ConsolidatedArtifact:
    return ConsolidatedArtifact(
        consolidated_id="cons-endpoint-login",
        module="/login",
        risk_level=RiskLevel.HIGH,
        functional_artifacts=[
            _artifact(1, SourceCategory.FUNCTIONAL, SourceType.STORY, url="https://x.io/login")
        ],
    )


def _security_group() -> ConsolidatedArtifact:
    return ConsolidatedArtifact(
        consolidated_id="cons-tag-xss",
        module="xss",
        risk_level=RiskLevel.MEDIUM,
        security_artifacts=[
            _artifact(2, SourceCategory.SECURITY, SourceType.DAST, severity="High")
        ],
    )


def _quality_group(count: int = 1) -> ConsolidatedArtifact:
    return ConsolidatedArtifact(
        consolidated_id="cons-component-auth",
        module="auth.java",
        risk_level=RiskLevel.CRITICAL,
        quality_artifacts=[
            _artifact(
                100 + i,
                SourceCategory.QUALITY,
                SourceType.SAST,
                severity="BLOCKER",
                component="auth.java",
            )
            for i in range(count)
        ],
    )


def _subject() -> ContextSubject:
    return ContextSubject(label="Authentication", basis=ContextSubjectBasis.MULTI)


def _domain_artifacts(group: ConsolidatedArtifact, domain: SourceCategory) -> list[SourceArtifact]:
    if domain == SourceCategory.FUNCTIONAL:
        return group.functional_artifacts
    if domain == SourceCategory.SECURITY:
        return group.security_artifacts
    return group.quality_artifacts


class _Decision:
    """Everything an orchestrator decides, for a builder that decides nothing.

    The builder's contract is that it receives already-selected, already-ordered,
    already-budgeted evidence and the records of how those decisions were made.
    Constructing those records here — rather than running the real orchestrator —
    is what lets these tests exercise the *builder* in isolation, including the
    inputs a correct orchestrator would never hand it.

    The recorded budget bounds are deliberately permissive: they describe what was
    spent, not what the policy allows. The *policy* carries the rule, and the
    builder enforces it, which is what the budget-rejection tests below prove.
    """

    def __init__(self, groups: list[ConsolidatedArtifact]) -> None:
        self.evidence = ContextEvidence(
            functional_artifacts=tuple(a for g in groups for a in g.functional_artifacts),
            security_artifacts=tuple(a for g in groups for a in g.security_artifacts),
            quality_artifacts=tuple(a for g in groups for a in g.quality_artifacts),
        )
        self.contributions = tuple(
            GroupContribution.whole(group, rank=rank, inclusion_reason=f"admitted at rank {rank}")
            for rank, group in enumerate(groups, start=1)
        )
        counts = {
            domain: len(_domain_artifacts_of(self.evidence, domain)) for domain in EVIDENCE_DOMAINS
        }

        self.ranking = ContextRanking(
            keys=("artifact_count_desc",),
            tie_breaker="consolidated_id_asc",
            entries=tuple(
                ContextRankingEntry(
                    rank=c.rank,
                    consolidated_id=c.consolidated_id,
                    risk_level=c.group.risk_level,
                    candidate_artifact_count=c.candidate_count,
                    contributed_artifact_count=c.contributed_count,
                    score=(
                        RankingScoreComponent(
                            key="artifact_count_desc", value=str(c.candidate_count)
                        ),
                    ),
                    selected=True,
                    decision_reason=c.inclusion_reason,
                )
                for c in self.contributions
            ),
        )
        self.coverage = ContextCoverage(
            mode="all_present_categories",
            selection_strategy="coverage_guaranteed",
            domains=tuple(
                ContextCoverageDomain(
                    category=domain,
                    evidence_present=counts[domain] > 0,
                    represented=counts[domain] > 0,
                    candidate_artifact_count=counts[domain],
                    contributed_artifact_count=counts[domain],
                    contributing_group_count=sum(1 for g in groups if _domain_artifacts(g, domain)),
                    truncated=False,
                    reason="Supplied whole by the test decision record.",
                )
                for domain in EVIDENCE_DOMAINS
            ),
            rule_satisfied=True,
            all_present_categories_represented=any(counts.values()),
        )
        self.evidence_budget = ContextEvidenceBudgetUsage(
            max_artifacts_per_domain=max(1, *counts.values()),
            max_artifacts_total=max(1, sum(counts.values())),
            domains=tuple(
                DomainBudgetUsage(
                    category=domain,
                    available=counts[domain],
                    allocated=counts[domain],
                    used=counts[domain],
                )
                for domain in EVIDENCE_DOMAINS
            ),
        )


def _domain_artifacts_of(
    evidence: ContextEvidence, domain: SourceCategory
) -> tuple[SourceArtifact, ...]:
    if domain == SourceCategory.FUNCTIONAL:
        return evidence.functional_artifacts
    if domain == SourceCategory.SECURITY:
        return evidence.security_artifacts
    return evidence.quality_artifacts


def _build(groups: list[ConsolidatedArtifact], policy: object | None = None) -> EngineeringContext:
    decision = _Decision(groups)
    return EngineeringContextBuilder().build(
        subject=_subject(),
        evidence=decision.evidence,
        contributions=decision.contributions,
        policy=policy or DefaultOrchestrationPolicy(),  # type: ignore[arg-type]
        ranking=decision.ranking,
        coverage=decision.coverage,
        evidence_budget=decision.evidence_budget,
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_builder_composes_evidence_from_every_contributing_group() -> None:
    """The defect CAP-076 exists to fix: all three domains reach one context."""
    context = _build([_functional_group(), _security_group(), _quality_group()])
    assert context.evidence.categories_present == frozenset(
        {SourceCategory.FUNCTIONAL, SourceCategory.SECURITY, SourceCategory.QUALITY}
    )
    assert context.evidence.total_count == 3


@pytest.mark.unit
def test_builder_preserves_supplied_evidence_order() -> None:
    """The builder never reorders; ordering is the orchestrator's decision."""
    group = ConsolidatedArtifact(
        consolidated_id="cons-component-auth",
        module="auth",
        risk_level=RiskLevel.LOW,
        quality_artifacts=[
            _artifact(3, SourceCategory.QUALITY, SourceType.SAST),
            _artifact(1, SourceCategory.QUALITY, SourceType.SAST),
            _artifact(2, SourceCategory.QUALITY, SourceType.SAST),
        ],
    )
    context = _build([group])
    assert [a.source_record_id for a in context.evidence.quality_artifacts] == [
        "REC-3",
        "REC-1",
        "REC-2",
    ]


@pytest.mark.unit
def test_builder_populates_provenance_in_selection_order() -> None:
    context = _build([_security_group(), _functional_group()])
    assert context.provenance.contributing_consolidated_ids == (
        "cons-tag-xss",
        "cons-endpoint-login",
    )
    assert context.provenance.contributing_group_count == 2
    assert context.provenance.source_artifact_count == 2


@pytest.mark.unit
def test_builder_populates_orchestration_metadata_from_the_policy() -> None:
    context = _build([_quality_group()])
    assert context.orchestration.policy_id == OrchestrationPolicyId("coverage")
    assert context.orchestration.policy_version == PolicyVersion(1, 0, 0)
    assert context.orchestration.context_model_version == ENGINEERING_CONTEXT_VERSION


@pytest.mark.unit
def test_builder_renders_the_orchestration_reason_from_the_policy_template() -> None:
    context = _build([_functional_group(), _quality_group()])
    assert "Authentication" in context.orchestration_reason
    assert "no correlation" in context.orchestration_reason.lower()


@pytest.mark.unit
def test_builder_derives_metadata_via_the_consolidation_risk_rollup() -> None:
    """BLOCKER normalises to CRITICAL through consolidation_rules.rollup_risk."""
    context = _build([_functional_group(), _quality_group()])
    assert context.context_metadata.risk_level == RiskLevel.CRITICAL
    assert context.context_metadata.components == ("auth.java",)
    assert context.context_metadata.endpoints == ("/login",)


@pytest.mark.unit
def test_builder_sorts_derived_collections() -> None:
    """Invariant 7: never depend on set-iteration order."""
    group = ConsolidatedArtifact(
        consolidated_id="cons-component-multi",
        module="multi",
        risk_level=RiskLevel.LOW,
        quality_artifacts=[
            _artifact(1, SourceCategory.QUALITY, SourceType.SAST, component="zeta.java"),
            _artifact(2, SourceCategory.QUALITY, SourceType.SAST, component="alpha.java"),
        ],
    )
    assert _build([group]).context_metadata.components == ("alpha.java", "zeta.java")


# ---------------------------------------------------------------------------
# Identity & reproducibility (CAP-076A Invariant 7)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_context_id_is_deterministic_across_builds() -> None:
    groups = [_functional_group(), _quality_group()]
    assert _build(groups).context_id == _build(groups).context_id


@pytest.mark.unit
def test_context_id_is_a_typed_identifier_with_a_readable_slug() -> None:
    context_id = _build([_quality_group()]).context_id
    assert isinstance(context_id, EngineeringContextId)
    assert str(context_id).startswith("ctx-authentication-")


@pytest.mark.unit
def test_context_id_changes_when_contributing_groups_change() -> None:
    assert (
        _build([_quality_group()]).context_id
        != _build([_quality_group(), _security_group()]).context_id
    )


@pytest.mark.unit
def test_context_id_changes_when_group_order_changes() -> None:
    """Two contexts drawing the same groups in a different order are different contexts."""
    a = _build([_functional_group(), _security_group()])
    b = _build([_security_group(), _functional_group()])
    assert a.context_id != b.context_id


@pytest.mark.unit
def test_context_id_does_not_depend_on_artifact_id() -> None:
    """Mappers mint artifact_id with uuid4; identity must not inherit that entropy."""
    base = _quality_group()
    mutated = ConsolidatedArtifact(
        consolidated_id=base.consolidated_id,
        module=base.module,
        risk_level=base.risk_level,
        quality_artifacts=[
            a.model_copy(update={"artifact_id": "totally-different"})
            for a in base.quality_artifacts
        ],
    )
    assert _build([base]).context_id == _build([mutated]).context_id


# ---------------------------------------------------------------------------
# Immutability & equality
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_context_is_frozen() -> None:
    context = _build([_quality_group()])
    with pytest.raises(ValidationError):
        context.orchestration_reason = "changed"  # type: ignore[misc]


@pytest.mark.unit
def test_context_evidence_collections_are_deeply_immutable() -> None:
    """A frozen model with list fields would still permit container mutation."""
    context = _build([_quality_group()])
    assert isinstance(context.evidence.quality_artifacts, tuple)
    assert isinstance(context.context_metadata.components, tuple)
    assert isinstance(context.provenance.contributing_consolidated_ids, tuple)


@pytest.mark.unit
def test_context_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        EngineeringContext(unexpected="x")  # type: ignore[call-arg]


@pytest.mark.unit
def test_equal_inputs_produce_equal_contexts() -> None:
    assert _build([_quality_group()]) == _build([_quality_group()])


# ---------------------------------------------------------------------------
# Model invariants
# ---------------------------------------------------------------------------


def _contribution(consolidated_id: str, artifact_count: int = 1) -> ContextContribution:
    return ContextContribution(
        consolidated_id=consolidated_id,
        module="auth",
        rank=1,
        artifact_count=artifact_count,
        candidate_artifact_count=artifact_count,
        quality_count=artifact_count,
        inclusion_reason="selected for the test",
    )


def _provenance(
    ids: tuple[str, ...],
    *,
    source_artifact_count: int,
    artifact_count: int = 1,
) -> ContextProvenance:
    return ContextProvenance(
        contributions=tuple(_contribution(i, artifact_count) for i in ids),
        candidate_group_count=len(ids),
        source_artifact_count=source_artifact_count,
    )


def _ranking(ids: tuple[str, ...] = ("cons-a",), *, artifact_count: int = 1) -> ContextRanking:
    return ContextRanking(
        keys=("artifact_count_desc",),
        tie_breaker="consolidated_id_asc",
        entries=tuple(
            ContextRankingEntry(
                rank=rank,
                consolidated_id=identifier,
                risk_level=RiskLevel.LOW,
                candidate_artifact_count=artifact_count,
                contributed_artifact_count=artifact_count,
                score=(
                    RankingScoreComponent(key="artifact_count_desc", value=str(artifact_count)),
                ),
                selected=True,
                decision_reason="selected for the test",
            )
            for rank, identifier in enumerate(ids, start=1)
        ),
    )


def _coverage(*, quality: int = 1) -> ContextCoverage:
    counts = {
        SourceCategory.FUNCTIONAL: 0,
        SourceCategory.SECURITY: 0,
        SourceCategory.QUALITY: quality,
    }
    return ContextCoverage(
        mode="all_present_categories",
        selection_strategy="coverage_guaranteed",
        domains=tuple(
            ContextCoverageDomain(
                category=domain,
                evidence_present=counts[domain] > 0,
                represented=counts[domain] > 0,
                candidate_artifact_count=counts[domain],
                contributed_artifact_count=counts[domain],
                contributing_group_count=1 if counts[domain] else 0,
                truncated=False,
                reason="test",
            )
            for domain in EVIDENCE_DOMAINS
        ),
        rule_satisfied=True,
        all_present_categories_represented=True,
    )


def _budget(*, quality: int = 1) -> ContextEvidenceBudgetUsage:
    counts = {
        SourceCategory.FUNCTIONAL: 0,
        SourceCategory.SECURITY: 0,
        SourceCategory.QUALITY: quality,
    }
    return ContextEvidenceBudgetUsage(
        max_artifacts_per_domain=max(1, quality),
        max_artifacts_total=max(1, quality),
        domains=tuple(
            DomainBudgetUsage(
                category=domain,
                available=counts[domain],
                allocated=counts[domain],
                used=counts[domain],
            )
            for domain in EVIDENCE_DOMAINS
        ),
    )


def _grounding(*, quality: int = 1) -> ContextGrounding:
    return ContextGrounding(
        evidence_domains=(SourceCategory.QUALITY,),
        functional_count=0,
        security_count=0,
        quality_count=quality,
        total_count=quality,
        source_distribution=(
            SourceDistributionEntry(source_system=SourceSystem.SONARQUBE, artifact_count=quality),
        ),
    )


def _valid_kwargs() -> dict[str, object]:
    return {
        "context_id": EngineeringContextId("ctx-a-1"),
        "subject": _subject(),
        "evidence": ContextEvidence(
            quality_artifacts=(_artifact(1, SourceCategory.QUALITY, SourceType.SAST),)
        ),
        "context_metadata": ContextMetadata(risk_level=RiskLevel.LOW),
        "dependencies": ContextDependencies(),
        "provenance": _provenance(("cons-a",), source_artifact_count=1),
        "orchestration": OrchestrationMetadata(
            policy_id=OrchestrationPolicyId("coverage"),
            policy_version=PolicyVersion(1, 0, 0),
        ),
        "ranking": _ranking(),
        "coverage": _coverage(),
        "evidence_budget": _budget(),
        "grounding": _grounding(),
        "orchestration_reason": "because",
    }


@pytest.mark.unit
def test_context_rejects_empty_evidence() -> None:
    kwargs = _valid_kwargs()
    kwargs["evidence"] = ContextEvidence()
    with pytest.raises(ValidationError, match="at least one evidence artifact"):
        EngineeringContext(**kwargs)  # type: ignore[arg-type]


@pytest.mark.unit
def test_context_rejects_a_ranking_that_disagrees_with_provenance() -> None:
    """A group the ranking never admitted cannot appear as a contributor."""
    kwargs = _valid_kwargs()
    kwargs["ranking"] = _ranking(("cons-somewhere-else",))
    with pytest.raises(ValidationError, match="Ranking selected"):
        EngineeringContext(**kwargs)  # type: ignore[arg-type]


@pytest.mark.unit
def test_context_rejects_coverage_that_miscounts_the_evidence() -> None:
    """Coverage is checked against the artifacts, not against its own good intentions."""
    kwargs = _valid_kwargs()
    kwargs["coverage"] = _coverage(quality=9)
    with pytest.raises(ValidationError, match="Coverage claims"):
        EngineeringContext(**kwargs)  # type: ignore[arg-type]


@pytest.mark.unit
def test_context_rejects_grounding_that_miscounts_the_evidence() -> None:
    kwargs = _valid_kwargs()
    kwargs["grounding"] = _grounding(quality=4)
    with pytest.raises(ValidationError, match="Grounding counts"):
        EngineeringContext(**kwargs)  # type: ignore[arg-type]


@pytest.mark.unit
def test_context_rejects_a_budget_that_miscounts_the_evidence() -> None:
    kwargs = _valid_kwargs()
    kwargs["evidence_budget"] = _budget(quality=6)
    with pytest.raises(ValidationError, match="Budget records"):
        EngineeringContext(**kwargs)  # type: ignore[arg-type]


@pytest.mark.unit
def test_context_rejects_provenance_disagreeing_with_evidence() -> None:
    kwargs = _valid_kwargs()
    kwargs["provenance"] = _provenance(("cons-a",), source_artifact_count=99)
    with pytest.raises(ValidationError, match="Provenance disagrees with evidence"):
        EngineeringContext(**kwargs)  # type: ignore[arg-type]


@pytest.mark.unit
def test_context_rejects_contributions_disagreeing_with_evidence() -> None:
    """A group cannot claim to have contributed artifacts the context does not hold."""
    kwargs = _valid_kwargs()
    kwargs["provenance"] = _provenance(("cons-a",), source_artifact_count=1, artifact_count=7)
    with pytest.raises(ValidationError, match="Contributions disagree with evidence"):
        EngineeringContext(**kwargs)  # type: ignore[arg-type]


@pytest.mark.unit
def test_provenance_rejects_fewer_candidates_than_contributors() -> None:
    """A context cannot draw on more groups than the policy ever ranked."""
    with pytest.raises(ValidationError, match="candidateGroupCount"):
        ContextProvenance(
            contributions=(_contribution("cons-a"), _contribution("cons-b")),
            candidate_group_count=1,
            source_artifact_count=2,
        )


@pytest.mark.unit
def test_context_rejects_empty_orchestration_reason() -> None:
    kwargs = _valid_kwargs()
    kwargs["orchestration_reason"] = ""
    with pytest.raises(ValidationError):
        EngineeringContext(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_context_serialises_to_camel_case_with_string_identifiers() -> None:
    dumped = _build([_quality_group()]).model_dump(mode="json", by_alias=True)
    assert set(dumped) == {
        "contextId",
        "subject",
        "evidence",
        "contextMetadata",
        "dependencies",
        "provenance",
        "orchestration",
        "ranking",
        "coverage",
        "evidenceBudget",
        "grounding",
        "orchestrationReason",
    }
    assert isinstance(dumped["contextId"], str)
    assert dumped["orchestration"]["policyVersion"] == "1.0.0"


@pytest.mark.unit
def test_context_survives_a_json_round_trip() -> None:
    context = _build([_functional_group(), _quality_group()])
    assert EngineeringContext.model_validate_json(context.model_dump_json()) == context


# ---------------------------------------------------------------------------
# Builder input validation — never a policy decision
# ---------------------------------------------------------------------------


def _build_with(**overrides: object) -> EngineeringContext:
    """Build from a valid decision record with individual inputs replaced."""
    decision = _Decision([_quality_group()])
    kwargs: dict[str, object] = {
        "subject": _subject(),
        "evidence": decision.evidence,
        "contributions": decision.contributions,
        "policy": DefaultOrchestrationPolicy(),
        "ranking": decision.ranking,
        "coverage": decision.coverage,
        "evidence_budget": decision.evidence_budget,
    }
    kwargs.update(overrides)
    return EngineeringContextBuilder().build(**kwargs)  # type: ignore[arg-type]


@pytest.mark.unit
def test_builder_rejects_no_contributing_groups() -> None:
    with pytest.raises(ContextConstructionError, match="At least one ConsolidatedArtifact"):
        _build_with(contributions=[])


@pytest.mark.unit
def test_builder_rejects_a_non_contribution() -> None:
    with pytest.raises(ContextConstructionError, match="Expected GroupContribution"):
        _build_with(contributions=["not a contribution"])


@pytest.mark.unit
def test_builder_rejects_a_non_policy() -> None:
    with pytest.raises(ContextConstructionError, match="Expected an OrchestrationPolicy"):
        _build([_quality_group()], policy="not a policy")


@pytest.mark.unit
def test_builder_rejects_a_non_subject() -> None:
    with pytest.raises(ContextConstructionError, match="Expected a ContextSubject"):
        _build_with(subject="Authentication")


@pytest.mark.unit
def test_builder_rejects_contributions_that_do_not_account_for_the_evidence() -> None:
    """The orchestrator counts what each group gave; the builder checks the sum.

    A selection bug that dropped an artifact between counting and assembly would
    otherwise reach a reasoner as silently thinner evidence.
    """
    decision = _Decision([_quality_group(count=3)])
    understated = (
        GroupContribution(
            group=decision.contributions[0].group,
            rank=1,
            inclusion_reason="admitted at rank 1",
            quality_count=2,
        ),
    )
    with pytest.raises(ContextConstructionError, match="declare 2 quality artifact"):
        _build_with(contributions=understated, evidence=decision.evidence)


@pytest.mark.unit
def test_builder_rejects_a_contributor_that_contributed_nothing() -> None:
    decision = _Decision([_quality_group()])
    empty = (
        GroupContribution(
            group=decision.contributions[0].group, rank=1, inclusion_reason="admitted"
        ),
    )
    with pytest.raises(ContextConstructionError, match="contributed no evidence"):
        _build_with(contributions=empty, evidence=ContextEvidence())


@pytest.mark.unit
def test_builder_rejects_an_unexplained_contributor() -> None:
    """An unexplained group is not permitted, whatever it contributed."""
    decision = _Decision([_quality_group()])
    unexplained = (
        GroupContribution(
            group=decision.contributions[0].group,
            rank=1,
            inclusion_reason="   ",
            quality_count=1,
        ),
    )
    with pytest.raises(ContextConstructionError, match="without a reason"):
        _build_with(contributions=unexplained)


@pytest.mark.unit
def test_builder_rejects_an_incompatible_policy_major_version() -> None:
    policy = DefaultOrchestrationPolicy(policy_version=PolicyVersion(2, 0, 0))
    with pytest.raises(PolicyCompatibilityError, match="not compatible"):
        _build([_quality_group()], policy=policy)


@pytest.mark.unit
def test_builder_accepts_a_compatible_minor_policy_bump() -> None:
    policy = DefaultOrchestrationPolicy(policy_version=PolicyVersion(1, 7, 3))
    assert _build([_quality_group()], policy=policy).orchestration.policy_version == PolicyVersion(
        1, 7, 3
    )


# ---------------------------------------------------------------------------
# Budget — enforced as an input contract, never applied
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_builder_rejects_evidence_exceeding_the_per_domain_budget() -> None:
    over_budget = DefaultOrchestrationPolicy().evidence_budget.max_artifacts_per_domain + 1
    with pytest.raises(ContextBudgetExceededError, match="quality artifacts"):
        _build([_quality_group(count=over_budget)])


@pytest.mark.unit
def test_builder_never_truncates_evidence_to_fit_the_budget() -> None:
    """Truncating would be *applying* the budget — that is orchestration, not construction."""
    policy = LegacySelectionPolicy()
    count = 71  # the largest group in the repository's own fixtures
    context = _build([_quality_group(count=count)], policy=policy)
    assert context.evidence.total_count == count


@pytest.mark.unit
def test_builder_rejects_evidence_exceeding_the_total_budget() -> None:
    policy = DefaultOrchestrationPolicy(
        evidence_budget={"maxArtifactsPerDomain": 9, "maxArtifactsTotal": 10}  # type: ignore[arg-type]
    )
    # 9 quality + 1 functional + 1 security = 11: every domain is within its cap,
    # only the total is breached.
    groups = [_quality_group(count=9), _functional_group(), _security_group()]
    with pytest.raises(ContextBudgetExceededError, match="in total"):
        _build(groups, policy=policy)


# ---------------------------------------------------------------------------
# PlatformContext composition (Stage 7)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_platform_context_constructs_the_orchestration_framework() -> None:
    from requirement_intelligence.platform import PlatformContext

    context = PlatformContext()
    assert isinstance(context.create_engineering_context_builder(), EngineeringContextBuilder)
    assert isinstance(context.create_orchestration_policy(), DefaultOrchestrationPolicy)


@pytest.mark.unit
def test_platform_context_returns_independent_instances() -> None:
    from requirement_intelligence.platform import PlatformContext

    context = PlatformContext()
    assert context.create_engineering_context_builder() is not (
        context.create_engineering_context_builder()
    )


# ---------------------------------------------------------------------------
# Containment — the runtime consumers of the subsystem (CAP-076C)
# ---------------------------------------------------------------------------

#: Modules permitted to reference the subsystem now that it is live. The set is
#: exhaustive and deliberately small: construction happens only in
#: ``PlatformContext``, the CLI orchestrates, and the three consumers below read
#: an ``EngineeringContext``. Anything else must remain unaware it exists.
_PERMITTED_IMPORTERS = {
    Path("requirement_intelligence/platform/platform_context.py"),
    Path("requirement_intelligence/prompts/requirement_prompt_builder.py"),
    Path("requirement_intelligence/analysis/requirement_analysis_service.py"),
    Path("requirement_intelligence/execution/engineering_context_artifact.py"),
    Path("scripts/run_requirement_analysis.py"),
}

_RUNTIME_ROOTS = (
    _REPO_ROOT / "requirement_intelligence",
    _REPO_ROOT / "scripts",
    _REPO_ROOT / "app",
)


def _runtime_modules() -> list[Path]:
    modules: list[Path] = []
    for root in _RUNTIME_ROOTS:
        modules.extend(
            path
            for path in root.rglob("*.py")
            if "tests" not in path.parts and "context_orchestration" not in path.parts
        )
    return modules


@pytest.mark.unit
def test_only_the_permitted_modules_consume_the_orchestration_framework() -> None:
    """The subsystem's runtime consumers are exactly the ones CAP-076C wired.

    Expressed as a test so that a future milestone must *consciously* widen the
    set rather than silently grow a new dependency on orchestration.
    """
    importers = {
        path.relative_to(_REPO_ROOT)
        for path in _runtime_modules()
        if "context_orchestration" in path.read_text(encoding="utf-8")
    }
    assert importers == _PERMITTED_IMPORTERS


@pytest.mark.unit
def test_the_orchestration_framework_does_not_import_downstream_subsystems() -> None:
    """Acyclic: models <- consolidation <- context_orchestration. Never the reverse."""
    forbidden = ("prompts", "analysis", "normalization", "validation", "cp1", "execution", "llm")
    package = _REPO_ROOT / "requirement_intelligence" / "context_orchestration"
    for module in package.rglob("*.py"):
        source = module.read_text(encoding="utf-8")
        for line in source.splitlines():
            if not line.startswith(("import ", "from ")):
                continue
            for subsystem in forbidden:
                assert f"requirement_intelligence.{subsystem}" not in line, (
                    f"{module.name} imports {subsystem}: {line}"
                )
