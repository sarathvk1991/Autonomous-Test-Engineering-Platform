"""Builder for the governed default :class:`ImprovementRuleCatalog` (CAP-083B).

Construction only. It assembles the framework's default governed rule
catalogue — a deterministic, immutable value — and rejects nothing beyond the
models' own field and invariant constraints. It observes nothing, reads no
Historical Dataset, and has no runtime consumers.

The catalogue is **governed data**. Future rule additions, removals, or
retunings require only a builder change, never an engine code change (mirrors
ADR-0019 Recommendation 3/5).

The default catalogue spans all six governed :class:`ImprovementSourceLayer`
values across the three capability families: five RECURRENCE rules (one per
finding category), six TREND rules (one per source), and five OPPORTUNITY
rules (one per opportunity category, several sourced from a second subsystem).
"""

from __future__ import annotations

from requirement_intelligence.continuous_improvement.models.enums import (
    ImprovementFindingCategory,
    ImprovementOpportunityCategory,
    ImprovementSeverity,
    ImprovementSourceLayer,
)
from requirement_intelligence.continuous_improvement.rules.improvement_rule import (
    ImprovementPolicyToggle,
    ImprovementRule,
    ImprovementRuleFamily,
)
from requirement_intelligence.continuous_improvement.rules.improvement_rule_catalog import (
    IMPROVEMENT_RULE_CATALOG_VERSION,
    ImprovementRuleCatalog,
)

_RECURRENCE = ImprovementPolicyToggle.ENABLE_RECURRING_FINDING_DETECTION
_TREND = ImprovementPolicyToggle.ENABLE_TREND_DETECTION
_OPPORTUNITY = ImprovementPolicyToggle.ENABLE_OPPORTUNITY_GENERATION


