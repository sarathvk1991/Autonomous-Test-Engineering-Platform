"""Builder for the governed default :class:`RecommendationRuleCatalog` (CAP-082B).

Construction only. It assembles the framework's default governed rule catalogue — a
deterministic, immutable value — and rejects nothing beyond the models' own field
and invariant constraints. It generates no recommendation, reads no upstream
result, and has no runtime consumers.

The catalogue is **governed data**. Future rule additions, removals, or retunings
require only a builder change (a versioned catalogue change under the golden
re-baseline procedure), never an engine code change — mirroring the policy
discipline (ADR-0019 Recommendation 3/5).

The default catalogue spans all five governed :class:`RecommendationSource` values
(Enhancement, Grounding, Validation, CP1, Quality Governance) and, between them,
exercises all nine :class:`RecommendationType` values and all four
:class:`RecommendationPriority` values — so the deterministic engine has full
governed coverage from day one.
"""

from __future__ import annotations

from requirement_intelligence.recommendation.models.enums import (
    RecommendationEffort,
    RecommendationPriority,
    RecommendationSource,
    RecommendationType,
)
from requirement_intelligence.recommendation.rules.recommendation_rule import (
    RecommendationPolicyToggle,
    RecommendationRule,
    RecommendationRuleCategory,
)
from requirement_intelligence.recommendation.rules.recommendation_rule_catalog import (
    RECOMMENDATION_RULE_CATALOG_VERSION,
    RecommendationRuleCatalog,
)

_DETERMINISTIC = RecommendationPolicyToggle.ENABLE_DETERMINISTIC_ENGINE


