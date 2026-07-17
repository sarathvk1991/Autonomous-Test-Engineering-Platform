"""Architecture-only tests for the CAP-086A.1 engine architecture refinement
(ADR-0029 "Internal Engine Architecture" section, D9-D17, Recommendations
15-22).

CAP-086A.1 itself introduced no code — no collaborator class, no rule
catalogue, no ``engine/`` package existed yet at that milestone. CAP-086B (a
later milestone) has since implemented the collaborator pipeline and rule
catalogue this ADR section pre-specified. These tests therefore verify two
things only:

1. The documentation itself (ADR-0029 and the proposal) carries the frozen
   sections, the named collaborators, and the new Recommendations — the
   permanent record CAP-086B was built against, and which remains true
   regardless of engine version.
2. The CAP-086A models *already* structurally satisfy the principles this
   milestone freezes (adjacent-only promotion, full validation provenance,
   policy-as-data-only) — proving the freeze was not aspirational but
   already true of the shipped contract, exactly as ADR-0027 §D10/§D11
   pre-specified Organizational Memory's own decomposition one milestone
   ahead of its engine.

``TestNoEngineCodeExistsYet`` (CAP-086A.1's own point-in-time check) has
been superseded by ``TestEngineCodeNowFulfillsThePromise`` below, which
verifies CAP-086B actually built every collaborator this section named —
the natural continuation of the same regression guard, not a contradiction
of it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from requirement_intelligence.learning.models.learning import Learning
from requirement_intelligence.learning.models.learning_candidate import LearningCandidate
from requirement_intelligence.learning.models.learning_lifecycle import LearningLifecycle
from requirement_intelligence.learning.models.learning_validation import LearningValidation
from requirement_intelligence.learning.models.result import LearningResult
from requirement_intelligence.learning.policy.learning_policy import LearningPolicy

_REPO_ROOT = Path(__file__).resolve().parents[2]
_LEARNING_PKG = _REPO_ROOT / "requirement_intelligence" / "learning"
_ADR_0029 = _REPO_ROOT / "docs" / "adr" / "0029-learning-framework.md"
_PROPOSAL = _REPO_ROOT / "docs" / "proposals" / "learning-framework.md"

_COLLABORATOR_NAMES = (
    "LearningCandidateCollector",
    "LearningCandidateClusterer",
    "LearningGenerator",
    "InstitutionalizationEvaluator",
    "LearningValidator",
    "StabilityEvaluator",
    "ConfidenceRecorder",
    "PromotionRecorder",
    "LifecycleRecorder",
    "SummaryBuilder",
    "MetricsBuilder",
    "ResultBuilder",
)


def _adr_text() -> str:
    return _ADR_0029.read_text(encoding="utf-8")


def _proposal_text() -> str:
    return _PROPOSAL.read_text(encoding="utf-8")


@pytest.mark.unit
class TestEngineCodeNowFulfillsThePromise:
    """CAP-086B built exactly the shape CAP-086A.1's D9-D17 pre-specified.

    Serialization was absent through CAP-086B.1 — a pure implementation and
    contract-freeze milestone pair that explicitly introduced no serializer,
    Execution Package integration, or CLI phase. CAP-086C has since activated
    the runtime: a projection-only serializer now exists (ADR-0029 §D29), so
    this class asserts the serializer package's presence rather than its
    absence.
    """

    def test_engine_package_exists(self) -> None:
        assert (_LEARNING_PKG / "engine").exists()

    def test_rules_package_exists(self) -> None:
        assert (_LEARNING_PKG / "rules").exists()

    def test_serialization_package_now_exists(self) -> None:
        """CAP-086C (ADR-0029 §D29) introduces the projection-only serializer."""
        assert (_LEARNING_PKG / "serialization").exists()

    @pytest.mark.parametrize("name", _COLLABORATOR_NAMES)
    def test_every_frozen_collaborator_is_now_defined_in_code(self, name: str) -> None:
        """Each collaborator D9/D10 named is now a real class in engine/."""
        matches = [
            path
            for path in (_LEARNING_PKG / "engine").rglob("*.py")
            if f"class {name}" in path.read_text(encoding="utf-8")
        ]
        assert matches, f"no engine module defines class {name}"

    def test_no_learning_promotion_class_is_defined_in_code(self) -> None:
        """PromotionRecorder's output (D10) remains reserved — no dedicated
        LearningPromotion model exists; only the engine-internal PromotionEvent
        dataclass, which is never a runtime contract."""
        for path in _LEARNING_PKG.rglob("*.py"):
            assert "class LearningPromotion" not in path.read_text(encoding="utf-8")

    def test_no_stability_class_is_defined_in_code(self) -> None:
        """StabilityEvaluator's output (D13) remains reserved — no dedicated model yet."""
        for path in _LEARNING_PKG.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            assert "class LearningStability" not in source
            assert "class StabilityRecord" not in source

    def test_rule_catalog_class_is_now_defined_in_code(self) -> None:
        matches = [
            path
            for path in (_LEARNING_PKG / "rules").rglob("*.py")
            if "class LearningRule" in path.read_text(encoding="utf-8")
        ]
        assert matches, "no rules module defines class LearningRule"


