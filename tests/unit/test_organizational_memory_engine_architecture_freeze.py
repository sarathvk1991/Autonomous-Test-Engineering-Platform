"""Architecture-only tests for the CAP-085A.1 engine architecture refinement
(ADR-0027 "Internal Engine Architecture" section, D9-D16, Recommendations
13-17).

CAP-085A.1 introduces no code — no collaborator class, no rule catalogue, no
``engine/`` package exists yet. These tests therefore verify two things only:

1. The documentation itself (ADR-0027 and the proposal) carries the frozen
   sections, the named collaborators, and the new Recommendations — the
   permanent record a future CAP-085B implementer must build against.
2. The CAP-085A models *already* structurally satisfy the principles this
   milestone freezes (adjacent-only promotion, full promotion provenance,
   policy-as-data-only) — proving the freeze is not aspirational but already
   true of the shipped contract, exactly as ADR-0023 §D10 pre-specified
   Knowledge Graph's decomposition one milestone ahead of its own engine.

No behaviour is exercised — nothing is captured, promoted, or retired.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from requirement_intelligence.organizational_memory.models.best_practice import BestPractice
from requirement_intelligence.organizational_memory.models.knowledge_lifecycle import (
    KnowledgeLifecycle,
)
from requirement_intelligence.organizational_memory.models.knowledge_promotion import (
    KnowledgePromotion,
)
from requirement_intelligence.organizational_memory.models.lesson import Lesson
from requirement_intelligence.organizational_memory.models.result import OrganizationalMemoryResult
from requirement_intelligence.organizational_memory.policy.organizational_memory_policy import (
    OrganizationalMemoryPolicy,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ORGANIZATIONAL_MEMORY_PKG = _REPO_ROOT / "requirement_intelligence" / "organizational_memory"
_ADR_0027 = _REPO_ROOT / "docs" / "adr" / "0027-organizational-memory-framework.md"
_PROPOSAL = _REPO_ROOT / "docs" / "proposals" / "organizational-memory-framework.md"

_COLLABORATOR_NAMES = (
    "ExperienceCollector",
    "ExperienceClusterer",
    "LessonGenerator",
    "LessonConsolidator",
    "BestPracticeGenerator",
    "PromotionRecorder",
    "LifecycleRecorder",
    "SummaryBuilder",
    "MetricsBuilder",
    "ResultBuilder",
)


def _adr_text() -> str:
    return _ADR_0027.read_text(encoding="utf-8")


def _proposal_text() -> str:
    return _PROPOSAL.read_text(encoding="utf-8")


@pytest.mark.unit
class TestNoEngineCodeExistsYet:
    """CAP-085A.1 introduces documentation only — no collaborator implementation."""

    def test_no_engine_package_exists(self) -> None:
        assert not (_ORGANIZATIONAL_MEMORY_PKG / "engine").exists()

    def test_no_rules_package_exists(self) -> None:
        assert not (_ORGANIZATIONAL_MEMORY_PKG / "rules").exists()

    def test_no_serialization_package_exists(self) -> None:
        assert not (_ORGANIZATIONAL_MEMORY_PKG / "serialization").exists()

    @pytest.mark.parametrize("name", _COLLABORATOR_NAMES)
    def test_no_collaborator_class_is_defined_in_code(self, name: str) -> None:
        """Each frozen collaborator name is documentation-only — not yet a class."""
        for path in _ORGANIZATIONAL_MEMORY_PKG.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            assert f"class {name}" not in source, f"{path.name} already defines class {name}"

    def test_no_promotion_rule_class_is_defined_in_code(self) -> None:
        for path in _ORGANIZATIONAL_MEMORY_PKG.rglob("*.py"):
            assert "class PromotionRule" not in path.read_text(encoding="utf-8")


@pytest.mark.unit
class TestAdrDocumentsTheInternalEngineArchitecture:
    """ADR-0027 permanently records the frozen engine decomposition (D9)."""

    def test_adr_has_the_internal_engine_architecture_heading(self) -> None:
        assert "## Internal Engine Architecture" in _adr_text()

    def test_adr_has_d9_through_d16(self) -> None:
        source = _adr_text()
        for number in range(9, 17):
            assert f"### D{number}" in source, f"ADR-0027 is missing D{number}"

    @pytest.mark.parametrize("name", _COLLABORATOR_NAMES)
    def test_adr_names_every_collaborator(self, name: str) -> None:
        assert name in _adr_text()

    def test_adr_documents_the_promotion_rule_concept(self) -> None:
        assert "PromotionRule" in _adr_text()

    def test_adr_states_promotion_rule_has_no_implementation(self) -> None:
        assert "No implementation exists." in _adr_text()

    def test_adr_documents_the_complete_explainability_chain(self) -> None:
        source = _adr_text()
        for term in ("Best Practice", "Lesson", "Experience", "Runtime Truth"):
            assert term in source


@pytest.mark.unit
class TestAdrDocumentsNewRecommendations:
    """ADR-0027 permanently freezes Recommendations 13-17 (CAP-085A.1)."""

    @pytest.mark.parametrize(
        "number,title",
        [
            (13, "Organizational Knowledge Promotion Principle"),
            (14, "Single Responsibility Collaborators"),
            (15, "Result Assembly Principle"),
            (16, "Promotion is Policy Governed"),
            (17, "Explainability Before Promotion"),
        ],
    )
    def test_recommendation_is_present(self, number: int, title: str) -> None:
        source = _adr_text()
        assert f"### Recommendation {number} — {title}" in source

    def test_every_new_recommendation_is_marked_mandatory_and_frozen_permanently(self) -> None:
        source = _adr_text()
        for number in range(13, 18):
            heading_index = source.index(f"### Recommendation {number} —")
            body = source[heading_index : heading_index + 400]
            assert "CAP-085A.1" in body
            assert "frozen permanently" in body


@pytest.mark.unit
class TestProposalMirrorsTheAdr:
    """§8a of the proposal mirrors ADR-0027's engine architecture section (Stage 10)."""

    def test_proposal_has_the_8a_section(self) -> None:
        assert "## 8a. CAP-085A.1" in _proposal_text()

    def test_proposal_names_every_collaborator(self) -> None:
        source = _proposal_text()
        for name in _COLLABORATOR_NAMES:
            assert name in source, f"proposal is missing {name}"

    def test_proposal_roadmap_marks_cap_085a1_done(self) -> None:
        assert "**Done (CAP-085A.1)" in _proposal_text()

    def test_proposal_status_line_names_cap_085a1(self) -> None:
        assert "CAP-085A.1" in _proposal_text().splitlines()[2]


