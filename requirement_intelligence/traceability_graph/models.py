"""Canonical models for the Traceability Graph — the minimal slice, plus
method-level change-impact.

Scope: `requirement -> scenario -> step` (the minimal slice), the
step-definition-binding annotation (`UnboundStep`/`BindingCompletenessReport`
below) — the binding-data half of ADR-0048 D4's named "page-object hop"
(D5's own text: "the deferred page-object/step-definition hop") — and now
`PAGE_OBJECT_METHOD`/`CALLS_METHOD` (`MethodImpact`/`ChangeImpactReport`
below): the method-level half of ADR-0048 D4's own separately-named
"change-impact graph" (`docs/architecture/mentor-feedback-scoping.md` item
#3's "CHANGE-IMPACT GRAPH DESIGN SURFACED" note), extending this SAME graph
rather than a new sibling. Element/locator-level change-impact (a locator
field's own value, as opposed to the method that uses it) and the
execution-result/state-flow hops remain deferred, not modeled here.

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
    PAGE_OBJECT_METHOD = "page_object_method"


class TraceabilityEdgeType(StrEnum):
    """The governed vocabulary of what one `TraceabilityEdge` relates."""

    HAS_SCENARIO = "has_scenario"
    HAS_STEP = "has_step"
    CALLS_METHOD = "calls_method"


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


class UnboundStep(Schema):
    """One STEP node the binding sweep found without a resolved step-definition."""

    model_config = ConfigDict(alias_generator=to_camel)

    step_id: str = Field(..., min_length=1, description="The STEP node's own referenced_id.")
    step_text: str = Field(..., min_length=1, description="The step's raw Gherkin text.")
    reason: str = Field(
        ...,
        min_length=1,
        description='Either "escalated" (a step-definition need was derived for this text but '
        "the reuse engine could neither bind nor generate one) or \"no_step_definition_need\" "
        "(no automation-engineering record exists for this text at all).",
    )


class BindingCompletenessReport(Schema):
    """Corpus-level step-definition-binding completeness — the binding-hop payoff.

    Distinct from `CompletenessReport` (Gherkin-authoring completeness): a
    step this graph counts as authored may still have no proven, bound step
    definition — this report closes exactly that gap, for the identical step
    set (ADR-0048 D5's own two-layer finding: 100% authoring, ~50% binding,
    previously only visible via a manual CP3 cross-reference). Report-only,
    same posture as `CompletenessReport`: no gate, no threshold, no fail
    logic anywhere in this module.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    graph_id: str = Field(..., min_length=1)
    total_steps: int = Field(..., ge=0)
    bound_step_count: int = Field(..., ge=0)
    unbound_step_count: int = Field(..., ge=0)
    coverage_percentage: float = Field(..., ge=0.0, le=100.0)
    unbound_steps: tuple[UnboundStep, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _counts_are_consistent(self) -> BindingCompletenessReport:
        """Enforce the report's own arithmetic — explainable, never asserted blind."""
        counted = self.bound_step_count + self.unbound_step_count
        if counted != self.total_steps:
            raise ValueError(
                "bound_step_count + unbound_step_count must equal total_steps."
            )
        if len(self.unbound_steps) != self.unbound_step_count:
            raise ValueError("unbound_steps length must equal unbound_step_count.")
        return self


class MethodImpact(Schema):
    """One `PAGE_OBJECT_METHOD` node's own change-impact — the scenarios
    reachable from it by walking `CALLS_METHOD`/`HAS_STEP`/`HAS_SCENARIO`
    edges BACKWARD (a change to this method potentially affects each).

    Report-only, same posture as `CompletenessReport`/
    `BindingCompletenessReport`: identifies the affected set, never gates,
    never regenerates anything. A future delta-scoped-regeneration
    capability is this report's own intended consumer, not built here.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    class_name: str = Field(..., min_length=1)
    method_name: str = Field(..., min_length=1)
    affected_scenario_count: int = Field(..., ge=0)
    affected_scenario_ids: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _count_matches_ids(self) -> MethodImpact:
        """Enforce the report's own arithmetic — explainable, never asserted blind."""
        if len(self.affected_scenario_ids) != self.affected_scenario_count:
            raise ValueError(
                "affected_scenario_ids length must equal affected_scenario_count."
            )
        return self


class ChangeImpactReport(Schema):
    """Corpus-level change-impact — the full method -> affected-scenarios
    map, one `MethodImpact` per `PAGE_OBJECT_METHOD` node in the graph.

    Report-only: no gate, no threshold, no fail logic anywhere in this
    module. Structured so a future delta-scoped-regeneration capability
    could consume it directly (regenerate only the scenarios a changed
    method's own `MethodImpact` names) — but nothing here decides that.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    graph_id: str = Field(..., min_length=1)
    total_methods: int = Field(..., ge=0)
    method_impacts: tuple[MethodImpact, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _count_matches_impacts(self) -> ChangeImpactReport:
        """Enforce the report's own arithmetic — explainable, never asserted blind."""
        if len(self.method_impacts) != self.total_methods:
            raise ValueError("method_impacts length must equal total_methods.")
        return self


__all__ = [
    "BindingCompletenessReport",
    "ChangeImpactReport",
    "CompletenessReport",
    "MethodImpact",
    "TraceabilityEdge",
    "TraceabilityEdgeType",
    "TraceabilityGraph",
    "TraceabilityNode",
    "TraceabilityNodeType",
    "UnboundStep",
    "UncoveredRequirement",
]
