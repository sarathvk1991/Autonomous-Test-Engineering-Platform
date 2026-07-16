"""Builder for the governed default :class:`LearningRuleCatalog` (CAP-086B).

Construction only. It assembles the framework's default governed rule
catalogue — a deterministic, immutable value — and rejects nothing beyond the
models' own field and invariant constraints. It collects nothing, clusters
nothing, generates nothing, and has no runtime consumers.

The catalogue is **governed data**. Future rule additions, removals, or
retunings require only a builder change, never an engine code change (mirrors
ADR-0022 Recommendation 6, ADR-0027 rule catalogue precedent).

The default catalogue spans all twelve governed :class:`LearningRuleCategory`
lanes named in ADR-0029's "Internal Engine Architecture" section — one per
frozen collaborator: 24 rules, two per category.
"""

from __future__ import annotations

from requirement_intelligence.learning.rules.learning_rule import (
    LearningHierarchyLevel,
    LearningPolicyToggle,
    LearningRule,
    LearningRuleCategory,
)
from requirement_intelligence.learning.rules.learning_rule_catalog import (
    LEARNING_RULE_CATALOG_VERSION,
    LearningRuleCatalog,
)

_CANDIDATE_PROPOSAL = LearningPolicyToggle.ENABLE_CANDIDATE_PROPOSAL
_VALIDATION = LearningPolicyToggle.ENABLE_VALIDATION
_CONFIDENCE = LearningPolicyToggle.ENABLE_CONFIDENCE_RECORDING
_LIFECYCLE = LearningPolicyToggle.ENABLE_LIFECYCLE_RECORDING

_CANDIDATE_LEVEL = LearningHierarchyLevel.CANDIDATE
_LEARNING_LEVEL = LearningHierarchyLevel.LEARNING
_VALIDATION_LEVEL = LearningHierarchyLevel.VALIDATION
_CONFIDENCE_LEVEL = LearningHierarchyLevel.CONFIDENCE
_PROMOTION_LEVEL = LearningHierarchyLevel.PROMOTION
_LIFECYCLE_LEVEL = LearningHierarchyLevel.LIFECYCLE


