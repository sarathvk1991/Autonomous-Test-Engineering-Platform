"""Architecture-only tests for the CAP-085B.1 OrganizationalMemoryResult freeze.

These assert the *runtime contract* invariants — not behaviour (behaviour lives in
``test_organizational_memory_deterministic_engine.py``). They cover the independent
runtime-contract version, serialization round-trip / immutability / equality, the
explainability invariant (the result is self-contained), and the frozen runtime
boundary (ADR-0027 §D18), mirroring ``test_knowledge_graph_result_freeze.py``
(ADR-0023 §D11), ``test_continuous_improvement_result_freeze.py`` (ADR-0022 §D10),
``test_recommendation_result_freeze.py`` (ADR-0019 §D9),
``test_enhancement_result_freeze.py`` (ADR-0018 §D8), and
``test_quality_assessment_result_freeze.py`` (ADR-0017 §D27).

No runtime behaviour changes with this milestone: these tests exercise the engine
exactly as ``test_organizational_memory_deterministic_engine.py`` already does, only
through the lens of contract certification rather than dispatch behaviour. Unlike
its CAP-085A/CAP-085A.1 predecessor, ``_result()`` now builds through
``DeterministicOrganizationalMemoryEngine`` rather than hand-constructing the model,
mirroring how CAP-084B.1 updated Knowledge Graph's own freeze test once its engine
existed. Organizational Memory has no serializer and no ``HistoricalDatasetProvider``
analogue yet (it consumes two already-completed Layer 2 results directly, never a
resolved reference), so this file omits the serializer-boundary and provider-leak
tests KG's own post-CAP-084C freeze file carries.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from requirement_intelligence.continuous_improvement.identity import (
    ContinuousImprovementFrameworkVersion,
    ContinuousImprovementResultId,
    ImprovementFindingId,
    ImprovementPolicyId,
    ImprovementPolicyVersion,
)
from requirement_intelligence.continuous_improvement.models import ContinuousImprovementResult
from requirement_intelligence.continuous_improvement.models import (
    HistoricalDatasetReference as CIHistoricalDatasetReference,
)
from requirement_intelligence.continuous_improvement.models.enums import (
    ImprovementFindingCategory,
    ImprovementSeverity,
    ImprovementSourceLayer,
)
from requirement_intelligence.continuous_improvement.models.finding import ImprovementFinding
from requirement_intelligence.continuous_improvement.models.summary import (
    ImprovementMetrics,
    ImprovementSummary,
)
from requirement_intelligence.knowledge_graph.engine import DeterministicKnowledgeGraphEngine
from requirement_intelligence.knowledge_graph.models import (
    HistoricalDatasetReference as KGHistoricalDatasetReference,
)
from requirement_intelligence.knowledge_graph.models import KnowledgeGraphResult
from requirement_intelligence.knowledge_graph.policy import default_knowledge_graph_policy
from requirement_intelligence.knowledge_graph.rules import default_knowledge_graph_rule_catalog
from requirement_intelligence.organizational_memory.engine import (
    DeterministicOrganizationalMemoryEngine,
)
from requirement_intelligence.organizational_memory.identity import (
    BestPracticeId,
    BestPracticeVersion,
    ExperienceId,
    KnowledgeLifecycleId,
    KnowledgeLifecycleVersion,
    KnowledgePromotionId,
    LessonId,
    LessonVersion,
    OrganizationalMemoryFrameworkVersion,
    OrganizationalMemoryPolicyVersion,
    OrganizationalMemoryResultVersion,
    PromotionRuleCatalogVersion,
    PromotionRuleVersion,
)
from requirement_intelligence.organizational_memory.models import (
    ORGANIZATIONAL_MEMORY_RESULT_VERSION,
    BestPractice,
    Experience,
    KnowledgeLifecycle,
    KnowledgeLifecycleState,
    KnowledgePromotion,
    Lesson,
    OrganizationalMemoryConfidence,
    OrganizationalMemoryMetrics,
    OrganizationalMemoryResult,
    OrganizationalMemorySummary,
)
from requirement_intelligence.organizational_memory.policy import (
    default_organizational_memory_policy,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ORGANIZATIONAL_MEMORY_PKG = _REPO_ROOT / "requirement_intelligence" / "organizational_memory"
_NOW = datetime(2026, 7, 16, tzinfo=UTC)
_FIXED_CLOCK = lambda: _NOW  # noqa: E731


def _version_field_names(model: type) -> set[str]:
    return {name for name in model.model_fields if "version" in name.lower()}


def _ci_reference(**overrides: object) -> CIHistoricalDatasetReference:
    defaults: dict[str, object] = dict(
        dataset_id="ds-om-freeze",
        dataset_version="1.0.0",
        first_execution_id="ex-1",
        last_execution_id="ex-3",
        execution_count=3,
        history_window=25,
        generated_at=_NOW,
    )
    defaults.update(overrides)
    return CIHistoricalDatasetReference(**defaults)  # type: ignore[arg-type]


def _kg_reference(**overrides: object) -> KGHistoricalDatasetReference:
    defaults: dict[str, object] = dict(
        dataset_id="ds-om-freeze",
        dataset_version="1.0.0",
        first_execution_id="ex-1",
        last_execution_id="ex-1",
        execution_count=1,
        history_window=1,
        generated_at=_NOW,
    )
    defaults.update(overrides)
    return KGHistoricalDatasetReference(**defaults)  # type: ignore[arg-type]


def _kg_result() -> KnowledgeGraphResult:
    engine = DeterministicKnowledgeGraphEngine(
        policy=default_knowledge_graph_policy(),
        rule_catalog=default_knowledge_graph_rule_catalog(),
        clock=_FIXED_CLOCK,
    )
    return engine.build(_kg_reference())


def _repeated_ci_result(
    count: int = 6, dataset_id: str = "ds-om-freeze-repeat"
) -> ContinuousImprovementResult:
    """A ContinuousImprovementResult carrying *count* identical-message findings.

    Guarantees at least one lesson (and its promotion and lifecycle records) so
    the explainability tests below exercise real, non-empty content rather than
    only the validators' negative paths — mirroring how the deterministic engine's
    own tests force the promotion pathway with an identical fixture.
    """
    findings = tuple(
        ImprovementFinding(
            finding_id=ImprovementFindingId.for_ordinal(dataset_id, i),
            category=ImprovementFindingCategory.RECURRING_VALIDATION_FAILURE,
            source=ImprovementSourceLayer.VALIDATION,
            severity=ImprovementSeverity.WARNING,
            occurrence_count=3,
            contributing_execution_ids=(
                f"{dataset_id}-{i}-a",
                f"{dataset_id}-{i}-b",
                f"{dataset_id}-{i}-c",
            ),
            message="Same recurring validation issue",
        )
        for i in range(count)
    )
    return ContinuousImprovementResult(
        result_id=ContinuousImprovementResultId.for_dataset(dataset_id),
        historical_dataset=_ci_reference(dataset_id=dataset_id),
        findings=findings,
        trends=(),
        opportunities=(),
        summary=ImprovementSummary(
            policy_id=ImprovementPolicyId("p"),
            policy_version=ImprovementPolicyVersion(1, 0, 0),
            total_findings=count,
            total_trends=0,
            total_opportunities=0,
            headline="repeated",
        ),
        metrics=ImprovementMetrics(
            finding_density=1.0, trend_stability_ratio=0.0, opportunity_rate=0.0
        ),
        policy_id=ImprovementPolicyId("p"),
        policy_version=ImprovementPolicyVersion(1, 0, 0),
        framework_version=ContinuousImprovementFrameworkVersion(1, 0, 0),
        started_at=_NOW,
        completed_at=_NOW,
    )


def _result() -> OrganizationalMemoryResult:
    engine = DeterministicOrganizationalMemoryEngine(
        policy=default_organizational_memory_policy(),
        clock=_FIXED_CLOCK,
    )
    return engine.build(_repeated_ci_result(), _kg_result())


@pytest.mark.unit
class TestRuntimeContractVersion:
    def test_result_version_defaults_to_the_contract_version(self) -> None:
        assert _result().result_version == ORGANIZATIONAL_MEMORY_RESULT_VERSION

    def test_result_version_is_its_own_type(self) -> None:
        assert isinstance(ORGANIZATIONAL_MEMORY_RESULT_VERSION, OrganizationalMemoryResultVersion)

    def test_runtime_version_is_independent_of_every_other_axis(self) -> None:
        """The runtime-contract version is a distinct type from every other axis."""
        other_axes = (
            OrganizationalMemoryFrameworkVersion,
            OrganizationalMemoryPolicyVersion,
            LessonVersion,
            BestPracticeVersion,
            KnowledgeLifecycleVersion,
            PromotionRuleVersion,
            PromotionRuleCatalogVersion,
        )
        for axis in other_axes:
            assert not issubclass(OrganizationalMemoryResultVersion, axis)
            assert not issubclass(axis, OrganizationalMemoryResultVersion)
        # Eight distinct types in total (the seven above plus the result version).
        assert len({OrganizationalMemoryResultVersion, *other_axes}) == 8

    def test_result_and_policy_versions_are_carried_independently(self) -> None:
        result = _result()
        policy = default_organizational_memory_policy()
        assert result.result_version == ORGANIZATIONAL_MEMORY_RESULT_VERSION
        assert result.policy_version == policy.policy_version

    def test_experience_has_no_dedicated_version_field(self) -> None:
        """Experience carries no version-typed field (by design, not a gap)."""
        assert _version_field_names(Experience) == set()

    def test_promotion_has_no_dedicated_schema_version_field(self) -> None:
        """KnowledgePromotion carries only the governing policy_version (a policy
        reference, not a schema-version axis of its own)."""
        assert _version_field_names(KnowledgePromotion) == {"policy_version"}

    def test_summary_carries_only_the_governing_policy_version(self) -> None:
        """OrganizationalMemorySummary's only version field is the policy it was
        governed by."""
        assert _version_field_names(OrganizationalMemorySummary) == {"policy_version"}

    def test_metrics_has_no_dedicated_version_field(self) -> None:
        """OrganizationalMemoryMetrics carries no version-typed field (by design,
        not a gap)."""
        assert _version_field_names(OrganizationalMemoryMetrics) == set()


@pytest.mark.unit
class TestSelfContainedContract:
    def test_round_trips_from_serialization_alone(self) -> None:
        result = _result()
        dumped = result.model_dump(mode="json", by_alias=True)
        assert OrganizationalMemoryResult.model_validate(dumped) == result

    def test_deterministic_equality_with_a_fixed_clock(self) -> None:
        assert _result() == _result()

    def test_is_immutable(self) -> None:
        result = _result()
        with pytest.raises(ValidationError):
            result.result_id = "other"  # type: ignore[misc]

    def test_rejects_completed_before_started(self) -> None:
        result = _result()
        with pytest.raises(ValidationError):
            OrganizationalMemoryResult(
                **{**result.model_dump(), "started_at": _NOW.replace(hour=23)}
            )

    def test_rejects_duplicate_experience_ids(self) -> None:
        result = _result()
        assert result.experiences, "expected the repeated CI dataset to yield experiences"
        with pytest.raises(ValidationError):
            OrganizationalMemoryResult(
                **{
                    **result.model_dump(),
                    "experiences": (result.experiences[0], result.experiences[0]),
                }
            )

    def test_rejects_lesson_referencing_unknown_experience(self) -> None:
        result = _result()
        bogus_lesson = Lesson(
            lesson_id=LessonId.for_ordinal("om-freeze", 999),
            source_experience_ids=(ExperienceId.for_source("continuous_improvement", "ghost"),),
            message="orphaned",
            confidence=OrganizationalMemoryConfidence.LOW,
        )
        with pytest.raises(ValidationError):
            OrganizationalMemoryResult(
                **{**result.model_dump(), "lessons": (*result.lessons, bogus_lesson)}
            )

    def test_rejects_best_practice_referencing_unknown_lesson(self) -> None:
        result = _result()
        bogus_bp = BestPractice(
            best_practice_id=BestPracticeId.for_ordinal("om-freeze", 999),
            source_lesson_ids=(LessonId.for_ordinal("om-freeze", 999),),
            title="orphaned",
            description="orphaned",
            confidence=OrganizationalMemoryConfidence.LOW,
        )
        with pytest.raises(ValidationError):
            OrganizationalMemoryResult(
                **{**result.model_dump(), "best_practices": (*result.best_practices, bogus_bp)}
            )

    def test_rejects_promotion_referencing_unknown_source(self) -> None:
        result = _result()
        bogus_promotion = KnowledgePromotion(
            promotion_id=KnowledgePromotionId.for_ordinal("om-freeze", 999),
            source_ids=("ghost-id",),
            target_ids=(str(result.experiences[0].experience_id),),
            rationale="bogus",
            promoted_at=_NOW,
            confidence=OrganizationalMemoryConfidence.LOW,
            policy_version=OrganizationalMemoryPolicyVersion(1, 0, 0),
        )
        with pytest.raises(ValidationError):
            OrganizationalMemoryResult(
                **{**result.model_dump(), "promotions": (*result.promotions, bogus_promotion)}
            )

    def test_rejects_lifecycle_referencing_unknown_subject(self) -> None:
        result = _result()
        bogus_lifecycle = KnowledgeLifecycle(
            lifecycle_id=KnowledgeLifecycleId.for_ordinal("om-freeze", 999),
            subject_id="ghost-id",
            state=KnowledgeLifecycleState.ACTIVE,
            state_reason="bogus",
        )
        with pytest.raises(ValidationError):
            OrganizationalMemoryResult(
                **{**result.model_dump(), "lifecycles": (*result.lifecycles, bogus_lifecycle)}
            )

    def test_explainable_from_the_content_fields_alone(self) -> None:
        """The result carries every field an explanation needs — nothing external."""
        fields = set(OrganizationalMemoryResult.model_fields)
        assert {
            "experiences",
            "lessons",
            "best_practices",
            "promotions",
            "lifecycles",
            "summary",
            "metrics",
            "continuous_improvement_result_id",
            "knowledge_graph_result_id",
            "policy_id",
            "policy_version",
        } <= fields

    def test_experiences_are_explainable_from_source_layer_and_description(self) -> None:
        result = _result()
        assert result.experiences, "expected the repeated CI dataset to yield experiences"
        for experience in result.experiences:
            assert experience.source_layer
            assert experience.source_reference_id
            assert experience.description

    def test_lessons_are_explainable_from_source_experience_ids_and_message(self) -> None:
        result = _result()
        assert result.lessons, "expected the promotion pathway to yield at least one lesson"
        for lesson in result.lessons:
            assert lesson.source_experience_ids
            assert lesson.message
            assert lesson.confidence

    def test_best_practices_are_explainable_from_source_lesson_ids_and_description(self) -> None:
        result = _result()
        for best_practice in result.best_practices:
            assert best_practice.source_lesson_ids
            assert best_practice.title
            assert best_practice.description

    def test_promotions_are_explainable_from_source_and_target_ids(self) -> None:
        result = _result()
        assert result.promotions, "expected the promotion pathway to yield at least one promotion"
        for promotion in result.promotions:
            assert promotion.source_ids
            assert promotion.target_ids
            assert promotion.rationale

    def test_lifecycles_are_explainable_from_subject_and_state(self) -> None:
        result = _result()
        assert result.lifecycles, "expected experiences/lessons to yield lifecycle records"
        for lifecycle in result.lifecycles:
            assert lifecycle.subject_id
            assert lifecycle.state

    def test_carries_no_report_renderer_or_serialization_fields(self) -> None:
        """It is not a report, Markdown, a renderer, or a serializer (Stage 1 'is not' list)."""
        fields = set(OrganizationalMemoryResult.model_fields)
        forbidden = {"report", "markdown", "html", "rendered_report", "json_text", "serialized"}
        assert not (forbidden & fields)

    def test_carries_no_execution_package_manifest_or_cli_fields(self) -> None:
        """It is not an Execution Package, manifest, or CLI object (Stage 1 'is not' list)."""
        fields = set(OrganizationalMemoryResult.model_fields)
        forbidden = {"manifest", "generated_artifacts", "checksums", "cli_args"}
        assert not (forbidden & fields)

    def test_never_embeds_the_full_consumed_peer_results(self) -> None:
        """Reference, never copy (Recommendation 2 of ADR-0027) — only the two ids."""
        fields = set(OrganizationalMemoryResult.model_fields)
        forbidden = {"continuous_improvement_result", "knowledge_graph_result"}
        assert not (forbidden & fields)


@pytest.mark.unit
class TestRuntimeBoundary:
    def test_result_model_imports_no_execution_package_or_cli(self) -> None:
        source = (_ORGANIZATIONAL_MEMORY_PKG / "models" / "result.py").read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                assert "execution_writer" not in line.lower()
                assert "manifest_builder" not in line.lower()
                assert "scripts" not in line.lower()

    def test_result_model_imports_no_engine_service_or_platform_context(self) -> None:
        """The OrganizationalMemoryResult model imports none of its collaborators."""
        source = (_ORGANIZATIONAL_MEMORY_PKG / "models" / "result.py").read_text(encoding="utf-8")
        forbidden = (
            "DeterministicOrganizationalMemoryEngine",
            "DeterministicOrganizationalMemoryService",
            "OrganizationalMemoryService",
            "PlatformContext",
        )
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                for token in forbidden:
                    assert token not in line, f"result.py imports {token}: {line!r}"

    def test_result_model_imports_no_layer_1_or_peer_implementation(self) -> None:
        source = (_ORGANIZATIONAL_MEMORY_PKG / "models" / "result.py").read_text(encoding="utf-8")
        forbidden = (
            "requirement_intelligence.enhancement",
            "requirement_intelligence.grounding",
            "requirement_intelligence.continuous_improvement.continuous_improvement_service",
            "requirement_intelligence.knowledge_graph.knowledge_graph_service",
        )
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                for token in forbidden:
                    assert token not in line, f"result.py imports {token}: {line!r}"

    def test_no_module_outside_the_package_names_the_engine(self) -> None:
        """The engine is named only inside the organizational_memory package.

        Guards the serialization invariant (§D18) before any Organizational Memory
        renderer exists: nothing outside the subsystem re-runs experience capture,
        clustering, lesson/best-practice generation, promotion, or lifecycle
        recording.
        """
        needle = "DeterministicOrganizationalMemoryEngine"
        permitted: set[Path] = set()
        external: set[Path] = set()
        for path in (_REPO_ROOT / "requirement_intelligence").rglob("*.py"):
            if "tests" in path.parts or path.is_relative_to(_ORGANIZATIONAL_MEMORY_PKG):
                continue
            if needle in path.read_text(encoding="utf-8"):
                external.add(path.relative_to(_REPO_ROOT))
        assert external == permitted

    def test_platform_context_remains_the_sole_composition_root(self) -> None:
        """Only PlatformContext constructs the framework's deterministic service externally."""
        needle = "DeterministicOrganizationalMemoryService"
        permitted = {
            Path("requirement_intelligence/platform/platform_context.py"),
        }
        external: set[Path] = set()
        for path in (_REPO_ROOT / "requirement_intelligence").rglob("*.py"):
            if "tests" in path.parts or path.is_relative_to(_ORGANIZATIONAL_MEMORY_PKG):
                continue
            if needle in path.read_text(encoding="utf-8"):
                external.add(path.relative_to(_REPO_ROOT))
        assert external == permitted


@pytest.mark.unit
class TestNoRuntimeBehaviourChange:
    def test_platform_version_unchanged(self) -> None:
        from requirement_intelligence.platform import platform_metadata

        assert platform_metadata.PLATFORM_VERSION == "1.0.0"

    def test_organizational_memory_framework_version_unchanged_by_this_milestone(self) -> None:
        from requirement_intelligence.organizational_memory.version import (
            ORGANIZATIONAL_MEMORY_FRAMEWORK_VERSION,
        )

        assert str(ORGANIZATIONAL_MEMORY_FRAMEWORK_VERSION) == "1.0.0"

    def test_organizational_memory_result_version_unchanged_by_this_milestone(self) -> None:
        assert str(ORGANIZATIONAL_MEMORY_RESULT_VERSION) == "1.0.0"
