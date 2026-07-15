"""Unit tests for the governed KnowledgeGraphPolicy and its builder (CAP-084A).

The policy is governed data only — immutable, versioned, deterministic. The
builder constructs; it ingests no node, ingests no edge, partitions no subgraph,
observes no fact, detects no finding. These tests assert construction and shape,
never a computation, because no engine exists yet.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from requirement_intelligence.knowledge_graph.policy import (
    DEFAULT_KNOWLEDGE_GRAPH_POLICY_ID,
    KnowledgeGraphCapabilitySwitches,
    KnowledgeGraphPolicy,
    KnowledgeGraphPolicyBuilder,
    KnowledgeGraphThresholds,
    default_knowledge_graph_policy,
)
from requirement_intelligence.knowledge_graph.version import KNOWLEDGE_POLICY_VERSION


@pytest.mark.unit
class TestDefaultPolicy:
    def test_default_is_versioned_and_identified(self) -> None:
        policy = default_knowledge_graph_policy()
        assert policy.policy_id == DEFAULT_KNOWLEDGE_GRAPH_POLICY_ID
        assert policy.policy_version == KNOWLEDGE_POLICY_VERSION

    def test_builder_is_deterministic(self) -> None:
        assert KnowledgeGraphPolicyBuilder().build() == KnowledgeGraphPolicyBuilder().build()

    def test_policy_is_immutable(self) -> None:
        policy = default_knowledge_graph_policy()
        with pytest.raises(ValidationError):
            policy.description = "changed"  # type: ignore[misc]

    def test_construction_capabilities_enabled_engine_families_reserved_off(self) -> None:
        # No engine exists yet (CAP-084A): the governed intent switches (node/edge
        # ingestion, subgraph partitioning, observation/finding generation) are
        # enabled as data, but no code reads them; the deterministic/ML/LLM engine
        # families all remain reserved off until CAP-084B (mirrors ADR-0022
        # Recommendation 5).
        switches = default_knowledge_graph_policy().capability_switches
        assert switches.enable_node_ingestion
        assert switches.enable_edge_ingestion
        assert switches.enable_subgraph_partitioning
        assert switches.enable_observation_generation
        assert switches.enable_finding_detection
        assert not switches.enable_deterministic_engine
        assert not switches.enable_ml_engine
        assert not switches.enable_llm_engine

    def test_policy_version_is_the_cap_084a_foundation(self) -> None:
        assert str(default_knowledge_graph_policy().policy_version) == "1.0.0"

    def test_default_thresholds(self) -> None:
        thresholds = default_knowledge_graph_policy().thresholds
        assert thresholds.max_nodes_per_graph == 10_000
        assert thresholds.max_edges_per_graph == 50_000
        assert thresholds.max_traversal_depth == 25

    def test_traversal_depth_does_not_exceed_node_bound(self) -> None:
        thresholds = default_knowledge_graph_policy().thresholds
        assert thresholds.max_traversal_depth <= thresholds.max_nodes_per_graph


@pytest.mark.unit
class TestPolicyValidation:
    def test_zero_max_nodes_rejected(self) -> None:
        with pytest.raises(ValidationError):
            KnowledgeGraphThresholds(
                max_nodes_per_graph=0, max_edges_per_graph=10, max_traversal_depth=1
            )

    def test_zero_max_edges_rejected(self) -> None:
        with pytest.raises(ValidationError):
            KnowledgeGraphThresholds(
                max_nodes_per_graph=10, max_edges_per_graph=0, max_traversal_depth=1
            )

    def test_traversal_depth_exceeding_node_bound_rejected(self) -> None:
        with pytest.raises(ValidationError):
            KnowledgeGraphThresholds(
                max_nodes_per_graph=10, max_edges_per_graph=50, max_traversal_depth=11
            )

    def test_traversal_depth_equal_to_node_bound_accepted(self) -> None:
        thresholds = KnowledgeGraphThresholds(
            max_nodes_per_graph=10, max_edges_per_graph=50, max_traversal_depth=10
        )
        assert thresholds.max_traversal_depth == thresholds.max_nodes_per_graph

    def test_policy_round_trips(self) -> None:
        policy = default_knowledge_graph_policy()
        dumped = policy.model_dump(mode="json", by_alias=True)
        assert KnowledgeGraphPolicy.model_validate(dumped) == policy

    def test_capability_switches_round_trip(self) -> None:
        switches = KnowledgeGraphCapabilitySwitches()
        dumped = switches.model_dump(mode="json", by_alias=True)
        assert KnowledgeGraphCapabilitySwitches.model_validate(dumped) == switches
