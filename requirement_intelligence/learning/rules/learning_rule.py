"""The canonical governed :class:`LearningRule` and its controlled
vocabularies (CAP-086B).

A ``LearningRule`` is **metadata only** — the governed declaration of *which*
category of Learning behaviour a rule concerns, *which* hierarchy level it
supports, and *which* policy switch gates it. It carries **no executable
behaviour**: no lambda, no callback, no embedded algorithm, and no threshold
value that itself executes anything — every numeric threshold a future
engine actually enforces remains owned exclusively by
:class:`~requirement_intelligence.learning.policy.learning_policy.
LearningThresholds` (ADR-0029 D6/D19, Recommendation 24/28). The
deterministic engine's collaborators own the behaviour; a rule only *names*
it — exactly mirroring how the Organizational Memory Framework's own
governed rule relates to its deterministic engine (ADR-0027).

Because a rule is data, adding, removing, or retuning a rule is a versioned
catalogue change (a ``LearningRuleBuilder`` edit), never an engine code
change (mirrors ADR-0022 Recommendation 6, ADR-0027 rule catalogue
precedent).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.learning.identity import LearningRuleVersion
from shared.contracts.base import Schema

#: Version of the governed ``LearningRule`` **schema** (CAP-086B foundation).
LEARNING_RULE_VERSION = LearningRuleVersion(1, 0, 0)


class LearningRuleCategory(StrEnum):
    """Which of the twelve CAP-086B governance lanes a rule belongs to —
    one per frozen collaborator (ADR-0029 D9/D10).

    A fixed, governed classification a future engine may dispatch on, never
    a computation performed by the rule itself.
    """

    CANDIDATE_COLLECTION = "candidate_collection"
    CANDIDATE_CONSOLIDATION = "candidate_consolidation"
    VALIDATION = "validation"
    LEARNING_GENERATION = "learning_generation"
    INSTITUTIONALIZATION = "institutionalization"
    STABILITY = "stability"
    CONFIDENCE = "confidence"
    PROMOTION = "promotion"
    LIFECYCLE = "lifecycle"
    EXPLAINABILITY = "explainability"
    DETERMINISM = "determinism"
    STRUCTURAL_INTEGRITY = "structural_integrity"


class LearningHierarchyLevel(StrEnum):
    """The governed knowledge-hierarchy level a rule supports (ADR-0028
    §Stage 2, ADR-0029 D11).

    Names one rung of the frozen ``Learning Candidate → Learning``
    hierarchy, or the record types (``Validation``, ``Confidence``,
    ``Promotion``, ``Lifecycle``) that describe decisions made about it —
    never a level the rule may skip to.
    """

    CANDIDATE = "candidate"
    LEARNING = "learning"
    VALIDATION = "validation"
    CONFIDENCE = "confidence"
    PROMOTION = "promotion"
    LIFECYCLE = "lifecycle"


class LearningPolicyToggle(StrEnum):
    """A governed ``LearningCapabilitySwitches`` field that gates a rule.

    Names the switch rather than the rule reading it directly, so retuning
    which capability gates a rule is a catalogue change, and flipping the
    switch itself is a policy change — neither is an engine change (mirrors
    ``OrganizationalMemoryPolicyToggle``, ADR-0027).
    """

    ENABLE_CANDIDATE_PROPOSAL = "enable_candidate_proposal"
    ENABLE_VALIDATION = "enable_validation"
    ENABLE_CONFIDENCE_RECORDING = "enable_confidence_recording"
    ENABLE_LIFECYCLE_RECORDING = "enable_lifecycle_recording"


class LearningRule(Schema):
    """One governed Learning rule — immutable metadata, no behaviour.

    A rule declares the category it belongs to (:attr:`category`), the
    hierarchy level it supports (:attr:`supported_hierarchy_level`), and the
    policy switch that gates it (:attr:`capability_switch`). It carries no
    executable logic, and — deliberately, unlike a numeric policy threshold —
    it carries no threshold value at all: every governed number a future
    engine reads comes from ``LearningPolicy.thresholds`` alone
    (Recommendation 24/28 of ADR-0029).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    rule_id: str = Field(
        ...,
        min_length=1,
        pattern=r"^[A-Z0-9][A-Z0-9._:-]*$",
        description="Stable, governed rule identity (e.g. 'LN-CAN-001').",
    )
    rule_version: LearningRuleVersion = Field(
        default=LEARNING_RULE_VERSION, description="Version of this rule's definition."
    )
    title: str = Field(..., min_length=1, description="Human-readable rule title.")
    description: str = Field(
        ..., min_length=1, description="What this rule represents and what it governs."
    )
    category: LearningRuleCategory = Field(
        ..., description="Which of the twelve governed lanes this rule belongs to."
    )
    priority: int = Field(
        ..., ge=0, description="Deterministic priority among rules of the same category."
    )
    capability_switch: LearningPolicyToggle = Field(
        ..., description="The governed LearningPolicy switch that gates this rule."
    )
    supported_hierarchy_level: LearningHierarchyLevel = Field(
        ..., description="The governed knowledge-hierarchy level this rule supports."
    )
    documentation_reference: str = Field(
        ..., min_length=1, description="The ADR/proposal section this rule is governed by."
    )
    enabled: bool = Field(default=True, description="Whether the catalogue evaluates this rule.")
    evaluation_order: int = Field(
        ..., ge=0, description="Deterministic ordering key within the catalogue."
    )
