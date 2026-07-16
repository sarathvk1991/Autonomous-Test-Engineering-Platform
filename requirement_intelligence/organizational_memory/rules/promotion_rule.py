"""The canonical governed :class:`PromotionRule` and its controlled
vocabularies (CAP-085B).

A ``PromotionRule`` is **metadata only** — the governed declaration of *which*
category of Organizational Memory behaviour a rule concerns, *which* hierarchy
level it supports, and *which* policy switch gates it. It carries **no
executable behaviour**: no lambda, no callback, no embedded algorithm, and no
threshold value that itself executes anything — every numeric threshold a
future engine actually enforces remains owned exclusively by
:class:`~requirement_intelligence.organizational_memory.policy.
organizational_memory_policy.OrganizationalMemoryThresholds` (ADR-0027 §D6/D14,
Recommendation 16). The deterministic engine's collaborators own the
behaviour; a rule only *names* it — exactly mirroring how the Continuous
Improvement Framework's own governed rule relates to its deterministic engine
(ADR-0022) and the Knowledge Graph Framework's own governed rule relates to
its deterministic engine (ADR-0023).

Because a rule is data, adding, removing, or retuning a rule is a versioned
catalogue change (a ``PromotionRuleBuilder`` edit), never an engine code
change (mirrors ADR-0022 Recommendation 6, ADR-0023 rule catalogue precedent).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.organizational_memory.identity import PromotionRuleVersion
from shared.contracts.base import Schema

#: Version of the governed ``PromotionRule`` **schema** (CAP-085B foundation).
PROMOTION_RULE_VERSION = PromotionRuleVersion(1, 0, 0)


class PromotionRuleCategory(StrEnum):
    """Which of the ten CAP-085B governance lanes a rule belongs to (ADR-0027
    §Stage 1 of the CAP-085B brief).

    A fixed, governed classification a future engine may dispatch on, never a
    computation performed by the rule itself.
    """

    EXPERIENCE_CAPTURE = "experience_capture"
    EXPERIENCE_CONSOLIDATION = "experience_consolidation"
    LESSON_GENERATION = "lesson_generation"
    LESSON_CONSOLIDATION = "lesson_consolidation"
    BEST_PRACTICE_GENERATION = "best_practice_generation"
    PROMOTION = "promotion"
    LIFECYCLE = "lifecycle"
    EXPLAINABILITY = "explainability"
    DETERMINISM = "determinism"
    STRUCTURAL_INTEGRITY = "structural_integrity"


class PromotionHierarchyLevel(StrEnum):
    """The governed knowledge-hierarchy level a rule supports (ADR-0026 §Stage
    2, ADR-0027 §D10).

    Names one rung of the frozen ``Experience → Lesson → Best Practice``
    hierarchy, or the ``Promotion``/``Lifecycle`` record types that describe
    transitions across it — never a level the rule may skip to.
    """

    EXPERIENCE = "experience"
    LESSON = "lesson"
    BEST_PRACTICE = "best_practice"
    PROMOTION = "promotion"
    LIFECYCLE = "lifecycle"


class OrganizationalMemoryPolicyToggle(StrEnum):
    """A governed ``OrganizationalMemoryCapabilitySwitches`` field that gates a rule.

    Names the switch rather than the rule reading it directly, so retuning
    which capability gates a rule is a catalogue change, and flipping the
    switch itself is a policy change — neither is an engine change (mirrors
    ``ImprovementPolicyToggle``, ADR-0022; ``KnowledgeGraphPolicyToggle``,
    ADR-0023).
    """

    ENABLE_EXPERIENCE_CAPTURE = "enable_experience_capture"
    ENABLE_LESSON_PROMOTION = "enable_lesson_promotion"
    ENABLE_BEST_PRACTICE_PROMOTION = "enable_best_practice_promotion"
    ENABLE_RETIREMENT = "enable_retirement"


class PromotionRule(Schema):
    """One governed Organizational Memory rule — immutable metadata, no behaviour.

    A rule declares the category it belongs to (:attr:`category`), the
    hierarchy level it supports (:attr:`supported_hierarchy_level`), and the
    policy switch that gates it (:attr:`capability_switch`). It carries no
    executable logic, and — deliberately, unlike a numeric policy threshold —
    it carries no threshold value at all: every governed number a future
    engine reads comes from ``OrganizationalMemoryPolicy.thresholds`` alone
    (Recommendation 16 of ADR-0027).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    rule_id: str = Field(
        ...,
        min_length=1,
        pattern=r"^[A-Z0-9][A-Z0-9._:-]*$",
        description="Stable, governed rule identity (e.g. 'OM-EXP-001').",
    )
    rule_version: PromotionRuleVersion = Field(
        default=PROMOTION_RULE_VERSION, description="Version of this rule's definition."
    )
    title: str = Field(..., min_length=1, description="Human-readable rule title.")
    description: str = Field(
        ..., min_length=1, description="What this rule represents and what it governs."
    )
    category: PromotionRuleCategory = Field(
        ..., description="Which of the ten governed lanes this rule belongs to."
    )
    priority: int = Field(
        ..., ge=0, description="Deterministic priority among rules of the same category."
    )
    capability_switch: OrganizationalMemoryPolicyToggle = Field(
        ..., description="The governed OrganizationalMemoryPolicy switch that gates this rule."
    )
    supported_hierarchy_level: PromotionHierarchyLevel = Field(
        ..., description="The governed knowledge-hierarchy level this rule supports."
    )
    documentation_reference: str = Field(
        ..., min_length=1, description="The ADR/proposal section this rule is governed by."
    )
    enabled: bool = Field(default=True, description="Whether the catalogue evaluates this rule.")
    evaluation_order: int = Field(
        ..., ge=0, description="Deterministic ordering key within the catalogue."
    )
