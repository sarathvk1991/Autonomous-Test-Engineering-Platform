"""Architecture-only tests for the CAP-086A.2 decision governance freeze
(ADR-0029 "Decision Governance & Deterministic Execution" section, D18-D26,
Recommendations 23-30).

CAP-086A.2 itself introduced no code — no collaborator class, no rule
catalogue, no ``engine/`` package existed yet at that milestone, and no
model, policy, contract, or version changes. CAP-086B (a later milestone)
has since implemented the engine and rule catalogue this ADR section's
decision-governance principles now bind. These tests therefore verify two
things only:

1. The documentation itself (ADR-0029) carries the frozen decision-governance
   sections and the new Recommendations — the permanent record CAP-086B was
   built against, and which remains true regardless of engine version.
2. Nothing about the CAP-086A/CAP-086A.1 shipped runtime *contract* drifted:
   the same models, the same fields, the same versions — the service itself
   has legitimately gone from dormant to deterministic (CAP-086B), which is
   activation, not drift; see ``test_learning_service.py`` for the dedicated
   coverage of that activation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from requirement_intelligence.learning.models.learning import Learning
from requirement_intelligence.learning.models.learning_candidate import LearningCandidate
from requirement_intelligence.learning.models.learning_validation import LearningValidation
from requirement_intelligence.learning.models.result import LearningResult

_REPO_ROOT = Path(__file__).resolve().parents[2]
_LEARNING_PKG = _REPO_ROOT / "requirement_intelligence" / "learning"
_ADR_0029 = _REPO_ROOT / "docs" / "adr" / "0029-learning-framework.md"

_D_SECTIONS = tuple(range(18, 27))

_DECISION_CATEGORIES = (
    "Promotion decisions",
    "Validation decisions",
    "Institutionalization decisions",
    "Stability decisions",
    "Confidence decisions",
    "Lifecycle decisions",
)


def _adr_text() -> str:
    return _ADR_0029.read_text(encoding="utf-8")


@pytest.mark.unit
class TestEngineCodeNowExists:
    """CAP-086A.2's own point-in-time check (no engine/rules code yet) has
    been superseded by CAP-086B, which built exactly what D9-D26 governs."""

    def test_engine_package_exists(self) -> None:
        assert (_LEARNING_PKG / "engine").exists()

    def test_rules_package_exists(self) -> None:
        assert (_LEARNING_PKG / "rules").exists()

    def test_no_serialization_package_exists_yet(self) -> None:
        assert not (_LEARNING_PKG / "serialization").exists()


@pytest.mark.unit
class TestAdrDocumentsDecisionGovernance:
    """ADR-0029 permanently records the frozen decision-governance sections."""

    def test_adr_has_the_decision_governance_heading(self) -> None:
        assert "## Decision Governance & Deterministic Execution" in _adr_text()

    def test_adr_has_d18_through_d26(self) -> None:
        source = _adr_text()
        for number in _D_SECTIONS:
            assert f"### D{number}" in source, f"ADR-0029 is missing D{number}"

    @pytest.mark.parametrize("category", _DECISION_CATEGORIES)
    def test_adr_names_every_decision_category(self, category: str) -> None:
        assert category in _adr_text()


@pytest.mark.unit
class TestAdrDocumentsTheDeterministicDecisionPrinciple:
    """D18: the six permanent properties and the four hidden-state prohibitions."""

    @pytest.mark.parametrize(
        "property_name",
        ["deterministic", "explainable", "reproducible", "policy-governed", "immutable",
         "append-only"],
    )
    def test_property_is_documented(self, property_name: str) -> None:
        assert property_name in _adr_text()

    def test_hidden_reasoning_is_forbidden(self) -> None:
        assert "No hidden reasoning" in _adr_text()

    def test_hidden_heuristics_is_forbidden(self) -> None:
        assert "No hidden heuristics" in _adr_text()

    def test_hidden_cache_is_forbidden(self) -> None:
        assert "No hidden cache" in _adr_text()

    def test_hidden_mutable_state_is_forbidden(self) -> None:
        assert "No hidden mutable state" in _adr_text()


@pytest.mark.unit
class TestAdrDocumentsEnginePurity:
    """D21: the whole-engine pure-function boundary."""

    def test_engine_purity_heading_present(self) -> None:
        assert "### D21 — Engine Purity" in _adr_text()

    def test_pure_function_inputs_and_output_are_named(self) -> None:
        source = _adr_text()
        assert "OrganizationalMemoryResult" in source
        assert "LearningPolicy" in source
        assert "LearningResult" in source

    def test_same_input_same_output_always_is_frozen(self) -> None:
        assert "Same input, same output, always." in _adr_text()


@pytest.mark.unit
class TestAdrDocumentsCollaboratorCommunication:
    """D20: immutable-object-only communication between collaborators."""

    def test_collaborators_communicate_only_through_immutable_objects(self) -> None:
        assert "Collaborators communicate only through immutable objects" in _adr_text()

    def test_forbidden_communication_channels_are_named(self) -> None:
        source = _adr_text()
        for channel in ("shared mutable state", "singleton cache", "global variable"):
            assert channel in source


@pytest.mark.unit
class TestAdrDocumentsResultAssemblyIsNonComputational:
    """D22: ResultBuilder/SummaryBuilder/MetricsBuilder assemble; they never compute."""

    def test_result_builder_never_computes(self) -> None:
        assert "`ResultBuilder` never computes a decision" in _adr_text()

    def test_summary_and_metrics_builders_never_compute_learning(self) -> None:
        source = _adr_text()
        assert "`SummaryBuilder` never computes Learning" in source
        assert "`MetricsBuilder` never computes Learning" in source


@pytest.mark.unit
class TestAdrDocumentsNewRecommendations:
    """ADR-0029 permanently freezes Recommendations 23-30 (CAP-086A.2)."""

    @pytest.mark.parametrize(
        "number,title",
        [
            (23, "Every Learning decision is deterministic, explainable, reproducible, "
                 "governed, immutable, and append-only"),
            (24, "Learning decisions never depend on hidden state"),
            (25, "Collaborators communicate only through immutable objects"),
            (26, "The deterministic engine is a pure function"),
            (27, "Institutionalization, Stability, and Confidence decisions remain "
                 "mutually independent"),
            (28, "Confidence is always derived, never guessed"),
            (29, "Lifecycle transitions are append-only and never rewrite history"),
            (30, "ResultBuilder, SummaryBuilder, and MetricsBuilder assemble; they never "
                 "compute Learning"),
        ],
    )
    def test_recommendation_is_present(self, number: int, title: str) -> None:
        source = _adr_text()
        assert f"### Recommendation {number} — {title}" in source

    def test_every_new_recommendation_is_marked_mandatory_and_frozen_permanently(self) -> None:
        source = _adr_text()
        for number in range(23, 31):
            heading_index = source.index(f"### Recommendation {number} —")
            body = source[heading_index : heading_index + 400]
            assert "CAP-086A.2" in body
            assert "frozen permanently" in body


@pytest.mark.unit
class TestModelsUnchangedByThisMilestone:
    """CAP-086A.2 changes no model shape — only documentation (Stage 15 verification)."""

    def test_learning_field_set_unchanged(self) -> None:
        assert set(Learning.model_fields) == {
            "learning_id",
            "candidate_id",
            "validation_id",
            "message",
            "maturity",
            "confidence",
        }

    def test_learning_candidate_field_set_unchanged(self) -> None:
        assert set(LearningCandidate.model_fields) == {
            "candidate_id",
            "source_best_practice_ids",
            "proposed_change",
            "confidence",
        }

    def test_learning_validation_field_set_unchanged(self) -> None:
        assert set(LearningValidation.model_fields) == {
            "validation_id",
            "candidate_id",
            "gates_cleared",
            "rationale",
            "validated_at",
            "confidence",
            "policy_version",
        }

    def test_learning_result_field_set_unchanged(self) -> None:
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


@pytest.mark.unit
class TestNoRuntimeBehaviourChange:
    def test_platform_version_unchanged(self) -> None:
        from requirement_intelligence.platform import platform_metadata

        assert platform_metadata.PLATFORM_VERSION == "1.0.0"

    def test_learning_framework_version_unchanged_by_this_milestone(self) -> None:
        from requirement_intelligence.learning.version import LEARNING_FRAMEWORK_VERSION

        assert str(LEARNING_FRAMEWORK_VERSION) == "1.0.0"

    def test_learning_result_version_unchanged_by_this_milestone(self) -> None:
        from requirement_intelligence.learning.models.result import LEARNING_RESULT_VERSION

        assert str(LEARNING_RESULT_VERSION) == "1.0.0"

    def test_platform_context_registers_a_real_service(self) -> None:
        """CAP-086A.2 itself changed nothing here; CAP-086B (a later milestone)
        legitimately replaced the dormant service this test originally checked
        for — see ``test_learning_service.py`` for the dedicated CAP-086B
        coverage of that activation."""
        from requirement_intelligence.learning.learning_service import LearningService
        from requirement_intelligence.platform.platform_context import PlatformContext

        service = PlatformContext().create_learning_service()
        assert isinstance(service, LearningService)
