"""The canonical governed :class:`KnowledgeGraphPolicy`.

A ``KnowledgeGraphPolicy`` defines **what Knowledge Graph node ingestion, edge
ingestion, subgraph partitioning, observation generation, and finding detection
are allowed to do** — deterministic configuration and enabled capability switches
a future engine must obey. It is the Knowledge Graph Framework counterpart to the
Continuous Improvement Framework's ``ImprovementPolicy``: an immutable,
declarative, governed rule set that contains **no executable logic**. A future
engine reads a policy and acts within it; the policy computes nothing.

Policy vs engine (frozen, ADR-0023)
------------------------------------
* ``KnowledgeGraphPolicy`` — the governed rules and switches (this file). Data
  only.
* A future deterministic / statistical / ML / LLM / hybrid Knowledge Graph engine
  (CAP-084B onward, reserved) — the behaviour that acts within them against a
  resolved Historical Dataset.

Tuning graph-construction behaviour is therefore a *versioned policy change*,
never an engine code change, and it must never force a change to
``KnowledgeGraphResult`` or the service contract (mirrors ADR-0022 Recommendation
5, itself mirroring ADR-0019 Recommendation 5).
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.knowledge_graph.identity import (
    KnowledgePolicyId,
    KnowledgePolicyVersion,
)
from shared.contracts.base import Schema


class KnowledgeGraphCapabilitySwitches(Schema):
    """Governed on/off switches for each Knowledge Graph capability. Data only.

    Each future capability (node ingestion, edge ingestion, subgraph
    partitioning, observation generation, finding detection, and the future
    deterministic/ML/LLM engine families) is independently enabled/disabled
    here — a governed data change, never an engine change (mirrors ADR-0022
    Recommendation 5).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    enable_node_ingestion: bool = Field(default=True, description="Whether node ingestion may run.")
    enable_edge_ingestion: bool = Field(default=True, description="Whether edge ingestion may run.")
    enable_subgraph_partitioning: bool = Field(
        default=True, description="Whether subgraph partitioning may run."
    )
    enable_observation_generation: bool = Field(
        default=True, description="Whether observation generation may run."
    )
    enable_finding_detection: bool = Field(
        default=True, description="Whether structural finding detection may run."
    )
    enable_deterministic_engine: bool = Field(
        default=False,
        description="Whether the deterministic Knowledge Graph engine is enabled (reserved).",
    )
    enable_ml_engine: bool = Field(
        default=False,
        description="Whether a future ML Knowledge Graph engine is enabled (reserved).",
    )
    enable_llm_engine: bool = Field(
        default=False,
        description="Whether a future LLM Knowledge Graph engine is enabled (reserved).",
    )


class KnowledgeGraphThresholds(Schema):
    """Governed deterministic thresholds bounding a future engine. Data only.

    A rule never carries a literal bound; a future engine reads these thresholds
    the same way a Continuous Improvement rule names a policy field rather than a
    literal (ADR-0022, mirroring ADR-0017 §D25).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    max_nodes_per_graph: int = Field(
        ..., ge=1, description="Maximum number of nodes a single graph build may contain."
    )
    max_edges_per_graph: int = Field(
        ..., ge=1, description="Maximum number of edges a single graph build may contain."
    )
    max_traversal_depth: int = Field(
        ..., ge=1, description="Maximum traversal depth a future engine may explore."
    )

    @model_validator(mode="after")
    def _validate_thresholds(self) -> KnowledgeGraphThresholds:
        """The traversal depth bound must not exceed the node bound it traverses within."""
        if self.max_traversal_depth > self.max_nodes_per_graph:
            raise ValueError("max_traversal_depth must not exceed max_nodes_per_graph.")
        return self


class KnowledgeGraphPolicy(Schema):
    """An immutable, declarative, governed rule set for Knowledge Graph construction."""

    model_config = ConfigDict(alias_generator=to_camel)

    policy_id: KnowledgePolicyId = Field(..., description="Governed policy identity.")
    policy_version: KnowledgePolicyVersion = Field(..., description="Semantic policy version.")
    description: str = Field(..., min_length=1, description="Human-readable policy summary.")

    capability_switches: KnowledgeGraphCapabilitySwitches = Field(
        ..., description="Which Knowledge Graph capabilities are enabled."
    )
    thresholds: KnowledgeGraphThresholds = Field(
        ..., description="Governed deterministic thresholds a future engine must respect."
    )