class RecommendationRuleBuilder:
    """Assemble the governed default :class:`RecommendationRuleCatalog`."""

    def build(self) -> RecommendationRuleCatalog:
        """Return the framework's default governed rule catalogue, in canonical order."""
        rules = (
            # ---- Enhancement ------------------------------------------------------
            RecommendationRule(
                rule_id="RC-ENH-001",
                rule_name="Resolve the missing dependency",
                category=RecommendationRuleCategory.ENHANCEMENT_DEPENDENCY_GAP,
                source_subsystem=RecommendationSource.ENHANCEMENT,
                recommendation_type=RecommendationType.RESOLVE_DEPENDENCY,
                guidance=(
                    "Add the missing dependency relationship, or rephrase the "
                    "requirement so the dependency it names can be resolved."
                ),
                priority_hint=RecommendationPriority.MEDIUM,
                effort_hint=RecommendationEffort.MEDIUM,
                confidence_hint=0.70,
                policy_reference=_DETERMINISTIC,
                evaluation_order=10,
                tags=("enhancement", "dependency"),
            ),
            RecommendationRule(
                rule_id="RC-ENH-002",
                rule_name="Resolve the duplicate requirement",
                category=RecommendationRuleCategory.ENHANCEMENT_DUPLICATE_REQUIREMENT,
                source_subsystem=RecommendationSource.ENHANCEMENT,
                recommendation_type=RecommendationType.RESOLVE_DUPLICATE,
                guidance="Merge or remove the duplicate requirement pair.",
                priority_hint=RecommendationPriority.MEDIUM,
                effort_hint=RecommendationEffort.LOW,
                confidence_hint=0.95,
                policy_reference=_DETERMINISTIC,
                evaluation_order=20,
                tags=("enhancement", "duplication"),
            ),
            RecommendationRule(
                rule_id="RC-ENH-003",
                rule_name="Clarify the disconnected requirement set",
                category=RecommendationRuleCategory.ENHANCEMENT_CONSISTENCY_WARNING,
                source_subsystem=RecommendationSource.ENHANCEMENT,
                recommendation_type=RecommendationType.CLARIFY_REQUIREMENT,
                guidance=(
                    "Review the disconnected requirement(s) and clarify how they "
                    "relate to the rest of the set."
                ),
                priority_hint=RecommendationPriority.MEDIUM,
                effort_hint=RecommendationEffort.MEDIUM,
                confidence_hint=0.75,
                policy_reference=_DETERMINISTIC,
                evaluation_order=30,
                tags=("enhancement", "consistency"),
            ),
            RecommendationRule(
                rule_id="RC-ENH-004",
                rule_name="Resolve the circular dependency",
                category=RecommendationRuleCategory.ENHANCEMENT_CONSISTENCY_CRITICAL,
                source_subsystem=RecommendationSource.ENHANCEMENT,
                recommendation_type=RecommendationType.RESOLVE_CONFLICT,
                guidance="Break the circular DEPENDS_ON relationship among the named requirements.",
                priority_hint=RecommendationPriority.CRITICAL,
                effort_hint=RecommendationEffort.HIGH,
                confidence_hint=0.90,
                policy_reference=_DETERMINISTIC,
                evaluation_order=40,
                tags=("enhancement", "consistency", "cycle"),
            ),
            RecommendationRule(
                rule_id="RC-ENH-005",
                rule_name="Clarify the untraceable requirement",
                category=RecommendationRuleCategory.ENHANCEMENT_TRACEABILITY_GAP,
                source_subsystem=RecommendationSource.ENHANCEMENT,
                recommendation_type=RecommendationType.CLARIFY_REQUIREMENT,
                guidance="Add a traceability reference so the requirement's origin is clear.",
                priority_hint=RecommendationPriority.LOW,
                effort_hint=RecommendationEffort.LOW,
                confidence_hint=0.60,
                policy_reference=_DETERMINISTIC,
                evaluation_order=50,
                tags=("enhancement", "traceability"),
            ),
            # ---- Grounding ---------------------------------------------------------
            RecommendationRule(
                rule_id="RC-GRD-001",
                rule_name="Strengthen evidence for the unsupported requirement",
                category=RecommendationRuleCategory.GROUNDING_UNSUPPORTED,
                source_subsystem=RecommendationSource.GROUNDING,
                recommendation_type=RecommendationType.STRENGTHEN_EVIDENCE,
                guidance="Attach supporting evidence to the unsupported requirement, or remove it.",
                priority_hint=RecommendationPriority.HIGH,
                effort_hint=RecommendationEffort.MEDIUM,
                confidence_hint=0.85,
                policy_reference=_DETERMINISTIC,
                evaluation_order=60,
                tags=("grounding", "unsupported"),
            ),
            RecommendationRule(
                rule_id="RC-GRD-002",
                rule_name="Resolve the contradicted requirement",
                category=RecommendationRuleCategory.GROUNDING_CONTRADICTED,
                source_subsystem=RecommendationSource.GROUNDING,
                recommendation_type=RecommendationType.RESOLVE_CONFLICT,
                guidance=(
                    "Reconcile the requirement with the evidence it contradicts, "
                    "or remove the requirement."
                ),
                priority_hint=RecommendationPriority.CRITICAL,
                effort_hint=RecommendationEffort.HIGH,
                confidence_hint=0.90,
                policy_reference=_DETERMINISTIC,
                evaluation_order=70,
                tags=("grounding", "contradiction"),
            ),
            # ---- Validation ---------------------------------------------------------
            RecommendationRule(
                rule_id="RC-VAL-001",
                rule_name="Review the informational validation issue",
                category=RecommendationRuleCategory.VALIDATION_ISSUE_INFO,
                source_subsystem=RecommendationSource.VALIDATION,
                recommendation_type=RecommendationType.ADDRESS_VALIDATION_ISSUE,
                guidance="Review the informational validation issue; no urgent action required.",
                priority_hint=RecommendationPriority.LOW,
                effort_hint=RecommendationEffort.TRIVIAL,
                confidence_hint=0.60,
                policy_reference=_DETERMINISTIC,
                evaluation_order=80,
                tags=("validation", "info"),
            ),
            RecommendationRule(
                rule_id="RC-VAL-002",
                rule_name="Address the validation warning",
                category=RecommendationRuleCategory.VALIDATION_ISSUE_WARNING,
                source_subsystem=RecommendationSource.VALIDATION,
                recommendation_type=RecommendationType.ADDRESS_VALIDATION_ISSUE,
                guidance="Address the warning-level validation issue.",
                priority_hint=RecommendationPriority.MEDIUM,
                effort_hint=RecommendationEffort.LOW,
                confidence_hint=0.75,
                policy_reference=_DETERMINISTIC,
                evaluation_order=90,
                tags=("validation", "warning"),
            ),
            RecommendationRule(
                rule_id="RC-VAL-003",
                rule_name="Resolve the validation error",
                category=RecommendationRuleCategory.VALIDATION_ISSUE_ERROR,
                source_subsystem=RecommendationSource.VALIDATION,
                recommendation_type=RecommendationType.ADDRESS_VALIDATION_ISSUE,
                guidance="Resolve the error-level validation issue before proceeding.",
                priority_hint=RecommendationPriority.HIGH,
                effort_hint=RecommendationEffort.MEDIUM,
                confidence_hint=0.85,
                policy_reference=_DETERMINISTIC,
                evaluation_order=100,
                tags=("validation", "error"),
            ),
            RecommendationRule(
                rule_id="RC-VAL-004",
                rule_name="Resolve the critical validation issue",
                category=RecommendationRuleCategory.VALIDATION_ISSUE_CRITICAL,
                source_subsystem=RecommendationSource.VALIDATION,
                recommendation_type=RecommendationType.ADDRESS_VALIDATION_ISSUE,
                guidance="Resolve the critical validation issue; the response is unsafe otherwise.",
                priority_hint=RecommendationPriority.CRITICAL,
                effort_hint=RecommendationEffort.HIGH,
                confidence_hint=0.95,
                policy_reference=_DETERMINISTIC,
                evaluation_order=110,
                tags=("validation", "critical"),
            ),
            # ---- CP1 ------------------------------------------------------------------
            RecommendationRule(
                rule_id="RC-CP1-001",
                rule_name="Author the missing engineering-readiness requirement",
                category=RecommendationRuleCategory.CP1_FINDING_FAIL,
                source_subsystem=RecommendationSource.CP1,
                recommendation_type=RecommendationType.ADD_REQUIREMENT,
                guidance="Author the requirement needed to close the blocking readiness gap.",
                priority_hint=RecommendationPriority.HIGH,
                effort_hint=RecommendationEffort.HIGH,
                confidence_hint=0.90,
                policy_reference=_DETERMINISTIC,
                evaluation_order=120,
                tags=("cp1", "blocking"),
            ),
            RecommendationRule(
                rule_id="RC-CP1-002",
                rule_name="Address the engineering-readiness gap",
                category=RecommendationRuleCategory.CP1_FINDING_WARN,
                source_subsystem=RecommendationSource.CP1,
                recommendation_type=RecommendationType.ADDRESS_ENGINEERING_GAP,
                guidance="Address the warn-level engineering-readiness gap.",
                priority_hint=RecommendationPriority.MEDIUM,
                effort_hint=RecommendationEffort.MEDIUM,
                confidence_hint=0.75,
                policy_reference=_DETERMINISTIC,
                evaluation_order=130,
                tags=("cp1", "warn"),
            ),
            # ---- Quality Governance findings ------------------------------------------
            RecommendationRule(
                rule_id="RC-QUA-001",
                rule_name="Review the informational quality finding",
                category=RecommendationRuleCategory.QUALITY_FINDING_INFO,
                source_subsystem=RecommendationSource.QUALITY_GOVERNANCE,
                recommendation_type=RecommendationType.IMPROVE_QUALITY_SCORE,
                guidance="Review the informational quality finding; no urgent action required.",
                priority_hint=RecommendationPriority.LOW,
                effort_hint=RecommendationEffort.TRIVIAL,
                confidence_hint=0.60,
                policy_reference=_DETERMINISTIC,
                evaluation_order=140,
                tags=("quality_governance", "info"),
            ),
            RecommendationRule(
                rule_id="RC-QUA-002",
                rule_name="Address the quality warning",
                category=RecommendationRuleCategory.QUALITY_FINDING_WARNING,
                source_subsystem=RecommendationSource.QUALITY_GOVERNANCE,
                recommendation_type=RecommendationType.IMPROVE_QUALITY_SCORE,
                guidance="Address the warning-level quality finding to improve the release grade.",
                priority_hint=RecommendationPriority.MEDIUM,
                effort_hint=RecommendationEffort.LOW,
                confidence_hint=0.75,
                policy_reference=_DETERMINISTIC,
                evaluation_order=150,
                tags=("quality_governance", "warning"),
            ),
            RecommendationRule(
                rule_id="RC-QUA-003",
                rule_name="Resolve the quality failure",
                category=RecommendationRuleCategory.QUALITY_FINDING_FAILURE,
                source_subsystem=RecommendationSource.QUALITY_GOVERNANCE,
                recommendation_type=RecommendationType.IMPROVE_QUALITY_SCORE,
                guidance="Resolve the failure-level quality finding; it blocks release.",
                priority_hint=RecommendationPriority.HIGH,
                effort_hint=RecommendationEffort.HIGH,
                confidence_hint=0.90,
                policy_reference=_DETERMINISTIC,
                evaluation_order=160,
                tags=("quality_governance", "failure"),
            ),
            # ---- Quality Governance decision -------------------------------------------
            RecommendationRule(
                rule_id="RC-QUA-004",
                rule_name="Resolve the blocking release decision",
                category=RecommendationRuleCategory.QUALITY_DECISION_FAIL,
                source_subsystem=RecommendationSource.QUALITY_GOVERNANCE,
                recommendation_type=RecommendationType.IMPROVE_QUALITY_SCORE,
                guidance="Resolve every mandatory quality finding blocking this release decision.",
                priority_hint=RecommendationPriority.CRITICAL,
                effort_hint=RecommendationEffort.HIGH,
                confidence_hint=0.95,
                policy_reference=_DETERMINISTIC,
                evaluation_order=170,
                tags=("quality_governance", "decision", "fail"),
            ),
            RecommendationRule(
                rule_id="RC-QUA-005",
                rule_name="Clear the release warnings",
                category=RecommendationRuleCategory.QUALITY_DECISION_PASS_WITH_WARNINGS,
                source_subsystem=RecommendationSource.QUALITY_GOVERNANCE,
                recommendation_type=RecommendationType.IMPROVE_QUALITY_SCORE,
                guidance="Clear the recorded warnings to reach a clean release decision.",
                priority_hint=RecommendationPriority.MEDIUM,
                effort_hint=RecommendationEffort.MEDIUM,
                confidence_hint=0.80,
                policy_reference=_DETERMINISTIC,
                evaluation_order=180,
                tags=("quality_governance", "decision", "warnings"),
            ),
        )
        return RecommendationRuleCatalog(
            catalog_version=RECOMMENDATION_RULE_CATALOG_VERSION, rules=rules
        )


def default_recommendation_rule_catalog() -> RecommendationRuleCatalog:
    """Return the framework's default governed rule catalogue."""
    return RecommendationRuleBuilder().build()
