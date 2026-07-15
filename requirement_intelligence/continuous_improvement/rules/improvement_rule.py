"""The canonical governed :class:`ImprovementRule` and its controlled vocabularies
(CAP-083B).

An ``ImprovementRule`` is **metadata only** — the governed declaration of *which*
family of observation a rule belongs to (recurrence, trend, or opportunity),
*which* Layer 1 subsystem it concerns, *which* governed vocabulary member it
names, and *which* policy switch gates it. It carries **no executable
behaviour**: no lambda, no callback, no embedded algorithm, no threshold value.
The :class:`~requirement_intelligence.continuous_improvement.engine.
DeterministicContinuousImprovementEngine` owns the behaviour; a rule only *names*
it — exactly mirroring how ``RecommendationRule`` relates to its deterministic
engine (ADR-0019) and ``QualityRule`` relates to its evaluator (ADR-0017 §D25).

Because a rule is data, adding, removing, or retuning a rule is a versioned
catalogue change (an ``ImprovementRuleBuilder`` edit), never an engine code
change (Recommendation 6 of ADR-0022, mirroring ADR-0019 Recommendation 3/5).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.continuous_improvement.identity import ImprovementRuleVersion
from requirement_intelligence.continuous_improvement.models.enums import (
    ImprovementFindingCategory,
    ImprovementOpportunityCategory,
    ImprovementSeverity,
    ImprovementSourceLayer,
)
from shared.contracts.base import Schema

#: Version of the governed ``ImprovementRule`` **schema** (CAP-083B foundation).
IMPROVEMENT_RULE_VERSION = ImprovementRuleVersion(1, 0, 0)


class ImprovementRuleFamily(StrEnum):
    """Which of the three CAP-083B capability lanes a rule belongs to.

    Mirrors ``EnhancementRuleCategory`` (ADR-0018): a fixed, governed
    classification the engine dispatches on, never a computation.
    """

    RECURRENCE = "recurrence"
    TREND = "trend"
    OPPORTUNITY = "opportunity"


class ImprovementPolicyToggle(StrEnum):
    """A governed ``ImprovementCapabilitySwitches`` field that gates a rule.

    Names the switch rather than the rule reading it directly, so retuning which
    capability gates a rule is a catalogue change, and flipping the switch itself
    is a policy change — neither is an engine change (mirrors
    ``RecommendationPolicyToggle``, ADR-0019).
    """

    ENABLE_RECURRING_FINDING_DETECTION = "enable_recurring_finding_detection"
    ENABLE_TREND_DETECTION = "enable_trend_detection"
    ENABLE_OPPORTUNITY_GENERATION = "enable_opportunity_generation"


class ImprovementRule(Schema):
    """One governed improvement rule — immutable metadata, no behaviour.

    A rule declares the family it belongs to (:attr:`family`), the Layer 1
    subsystem it concerns (:attr:`source_subsystem`), the governed vocabulary
    member(s) it names, and the policy switch that gates it
    (:attr:`policy_reference`). It carries no executable logic; the engine
    resolves the switch, matches evidence to a rule, and applies the named
    hints.

    Shape by family (enforced by the validator, never by the engine):

    * ``RECURRENCE`` — names :attr:`finding_category` and :attr:`severity_hint`;
      never :attr:`opportunity_category` or :attr:`metric_name`.
    * ``TREND`` — names :attr:`metric_name`; never :attr:`finding_category`,
      :attr:`opportunity_category`, or :attr:`severity_hint`.
    * ``OPPORTUNITY`` — names :attr:`opportunity_category` and exactly one of
      :attr:`finding_category` (the recurrence this opportunity aggregates) or
      :attr:`metric_name` (the trend this opportunity aggregates); never
      :attr:`severity_hint`.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    rule_id: str = Field(
        ...,
        min_length=1,
        pattern=r"^[A-Z0-9][A-Z0-9._:-]*$",
        description="Stable, governed rule identity (e.g. 'IR-REC-001').",
    )
    rule_version: ImprovementRuleVersion = Field(
        default=IMPROVEMENT_RULE_VERSION, description="Version of this rule's definition."
    )
    rule_name: str = Field(..., min_length=1, description="Human-readable rule name (a title).")
    family: ImprovementRuleFamily = Field(
        ..., description="Which capability lane this rule governs."
    )
    source_subsystem: ImprovementSourceLayer = Field(
        ..., description="The Layer 1 subsystem this rule concerns."
    )
    finding_category: ImprovementFindingCategory | None = Field(
        default=None,
        description=(
            "For RECURRENCE: the finding category this rule names. For "
            "OPPORTUNITY: the finding category this opportunity aggregates."
        ),
    )
    opportunity_category: ImprovementOpportunityCategory | None = Field(
        default=None, description="For OPPORTUNITY: the opportunity category this rule names."
    )
    metric_name: str | None = Field(
        default=None,
        description=(
            "For TREND: the governed metric this rule watches. For OPPORTUNITY: "
            "the trend metric this opportunity aggregates."
        ),
    )
    severity_hint: ImprovementSeverity | None = Field(
        default=None,
        description="For RECURRENCE: the governed severity a matching finding carries.",
    )
    guidance: str = Field(
        ...,
        min_length=1,
        description="What this rule represents and what a matching observation means.",
    )
    policy_reference: ImprovementPolicyToggle = Field(
        ..., description="The governed ImprovementPolicy switch that gates this rule."
    )
    enabled: bool = Field(default=True, description="Whether the catalogue evaluates this rule.")
    evaluation_order: int = Field(
        ..., ge=0, description="Deterministic ordering key within the catalogue."
    )
    tags: tuple[str, ...] = Field(default=(), description="Governed classification tags.")

    @model_validator(mode="after")
    def _validate_rule(self) -> ImprovementRule:
        """Enforce the per-family shape invariants — no value is computed."""
        if self.family == ImprovementRuleFamily.RECURRENCE:
            if self.finding_category is None or self.severity_hint is None:
                raise ValueError(
                    f"Rule '{self.rule_id}' is RECURRENCE but is missing finding_category "
                    f"and/or severity_hint."
                )
            if self.opportunity_category is not None or self.metric_name is not None:
                raise ValueError(
                    f"Rule '{self.rule_id}' is RECURRENCE but names opportunity_category "
                    f"or metric_name; it must name neither."
                )
        elif self.family == ImprovementRuleFamily.TREND:
            if self.metric_name is None:
                raise ValueError(f"Rule '{self.rule_id}' is TREND but names no metric_name.")
            if (
                self.finding_category is not None
                or self.opportunity_category is not None
                or self.severity_hint is not None
            ):
                raise ValueError(
                    f"Rule '{self.rule_id}' is TREND but names finding_category, "
                    f"opportunity_category, or severity_hint; it must name none of those."
                )
        else:  # OPPORTUNITY
            if self.opportunity_category is None:
                raise ValueError(
                    f"Rule '{self.rule_id}' is OPPORTUNITY but names no opportunity_category."
                )
            names_finding = self.finding_category is not None
            names_metric = self.metric_name is not None
            if names_finding == names_metric:
                raise ValueError(
                    f"Rule '{self.rule_id}' is OPPORTUNITY but must name exactly one of "
                    f"finding_category or metric_name (named: finding={names_finding}, "
                    f"metric={names_metric})."
                )
            if self.severity_hint is not None:
                raise ValueError(
                    f"Rule '{self.rule_id}' is OPPORTUNITY but names severity_hint; it must not."
                )
        return self
