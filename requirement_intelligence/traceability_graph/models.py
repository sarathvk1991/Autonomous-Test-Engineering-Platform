"""Canonical models for the Traceability Graph — the minimal slice.

Scope, deliberately: `requirement -> scenario -> step` only. Page-object and
execution-result hops, change-impact, and state/flow are explicitly deferred
(mentor item #3's "GRAPHS DESIGN SURFACED" note, `docs/architecture/
mentor-feedback-scoping.md`) — additive later, not modeled here.

Every model is frozen (`shared.contracts.base.Schema`), camelCase, and
reference-not-copy: a node carries only the referenced entity's own id, never
its content (mirrors ADR-0023 Recommendation 2). `TraceabilityGraph` enforces
the same cross-referential invariant ADR-0023 §D4 freezes for its own graph:
an edge may never reference a node absent from the same graph.

`CompletenessReport` is the payoff — report-only. It carries counts and the
untested-requirement list a future gate *could* evaluate, but this module
computes no pass/fail judgement anywhere (scores-first, per this build's own
scope: surface the real numbers, decide gating later).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from shared.contracts.base import Schema


class TraceabilityNodeType(StrEnum):
    """The governed vocabulary of what one `TraceabilityNode` represents."""

    REQUIREMENT = "requirement"
    SCENARIO = "scenario"
    STEP = "step"


class TraceabilityEdgeType(StrEnum):
    """The governed vocabulary of what one `TraceabilityEdge` relates."""

    HAS_SCENARIO = "has_scenario"
    HAS_STEP = "has_step"


class TraceabilityNode(Schema):
    """One platform entity — data only, referencing an external object by id alone."""

    model_config = ConfigDict(alias_generator=to_camel)

    node_id: str = Field(..., min_length=1, description="Deterministic identity of this node.")
    node_type: TraceabilityNodeType = Field(
        ..., description="The governed platform entity type this node represents."
    )
    referenced_id: str = Field(
        ...,
        min_length=1,
        description="Identity of the referenced platform entity. Never the entity itself.",
    )
    label: str = Field(..., min_length=1, description="Human-readable display label.")


class TraceabilityEdge(Schema):
    """One directed, governed relationship between two nodes — data only."""

    model_config = ConfigDict(alias_generator=to_camel)

    edge_id: str = Field(..., min_length=1, description="Deterministic identity of this edge.")
    edge_type: TraceabilityEdgeType = Field(
        ..., description="The governed relationship type this edge names."
    )
    source_node_id: str = Field(..., min_length=1, description="The edge's originating node.")
    target_node_id: str = Field(..., min_length=1, description="The edge's destination node.")
    rationale: str = Field(
        ..., min_length=1, description="Human-readable reason this relationship was recorded."
    )


class TraceabilityGraph(Schema):
    """The complete requirement -> scenario -> step graph for one projection."""

    model_config = ConfigDict(alias_generator=to_camel)

    graph_id: str = Field(..., min_length=1, description="Deterministic identity of this graph.")
    nodes: tuple[TraceabilityNode, ...] = Field(default_factory=tuple)
    edges: tuple[TraceabilityEdge, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _edges_reference_existing_nodes(self) -> TraceabilityGraph:
        """Reject a graph whose edge names a node this graph does not itself contain."""
        node_ids = {node.node_id for node in self.nodes}
        for edge in self.edges:
            if edge.source_node_id not in node_ids or edge.target_node_id not in node_ids:
                raise ValueError(
                    f"Edge {edge.edge_id!r} references a node not present in this graph."
                )
        return self


class UncoveredRequirement(Schema):
    """One requirement the completeness sweep found without a full test chain."""

    model_config = ConfigDict(alias_generator=to_camel)

    requirement_id: str = Field(..., min_length=1)
    reason: str = Field(
        ...,
        min_length=1,
        description='Either "no_scenario" (zero scenarios at all) or '
        '"scenario_without_steps" (has a scenario, but it has no steps).',
    )


class CompletenessReport(Schema):
    """Corpus-level completeness — the payoff. Report-only: no gate, no threshold.

    Structured so a future gate could evaluate it directly (compare
    `coverage_percentage` or `untested_requirement_count` against a bound) —
    but no such evaluation exists anywhere in this module.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    graph_id: str = Field(..., min_length=1)
    total_requirements: int = Field(..., ge=0)
    tested_requirement_count: int = Field(..., ge=0)
    untested_requirement_count: int = Field(..., ge=0)
    coverage_percentage: float = Field(..., ge=0.0, le=100.0)
    untested_requirements: tuple[UncoveredRequirement, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _counts_are_consistent(self) -> CompletenessReport:
        """Enforce the report's own arithmetic — explainable, never asserted blind."""
        counted = self.tested_requirement_count + self.untested_requirement_count
        if counted != self.total_requirements:
            raise ValueError(
                "tested_requirement_count + untested_requirement_count must equal "
                "total_requirements."
            )
        if len(self.untested_requirements) != self.untested_requirement_count:
            raise ValueError(
                "untested_requirements length must equal untested_requirement_count."
            )
        return self


__all__ = [
    "CompletenessReport",
    "TraceabilityEdge",
    "TraceabilityEdgeType",
    "TraceabilityGraph",
    "TraceabilityNode",
    "TraceabilityNodeType",
    "UncoveredRequirement",
]