class LearningRuleBuilder:
    """Assemble the governed default :class:`LearningRuleCatalog`."""

    def build(self) -> LearningRuleCatalog:
        """Return the framework's default governed rule catalogue, in canonical order."""
        rules = (
            # ---- Candidate Collection (ADR-0029 D9, LearningCandidateCollector) -----
            LearningRule(
                rule_id="LN-CAN-001",
                title="Best Practice candidate capture",
                description="A BestPractice is captured as one Learning Candidate.",
                category=LearningRuleCategory.CANDIDATE_COLLECTION,
                priority=10,
                capability_switch=_CANDIDATE_PROPOSAL,
                supported_hierarchy_level=_CANDIDATE_LEVEL,
                documentation_reference="ADR-0029 D9",
                evaluation_order=10,
            ),
            LearningRule(
                rule_id="LN-CAN-002",
                title="Candidate proposal requires a sufficient corpus",
                description=(
                    "No candidate is proposed unless the consumed OrganizationalMemoryResult "
                    "carries at least LearningThresholds.minimum_best_practices_for_candidate "
                    "best practices in total."
                ),
                category=LearningRuleCategory.CANDIDATE_COLLECTION,
                priority=20,
                capability_switch=_CANDIDATE_PROPOSAL,
                supported_hierarchy_level=_CANDIDATE_LEVEL,
                documentation_reference="ADR-0028 §Stage 6",
                evaluation_order=20,
            ),
            # ---- Candidate Consolidation (LearningCandidateClusterer) ---------------
            LearningRule(
                rule_id="LN-CON-001",
                title="Consolidate by deterministic equality",
                description=(
                    "Candidates are consolidated only by exact, deterministic equality "
                    "(byte-identical proposed_change text) — never semantic similarity."
                ),
                category=LearningRuleCategory.CANDIDATE_CONSOLIDATION,
                priority=10,
                capability_switch=_CANDIDATE_PROPOSAL,
                supported_hierarchy_level=_CANDIDATE_LEVEL,
                documentation_reference="ADR-0029 D10",
                evaluation_order=30,
            ),
            LearningRule(
                rule_id="LN-CON-002",
                title="Consolidation preserves every source best practice id",
                description=(
                    "Consolidating two candidates unions their source_best_practice_ids — "
                    "no provenance reference is ever dropped."
                ),
                category=LearningRuleCategory.CANDIDATE_CONSOLIDATION,
                priority=20,
                capability_switch=_CANDIDATE_PROPOSAL,
                supported_hierarchy_level=_CANDIDATE_LEVEL,
                documentation_reference="ADR-0028 Recommendation 5 (ADR-0029 D10)",
                evaluation_order=40,
            ),
            # ---- Validation (LearningValidator) --------------------------------------
            LearningRule(
                rule_id="LN-VAL-001",
                title="Validate a consolidated candidate's own evidence",
                description=(
                    "A candidate is validated only from its own referenced Best "
                    "Practices and the governed policy — never hidden context."
                ),
                category=LearningRuleCategory.VALIDATION,
                priority=10,
                capability_switch=_VALIDATION,
                supported_hierarchy_level=_VALIDATION_LEVEL,
                documentation_reference="ADR-0029 D12/D19",
                evaluation_order=50,
            ),
            LearningRule(
                rule_id="LN-VAL-002",
                title="Validation clears all six governed gates or none",
                description=(
                    "A LearningValidation records every governed Stage 6 gate as cleared "
                    "once the candidate's evidence clears the governed confidence floor, "
                    "or no LearningValidation is produced for that candidate at all."
                ),
                category=LearningRuleCategory.VALIDATION,
                priority=20,
                capability_switch=_VALIDATION,
                supported_hierarchy_level=_VALIDATION_LEVEL,
                documentation_reference="ADR-0028 §Stage 6, ADR-0029 D12",
                evaluation_order=60,
            ),
            # ---- Learning Generation (LearningGenerator) -----------------------------
            LearningRule(
                rule_id="LN-GEN-001",
                title="Generate Learning only for a validated candidate",
                description=(
                    "A Learning is constructed only for a candidate that already has a "
                    "LearningValidation — never before, never without one."
                ),
                category=LearningRuleCategory.LEARNING_GENERATION,
                priority=10,
                capability_switch=_VALIDATION,
                supported_hierarchy_level=_LEARNING_LEVEL,
                documentation_reference="ADR-0029 D9/D17 (Stage 0 Constitutional Correction)",
                evaluation_order=70,
            ),
            LearningRule(
                rule_id="LN-GEN-002",
                title="Learning generation never bypasses Learning Candidate",
                description=(
                    "A Learning is generated only from a Learning Candidate — Best "
                    "Practice is never promoted to Learning directly (no skip-level "
                    "promotion)."
                ),
                category=LearningRuleCategory.LEARNING_GENERATION,
                priority=20,
                capability_switch=_VALIDATION,
                supported_hierarchy_level=_LEARNING_LEVEL,
                documentation_reference="ADR-0029 D11, Recommendation 18",
                evaluation_order=80,
            ),
            # ---- Institutionalization (InstitutionalizationEvaluator) ---------------
            LearningRule(
                rule_id="LN-INS-001",
                title="Institutionalization evaluates organizational readiness only",
                description=(
                    "Institutionalization never evaluates technical correctness — that "
                    "remains LearningValidator's exclusive responsibility."
                ),
                category=LearningRuleCategory.INSTITUTIONALIZATION,
                priority=10,
                capability_switch=_VALIDATION,
                supported_hierarchy_level=_LEARNING_LEVEL,
                documentation_reference="ADR-0029 D12, Recommendation 16",
                evaluation_order=90,
            ),
            LearningRule(
                rule_id="LN-INS-002",
                title="Institutionalization never changes validation",
                description=(
                    "InstitutionalizationEvaluator never mutates a LearningValidation "
                    "record, and validation never changes an institutionalization "
                    "outcome."
                ),
                category=LearningRuleCategory.INSTITUTIONALIZATION,
                priority=20,
                capability_switch=_VALIDATION,
                supported_hierarchy_level=_LEARNING_LEVEL,
                documentation_reference="ADR-0029 D19, Recommendation 16",
                evaluation_order=100,
            ),
            # ---- Stability (StabilityEvaluator) --------------------------------------
            LearningRule(
                rule_id="LN-STB-001",
                title="Stability is independent of confidence and maturity",
                description=(
                    "Stability never changes Confidence; Confidence never changes "
                    "Stability; neither changes Maturity."
                ),
                category=LearningRuleCategory.STABILITY,
                priority=10,
                capability_switch=_VALIDATION,
                supported_hierarchy_level=_LEARNING_LEVEL,
                documentation_reference="ADR-0029 D13, Recommendation 17",
                evaluation_order=110,
            ),
            LearningRule(
                rule_id="LN-STB-002",
                title="Stability decisions are not yet persisted",
                description=(
                    "The engine computes a Stability decision deterministically, but "
                    "LearningResult carries no dedicated field for it (reserved scope)."
                ),
                category=LearningRuleCategory.STABILITY,
                priority=20,
                capability_switch=_VALIDATION,
                supported_hierarchy_level=_LEARNING_LEVEL,
                documentation_reference="ADR-0029 D13",
                evaluation_order=120,
            ),
            # ---- Confidence (ConfidenceRecorder) -------------------------------------
            LearningRule(
                rule_id="LN-CNF-001",
                title="Confidence is derived from evidence count",
                description=(
                    "ConfidenceRecorder's output is a deterministic function of the "
                    "referenced evidence count and the governed policy thresholds — "
                    "never an estimate or a heuristic."
                ),
                category=LearningRuleCategory.CONFIDENCE,
                priority=10,
                capability_switch=_CONFIDENCE,
                supported_hierarchy_level=_CONFIDENCE_LEVEL,
                documentation_reference="ADR-0029 D19/D20, Recommendation 28",
                evaluation_order=130,
            ),
            LearningRule(
                rule_id="LN-CNF-002",
                title="Confidence recording never bypasses the governed thresholds",
                description=(
                    "A LearningConfidence record never carries a level a future engine "
                    "could not re-derive from the same evidence count and policy."
                ),
                category=LearningRuleCategory.CONFIDENCE,
                priority=20,
                capability_switch=_CONFIDENCE,
                supported_hierarchy_level=_CONFIDENCE_LEVEL,
                documentation_reference="ADR-0029 D24 (Decision Reproducibility)",
                evaluation_order=140,
            ),
            # ---- Promotion (PromotionRecorder) ---------------------------------------
            LearningRule(
                rule_id="LN-PRM-001",
                title="Record a Candidate-to-Learning promotion",
                description=(
                    "Every Learning generation records one promotion decision naming "
                    "its source candidate and itself as target — reserved, not yet a "
                    "persisted model."
                ),
                category=LearningRuleCategory.PROMOTION,
                priority=10,
                capability_switch=_VALIDATION,
                supported_hierarchy_level=_PROMOTION_LEVEL,
                documentation_reference="ADR-0029 D10 (reserved promotion metadata)",
                evaluation_order=150,
            ),
            LearningRule(
                rule_id="LN-PRM-002",
                title="Promotion never creates or validates Learning",
                description=(
                    "PromotionRecorder records that a promotion happened; it never "
                    "constructs a Learning and never validates one."
                ),
                category=LearningRuleCategory.PROMOTION,
                priority=20,
                capability_switch=_VALIDATION,
                supported_hierarchy_level=_PROMOTION_LEVEL,
                documentation_reference="ADR-0029 D10",
                evaluation_order=160,
            ),
            # ---- Lifecycle (LifecycleRecorder) ---------------------------------------
            LearningRule(
                rule_id="LN-LIF-001",
                title="Record maturity on creation",
                description=(
                    "Every newly proposed Learning Candidate receives a CANDIDATE "
                    "lifecycle record; every newly generated Learning receives a "
                    "VALIDATED or INSTITUTIONAL lifecycle record."
                ),
                category=LearningRuleCategory.LIFECYCLE,
                priority=10,
                capability_switch=_LIFECYCLE,
                supported_hierarchy_level=_LIFECYCLE_LEVEL,
                documentation_reference="ADR-0028 §Stage 8, ADR-0029 D10",
                evaluation_order=170,
            ),
            LearningRule(
                rule_id="LN-LIF-002",
                title="Lifecycle recording never deletes",
                description=(
                    "LifecycleRecorder only appends maturity records — it never removes "
                    "or overwrites a prior LearningLifecycle entry."
                ),
                category=LearningRuleCategory.LIFECYCLE,
                priority=20,
                capability_switch=_LIFECYCLE,
                supported_hierarchy_level=_LIFECYCLE_LEVEL,
                documentation_reference="ADR-0028 §Stage 8, Recommendation 29",
                evaluation_order=180,
            ),
            # ---- Explainability --------------------------------------------------------
            LearningRule(
                rule_id="LN-EXP-001",
                title="Every candidate references its source best practices",
                description=(
                    "A LearningCandidate with zero source_best_practice_ids is not "
                    "constructible (enforced by the frozen model validator)."
                ),
                category=LearningRuleCategory.EXPLAINABILITY,
                priority=10,
                capability_switch=_CANDIDATE_PROPOSAL,
                supported_hierarchy_level=_CANDIDATE_LEVEL,
                documentation_reference="ADR-0029 D14",
                evaluation_order=190,
            ),
            LearningRule(
                rule_id="LN-EXP-002",
                title="Every Learning references its candidate and validation",
                description=(
                    "A Learning with no candidate_id or no validation_id is not "
                    "constructible (enforced by the frozen model's required fields)."
                ),
                category=LearningRuleCategory.EXPLAINABILITY,
                priority=10,
                capability_switch=_VALIDATION,
                supported_hierarchy_level=_LEARNING_LEVEL,
                documentation_reference="ADR-0029 D14",
                evaluation_order=200,
            ),
            # ---- Determinism -------------------------------------------------------------
            LearningRule(
                rule_id="LN-DET-001",
                title="No randomness in any Learning decision",
                description=(
                    "No collaborator consults a UUID, a random number generator, or "
                    "any non-deterministic input when deciding."
                ),
                category=LearningRuleCategory.DETERMINISM,
                priority=10,
                capability_switch=_CANDIDATE_PROPOSAL,
                supported_hierarchy_level=_CANDIDATE_LEVEL,
                documentation_reference="ADR-0029 D18",
                evaluation_order=210,
            ),
            LearningRule(
                rule_id="LN-DET-002",
                title="Reproducible given the same inputs",
                description=(
                    "The same OrganizationalMemoryResult, under the same policy, always "
                    "produces the same LearningResult content."
                ),
                category=LearningRuleCategory.DETERMINISM,
                priority=10,
                capability_switch=_CANDIDATE_PROPOSAL,
                supported_hierarchy_level=_CANDIDATE_LEVEL,
                documentation_reference="ADR-0029 D21/D24",
                evaluation_order=220,
            ),
            # ---- Structural Integrity -----------------------------------------------
            LearningRule(
                rule_id="LN-STR-001",
                title="No duplicate knowledge ids",
                description=(
                    "No two candidates, learnings, validations, confidences, or "
                    "lifecycle records in one result may share an id."
                ),
                category=LearningRuleCategory.STRUCTURAL_INTEGRITY,
                priority=10,
                capability_switch=_CANDIDATE_PROPOSAL,
                supported_hierarchy_level=_CANDIDATE_LEVEL,
                documentation_reference="ADR-0029 §D3 (result validator)",
                evaluation_order=230,
            ),
            LearningRule(
                rule_id="LN-STR-002",
                title="No skip-level promotion",
                description=(
                    "Best Practice is never promoted directly to Learning — "
                    "structurally impossible given Learning's own field types "
                    "(ADR-0029 D11)."
                ),
                category=LearningRuleCategory.STRUCTURAL_INTEGRITY,
                priority=10,
                capability_switch=_VALIDATION,
                supported_hierarchy_level=_LEARNING_LEVEL,
                documentation_reference="ADR-0029 D11, Recommendation 18",
                evaluation_order=240,
            ),
        )
        return LearningRuleCatalog(catalog_version=LEARNING_RULE_CATALOG_VERSION, rules=rules)


def default_learning_rule_catalog() -> LearningRuleCatalog:
    """Return the framework's default governed Learning rule catalogue."""
    return LearningRuleBuilder().build()
