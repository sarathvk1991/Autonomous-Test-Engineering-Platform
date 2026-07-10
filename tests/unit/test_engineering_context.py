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
    ContextBudgetExceededError,
    ContextConstructionError,
    ContextDependencies,
    ContextEvidence,
    ContextMetadata,
    ContextProvenance,
    ContextSubject,
    ContextSubjectBasis,
    DefaultOrchestrationPolicy,
    EngineeringContext,
    EngineeringContextBuilder,
    EngineeringContextId,
    LegacySelectionPolicy,
    OrchestrationMetadata,
    OrchestrationPolicyId,
    PolicyCompatibilityError,
    PolicyVersion,
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


def _build(groups: list[ConsolidatedArtifact], policy: object | None = None) -> EngineeringContext:
    return EngineeringContextBuilder().build(
        subject=_subject(),
        contributing_groups=groups,
        policy=policy or DefaultOrchestrationPolicy(),  # type: ignore[arg-type]
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


def _valid_kwargs() -> dict[str, object]:
    return {
        "context_id": EngineeringContextId("ctx-a-1"),
        "subject": _subject(),
        "evidence": ContextEvidence(
            quality_artifacts=(_artifact(1, SourceCategory.QUALITY, SourceType.SAST),)
        ),
        "context_metadata": ContextMetadata(risk_level=RiskLevel.LOW),
        "dependencies": ContextDependencies(),
        "provenance": ContextProvenance(
            contributing_consolidated_ids=("cons-a",),
            contributing_group_count=1,
            source_artifact_count=1,
        ),
        "orchestration": OrchestrationMetadata(
            policy_id=OrchestrationPolicyId("coverage"),
            policy_version=PolicyVersion(1, 0, 0),
        ),
        "orchestration_reason": "because",
    }


@pytest.mark.unit
def test_context_rejects_empty_evidence() -> None:
    kwargs = _valid_kwargs()
    kwargs["evidence"] = ContextEvidence()
    with pytest.raises(ValidationError, match="at least one evidence artifact"):
        EngineeringContext(**kwargs)  # type: ignore[arg-type]


@pytest.mark.unit
def test_context_rejects_provenance_disagreeing_with_evidence() -> None:
    kwargs = _valid_kwargs()
    kwargs["provenance"] = ContextProvenance(
        contributing_consolidated_ids=("cons-a",),
        contributing_group_count=1,
        source_artifact_count=99,
    )
    with pytest.raises(ValidationError, match="Provenance disagrees with evidence"):
        EngineeringContext(**kwargs)  # type: ignore[arg-type]


@pytest.mark.unit
def test_context_rejects_self_inconsistent_provenance() -> None:
    kwargs = _valid_kwargs()
    kwargs["provenance"] = ContextProvenance(
        contributing_consolidated_ids=("cons-a", "cons-b"),
        contributing_group_count=1,
        source_artifact_count=1,
    )
    with pytest.raises(ValidationError, match="Provenance disagrees with itself"):
        EngineeringContext(**kwargs)  # type: ignore[arg-type]


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


@pytest.mark.unit
def test_builder_rejects_no_contributing_groups() -> None:
    with pytest.raises(ContextConstructionError, match="At least one ConsolidatedArtifact"):
        _build([])


@pytest.mark.unit
def test_builder_rejects_a_non_consolidated_artifact() -> None:
    with pytest.raises(ContextConstructionError, match="Expected ConsolidatedArtifact"):
        _build(["not a group"])  # type: ignore[list-item]


@pytest.mark.unit
def test_builder_rejects_a_non_policy() -> None:
    with pytest.raises(ContextConstructionError, match="Expected an OrchestrationPolicy"):
        _build([_quality_group()], policy="not a policy")


@pytest.mark.unit
def test_builder_rejects_a_non_subject() -> None:
    with pytest.raises(ContextConstructionError, match="Expected a ContextSubject"):
        EngineeringContextBuilder().build(
            subject="Authentication",  # type: ignore[arg-type]
            contributing_groups=[_quality_group()],
            policy=DefaultOrchestrationPolicy(),
        )


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
# Containment — the central CAP-076B claim
# ---------------------------------------------------------------------------

#: Modules permitted to import the subsystem at CAP-076B. Everything else must
#: be unaware it exists. CAP-076C will add the orchestrator and the CLI.
_PERMITTED_IMPORTERS = {
    Path("requirement_intelligence/platform/platform_context.py"),
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
def test_nothing_but_platform_context_consumes_the_orchestration_framework() -> None:
    """EngineeringContext, the builder, and the policy have zero runtime consumers.

    This is the milestone's behavioural guarantee, expressed as a test so that
    CAP-076C must *consciously* update it rather than silently wire the runtime.
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