class ImprovementRuleBuilder:
    """Assemble the governed default :class:`ImprovementRuleCatalog`."""

    def build(self) -> ImprovementRuleCatalog:
        """Return the framework's default governed rule catalogue, in canonical order."""
        rules = (
            # ---- Recurrence ---------------------------------------------------------
            ImprovementRule(
                rule_id="IR-REC-001",
                rule_name="Recurring validation failure",
                family=ImprovementRuleFamily.RECURRENCE,
                source_subsystem=ImprovementSourceLayer.VALIDATION,
                finding_category=ImprovementFindingCategory.RECURRING_VALIDATION_FAILURE,
                severity_hint=ImprovementSeverity.WARNING,
                guidance="A validation failure has recurred across the historical dataset.",
                policy_reference=_RECURRENCE,
                evaluation_order=10,
                tags=("recurrence", "validation"),
            ),
            ImprovementRule(
                rule_id="IR-REC-002",
                rule_name="Recurring grounding contradiction",
                family=ImprovementRuleFamily.RECURRENCE,
                source_subsystem=ImprovementSourceLayer.GROUNDING,
                finding_category=ImprovementFindingCategory.RECURRING_GROUNDING_CONTRADICTION,
                severity_hint=ImprovementSeverity.CRITICAL,
                guidance="A grounding contradiction has recurred across the historical dataset.",
                policy_reference=_RECURRENCE,
                evaluation_order=20,
                tags=("recurrence", "grounding"),
            ),
            ImprovementRule(
                rule_id="IR-REC-003",
                rule_name="Recurring governance failure",
                family=ImprovementRuleFamily.RECURRENCE,
                source_subsystem=ImprovementSourceLayer.QUALITY_GOVERNANCE,
                finding_category=ImprovementFindingCategory.RECURRING_GOVERNANCE_FAILURE,
                severity_hint=ImprovementSeverity.CRITICAL,
                guidance="A governance failure has recurred across the historical dataset.",
                policy_reference=_RECURRENCE,
                evaluation_order=30,
                tags=("recurrence", "quality_governance"),
            ),
            ImprovementRule(
                rule_id="IR-REC-004",
                rule_name="Recurring recommendation",
                family=ImprovementRuleFamily.RECURRENCE,
                source_subsystem=ImprovementSourceLayer.RECOMMENDATION,
                finding_category=ImprovementFindingCategory.RECURRING_RECOMMENDATION,
                severity_hint=ImprovementSeverity.INFO,
                guidance="The same recommendation category has recurred across the dataset.",
                policy_reference=_RECURRENCE,
                evaluation_order=40,
                tags=("recurrence", "recommendation"),
            ),
            ImprovementRule(
                rule_id="IR-REC-005",
                rule_name="Recurring enhancement issue",
                family=ImprovementRuleFamily.RECURRENCE,
                source_subsystem=ImprovementSourceLayer.ENHANCEMENT,
                finding_category=ImprovementFindingCategory.RECURRING_ENHANCEMENT_ISSUE,
                severity_hint=ImprovementSeverity.WARNING,
                guidance="A requirement enhancement issue has recurred across the dataset.",
                policy_reference=_RECURRENCE,
                evaluation_order=50,
                tags=("recurrence", "enhancement"),
            ),
            # ---- Trend ----------------------------------------------------------------
            ImprovementRule(
                rule_id="IR-TRD-001",
                rule_name="Grounding score trend",
                family=ImprovementRuleFamily.TREND,
                source_subsystem=ImprovementSourceLayer.GROUNDING,
                metric_name="groundingScore",
                guidance="Observe the direction of the grounding score across the dataset.",
                policy_reference=_TREND,
                evaluation_order=60,
                tags=("trend", "grounding"),
            ),
            ImprovementRule(
                rule_id="IR-TRD-002",
                rule_name="Quality score trend",
                family=ImprovementRuleFamily.TREND,
                source_subsystem=ImprovementSourceLayer.QUALITY_GOVERNANCE,
                metric_name="qualityScore",
                guidance="Observe the direction of the quality score across the dataset.",
                policy_reference=_TREND,
                evaluation_order=70,
                tags=("trend", "quality_governance"),
            ),
            ImprovementRule(
                rule_id="IR-TRD-003",
                rule_name="Validation health trend",
                family=ImprovementRuleFamily.TREND,
                source_subsystem=ImprovementSourceLayer.VALIDATION,
                metric_name="validationHealthScore",
                guidance="Observe the direction of validation health across the dataset.",
                policy_reference=_TREND,
                evaluation_order=80,
                tags=("trend", "validation"),
            ),
            ImprovementRule(
                rule_id="IR-TRD-004",
                rule_name="Engineering readiness trend",
                family=ImprovementRuleFamily.TREND,
                source_subsystem=ImprovementSourceLayer.CP1,
                metric_name="engineeringReadinessScore",
                guidance="Observe the direction of engineering readiness across the dataset.",
                policy_reference=_TREND,
                evaluation_order=90,
                tags=("trend", "cp1"),
            ),
            ImprovementRule(
                rule_id="IR-TRD-005",
                rule_name="Recommendation density trend",
                family=ImprovementRuleFamily.TREND,
                source_subsystem=ImprovementSourceLayer.RECOMMENDATION,
                metric_name="recommendationDensity",
                guidance="Observe the direction of recommendation density across the dataset.",
                policy_reference=_TREND,
                evaluation_order=100,
                tags=("trend", "recommendation"),
            ),
            ImprovementRule(
                rule_id="IR-TRD-006",
                rule_name="Enrichment coverage trend",
                family=ImprovementRuleFamily.TREND,
                source_subsystem=ImprovementSourceLayer.ENHANCEMENT,
                metric_name="enrichmentCoverage",
                guidance="Observe the direction of enrichment coverage across the dataset.",
                policy_reference=_TREND,
                evaluation_order=110,
                tags=("trend", "enhancement"),
            ),
            # ---- Opportunity ------------------------------------------------------------
            ImprovementRule(
                rule_id="IR-OPP-001",
                rule_name="Recurring documentation gap",
                family=ImprovementRuleFamily.OPPORTUNITY,
                source_subsystem=ImprovementSourceLayer.ENHANCEMENT,
                opportunity_category=ImprovementOpportunityCategory.RECURRING_DOCUMENTATION_GAP,
                finding_category=ImprovementFindingCategory.RECURRING_ENHANCEMENT_ISSUE,
                guidance="Address the recurring documentation gap this enhancement issue names.",
                policy_reference=_OPPORTUNITY,
                evaluation_order=120,
                tags=("opportunity", "enhancement"),
            ),
            ImprovementRule(
                rule_id="IR-OPP-002",
                rule_name="Recurring architecture weakness",
                family=ImprovementRuleFamily.OPPORTUNITY,
                source_subsystem=ImprovementSourceLayer.CP1,
                opportunity_category=ImprovementOpportunityCategory.RECURRING_ARCHITECTURE_WEAKNESS,
                metric_name="engineeringReadinessScore",
                guidance="Address the recurring architecture weakness this readiness trend names.",
                policy_reference=_OPPORTUNITY,
                evaluation_order=130,
                tags=("opportunity", "cp1"),
            ),
            ImprovementRule(
                rule_id="IR-OPP-003",
                rule_name="Recurring quality issue (governance)",
                family=ImprovementRuleFamily.OPPORTUNITY,
                source_subsystem=ImprovementSourceLayer.QUALITY_GOVERNANCE,
                opportunity_category=ImprovementOpportunityCategory.RECURRING_QUALITY_ISSUE,
                finding_category=ImprovementFindingCategory.RECURRING_GOVERNANCE_FAILURE,
                guidance="Address the recurring quality issue this governance failure names.",
                policy_reference=_OPPORTUNITY,
                evaluation_order=140,
                tags=("opportunity", "quality_governance"),
            ),
            ImprovementRule(
                rule_id="IR-OPP-004",
                rule_name="Recurring quality issue (validation)",
                family=ImprovementRuleFamily.OPPORTUNITY,
                source_subsystem=ImprovementSourceLayer.VALIDATION,
                opportunity_category=ImprovementOpportunityCategory.RECURRING_QUALITY_ISSUE,
                finding_category=ImprovementFindingCategory.RECURRING_VALIDATION_FAILURE,
                guidance="Address the recurring quality issue this validation failure names.",
                policy_reference=_OPPORTUNITY,
                evaluation_order=150,
                tags=("opportunity", "validation"),
            ),
            ImprovementRule(
                rule_id="IR-OPP-005",
                rule_name="Recurring recommendation category",
                family=ImprovementRuleFamily.OPPORTUNITY,
                source_subsystem=ImprovementSourceLayer.RECOMMENDATION,
                opportunity_category=ImprovementOpportunityCategory.RECURRING_RECOMMENDATION_CATEGORY,
                finding_category=ImprovementFindingCategory.RECURRING_RECOMMENDATION,
                guidance="Address the recurring recommendation category this finding names.",
                policy_reference=_OPPORTUNITY,
                evaluation_order=160,
                tags=("opportunity", "recommendation"),
            ),
        )
        return ImprovementRuleCatalog(catalog_version=IMPROVEMENT_RULE_CATALOG_VERSION, rules=rules)


def default_improvement_rule_catalog() -> ImprovementRuleCatalog:
    """Return the framework's default governed rule catalogue."""
    return ImprovementRuleBuilder().build()
