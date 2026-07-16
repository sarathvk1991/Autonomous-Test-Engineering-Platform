"""Builder for the governed default :class:`PromotionRuleCatalog` (CAP-085B).

Construction only. It assembles the framework's default governed rule
catalogue — a deterministic, immutable value — and rejects nothing beyond the
models' own field and invariant constraints. It captures nothing, clusters
nothing, generates nothing, and has no runtime consumers.

The catalogue is **governed data**. Future rule additions, removals, or
retunings require only a builder change, never an engine code change (mirrors
ADR-0022 Recommendation 6, ADR-0023 rule catalogue precedent).

The default catalogue spans all ten governed :class:`PromotionRuleCategory`
lanes named in ADR-0027's "Internal Engine Architecture" section: 24 rules,
two to six per category.
"""

from __future__ import annotations

from requirement_intelligence.organizational_memory.rules.promotion_rule import (
    OrganizationalMemoryPolicyToggle,
    PromotionHierarchyLevel,
    PromotionRule,
    PromotionRuleCategory,
)
from requirement_intelligence.organizational_memory.rules.promotion_rule_catalog import (
    PROMOTION_RULE_CATALOG_VERSION,
    PromotionRuleCatalog,
)

_CAPTURE = OrganizationalMemoryPolicyToggle.ENABLE_EXPERIENCE_CAPTURE
_LESSON = OrganizationalMemoryPolicyToggle.ENABLE_LESSON_PROMOTION
_BEST_PRACTICE = OrganizationalMemoryPolicyToggle.ENABLE_BEST_PRACTICE_PROMOTION
_RETIREMENT = OrganizationalMemoryPolicyToggle.ENABLE_RETIREMENT

_EXPERIENCE = PromotionHierarchyLevel.EXPERIENCE
_LESSON_LEVEL = PromotionHierarchyLevel.LESSON
_BEST_PRACTICE_LEVEL = PromotionHierarchyLevel.BEST_PRACTICE
_PROMOTION_LEVEL = PromotionHierarchyLevel.PROMOTION
_LIFECYCLE_LEVEL = PromotionHierarchyLevel.LIFECYCLE