@pytest.mark.unit
class TestKnowledgeHierarchyAdjacencyAlreadyEnforced:
    """D10: adjacent-only promotion is already structurally guaranteed by the
    CAP-085A model shapes — this milestone only freezes that fact permanently."""

    def test_lesson_cannot_reference_a_best_practice(self) -> None:
        """Lesson has no field capable of holding a BestPracticeId."""
        for name, field in Lesson.model_fields.items():
            assert "BestPracticeId" not in str(field.annotation), (
                f"Lesson.{name} can hold a BestPracticeId — downward promotion possible"
            )

    def test_best_practice_cannot_reference_an_experience_directly(self) -> None:
        """BestPractice has no field capable of holding an ExperienceId."""
        for name, field in BestPractice.model_fields.items():
            assert "ExperienceId" not in str(field.annotation), (
                f"BestPractice.{name} can hold an ExperienceId — skip-level promotion possible"
            )

    def test_lesson_only_field_typed_for_promotion_is_experience_ids(self) -> None:
        assert "source_experience_ids" in Lesson.model_fields
        assert "source_best_practice_ids" not in Lesson.model_fields

    def test_best_practice_only_field_typed_for_promotion_is_lesson_ids(self) -> None:
        assert "source_lesson_ids" in BestPractice.model_fields
        assert "source_experience_ids" not in BestPractice.model_fields


@pytest.mark.unit
class TestPromotionProvenanceAlreadyComplete:
    """D11: KnowledgePromotion already carries every required provenance field."""

    @pytest.mark.parametrize(
        "field_name",
        ["source_ids", "target_ids", "rationale", "promoted_at", "confidence", "policy_version"],
    )
    def test_field_exists(self, field_name: str) -> None:
        assert field_name in KnowledgePromotion.model_fields

    def test_no_field_beyond_the_frozen_six_exists(self) -> None:
        """Provenance is the reference chain (D13), never a seventh stored field."""
        assert set(KnowledgePromotion.model_fields) == {
            "promotion_id",
            "source_ids",
            "target_ids",
            "rationale",
            "promoted_at",
            "confidence",
            "policy_version",
        }


@pytest.mark.unit
class TestResultOwnsEveryKnowledgeCollectionAlready:
    """D16: OrganizationalMemoryResult already owns every collection a future
    ResultBuilder will assemble — no new field is introduced by this milestone."""

    @pytest.mark.parametrize(
        "field_name",
        ["experiences", "lessons", "best_practices", "promotions", "lifecycles"],
    )
    def test_field_exists(self, field_name: str) -> None:
        assert field_name in OrganizationalMemoryResult.model_fields

    def test_no_field_was_added_by_this_milestone(self) -> None:
        """CAP-085A.1 changes no model shape — only documentation."""
        assert set(OrganizationalMemoryResult.model_fields) == {
            "result_id",
            "memory_id",
            "continuous_improvement_result_id",
            "knowledge_graph_result_id",
            "experiences",
            "lessons",
            "best_practices",
            "promotions",
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
class TestPolicyRemainsGovernanceOnly:
    """D6 (strengthened)/D14: policy governs; it never performs. No method beyond
    pydantic's own validator machinery is defined on the policy classes."""

    def test_policy_defines_no_promotion_method(self) -> None:
        own_methods = {
            name
            for name in vars(OrganizationalMemoryPolicy)
            if not name.startswith("_") and callable(getattr(OrganizationalMemoryPolicy, name))
        }
        forbidden = {"promote", "capture", "retire", "generate", "institutionalize"}
        assert not (own_methods & forbidden)

    def test_knowledge_lifecycle_model_defines_no_transition_method(self) -> None:
        """D15: KnowledgeLifecycle is a record, never a transition performer."""
        own_methods = {
            name
            for name in vars(KnowledgeLifecycle)
            if not name.startswith("_") and callable(getattr(KnowledgeLifecycle, name))
        }
        forbidden = {"transition", "retire", "deprecate", "archive", "activate"}
        assert not (own_methods & forbidden)


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
        from requirement_intelligence.organizational_memory.models.result import (
            ORGANIZATIONAL_MEMORY_RESULT_VERSION,
        )

        assert str(ORGANIZATIONAL_MEMORY_RESULT_VERSION) == "1.0.0"

    def test_platform_context_still_registers_the_dormant_service(self) -> None:
        from requirement_intelligence.organizational_memory.organizational_memory_service import (
            DormantOrganizationalMemoryService,
        )
        from requirement_intelligence.platform.platform_context import PlatformContext

        service = PlatformContext().create_organizational_memory_service()
        assert isinstance(service, DormantOrganizationalMemoryService)
