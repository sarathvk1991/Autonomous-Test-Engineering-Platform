"""Architecture-only tests for the CAP-086B.1 LearningResult freeze.

These assert the *runtime contract* invariants — not behaviour (behaviour lives
in ``test_learning_deterministic_engine.py``). They cover the independent
runtime-contract version, serialization round-trip / immutability / equality,
the explainability invariant (the result is self-contained), collection
ordering, field/builder ownership, the frozen runtime boundary, Layer 2 output
permanence, and future-engine independence (ADR-0029 §D28), mirroring
``test_organizational_memory_result_freeze.py`` (ADR-0027 §D18),
``test_knowledge_graph_result_freeze.py`` (ADR-0023 §D11),
``test_continuous_improvement_result_freeze.py`` (ADR-0022 §D10),
``test_recommendation_result_freeze.py`` (ADR-0019 §D9), and
``test_enhancement_result_freeze.py`` (ADR-0018 §D8).

No runtime behaviour changes with this milestone: these tests exercise the
engine exactly as ``test_learning_deterministic_engine.py`` already does, only
through the lens of contract certification rather than dispatch behaviour.
Unlike its CAP-086A predecessor, ``_result()`` now builds through
``DeterministicLearningEngine`` rather than hand-constructing the model,
mirroring how CAP-085B.1 updated Organizational Memory's own freeze test once
its engine existed. Learning has no serializer yet, so this file omits any
serializer-boundary test.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from requirement_intelligence.learning.engine import DeterministicLearningEngine
from requirement_intelligence.learning.engine.result_builder import ResultBuilder
from requirement_intelligence.learning.engine.summary_builder import SummaryBuilder
from requirement_intelligence.learning.identity import (
    LearningCandidateId,
    LearningConfidenceId,
    LearningEngineVersion,
    LearningFrameworkVersion,
    LearningId,
    LearningLifecycleId,
    LearningLifecycleVersion,
    LearningPolicyVersion,
    LearningResultVersion,
    LearningRuleCatalogVersion,
    LearningRuleVersion,
    LearningValidationId,
    LearningValidationVersion,
    LearningVersion,
)
from requirement_intelligence.learning.models import (
    Learning,
    LearningCandidate,
    LearningConfidence,
    LearningConfidenceLevel,
    LearningLifecycle,
    LearningMaturity,
    LearningMetrics,
    LearningResult,
    LearningSummary,
    LearningValidation,
    LearningValidationGate,
)
from requirement_intelligence.learning.policy import default_learning_policy
from requirement_intelligence.organizational_memory.identity import (
    BestPracticeId,
    ExperienceId,
    LessonId,
    OrganizationalMemoryFrameworkVersion,
    OrganizationalMemoryId,
    OrganizationalMemoryPolicyId,
    OrganizationalMemoryPolicyVersion,
    OrganizationalMemoryResultId,
)
from requirement_intelligence.organizational_memory.models import (
    BestPractice,
    Experience,
    OrganizationalMemoryConfidence,
    OrganizationalMemoryMetrics,
    OrganizationalMemoryResult,
    OrganizationalMemorySourceLayer,
    OrganizationalMemorySummary,
)
from requirement_intelligence.organizational_memory.models.lesson import Lesson

_REPO_ROOT = Path(__file__).resolve().parents[2]
_LEARNING_PKG = _REPO_ROOT / "requirement_intelligence" / "learning"
_NOW = datetime(2026, 7, 16, tzinfo=UTC)


def _version_field_names(model: type) -> set[str]:
    return {name for name in model.model_fields if "version" in name.lower()}


def _best_practice_bundle(
    seed: str, ordinal: int, description: str
) -> tuple[Experience, Lesson, BestPractice]:
    experience = Experience(
        experience_id=ExperienceId.for_source("knowledge_graph", f"{seed}-kg-{ordinal}"),
        source_layer=OrganizationalMemorySourceLayer.KNOWLEDGE_GRAPH,
        source_reference_id=f"{seed}-kg-{ordinal}",
        description=description,
        confidence=OrganizationalMemoryConfidence.LOW,
    )
    lesson = Lesson(
        lesson_id=LessonId.for_ordinal(seed, ordinal),
        source_experience_ids=(experience.experience_id,),
        message=description,
        confidence=OrganizationalMemoryConfidence.MEDIUM,
    )
    best_practice = BestPractice(
        best_practice_id=BestPracticeId.for_ordinal(seed, ordinal),
        source_lesson_ids=(lesson.lesson_id,),
        title=f"practice {ordinal}",
        description=description,
        confidence=OrganizationalMemoryConfidence.VERIFIED,
    )
    return experience, lesson, best_practice


def _organizational_memory_result(
    descriptions: list[str], *, seed: str = "om-freeze"
) -> OrganizationalMemoryResult:
    bundles = [
        _best_practice_bundle(seed, i, description) for i, description in enumerate(descriptions)
    ]
    experiences = tuple(bundle[0] for bundle in bundles)
    lessons = tuple(bundle[1] for bundle in bundles)
    best_practices = tuple(bundle[2] for bundle in bundles)
    return OrganizationalMemoryResult(
        result_id=OrganizationalMemoryResultId.for_memory(seed),
        memory_id=OrganizationalMemoryId.for_inputs("ci-1", "kg-1"),
        continuous_improvement_result_id="ci-1",
        knowledge_graph_result_id="kg-1",
        experiences=experiences,
        lessons=lessons,
        best_practices=best_practices,
        promotions=(),
        lifecycles=(),
        summary=OrganizationalMemorySummary(
            policy_id=OrganizationalMemoryPolicyId("default-organizational-memory-policy"),
            policy_version=OrganizationalMemoryPolicyVersion(1, 0, 0),
            total_experiences=len(experiences),
            total_lessons=len(lessons),
            total_best_practices=len(best_practices),
            total_promotions=0,
            headline="test fixture",
        ),
        metrics=OrganizationalMemoryMetrics(
            experience_count=len(experiences),
            lesson_count=len(lessons),
            best_practice_count=len(best_practices),
            promotion_count=0,
            active_count=0,
            deprecated_count=0,
            historical_count=0,
            archived_count=0,
        ),
        policy_id=OrganizationalMemoryPolicyId("default-organizational-memory-policy"),
        policy_version=OrganizationalMemoryPolicyVersion(1, 0, 0),
        framework_version=OrganizationalMemoryFrameworkVersion(1, 0, 0),
        started_at=_NOW,
        completed_at=_NOW,
    )


def _result(descriptions: list[str] | None = None, *, seed: str = "om-freeze") -> LearningResult:
    """Build a real ``LearningResult`` through the deterministic engine.

    Six identical descriptions guarantee at least one candidate clears the
    default confidence floor, so the explainability/ordering tests below
    exercise real, non-empty content rather than only negative paths.
    """
    engine = DeterministicLearningEngine(policy=default_learning_policy(), clock=lambda: _NOW)
    om_result = _organizational_memory_result(descriptions or ["shared practice"] * 6, seed=seed)
    return engine.build(om_result)


@pytest.mark.unit
class TestRuntimeContractVersion:
    def test_result_version_is_its_own_type(self) -> None:
        assert isinstance(_result().result_version, LearningResultVersion)

    def test_runtime_version_is_independent_of_every_other_axis(self) -> None:
        other_axes = (
            LearningFrameworkVersion,
            LearningPolicyVersion,
            LearningVersion,
            LearningLifecycleVersion,
            LearningValidationVersion,
            LearningRuleVersion,
            LearningRuleCatalogVersion,
        )
        for axis in other_axes:
            assert not issubclass(LearningResultVersion, axis)
            assert not issubclass(axis, LearningResultVersion)
        assert len({LearningResultVersion, *other_axes}) == 8

    def test_all_nine_version_axes_are_pairwise_distinct(self) -> None:
        """ADR-0029 §D28: nine permanently independent version axes."""
        axes = (
            LearningFrameworkVersion,
            LearningPolicyVersion,
            LearningVersion,
            LearningLifecycleVersion,
            LearningValidationVersion,
            LearningResultVersion,
            LearningRuleVersion,
            LearningRuleCatalogVersion,
            LearningEngineVersion,
        )
        assert len(set(axes)) == 9
        for axis in axes:
            others = [other for other in axes if other is not axis]
            assert not any(issubclass(axis, other) for other in others)

    def test_candidate_has_no_dedicated_version_field(self) -> None:
        assert _version_field_names(LearningCandidate) == set()

    def test_validation_has_no_dedicated_schema_version_field(self) -> None:
        """LearningValidation carries only the governing policy_version (a policy
        reference, not a schema-version axis of its own)."""
        assert _version_field_names(LearningValidation) == {"policy_version"}

    def test_confidence_has_no_dedicated_version_field(self) -> None:
        assert _version_field_names(LearningConfidence) == set()

    def test_summary_carries_only_the_policy_version(self) -> None:
        assert _version_field_names(LearningSummary) == {"policy_version"}

    def test_metrics_has_no_dedicated_version_field(self) -> None:
        assert _version_field_names(LearningMetrics) == set()


@pytest.mark.unit
class TestSelfContainedContract:
    def test_round_trips_from_serialization_alone(self) -> None:
        result = _result()
        dumped = result.model_dump(mode="json", by_alias=True)
        assert LearningResult.model_validate(dumped) == result

    def test_deterministic_equality(self) -> None:
        assert _result() == _result()

    def test_is_immutable(self) -> None:
        result = _result()
        with pytest.raises(ValidationError):
            result.result_id = "other"  # type: ignore[misc]

    def test_rejects_completed_before_started(self) -> None:
        result = _result()
        with pytest.raises(ValidationError):
            LearningResult(**{**result.model_dump(), "started_at": _NOW.replace(hour=23)})

    def test_rejects_duplicate_candidate_ids(self) -> None:
        result = _result()
        duplicated_candidates = (result.candidates[0], result.candidates[0])
        with pytest.raises(ValidationError):
            LearningResult(**{**result.model_dump(), "candidates": duplicated_candidates})

    def test_rejects_validation_referencing_unknown_candidate(self) -> None:
        result = _result()
        bogus_validation = LearningValidation(
            validation_id=LearningValidationId.for_ordinal("lr-freeze", 99),
            candidate_id=LearningCandidateId.for_source("ghost"),
            gates_cleared=(LearningValidationGate.VALIDATED_EVIDENCE,),
            rationale="orphaned",
            validated_at=_NOW,
            confidence=LearningConfidenceLevel.LOW,
            policy_version=LearningPolicyVersion(1, 0, 0),
        )
        with pytest.raises(ValidationError):
            LearningResult(
                **{**result.model_dump(), "validations": (*result.validations, bogus_validation)}
            )

    def test_rejects_learning_referencing_unknown_candidate(self) -> None:
        result = _result()
        bogus_learning = Learning(
            learning_id=LearningId.for_ordinal("lr-freeze", 99),
            candidate_id=LearningCandidateId.for_source("ghost"),
            validation_id=result.validations[0].validation_id,
            message="orphaned",
            maturity=LearningMaturity.OBSERVED,
            confidence=LearningConfidenceLevel.LOW,
        )
        with pytest.raises(ValidationError):
            LearningResult(
                **{**result.model_dump(), "learnings": (*result.learnings, bogus_learning)}
            )

    def test_rejects_learning_referencing_unknown_validation(self) -> None:
        result = _result()
        bogus_learning = Learning(
            learning_id=LearningId.for_ordinal("lr-freeze", 99),
            candidate_id=result.candidates[0].candidate_id,
            validation_id=LearningValidationId.for_ordinal("lr-freeze", 99),
            message="orphaned",
            maturity=LearningMaturity.OBSERVED,
            confidence=LearningConfidenceLevel.LOW,
        )
        with pytest.raises(ValidationError):
            LearningResult(
                **{**result.model_dump(), "learnings": (*result.learnings, bogus_learning)}
            )

    def test_rejects_confidence_referencing_unknown_subject(self) -> None:
        result = _result()
        bogus_confidence = LearningConfidence(
            confidence_id=LearningConfidenceId.for_ordinal("lr-freeze", 99),
            subject_id="ghost-id",
            level=LearningConfidenceLevel.LOW,
            evidence_count=0,
            rationale="bogus",
            recorded_at=_NOW,
        )
        with pytest.raises(ValidationError):
            LearningResult(
                **{**result.model_dump(), "confidences": (*result.confidences, bogus_confidence)}
            )

    def test_rejects_lifecycle_referencing_unknown_subject(self) -> None:
        result = _result()
        bogus_lifecycle = LearningLifecycle(
            lifecycle_id=LearningLifecycleId.for_ordinal("lr-freeze", 99),
            subject_id="ghost-id",
            maturity=LearningMaturity.OBSERVED,
            maturity_reason="bogus",
        )
        with pytest.raises(ValidationError):
            LearningResult(
                **{**result.model_dump(), "lifecycles": (*result.lifecycles, bogus_lifecycle)}
            )

    def test_explainable_from_the_content_fields_alone(self) -> None:
        fields = set(LearningResult.model_fields)
        assert {
            "candidates",
            "learnings",
            "validations",
            "confidences",
            "lifecycles",
            "summary",
            "metrics",
            "organizational_memory_result_id",
            "policy_id",
            "policy_version",
        } <= fields

    def test_carries_no_report_renderer_or_serialization_fields(self) -> None:
        fields = set(LearningResult.model_fields)
        forbidden = {"report", "markdown", "html", "rendered_report", "json_text", "serialized"}
        assert not (forbidden & fields)

    def test_carries_no_execution_package_manifest_or_cli_fields(self) -> None:
        fields = set(LearningResult.model_fields)
        forbidden = {"manifest", "generated_artifacts", "checksums", "cli_args"}
        assert not (forbidden & fields)

    def test_never_embeds_the_full_consumed_result(self) -> None:
        """Reference, never copy — only the one id."""
        fields = set(LearningResult.model_fields)
        assert "organizational_memory_result" not in fields


@pytest.mark.unit
class TestRuntimeSurfaceCompleteness:
    """ADR-0029 §D28: LearningResult already carries everything a downstream
    projection would need — no additional field is required to explain it."""

    def test_result_carries_every_governed_collection(self) -> None:
        assert set(LearningResult.model_fields) == {
            "result_id",
            "organizational_memory_result_id",
            "candidates",
            "learnings",
            "validations",
            "confidences",
            "lifecycles",
            "summary",
            "metrics",
            "policy_id",
            "policy_version",
            "framework_version",
            "result_version",
            "started_at",
            "completed_at",
        }

    def test_summary_shape_is_frozen(self) -> None:
        assert set(LearningSummary.model_fields) == {
            "policy_id",
            "policy_version",
            "total_candidates",
            "total_learnings",
            "total_validations",
            "headline",
        }

    def test_metrics_shape_is_frozen(self) -> None:
        assert set(LearningMetrics.model_fields) == {
            "candidate_count",
            "learning_count",
            "validation_count",
            "observed_count",
            "validated_count",
            "trusted_count",
            "institutional_count",
            "standard_count",
            "retired_count",
        }

    def test_candidate_shape_is_frozen(self) -> None:
        assert set(LearningCandidate.model_fields) == {
            "candidate_id",
            "source_best_practice_ids",
            "proposed_change",
            "confidence",
        }

    def test_validation_shape_is_frozen(self) -> None:
        assert set(LearningValidation.model_fields) == {
            "validation_id",
            "candidate_id",
            "gates_cleared",
            "rationale",
            "validated_at",
            "confidence",
            "policy_version",
        }

    def test_confidence_shape_is_frozen(self) -> None:
        assert set(LearningConfidence.model_fields) == {
            "confidence_id",
            "subject_id",
            "level",
            "evidence_count",
            "rationale",
            "recorded_at",
            "supersedes_confidence_id",
        }

    def test_learning_shape_is_frozen(self) -> None:
        assert set(Learning.model_fields) == {
            "learning_id",
            "candidate_id",
            "validation_id",
            "message",
            "maturity",
            "confidence",
        }

    def test_lifecycle_shape_is_frozen(self) -> None:
        assert set(LearningLifecycle.model_fields) == {
            "lifecycle_id",
            "subject_id",
            "maturity",
            "maturity_reason",
        }


@pytest.mark.unit
class TestCollectionOrdering:
    """ADR-0029 §D28: runtime collections are deterministically ordered."""

    def test_candidate_ordering_is_deterministic_across_builds(self) -> None:
        assert _result().candidates == _result().candidates

    def test_learning_ordering_is_deterministic_across_builds(self) -> None:
        assert _result().learnings == _result().learnings

    def test_lifecycle_ordering_is_deterministic_across_builds(self) -> None:
        assert _result().lifecycles == _result().lifecycles

    def test_serialized_collection_order_is_stable(self) -> None:
        result = _result()
        first = result.model_dump(mode="json", by_alias=True)
        second = _result().model_dump(mode="json", by_alias=True)
        assert [c["candidateId"] for c in first["candidates"]] == [
            c["candidateId"] for c in second["candidates"]
        ]


@pytest.mark.unit
class TestBuilderOwnership:
    """ADR-0029 §D28, Recommendation 39: sole-constructor ownership is
    permanently frozen for every runtime record."""

    def test_result_builder_is_the_only_learning_result_constructor(self) -> None:
        engine_dir = _LEARNING_PKG / "engine"
        offenders = [
            path.name
            for path in engine_dir.rglob("*.py")
            if path.name not in ("result_builder.py", "__init__.py")
            and "LearningResult(" in path.read_text(encoding="utf-8")
        ]
        assert offenders == []

    def test_summary_builder_owns_summary_except_the_documented_empty_result_shortcut(
        self,
    ) -> None:
        engine_dir = _LEARNING_PKG / "engine"
        offenders = [
            path.name
            for path in engine_dir.rglob("*.py")
            if path.name not in ("summary_builder.py", "deterministic_engine.py", "__init__.py")
            and "LearningSummary(" in path.read_text(encoding="utf-8")
        ]
        assert offenders == []

    def test_metrics_builder_owns_metrics_except_the_documented_empty_result_shortcut(
        self,
    ) -> None:
        engine_dir = _LEARNING_PKG / "engine"
        offenders = [
            path.name
            for path in engine_dir.rglob("*.py")
            if path.name not in ("metrics_builder.py", "deterministic_engine.py", "__init__.py")
            and "LearningMetrics(" in path.read_text(encoding="utf-8")
        ]
        assert offenders == []

    def test_result_builder_produces_the_same_shape_as_a_direct_call(self) -> None:
        policy = default_learning_policy()
        summary = SummaryBuilder().build(policy.policy_id, policy.policy_version, (), (), ())
        metrics = LearningMetrics(
            candidate_count=0,
            learning_count=0,
            validation_count=0,
            observed_count=0,
            validated_count=0,
            trusted_count=0,
            institutional_count=0,
            standard_count=0,
            retired_count=0,
        )
        result = ResultBuilder().build(
            organizational_memory_result_id="omr-direct",
            candidates=(),
            learnings=(),
            validations=(),
            confidences=(),
            lifecycles=(),
            summary=summary,
            metrics=metrics,
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
            framework_version=LearningFrameworkVersion(1, 0, 0),
            started_at=_NOW,
            completed_at=_NOW,
        )
        assert isinstance(result, LearningResult)
        assert set(type(result).model_fields) == set(LearningResult.model_fields)


@pytest.mark.unit
class TestLayer2OutputPermanence:
    """ADR-0029 §D28, Recommendation 37: LearningResult is the sole Layer 2 →
    Layer 3 hand-off object."""

    def test_learning_result_is_the_only_learning_runtime_contract_class(self) -> None:
        """No engine-specific or implementation-specific alternative runtime
        contract exists anywhere in the learning package (Recommendation 36)."""
        forbidden_class_names = (
            "MLLearningResult",
            "LLMLearningResult",
            "GraphLearningResult",
            "AgentLearningResult",
            "NeuralLearningResult",
            "DeterministicLearningResult",
        )
        for path in _LEARNING_PKG.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            for name in forbidden_class_names:
                assert f"class {name}" not in source, f"{path.name} defines {name}"

    def test_no_field_on_any_runtime_model_names_an_engine_family(self) -> None:
        """Recommendation 35: no runtime field may reference implementation
        technology (deterministic, ML, LLM, GraphRAG, RL, neuro-symbolic)."""
        engine_tokens = ("deterministic", "_ml_", "_llm_", "graphrag", "neuro_symbolic")
        models = (
            LearningResult,
            LearningSummary,
            LearningMetrics,
            LearningCandidate,
            LearningValidation,
            LearningConfidence,
            Learning,
            LearningLifecycle,
        )
        for model in models:
            for field_name in model.model_fields:
                lowered = field_name.lower()
                assert not any(token in lowered for token in engine_tokens), (
                    f"{model.__name__}.{field_name} names an engine family"
                )

    def test_result_references_organizational_memory_result_by_id_only(self) -> None:
        result = _result()
        assert isinstance(result.organizational_memory_result_id, str)


@pytest.mark.unit
class TestRuntimeBoundary:
    def test_result_model_imports_no_execution_package_or_cli(self) -> None:
        source = (_LEARNING_PKG / "models" / "result.py").read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                assert "execution_writer" not in line.lower()
                assert "manifest_builder" not in line.lower()
                assert "scripts" not in line.lower()

    def test_result_model_imports_no_service_or_platform_context(self) -> None:
        source = (_LEARNING_PKG / "models" / "result.py").read_text(encoding="utf-8")
        forbidden = ("LearningService", "DeterministicLearningService", "PlatformContext")
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                for token in forbidden:
                    assert token not in line, f"result.py imports {token}: {line!r}"

    def test_result_model_imports_no_layer_1_or_peer_implementation(self) -> None:
        source = (_LEARNING_PKG / "models" / "result.py").read_text(encoding="utf-8")
        forbidden = (
            "requirement_intelligence.enhancement",
            "requirement_intelligence.grounding",
            "requirement_intelligence.organizational_memory.organizational_memory_service",
            "requirement_intelligence.continuous_improvement",
            "requirement_intelligence.knowledge_graph",
        )
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                for token in forbidden:
                    assert token not in line, f"result.py imports {token}: {line!r}"

    def test_no_model_module_imports_the_engine_package(self) -> None:
        """Runtime models must stay engine-independent: the engine imports the
        models, never the reverse."""
        models_dir = _LEARNING_PKG / "models"
        for path in models_dir.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            for line in source.splitlines():
                if line.strip().startswith(("import ", "from ")):
                    assert "learning.engine" not in line, (
                        f"{path.name} imports the engine: {line!r}"
                    )


@pytest.mark.unit
class TestNoRuntimeBehaviourChange:
    def test_platform_version_unchanged(self) -> None:
        from requirement_intelligence.platform import platform_metadata

        assert platform_metadata.PLATFORM_VERSION == "1.0.0"

    def test_learning_framework_version_is_the_cap_086a_foundation(self) -> None:
        from requirement_intelligence.learning.version import LEARNING_FRAMEWORK_VERSION

        assert str(LEARNING_FRAMEWORK_VERSION) == "1.0.0"

    def test_learning_result_version_is_the_cap_086a_foundation(self) -> None:
        from requirement_intelligence.learning.models.result import LEARNING_RESULT_VERSION

        assert str(LEARNING_RESULT_VERSION) == "1.0.0"

    def test_platform_context_still_registers_the_same_deterministic_service(self) -> None:
        from requirement_intelligence.learning.learning_service import DeterministicLearningService
        from requirement_intelligence.platform.platform_context import PlatformContext

        service = PlatformContext().create_learning_service()
        assert isinstance(service, DeterministicLearningService)
