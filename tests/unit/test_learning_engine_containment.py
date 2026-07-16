"""Containment, ownership, and PlatformContext wiring tests for the Learning
engine (CAP-086B, ADR-0029 D9-D26).

Verifies each of the twelve collaborators is the sole authority for its
stated responsibility (Stage 8 of the CAP-086B brief), that the
deterministic engine module imports only its own collaborators (never a
peer Layer 2 implementation package, never PlatformContext, never Layer 1),
that the rules/engine packages never touch the Historical Dataset directly,
and that ``PlatformContext`` exposes exactly one factory returning the real
deterministic service. No serializer, runtime pipeline, Execution Package,
or CLI behaviour is exercised here.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from requirement_intelligence.learning.engine import (
    ConfidenceRecorder,
    LearningCandidateClusterer,
    MetricsBuilder,
    PromotionRecorder,
    ResultBuilder,
    SummaryBuilder,
)
from requirement_intelligence.learning.identity import (
    LearningFrameworkVersion,
    LearningPolicyId,
    LearningPolicyVersion,
)
from requirement_intelligence.learning.learning_service import DeterministicLearningService
from requirement_intelligence.learning.policy import default_learning_policy
from requirement_intelligence.platform.platform_context import PlatformContext

_LEARNING_PKG = Path(__file__).resolve().parents[2] / "requirement_intelligence" / "learning"
_NOW = datetime(2026, 7, 16, tzinfo=UTC)

_FORBIDDEN_IMPORT_TOKENS = (
    "requirement_intelligence.enhancement",
    "requirement_intelligence.grounding",
    "requirement_intelligence.validation",
    "requirement_intelligence.cp1",
    "requirement_intelligence.quality_governance",
    "requirement_intelligence.recommendation",
    "requirement_intelligence.continuous_improvement",
    "requirement_intelligence.knowledge_graph",
    "requirement_intelligence.execution",
    "PlatformContext",
)

_ENGINE_FILENAMES = (
    "deterministic_engine.py",
    "learning_candidate_collector.py",
    "learning_candidate_clusterer.py",
    "learning_validator.py",
    "learning_generator.py",
    "institutionalization_evaluator.py",
    "stability_evaluator.py",
    "confidence_recorder.py",
    "promotion_recorder.py",
    "lifecycle_recorder.py",
    "summary_builder.py",
    "metrics_builder.py",
    "result_builder.py",
)


# ===========================================================================
# Import containment
# ===========================================================================


@pytest.mark.unit
class TestEngineImportContainment:
    @pytest.mark.parametrize("filename", _ENGINE_FILENAMES)
    def test_no_engine_module_imports_a_forbidden_layer(self, filename: str) -> None:
        source = (_LEARNING_PKG / "engine" / filename).read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                for token in _FORBIDDEN_IMPORT_TOKENS:
                    assert token not in line, f"{filename} imports {token}: {line!r}"

    def test_no_engine_module_imports_organizational_memory_implementation(self) -> None:
        forbidden = (
            "DeterministicOrganizationalMemoryEngine",
            "DeterministicOrganizationalMemoryService",
            "OrganizationalMemoryService",
            "OrganizationalMemoryPolicy",
            "PromotionRuleCatalog",
        )
        for path in (_LEARNING_PKG / "engine").rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in forbidden:
                        assert token not in line, f"{path.name} imports {token}: {line!r}"

    def test_no_engine_module_touches_historical_dataset_directly(self) -> None:
        for path in (_LEARNING_PKG / "engine").rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    assert "HistoricalDataset" not in line, (
                        f"{path.name} imports HistoricalDataset directly: {line!r}"
                    )

    def test_rules_package_carries_no_engine_imports(self) -> None:
        for path in (_LEARNING_PKG / "rules").rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    assert "learning.engine" not in line, (
                        f"{path.name} imports the engine package: {line!r}"
                    )

    def test_engine_package_carries_no_rules_imports(self) -> None:
        """Stage 3: rule catalogue and engine are independent — the engine's
        collaborators read the governed policy only, never the rule catalogue
        directly (rules are governance documentation of the algorithm, not an
        input to it)."""
        for path in (_LEARNING_PKG / "engine").rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    assert "learning.rules" not in line, (
                        f"{path.name} imports the rules package: {line!r}"
                    )


# ===========================================================================
# Sole-authority ownership (Stage 8 of the CAP-086B brief)
# ===========================================================================


@pytest.mark.unit
class TestSoleAuthorityOwnership:
    """Each collaborator, and only that collaborator, constructs its model type."""

    @pytest.mark.parametrize(
        ("model_name", "owner_filename"),
        [
            ("LearningCandidate(", "learning_candidate_collector.py"),
            ("LearningValidation(", "learning_validator.py"),
            ("Learning(", "learning_generator.py"),
            ("LearningConfidence(", "confidence_recorder.py"),
            ("LearningLifecycle(", "lifecycle_recorder.py"),
            ("LearningResult(", "result_builder.py"),
        ],
    )
    def test_model_is_constructed_only_by_its_owning_collaborator(
        self, model_name: str, owner_filename: str
    ) -> None:
        engine_dir = _LEARNING_PKG / "engine"
        offenders = []
        for path in engine_dir.rglob("*.py"):
            if path.name in (owner_filename, "__init__.py"):
                continue
            if model_name in path.read_text(encoding="utf-8"):
                offenders.append(path.name)
        assert offenders == [], f"{model_name} constructed outside {owner_filename}: {offenders}"

    @pytest.mark.parametrize(
        ("model_name", "owner_filename"),
        [
            ("LearningSummary(", "summary_builder.py"),
            ("LearningMetrics(", "metrics_builder.py"),
        ],
    )
    def test_summary_and_metrics_are_built_by_their_owner_or_the_engines_empty_path(
        self, model_name: str, owner_filename: str
    ) -> None:
        """The engine's policy-disabled empty-result short-circuit constructs these
        two directly, exactly as ``DeterministicOrganizationalMemoryEngine`` did for
        ``OrganizationalMemorySummary``/``OrganizationalMemoryMetrics`` in CAP-085B —
        every other module must still delegate to the owning builder."""
        engine_dir = _LEARNING_PKG / "engine"
        offenders = []
        for path in engine_dir.rglob("*.py"):
            if path.name in (owner_filename, "deterministic_engine.py", "__init__.py"):
                continue
            if model_name in path.read_text(encoding="utf-8"):
                offenders.append(path.name)
        assert offenders == [], f"{model_name} constructed outside {owner_filename}: {offenders}"

    def test_promotion_event_is_constructed_only_by_promotion_recorder(self) -> None:
        engine_dir = _LEARNING_PKG / "engine"
        offenders = []
        for path in engine_dir.rglob("*.py"):
            if path.name in ("promotion_recorder.py", "__init__.py"):
                continue
            if "PromotionEvent(" in path.read_text(encoding="utf-8"):
                offenders.append(path.name)
        assert offenders == []

    def test_candidate_clusterer_never_mints_new_candidate_ids(self) -> None:
        source = (_LEARNING_PKG / "engine" / "learning_candidate_clusterer.py").read_text(
            encoding="utf-8"
        )
        assert "LearningCandidateId.for_source" not in source

    def test_only_collector_mints_candidate_ids(self) -> None:
        engine_dir = _LEARNING_PKG / "engine"
        offenders = []
        for path in engine_dir.rglob("*.py"):
            if path.name in ("learning_candidate_collector.py", "__init__.py"):
                continue
            if "LearningCandidateId.for_source" in path.read_text(encoding="utf-8"):
                offenders.append(path.name)
        assert offenders == []

    def test_only_generator_mints_learning_ids(self) -> None:
        engine_dir = _LEARNING_PKG / "engine"
        offenders = []
        for path in engine_dir.rglob("*.py"):
            if path.name in ("learning_generator.py", "__init__.py"):
                continue
            if "LearningId.for_ordinal" in path.read_text(encoding="utf-8"):
                offenders.append(path.name)
        assert offenders == []

    def test_only_validator_mints_validation_ids(self) -> None:
        engine_dir = _LEARNING_PKG / "engine"
        offenders = []
        for path in engine_dir.rglob("*.py"):
            if path.name in ("learning_validator.py", "__init__.py"):
                continue
            if "LearningValidationId.for_ordinal" in path.read_text(encoding="utf-8"):
                offenders.append(path.name)
        assert offenders == []


# ===========================================================================
# Single computation, immutability
# ===========================================================================


@pytest.mark.unit
class TestSingleComputationAndImmutability:
    def test_summary_builder_output_is_immutable(self) -> None:
        policy = default_learning_policy()
        summary = SummaryBuilder().build(policy.policy_id, policy.policy_version, (), (), ())
        with pytest.raises((TypeError, AttributeError, ValueError)):
            summary.total_candidates = 5  # type: ignore[misc]

    def test_metrics_builder_output_is_immutable(self) -> None:
        metrics = MetricsBuilder().build((), (), (), ())
        with pytest.raises((TypeError, AttributeError, ValueError)):
            metrics.candidate_count = 5  # type: ignore[misc]

    def test_result_builder_output_is_immutable(self) -> None:
        policy = default_learning_policy()
        summary = SummaryBuilder().build(policy.policy_id, policy.policy_version, (), (), ())
        metrics = MetricsBuilder().build((), (), (), ())
        result = ResultBuilder().build(
            organizational_memory_result_id="omr-test",
            candidates=(),
            learnings=(),
            validations=(),
            confidences=(),
            lifecycles=(),
            summary=summary,
            metrics=metrics,
            policy_id=LearningPolicyId("default-learning-policy"),
            policy_version=LearningPolicyVersion(1, 0, 0),
            framework_version=LearningFrameworkVersion(1, 0, 0),
            started_at=_NOW,
            completed_at=_NOW,
        )
        with pytest.raises((TypeError, AttributeError, ValueError)):
            result.organizational_memory_result_id = "other"  # type: ignore[misc]

    def test_candidate_clusterer_returns_a_tuple(self) -> None:
        assert isinstance(LearningCandidateClusterer().cluster(()), tuple)

    def test_confidence_recorder_returns_a_tuple(self) -> None:
        recorder = ConfidenceRecorder(default_learning_policy())
        assert isinstance(recorder.record((), {}, "seed", _NOW), tuple)

    def test_promotion_recorder_returns_a_tuple(self) -> None:
        assert isinstance(PromotionRecorder().record((), _NOW), tuple)


# ===========================================================================
# PlatformContext wiring
# ===========================================================================


@pytest.mark.unit
class TestPlatformContextWiring:
    def test_platform_context_exposes_exactly_one_learning_service_factory(self) -> None:
        service = PlatformContext().create_learning_service()
        assert isinstance(service, DeterministicLearningService)

    def test_platform_context_injects_the_governed_policy(self) -> None:
        ctx = PlatformContext()
        service = ctx.create_learning_service()
        assert service._engine._policy == ctx.create_learning_policy()

    def test_repeated_calls_return_independent_service_instances(self) -> None:
        ctx = PlatformContext()
        a = ctx.create_learning_service()
        b = ctx.create_learning_service()
        assert a is not b
