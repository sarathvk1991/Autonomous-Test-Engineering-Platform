"""The canonical governed :class:`RecommendationRule` and its controlled vocabularies
(CAP-082B).

A ``RecommendationRule`` is **metadata only** — the governed declaration of *what*
shape of upstream evidence a rule covers, *which* upstream subsystem it concerns,
*what* action it suggests, and *which* governed policy switch gates it. It carries
**no executable behaviour**: no lambda, no callable, no comparison, no embedded
algorithm. The :class:`~requirement_intelligence.recommendation.engine.
DeterministicRecommendationEngine` owns the behaviour; a rule only *names* it —
exactly mirroring how ``QualityRule`` relates to its deterministic Quality Governance
rule evaluator (ADR-0017 §D25) and ``EnhancementRule`` to its deterministic engine
(ADR-0018).

The declaration is fully governed and deterministic:

* :class:`RecommendationRuleCategory` — the specific shape of upstream evidence the
  rule covers (an enhancement observation category, a grounding hallucination
  classification, a validation severity, a CP1 verdict contribution, a quality
  finding severity, or a quality release decision). The engine dispatches a
  candidate to exactly one category; the category never implies a priority — only
  which rule applies.
* :class:`RecommendationPolicyToggle` — which governed
  ``RecommendationCapabilitySwitches`` field gates this rule at generation time; a
  disabled toggle makes the engine skip every rule naming it entirely (no output,
  not an error) — mirroring ``EnhancementCapabilityToggle`` / ``governing_toggle``
  (ADR-0017 §D25).

Because a rule is data, adding, removing, or retuning a rule is a versioned
catalogue change (a ``RecommendationRuleBuilder`` edit), never an engine code
change (Recommendation 3/5, ADR-0019).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.recommendation.identity.recommendation_identity import (
    RecommendationRuleVersion,
)
from requirement_intelligence.recommendation.models.enums import (
    RecommendationEffort,
    RecommendationPriority,
    RecommendationSource,
    RecommendationType,
)
from shared.contracts.base import Schema

#: Version of the governed ``RecommendationRule`` **schema** (CAP-082B foundation).
RECOMMENDATION_RULE_VERSION = RecommendationRuleVersion(1, 0, 0)


class RecommendationRuleCategory(StrEnum):
    """The specific shape of upstream evidence a :class:`RecommendationRule` covers.

    Each member names one deterministically distinguishable condition the engine can
    observe on a completed upstream result — never a priority, and never a
    computation. The engine's only use of this vocabulary is dispatch: given one
    piece of upstream evidence, which single category (and therefore which single
    governed rule) applies.
    """

    ENHANCEMENT_DEPENDENCY_GAP = "enhancement_dependency_gap"
    ENHANCEMENT_DUPLICATE_REQUIREMENT = "enhancement_duplicate_requirement"
    ENHANCEMENT_CONSISTENCY_WARNING = "enhancement_consistency_warning"
    ENHANCEMENT_CONSISTENCY_CRITICAL = "enhancement_consistency_critical"
    ENHANCEMENT_TRACEABILITY_GAP = "enhancement_traceability_gap"

    GROUNDING_UNSUPPORTED = "grounding_unsupported"
    GROUNDING_CONTRADICTED = "grounding_contradicted"

    VALIDATION_ISSUE_INFO = "validation_issue_info"
    VALIDATION_ISSUE_WARNING = "validation_issue_warning"
    VALIDATION_ISSUE_ERROR = "validation_issue_error"
    VALIDATION_ISSUE_CRITICAL = "validation_issue_critical"

    CP1_FINDING_FAIL = "cp1_finding_fail"
    CP1_FINDING_WARN = "cp1_finding_warn"

    QUALITY_FINDING_INFO = "quality_finding_info"
    QUALITY_FINDING_WARNING = "quality_finding_warning"
    QUALITY_FINDING_FAILURE = "quality_finding_failure"

    QUALITY_DECISION_FAIL = "quality_decision_fail"
    QUALITY_DECISION_PASS_WITH_WARNINGS = "quality_decision_pass_with_warnings"  # noqa: S105


#: The upstream subsystem each :class:`RecommendationRuleCategory` belongs to — a
#: fixed, governed lookup, never a computation. Enforced as a shape invariant by
#: :meth:`RecommendationRule._validate_rule` (mirroring ``EnhancementRule``'s
#: ``_MECHANISM_CATEGORY`` invariant, ADR-0018).
_CATEGORY_SOURCE: dict[RecommendationRuleCategory, RecommendationSource] = {
    RecommendationRuleCategory.ENHANCEMENT_DEPENDENCY_GAP: RecommendationSource.ENHANCEMENT,
    RecommendationRuleCategory.ENHANCEMENT_DUPLICATE_REQUIREMENT: RecommendationSource.ENHANCEMENT,
    RecommendationRuleCategory.ENHANCEMENT_CONSISTENCY_WARNING: RecommendationSource.ENHANCEMENT,
    RecommendationRuleCategory.ENHANCEMENT_CONSISTENCY_CRITICAL: RecommendationSource.ENHANCEMENT,
    RecommendationRuleCategory.ENHANCEMENT_TRACEABILITY_GAP: RecommendationSource.ENHANCEMENT,
    RecommendationRuleCategory.GROUNDING_UNSUPPORTED: RecommendationSource.GROUNDING,
    RecommendationRuleCategory.GROUNDING_CONTRADICTED: RecommendationSource.GROUNDING,
    RecommendationRuleCategory.VALIDATION_ISSUE_INFO: RecommendationSource.VALIDATION,
    RecommendationRuleCategory.VALIDATION_ISSUE_WARNING: RecommendationSource.VALIDATION,
    RecommendationRuleCategory.VALIDATION_ISSUE_ERROR: RecommendationSource.VALIDATION,
    RecommendationRuleCategory.VALIDATION_ISSUE_CRITICAL: RecommendationSource.VALIDATION,
    RecommendationRuleCategory.CP1_FINDING_FAIL: RecommendationSource.CP1,
    RecommendationRuleCategory.CP1_FINDING_WARN: RecommendationSource.CP1,
    RecommendationRuleCategory.QUALITY_FINDING_INFO: RecommendationSource.QUALITY_GOVERNANCE,
    RecommendationRuleCategory.QUALITY_FINDING_WARNING: RecommendationSource.QUALITY_GOVERNANCE,
    RecommendationRuleCategory.QUALITY_FINDING_FAILURE: RecommendationSource.QUALITY_GOVERNANCE,
    RecommendationRuleCategory.QUALITY_DECISION_FAIL: RecommendationSource.QUALITY_GOVERNANCE,
    RecommendationRuleCategory.QUALITY_DECISION_PASS_WITH_WARNINGS: (
        RecommendationSource.QUALITY_GOVERNANCE
    ),
}


class RecommendationPolicyToggle(StrEnum):
    """A governed ``RecommendationCapabilitySwitches`` field that gates a rule.

    Names the switch rather than the rule reading it directly, so retuning which
    capability gates a rule is a catalogue change, and flipping the switch itself is
    a policy change — neither is an engine change (mirrors
    ``EnhancementCapabilityToggle`` / ``QualityReleaseToggle``).
    """

    ENABLE_DETERMINISTIC_ENGINE = "enable_deterministic_engine"
    ENABLE_ML_ENGINE = "enable_ml_engine"
    ENABLE_LLM_ENGINE = "enable_llm_engine"


class RecommendationRule(Schema):
    """One governed recommendation rule — immutable metadata, no behaviour.

    A rule declares the specific shape of upstream evidence it covers
    (:attr:`category`), the upstream subsystem it concerns (:attr:`source_subsystem`),
    the governed action it suggests (:attr:`recommendation_type`), the deterministic
    hints a future recommendation is populated with (:attr:`priority_hint`,
    :attr:`effort_hint`, :attr:`confidence_hint`), whether the catalogue evaluates it
    (:attr:`enabled`), and the governed policy switch that gates it
    (:attr:`policy_reference`). It carries no executable logic; the engine resolves
    the switch, matches evidence to a category, and applies the named hints —
    final priority is governed further by ``RecommendationPolicy`` (Recommendation 9),
    never invented by the rule or by the engine's source dispatch.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    rule_id: str = Field(
        ...,
        min_length=1,
        pattern=r"^[A-Z0-9][A-Z0-9._:-]*$",
        description="Stable, governed rule identity (e.g. 'RC-ENH-001').",
    )
    rule_version: RecommendationRuleVersion = Field(
        default=RECOMMENDATION_RULE_VERSION, description="Version of this rule's definition."
    )
    rule_name: str = Field(..., min_length=1, description="Human-readable rule name (a title).")
    category: RecommendationRuleCategory = Field(
        ..., description="The specific shape of upstream evidence this rule covers."
    )
    source_subsystem: RecommendationSource = Field(
        ..., description="The upstream subsystem this rule concerns."
    )
    recommendation_type: RecommendationType = Field(
        ..., description="The governed action a matching recommendation suggests."
    )
    guidance: str = Field(
        ..., min_length=1, description="What should be done when this rule matches (a description)."
    )
    priority_hint: RecommendationPriority = Field(
        ..., description="The governed base priority a matching recommendation carries."
    )
    effort_hint: RecommendationEffort = Field(
        ..., description="The governed estimated effort a matching recommendation carries."
    )
    confidence_hint: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="The governed base confidence a matching recommendation carries.",
    )
    enabled: bool = Field(default=True, description="Whether the catalogue evaluates this rule.")
    policy_reference: RecommendationPolicyToggle = Field(
        ..., description="The governed RecommendationPolicy switch that gates this rule."
    )
    evaluation_order: int = Field(
        ..., ge=0, description="Deterministic ordering key within the catalogue."
    )
    tags: tuple[str, ...] = Field(default=(), description="Governed classification tags.")

    @model_validator(mode="after")
    def _validate_rule(self) -> RecommendationRule:
        """The category must belong to the declared source — a shape invariant only."""
        expected = _CATEGORY_SOURCE[self.category]
        if expected != self.source_subsystem:
            raise ValueError(
                f"Rule '{self.rule_id}' names category {self.category!r} which belongs to "
                f"source {expected!r}, not the declared {self.source_subsystem!r}."
            )
        return self