class PromotionRuleBuilder:
    """Assemble the governed default :class:`PromotionRuleCatalog`."""

    def build(self) -> PromotionRuleCatalog:
        """Return the framework's default governed rule catalogue, in canonical order."""
        rules = (
            # ---- Experience Capture (ADR-0027 D9, ExperienceCollector) --------------
            PromotionRule(
                rule_id="OM-EXP-001",
                title="Continuous Improvement finding capture",
                description="An ImprovementFinding is captured as one Experience.",
                category=PromotionRuleCategory.EXPERIENCE_CAPTURE,
                priority=10,
                capability_switch=_CAPTURE,
                supported_hierarchy_level=_EXPERIENCE,
                documentation_reference="ADR-0027 §D9",
                evaluation_order=10,
            ),
            PromotionRule(
                rule_id="OM-EXP-002",
                title="Continuous Improvement trend capture",
                description="An ImprovementTrend is captured as one Experience.",
                category=PromotionRuleCategory.EXPERIENCE_CAPTURE,
                priority=10,
                capability_switch=_CAPTURE,
                supported_hierarchy_level=_EXPERIENCE,
                documentation_reference="ADR-0027 §D9",
                evaluation_order=20,
            ),
            PromotionRule(
                rule_id="OM-EXP-003",
                title="Continuous Improvement opportunity capture",
                description="An ImprovementOpportunity is captured as one Experience.",
                category=PromotionRuleCategory.EXPERIENCE_CAPTURE,
                priority=10,
                capability_switch=_CAPTURE,
                supported_hierarchy_level=_EXPERIENCE,
                documentation_reference="ADR-0027 §D9",
                evaluation_order=30,
            ),
            PromotionRule(
                rule_id="OM-EXP-004",
                title="Knowledge Graph finding capture",
                description="A KnowledgeFinding is captured as one Experience.",
                category=PromotionRuleCategory.EXPERIENCE_CAPTURE,
                priority=10,
                capability_switch=_CAPTURE,
                supported_hierarchy_level=_EXPERIENCE,
                documentation_reference="ADR-0027 §D9",
                evaluation_order=40,
            ),
            PromotionRule(
                rule_id="OM-EXP-005",
                title="Knowledge Graph observation capture",
                description="A KnowledgeObservation is captured as one Experience.",
                category=PromotionRuleCategory.EXPERIENCE_CAPTURE,
                priority=10,
                capability_switch=_CAPTURE,
                supported_hierarchy_level=_EXPERIENCE,
                documentation_reference="ADR-0027 §D9",
                evaluation_order=50,
            ),
            PromotionRule(
                rule_id="OM-EXP-006",
                title="Knowledge Graph subgraph capture",
                description="A KnowledgeSubgraph is captured as one Experience.",
                category=PromotionRuleCategory.EXPERIENCE_CAPTURE,
                priority=10,
                capability_switch=_CAPTURE,
                supported_hierarchy_level=_EXPERIENCE,
                documentation_reference="ADR-0027 §D9",
                evaluation_order=60,
            ),
            # ---- Experience Consolidation (ExperienceClusterer) ----------------------
            PromotionRule(
                rule_id="OM-CLU-001",
                title="Cluster by deterministic equality",
                description=(
                    "Experiences are clustered only by exact, deterministic equality "
                    "(same source layer, same description) — never semantic similarity."
                ),
                category=PromotionRuleCategory.EXPERIENCE_CONSOLIDATION,
                priority=10,
                capability_switch=_CAPTURE,
                supported_hierarchy_level=_EXPERIENCE,
                documentation_reference="ADR-0027 Stage 4 (CAP-085B brief)",
                evaluation_order=70,
            ),
            PromotionRule(
                rule_id="OM-CLU-002",
                title="Clusters never cross source layers",
                description=(
                    "A cluster never mixes Continuous Improvement and Knowledge Graph "
                    "experiences — each cluster is layer-homogeneous."
                ),
                category=PromotionRuleCategory.EXPERIENCE_CONSOLIDATION,
                priority=20,
                capability_switch=_CAPTURE,
                supported_hierarchy_level=_EXPERIENCE,
                documentation_reference="ADR-0027 §D2 (peer-source isolation)",
                evaluation_order=80,
            ),
            # ---- Lesson Generation (LessonGenerator) ---------------------------------
            PromotionRule(
                rule_id="OM-LES-001",
                title="Generate a lesson from a qualifying cluster",
                description=(
                    "A Lesson is generated from an Experience cluster once it reaches "
                    "the governed minimum-experiences threshold."
                ),
                category=PromotionRuleCategory.LESSON_GENERATION,
                priority=10,
                capability_switch=_LESSON,
                supported_hierarchy_level=_LESSON_LEVEL,
                documentation_reference="ADR-0027 §D10/§D11",
                evaluation_order=90,
            ),
            PromotionRule(
                rule_id="OM-LES-002",
                title="Lesson generation never bypasses the experience floor",
                description=(
                    "A cluster below OrganizationalMemoryThresholds."
                    "minimum_experiences_for_lesson never produces a Lesson."
                ),
                category=PromotionRuleCategory.LESSON_GENERATION,
                priority=20,
                capability_switch=_LESSON,
                supported_hierarchy_level=_LESSON_LEVEL,
                documentation_reference="ADR-0027 §D6/§D14",
                evaluation_order=100,
            ),
            # ---- Lesson Consolidation (LessonConsolidator) ---------------------------
            PromotionRule(
                rule_id="OM-LSC-001",
                title="Consolidate duplicate lessons by equality",
                description=(
                    "Lessons whose message text is byte-identical are consolidated "
                    "into one, by equality only — never semantic merging."
                ),
                category=PromotionRuleCategory.LESSON_CONSOLIDATION,
                priority=10,
                capability_switch=_LESSON,
                supported_hierarchy_level=_LESSON_LEVEL,
                documentation_reference="ADR-0027 Stage 4 (CAP-085B brief)",
                evaluation_order=110,
            ),
            PromotionRule(
                rule_id="OM-LSC-002",
                title="Consolidation preserves every source experience id",
                description=(
                    "Consolidating two lessons unions their source_experience_ids — "
                    "no provenance reference is ever dropped."
                ),
                category=PromotionRuleCategory.LESSON_CONSOLIDATION,
                priority=20,
                capability_switch=_LESSON,
                supported_hierarchy_level=_LESSON_LEVEL,
                documentation_reference="ADR-0027 §D11",
                evaluation_order=120,
            ),
            # ---- Best Practice Generation (BestPracticeGenerator) --------------------
            PromotionRule(
                rule_id="OM-BP-001",
                title="Generate a best practice from a qualifying lesson group",
                description=(
                    "A Best Practice is generated from consolidated Lessons once they "
                    "reach the governed minimum-lessons threshold."
                ),
                category=PromotionRuleCategory.BEST_PRACTICE_GENERATION,
                priority=10,
                capability_switch=_BEST_PRACTICE,
                supported_hierarchy_level=_BEST_PRACTICE_LEVEL,
                documentation_reference="ADR-0027 §D10/§D11",
                evaluation_order=130,
            ),
            PromotionRule(
                rule_id="OM-BP-002",
                title="Best Practice generation never bypasses Lesson",
                description=(
                    "A Best Practice is generated only from Lessons — Experience is "
                    "never promoted to Best Practice directly (no skip-level promotion)."
                ),
                category=PromotionRuleCategory.BEST_PRACTICE_GENERATION,
                priority=20,
                capability_switch=_BEST_PRACTICE,
                supported_hierarchy_level=_BEST_PRACTICE_LEVEL,
                documentation_reference="ADR-0027 §D10, Recommendation 13",
                evaluation_order=140,
            ),
            # ---- Promotion (PromotionRecorder) ---------------------------------------
            PromotionRule(
                rule_id="OM-PRM-001",
                title="Record an Experience-to-Lesson promotion",
                description=(
                    "Every Lesson generation produces exactly one KnowledgePromotion "
                    "record naming its source experiences and itself as target."
                ),
                category=PromotionRuleCategory.PROMOTION,
                priority=10,
                capability_switch=_LESSON,
                supported_hierarchy_level=_PROMOTION_LEVEL,
                documentation_reference="ADR-0027 §D4/§D11",
                evaluation_order=150,
            ),
            PromotionRule(
                rule_id="OM-PRM-002",
                title="Record a Lesson-to-Best-Practice promotion",
                description=(
                    "Every Best Practice generation produces exactly one "
                    "KnowledgePromotion record naming its source lessons and itself "
                    "as target."
                ),
                category=PromotionRuleCategory.PROMOTION,
                priority=10,
                capability_switch=_BEST_PRACTICE,
                supported_hierarchy_level=_PROMOTION_LEVEL,
                documentation_reference="ADR-0027 §D4/§D11",
                evaluation_order=160,
            ),
            # ---- Lifecycle (LifecycleRecorder) ---------------------------------------
            PromotionRule(
                rule_id="OM-LIF-001",
                title="Record ACTIVE lifecycle on creation",
                description=(
                    "Every newly created Experience, Lesson, and Best Practice "
                    "receives exactly one ACTIVE KnowledgeLifecycle record."
                ),
                category=PromotionRuleCategory.LIFECYCLE,
                priority=10,
                capability_switch=_RETIREMENT,
                supported_hierarchy_level=_LIFECYCLE_LEVEL,
                documentation_reference="ADR-0027 §D5/§D15",
                evaluation_order=170,
            ),
            PromotionRule(
                rule_id="OM-LIF-002",
                title="Lifecycle recording never deletes",
                description=(
                    "LifecycleRecorder only appends state records — it never removes "
                    "or overwrites a prior KnowledgeLifecycle entry."
                ),
                category=PromotionRuleCategory.LIFECYCLE,
                priority=20,
                capability_switch=_RETIREMENT,
                supported_hierarchy_level=_LIFECYCLE_LEVEL,
                documentation_reference="ADR-0026 §Stage 7, ADR-0027 Recommendation 4",
                evaluation_order=180,
            ),
            # ---- Explainability --------------------------------------------------------
            PromotionRule(
                rule_id="OM-EXP-CHAIN-001",
                title="Every lesson references its source experiences",
                description=(
                    "A Lesson with zero source_experience_ids is not constructible "
                    "(enforced by the frozen model validator)."
                ),
                category=PromotionRuleCategory.EXPLAINABILITY,
                priority=10,
                capability_switch=_LESSON,
                supported_hierarchy_level=_LESSON_LEVEL,
                documentation_reference="ADR-0027 §D13",
                evaluation_order=190,
            ),
            PromotionRule(
                rule_id="OM-EXP-CHAIN-002",
                title="Every best practice references its source lessons",
                description=(
                    "A BestPractice with zero source_lesson_ids is not constructible "
                    "(enforced by the frozen model validator)."
                ),
                category=PromotionRuleCategory.EXPLAINABILITY,
                priority=10,
                capability_switch=_BEST_PRACTICE,
                supported_hierarchy_level=_BEST_PRACTICE_LEVEL,
                documentation_reference="ADR-0027 §D13",
                evaluation_order=200,
            ),
            # ---- Determinism -------------------------------------------------------------
            PromotionRule(
                rule_id="OM-DET-001",
                title="No randomness in promotion",
                description=(
                    "No collaborator consults a UUID, a random number generator, or "
                    "any non-deterministic input when promoting knowledge."
                ),
                category=PromotionRuleCategory.DETERMINISM,
                priority=10,
                capability_switch=_CAPTURE,
                supported_hierarchy_level=_EXPERIENCE,
                documentation_reference="ADR-0027 Stage 4 (CAP-085B brief)",
                evaluation_order=210,
            ),
            PromotionRule(
                rule_id="OM-DET-002",
                title="Reproducible given the same inputs",
                description=(
                    "The same ContinuousImprovementResult and KnowledgeGraphResult, "
                    "under the same policy, always produce the same "
                    "OrganizationalMemoryResult content."
                ),
                category=PromotionRuleCategory.DETERMINISM,
                priority=10,
                capability_switch=_CAPTURE,
                supported_hierarchy_level=_EXPERIENCE,
                documentation_reference="ADR-0027 §D11 (reproducibility)",
                evaluation_order=220,
            ),
            # ---- Structural Integrity -----------------------------------------------
            PromotionRule(
                rule_id="OM-STR-001",
                title="No duplicate knowledge ids",
                description=(
                    "No two experiences, lessons, best practices, promotions, or "
                    "lifecycle records in one result may share an id."
                ),
                category=PromotionRuleCategory.STRUCTURAL_INTEGRITY,
                priority=10,
                capability_switch=_CAPTURE,
                supported_hierarchy_level=_EXPERIENCE,
                documentation_reference="ADR-0027 §D3 (result validator)",
                evaluation_order=230,
            ),
            PromotionRule(
                rule_id="OM-STR-002",
                title="No skip-level promotion",
                description=(
                    "Experience is never promoted directly to Best Practice — "
                    "structurally impossible given Lesson/BestPractice's own field "
                    "types (ADR-0027 §D10)."
                ),
                category=PromotionRuleCategory.STRUCTURAL_INTEGRITY,
                priority=10,
                capability_switch=_BEST_PRACTICE,
                supported_hierarchy_level=_BEST_PRACTICE_LEVEL,
                documentation_reference="ADR-0027 §D10, Recommendation 13",
                evaluation_order=240,
            ),
        )
        return PromotionRuleCatalog(catalog_version=PROMOTION_RULE_CATALOG_VERSION, rules=rules)


def default_promotion_rule_catalog() -> PromotionRuleCatalog:
    """Return the framework's default governed promotion rule catalogue."""
    return PromotionRuleBuilder().build()