@pytest.mark.unit
class TestAdrDocumentsTheInternalEngineArchitecture:
    """ADR-0029 permanently records the frozen engine decomposition (D9)."""

    def test_adr_has_the_internal_engine_architecture_heading(self) -> None:
        assert "## Internal Engine Architecture" in _adr_text()

    def test_adr_has_d9_through_d17(self) -> None:
        source = _adr_text()
        for number in range(9, 18):
            assert f"### D{number}" in source, f"ADR-0029 is missing D{number}"

    @pytest.mark.parametrize("name", _COLLABORATOR_NAMES)
    def test_adr_names_every_collaborator(self, name: str) -> None:
        assert name in _adr_text()

    def test_adr_documents_the_promotion_metadata_as_reserved(self) -> None:
        assert "is reserved, not a new model" in _adr_text()

    def test_adr_documents_the_stability_concept_as_reserved_scope(self) -> None:
        source = _adr_text()
        assert "No dedicated runtime field exists yet" in source

    def test_adr_documents_the_complete_explainability_chain(self) -> None:
        source = _adr_text()
        terms = ("Learning Candidate", "Best Practice", "Lesson", "Experience", "Runtime Truth")
        for term in terms:
            assert term in source

    def test_adr_distinguishes_validation_from_institutionalization(self) -> None:
        source = _adr_text()
        assert "is the Learning technically valid?" in source
        assert "is the Learning organizationally ready" in source

    def test_adr_distinguishes_stability_from_confidence_and_maturity(self) -> None:
        source = _adr_text()
        assert "Stability measures consistency across organizational evidence over time" in source


@pytest.mark.unit
class TestAdrDocumentsNewRecommendations:
    """ADR-0029 permanently freezes Recommendations 15-22 (CAP-086A.1)."""

    @pytest.mark.parametrize(
        "number,title",
        [
            (15, "Learning Engine institutionalizes but never invents knowledge"),
            (16, "Validation is distinct from Institutionalization"),
            (17, "Stability is distinct from Confidence and Maturity"),
            (18, "Promotion remains adjacent, never skip-level"),
            (19, "Single Responsibility Collaborators"),
            (20, "Result Assembly Principle"),
            (21, "Explainability precedes promotion and institutionalization"),
            (22, "Future collaborators remain replaceable without contract change"),
        ],
    )
    def test_recommendation_is_present(self, number: int, title: str) -> None:
        source = _adr_text()
        assert f"### Recommendation {number} — {title}" in source

    def test_every_new_recommendation_is_marked_mandatory_and_frozen_permanently(self) -> None:
        source = _adr_text()
        for number in range(15, 23):
            heading_index = source.index(f"### Recommendation {number} —")
            body = source[heading_index : heading_index + 400]
            assert "CAP-086A.1" in body
            assert "frozen permanently" in body


@pytest.mark.unit
class TestProposalMirrorsTheAdr:
    """§8a of the proposal mirrors ADR-0029's engine architecture section (Stage 13)."""

    def test_proposal_has_the_8a_section(self) -> None:
        assert "## 8a. CAP-086A.1" in _proposal_text()

    def test_proposal_names_every_collaborator(self) -> None:
        source = _proposal_text()
        for name in _COLLABORATOR_NAMES:
            assert name in source, f"proposal is missing {name}"

    def test_proposal_roadmap_marks_cap_086a1_done(self) -> None:
        assert "**Done (CAP-086A.1)" in _proposal_text()

    def test_proposal_status_line_names_cap_086a1(self) -> None:
        assert "CAP-086A.1" in _proposal_text().splitlines()[2]


