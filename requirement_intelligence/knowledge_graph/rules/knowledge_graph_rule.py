"""The canonical governed :class:`KnowledgeGraphRule` and its controlled
vocabularies (CAP-084B).

A ``KnowledgeGraphRule`` is **metadata only** — the governed declaration of
*which* family a rule belongs to (node, edge, or structural), *which* governed
vocabulary member it names, and *which* policy switch gates it. It carries **no
executable behaviour**: no lambda, no callback, no embedded algorithm, no
threshold value. The deterministic engine's projectors/analyzers own the
behaviour; a rule only *names* it — exactly mirroring how the Continuous
Improvement Framework's own governed rule relates to its deterministic engine
(ADR-0022) and the Recommendation Framework's own governed rule relates to its
deterministic engine (ADR-0019).

Because a rule is data, adding, removing, or retuning a rule is a versioned
catalogue change (a ``KnowledgeGraphRuleBuilder`` edit), never an engine code
change (mirrors ADR-0022 Recommendation 6, ADR-0019 Recommendation 3/5).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.knowledge_graph.identity import KnowledgeGraphRuleVersion
from requirement_intelligence.knowledge_graph.models.enums import (
    KnowledgeEdgeType,
    KnowledgeFindingCategory,
    KnowledgeNodeType,
    KnowledgeSeverity,
)
from shared.contracts.base import Schema

#: Version of the governed ``KnowledgeGraphRule`` **schema** (CAP-084B foundation).
KNOWLEDGE_GRAPH_RULE_VERSION = KnowledgeGraphRuleVersion(1, 0, 0)


class KnowledgeGraphRuleFamily(StrEnum):
    """Which of the three CAP-084B capability lanes a rule belongs to.

    Mirrors ``ImprovementRuleFamily`` (ADR-0022): a fixed, governed
    classification the engine dispatches on, never a computation.
    """

    NODE = "node"
    EDGE = "edge"
    STRUCTURAL = "structural"


class KnowledgeGraphPolicyToggle(StrEnum):
    """A governed ``KnowledgeGraphCapabilitySwitches`` field that gates a rule.

    Names the switch rather than the rule reading it directly, so retuning
    which capability gates a rule is a catalogue change, and flipping the
    switch itself is a policy change — neither is an engine change (mirrors
    ``ImprovementPolicyToggle``, ADR-0022).
    """

    ENABLE_NODE_INGESTION = "enable_node_ingestion"
    ENABLE_EDGE_INGESTION = "enable_edge_ingestion"
    ENABLE_FINDING_DETECTION = "enable_finding_detection"


class KnowledgeGraphRule(Schema):
    """One governed knowledge graph rule — immutable metadata, no behaviour.

    A rule declares the family it belongs to (:attr:`family`), the governed
    vocabulary member it names, and the policy switch that gates it
    (:attr:`policy_reference`). It carries no executable logic; the engine's
    projectors and analyzers resolve the switch and apply the named hints.

    Shape by family (enforced by the validator, never by the engine):

    * ``NODE`` — names :attr:`node_type`; never :attr:`edge_type`,
      :attr:`finding_category`, or :attr:`severity_hint`.
    * ``EDGE`` — names :attr:`edge_type`; never :attr:`node_type`,
      :attr:`finding_category`, or :attr:`severity_hint`.
    * ``STRUCTURAL`` — names :attr:`finding_category` and :attr:`severity_hint`;
      never :attr:`node_type` or :attr:`edge_type`.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    rule_id: str = Field(
        ...,
        min_length=1,
        pattern=r"^[A-Z0-9][A-Z0-9._:-]*$",
        description="Stable, governed rule identity (e.g. 'KG-NODE-001').",
    )
    rule_version: KnowledgeGraphRuleVersion = Field(
        default=KNOWLEDGE_GRAPH_RULE_VERSION, description="Version of this rule's definition."
    )
    rule_name: str = Field(..., min_length=1, description="Human-readable rule name (a title).")
    family: KnowledgeGraphRuleFamily = Field(
        ..., description="Which capability lane this rule governs."
    )
    node_type: KnowledgeNodeType | None = Field(
        default=None, description="For NODE: the governed node type this rule names."
    )
    edge_type: KnowledgeEdgeType | None = Field(
        default=None, description="For EDGE: the governed edge type this rule names."
    )
    finding_category: KnowledgeFindingCategory | None = Field(
        default=None, description="For STRUCTURAL: the governed finding category this rule names."
    )
    severity_hint: KnowledgeSeverity | None = Field(
        default=None,
        description="For STRUCTURAL: the governed severity a matching finding carries.",
    )
    guidance: str = Field(
        ...,
        min_length=1,
        description="What this rule represents and what a matching observation means.",
    )
    policy_reference: KnowledgeGraphPolicyToggle = Field(
        ..., description="The governed KnowledgeGraphPolicy switch that gates this rule."
    )
    enabled: bool = Field(default=True, description="Whether the catalogue evaluates this rule.")
    evaluation_order: int = Field(
        ..., ge=0, description="Deterministic ordering key within the catalogue."
    )
    tags: tuple[str, ...] = Field(default=(), description="Governed classification tags.")

    @model_validator(mode="after")
    def _validate_rule(self) -> KnowledgeGraphRule:
        """Enforce the per-family shape invariants — no value is computed."""
        if self.family == KnowledgeGraphRuleFamily.NODE:
            if self.node_type is None:
                raise ValueError(f"Rule '{self.rule_id}' is NODE but names no node_type.")
            if (
                self.edge_type is not None
                or self.finding_category is not None
                or self.severity_hint is not None
            ):
                raise ValueError(
                    f"Rule '{self.rule_id}' is NODE but names edge_type, finding_category, "
                    f"or severity_hint; it must name none of those."
                )
        elif self.family == KnowledgeGraphRuleFamily.EDGE:
            if self.edge_type is None:
                raise ValueError(f"Rule '{self.rule_id}' is EDGE but names no edge_type.")
            if (
                self.node_type is not None
                or self.finding_category is not None
                or self.severity_hint is not None
            ):
                raise ValueError(
                    f"Rule '{self.rule_id}' is EDGE but names node_type, finding_category, "
                    f"or severity_hint; it must name none of those."
                )
        else:  # STRUCTURAL
            if self.finding_category is None or self.severity_hint is None:
                raise ValueError(
                    f"Rule '{self.rule_id}' is STRUCTURAL but is missing finding_category "
                    f"and/or severity_hint."
                )
            if self.node_type is not None or self.edge_type is not None:
                raise ValueError(
                    f"Rule '{self.rule_id}' is STRUCTURAL but names node_type or edge_type; "
                    f"it must name neither."
                )
        return self