@pytest.mark.unit
class TestAdjacentPromotionAlreadyEnforced:
    """D11: adjacent-only promotion is already structurally guaranteed by the
    CAP-086A model shapes — this milestone only freezes that fact permanently."""

    def test_learning_cannot_reference_a_best_practice_directly(self) -> None:
        """Learning has no field capable of naming a Best Practice id — only a candidate."""
        assert "source_best_practice_ids" not in Learning.model_fields

    def test_learning_only_field_typed_for_promotion_is_candidate_id(self) -> None:
        assert "candidate_id" in Learning.model_fields
        assert "source_best_practice_ids" not in Learning.model_fields

    def test_learning_candidate_never_references_a_learning(self) -> None:
        """A candidate names the Best Practices it was proposed from; it never names
        the Learning it may later be promoted into — promotion moves one way."""
        for name, field in LearningCandidate.model_fields.items():
            assert "LearningId" not in str(field.annotation), (
                f"LearningCandidate.{name} can hold a LearningId — reverse promotion possible"
            )


@pytest.mark.unit
class TestValidationProvenanceAlreadyComplete:
    """D12: LearningValidation already carries every required provenance field."""

    @pytest.mark.parametrize(
        "field_name",
        ["validation_id", "candidate_id", "gates_cleared", "rationale", "validated_at",
         "confidence", "policy_version"],
    )
    def test_field_exists(self, field_name: str) -> None:
        assert field_name in LearningValidation.model_fields

    def test_no_field_beyond_the_frozen_seven_exists(self) -> None:
        assert set(LearningValidation.model_fields) == {
            "validation_id",
            "candidate_id",
            "gates_cleared",
            "rationale",
            "validated_at",
            "confidence",
            "policy_version",
        }


@pytest.mark.unit
class TestResultOwnsEveryKnowledgeCollectionAlready:
    """D17: LearningResult already owns every collection a future ResultBuilder
    will assemble — no new field is introduced by this milestone."""

    @pytest.mark.parametrize(
        "field_name",
        ["candidates", "learnings", "validations", "confidences", "lifecycles"],
    )
    def test_field_exists(self, field_name: str) -> None:
        assert field_name in LearningResult.model_fields

    def test_no_field_was_added_by_this_milestone(self) -> None:
        """CAP-086A.1 changes no model shape — only documentation."""
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
class TestPolicyRemainsGovernanceOnly:
    """D6 (strengthened)/D10: policy governs; it never performs. No method beyond
    pydantic's own validator machinery is defined on the policy classes."""

    def test_policy_defines_no_validation_or_promotion_method(self) -> None:
        own_methods = {
            name
            for name in vars(LearningPolicy)
            if not name.startswith("_") and callable(getattr(LearningPolicy, name))
        }
        forbidden = {"promote", "validate", "generate", "institutionalize", "retire"}
        assert not (own_methods & forbidden)

    def test_learning_lifecycle_model_defines_no_transition_method(self) -> None:
        """D10: LearningLifecycle is a record, never a transition performer."""
        own_methods = {
            name
            for name in vars(LearningLifecycle)
            if not name.startswith("_") and callable(getattr(LearningLifecycle, name))
        }
        forbidden = {"transition", "retire", "advance", "institutionalize", "activate"}
        assert not (own_methods & forbidden)


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
        """CAP-086A.1 itself changed nothing here; CAP-086B (a later milestone)
        legitimately replaced the dormant service this test originally checked
        for — see ``test_learning_service.py`` for the dedicated CAP-086B
        coverage of that activation. This test now only confirms
        ``PlatformContext`` still constructs a real, valid service instance."""
        from requirement_intelligence.learning.learning_service import LearningService
        from requirement_intelligence.platform.platform_context import PlatformContext

        service = PlatformContext().create_learning_service()
        assert isinstance(service, LearningService)
