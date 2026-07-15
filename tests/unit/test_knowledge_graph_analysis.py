"""Unit tests for deterministic subgraph detection, observation, and finding
analysis (CAP-084B).

``SubgraphDetector`` is the sole subgraph authority; ``ObservationEngine`` is the
sole observation authority; ``FindingEngine`` is the sole finding authority.
Graphs are hand-built directly (nodes/edges), independent of the synthetic
provider, so every structural category can be exercised precisely — the same
discipline ``test_continuous_improvement_engine.py`` used for its own
hand-built ``HistoricalDataset`` fixtures.
"""

from __future__ import annotations

import pytest

from requirement_intelligence.knowledge_graph.engine.analysis import (
    FindingEngine,
    ObservationEngine,
    SubgraphDetector,
    detect_cycle,
)
from requirement_intelligence.knowledge_graph.identity import KnowledgeEdgeId, KnowledgeNodeId
from requirement_intelligence.knowledge_graph.models.edge import KnowledgeEdge
from requirement_intelligence.knowledge_graph.models.enums import (
    KnowledgeEdgeType,
    KnowledgeFindingCategory,
    KnowledgeNodeType,
    KnowledgeObservationCategory,
)
from requirement_intelligence.knowledge_graph.models.node import KnowledgeNode
from requirement_intelligence.knowledge_graph.policy import (
    KnowledgeGraphPolicy,
    KnowledgeGraphPolicyBuilder,
    default_knowledge_graph_policy,
)

_GRAPH_ID = "kg-analysis"


def _node(node_type: KnowledgeNodeType, referenced_id: str) -> KnowledgeNode:
    return KnowledgeNode(
        node_id=KnowledgeNodeId.for_entity(node_type.value, referenced_id),
        node_type=node_type,
        referenced_id=referenced_id,
        label=f"{node_type} {referenced_id}",
    )


def _req(referenced_id: str) -> KnowledgeNode:
    return _node(KnowledgeNodeType.REQUIREMENT, referenced_id)


def _edge(
    edge_type: KnowledgeEdgeType, source: KnowledgeNode, target: KnowledgeNode
) -> KnowledgeEdge:
    return KnowledgeEdge(
        edge_id=KnowledgeEdgeId.for_relationship(
            edge_type.value, str(source.node_id), str(target.node_id)
        ),
        edge_type=edge_type,
        source_node_id=source.node_id,
        target_node_id=target.node_id,
        rationale="test edge",
    )


def _policy_with(**switches: bool) -> KnowledgeGraphPolicy:
    base = KnowledgeGraphPolicyBuilder().build()
    return base.model_copy(
        update={"capability_switches": base.capability_switches.model_copy(update=switches)}
    )


_POLICY = default_knowledge_graph_policy()
_DEPENDS_ON = KnowledgeEdgeType.DEPENDS_ON


@pytest.mark.unit
class TestSubgraphDetector:
    def test_single_connected_component(self) -> None:
        a, b, c = _req("a"), _req("b"), _req("c")
        edges = (_edge(_DEPENDS_ON, a, b), _edge(_DEPENDS_ON, b, c))
        subgraphs = SubgraphDetector(_POLICY).detect(_GRAPH_ID, (a, b, c), edges)
        assert len(subgraphs) == 1
        assert set(subgraphs[0].node_ids) == {a.node_id, b.node_id, c.node_id}

    def test_two_disconnected_components(self) -> None:
        a, b = _req("a"), _req("b")
        c, d = _req("c"), _req("d")
        edges = (_edge(_DEPENDS_ON, a, b), _edge(_DEPENDS_ON, c, d))
        subgraphs = SubgraphDetector(_POLICY).detect(_GRAPH_ID, (a, b, c, d), edges)
        assert len(subgraphs) == 2

    def test_isolated_node_is_its_own_subgraph(self) -> None:
        a, b = _node(KnowledgeNodeType.REQUIREMENT, "a"), _node(KnowledgeNodeType.REQUIREMENT, "b")
        subgraphs = SubgraphDetector(_POLICY).detect(_GRAPH_ID, (a, b), ())
        assert len(subgraphs) == 2
        assert all(len(subgraph.node_ids) == 1 for subgraph in subgraphs)

    def test_empty_graph_yields_no_subgraphs(self) -> None:
        assert SubgraphDetector(_POLICY).detect(_GRAPH_ID, (), ()) == ()

    def test_subgraph_edges_stay_within_the_component(self) -> None:
        a, b = _node(KnowledgeNodeType.REQUIREMENT, "a"), _node(KnowledgeNodeType.REQUIREMENT, "b")
        c = _node(KnowledgeNodeType.REQUIREMENT, "c")
        edge = _edge(KnowledgeEdgeType.DEPENDS_ON, a, b)
        subgraphs = SubgraphDetector(_POLICY).detect(_GRAPH_ID, (a, b, c), (edge,))
        component_with_edge = next(s for s in subgraphs if len(s.node_ids) == 2)
        assert component_with_edge.edge_ids == (edge.edge_id,)

    def test_subgraph_partitioning_disabled_yields_no_subgraphs(self) -> None:
        policy = _policy_with(enable_subgraph_partitioning=False)
        a = _node(KnowledgeNodeType.REQUIREMENT, "a")
        assert SubgraphDetector(policy).detect(_GRAPH_ID, (a,), ()) == ()

    def test_is_deterministic(self) -> None:
        a, b = _node(KnowledgeNodeType.REQUIREMENT, "a"), _node(KnowledgeNodeType.REQUIREMENT, "b")
        edges = (_edge(KnowledgeEdgeType.DEPENDS_ON, a, b),)
        s1 = SubgraphDetector(_POLICY).detect(_GRAPH_ID, (a, b), edges)
        s2 = SubgraphDetector(_POLICY).detect(_GRAPH_ID, (a, b), edges)
        assert s1 == s2

    def test_undirected_connectivity_regardless_of_edge_direction(self) -> None:
        a, b = _node(KnowledgeNodeType.REQUIREMENT, "a"), _node(KnowledgeNodeType.REQUIREMENT, "b")
        edge = _edge(KnowledgeEdgeType.DEPENDS_ON, b, a)  # reversed direction
        subgraphs = SubgraphDetector(_POLICY).detect(_GRAPH_ID, (a, b), (edge,))
        assert len(subgraphs) == 1


@pytest.mark.unit
class TestObservationEngine:
    def test_node_coverage_observation_present(self) -> None:
        a, b = _node(KnowledgeNodeType.REQUIREMENT, "a"), _node(KnowledgeNodeType.REQUIREMENT, "b")
        edge = _edge(KnowledgeEdgeType.DEPENDS_ON, a, b)
        subgraphs = SubgraphDetector(_POLICY).detect(_GRAPH_ID, (a, b), (edge,))
        observations = ObservationEngine(_POLICY).analyze(_GRAPH_ID, (a, b), (edge,), subgraphs)
        categories = {str(o.category) for o in observations}
        assert "node_coverage" in categories

    def test_node_coverage_excludes_isolated_nodes(self) -> None:
        a, b = _node(KnowledgeNodeType.REQUIREMENT, "a"), _node(KnowledgeNodeType.REQUIREMENT, "b")
        edge = _edge(KnowledgeEdgeType.DEPENDS_ON, a, b)
        isolated = _node(KnowledgeNodeType.REQUIREMENT, "isolated")
        subgraphs = SubgraphDetector(_POLICY).detect(_GRAPH_ID, (a, b, isolated), (edge,))
        observations = ObservationEngine(_POLICY).analyze(
            _GRAPH_ID, (a, b, isolated), (edge,), subgraphs
        )
        coverage = next(o for o in observations if str(o.category) == "node_coverage")
        assert isolated.node_id not in coverage.subject_node_ids
        assert a.node_id in coverage.subject_node_ids

    def test_edge_coverage_observation_lists_distinct_types(self) -> None:
        a, b, c = (
            _node(KnowledgeNodeType.REQUIREMENT, "a"),
            _node(KnowledgeNodeType.REQUIREMENT, "b"),
            _node(KnowledgeNodeType.CAPABILITY, "c"),
        )
        edges = (
            _edge(KnowledgeEdgeType.DEPENDS_ON, a, b),
            _edge(KnowledgeEdgeType.IMPLEMENTS, a, c),
        )
        subgraphs = SubgraphDetector(_POLICY).detect(_GRAPH_ID, (a, b, c), edges)
        observations = ObservationEngine(_POLICY).analyze(_GRAPH_ID, (a, b, c), edges, subgraphs)
        edge_coverage = next(o for o in observations if str(o.category) == "edge_coverage")
        assert "depends_on" in edge_coverage.description
        assert "implements" in edge_coverage.description

    def test_lineage_depth_observation_only_when_depends_on_present(self) -> None:
        a, b = _node(KnowledgeNodeType.REQUIREMENT, "a"), _node(KnowledgeNodeType.REQUIREMENT, "b")
        edge = _edge(KnowledgeEdgeType.IMPLEMENTS, a, b)
        subgraphs = SubgraphDetector(_POLICY).detect(_GRAPH_ID, (a, b), (edge,))
        observations = ObservationEngine(_POLICY).analyze(_GRAPH_ID, (a, b), (edge,), subgraphs)
        assert not any(str(o.category) == "lineage_depth" for o in observations)

    def test_lineage_depth_reports_chain_length(self) -> None:
        a, b, c = (
            _node(KnowledgeNodeType.REQUIREMENT, "a"),
            _node(KnowledgeNodeType.REQUIREMENT, "b"),
            _node(KnowledgeNodeType.REQUIREMENT, "c"),
        )
        edges = (
            _edge(KnowledgeEdgeType.DEPENDS_ON, c, b),
            _edge(KnowledgeEdgeType.DEPENDS_ON, b, a),
        )
        subgraphs = SubgraphDetector(_POLICY).detect(_GRAPH_ID, (a, b, c), edges)
        observations = ObservationEngine(_POLICY).analyze(_GRAPH_ID, (a, b, c), edges, subgraphs)
        lineage = next(o for o in observations if str(o.category) == "lineage_depth")
        assert len(lineage.subject_node_ids) == 3

    def test_structural_consistency_present_when_nodes_exist(self) -> None:
        a = _node(KnowledgeNodeType.REQUIREMENT, "a")
        subgraphs = SubgraphDetector(_POLICY).detect(_GRAPH_ID, (a,), ())
        observations = ObservationEngine(_POLICY).analyze(_GRAPH_ID, (a,), (), subgraphs)
        assert any(str(o.category) == "structural_consistency" for o in observations)

    def test_empty_graph_yields_no_observations(self) -> None:
        assert ObservationEngine(_POLICY).analyze(_GRAPH_ID, (), (), ()) == ()

    def test_observation_generation_disabled_yields_nothing(self) -> None:
        policy = _policy_with(enable_observation_generation=False)
        a = _node(KnowledgeNodeType.REQUIREMENT, "a")
        assert ObservationEngine(policy).analyze(_GRAPH_ID, (a,), (), ()) == ()

    def test_is_deterministic(self) -> None:
        a, b = _node(KnowledgeNodeType.REQUIREMENT, "a"), _node(KnowledgeNodeType.REQUIREMENT, "b")
        edge = _edge(KnowledgeEdgeType.DEPENDS_ON, a, b)
        subgraphs = SubgraphDetector(_POLICY).detect(_GRAPH_ID, (a, b), (edge,))
        o1 = ObservationEngine(_POLICY).analyze(_GRAPH_ID, (a, b), (edge,), subgraphs)
        o2 = ObservationEngine(_POLICY).analyze(_GRAPH_ID, (a, b), (edge,), subgraphs)
        assert o1 == o2

    def test_all_four_observation_categories_are_governed(self) -> None:
        assert {c.value for c in KnowledgeObservationCategory} == {
            "node_coverage",
            "edge_coverage",
            "lineage_depth",
            "structural_consistency",
        }


@pytest.mark.unit
class TestFindingEngine:
    def test_isolated_node_finding(self) -> None:
        isolated = _node(KnowledgeNodeType.REQUIREMENT, "isolated")
        connected_a = _node(KnowledgeNodeType.REQUIREMENT, "a")
        connected_b = _node(KnowledgeNodeType.REQUIREMENT, "b")
        edge = _edge(KnowledgeEdgeType.DEPENDS_ON, connected_a, connected_b)
        nodes = (isolated, connected_a, connected_b)
        subgraphs = SubgraphDetector(_POLICY).detect(_GRAPH_ID, nodes, (edge,))
        findings = FindingEngine(_POLICY).detect(_GRAPH_ID, nodes, (edge,), subgraphs)
        isolated_finding = next(f for f in findings if str(f.category) == "isolated_node")
        assert isolated_finding.subject_node_ids == (isolated.node_id,)

    def test_no_isolated_node_finding_when_fully_connected(self) -> None:
        a, b = _node(KnowledgeNodeType.REQUIREMENT, "a"), _node(KnowledgeNodeType.REQUIREMENT, "b")
        edge = _edge(KnowledgeEdgeType.DEPENDS_ON, a, b)
        subgraphs = SubgraphDetector(_POLICY).detect(_GRAPH_ID, (a, b), (edge,))
        findings = FindingEngine(_POLICY).detect(_GRAPH_ID, (a, b), (edge,), subgraphs)
        assert not any(str(f.category) == "isolated_node" for f in findings)

    def test_duplicate_edge_finding(self) -> None:
        a, b = _node(KnowledgeNodeType.REQUIREMENT, "a"), _node(KnowledgeNodeType.REQUIREMENT, "b")
        edge1 = _edge(KnowledgeEdgeType.DEPENDS_ON, a, b)
        edge2 = _edge(KnowledgeEdgeType.RELATED_TO, a, b)  # same pair, different type
        subgraphs = SubgraphDetector(_POLICY).detect(_GRAPH_ID, (a, b), (edge1, edge2))
        findings = FindingEngine(_POLICY).detect(_GRAPH_ID, (a, b), (edge1, edge2), subgraphs)
        duplicate = next(f for f in findings if str(f.category) == "duplicate_edge")
        assert set(duplicate.subject_edge_ids) == {edge1.edge_id, edge2.edge_id}

    def test_no_duplicate_edge_finding_for_a_single_edge(self) -> None:
        a, b = _node(KnowledgeNodeType.REQUIREMENT, "a"), _node(KnowledgeNodeType.REQUIREMENT, "b")
        edge = _edge(KnowledgeEdgeType.DEPENDS_ON, a, b)
        subgraphs = SubgraphDetector(_POLICY).detect(_GRAPH_ID, (a, b), (edge,))
        findings = FindingEngine(_POLICY).detect(_GRAPH_ID, (a, b), (edge,), subgraphs)
        assert not any(str(f.category) == "duplicate_edge" for f in findings)

    def test_orphan_graph_finding_when_nodes_but_no_edges(self) -> None:
        a, b = _node(KnowledgeNodeType.REQUIREMENT, "a"), _node(KnowledgeNodeType.REQUIREMENT, "b")
        subgraphs = SubgraphDetector(_POLICY).detect(_GRAPH_ID, (a, b), ())
        findings = FindingEngine(_POLICY).detect(_GRAPH_ID, (a, b), (), subgraphs)
        orphan = next(f for f in findings if str(f.category) == "orphan_graph")
        assert set(orphan.subject_node_ids) == {a.node_id, b.node_id}

    def test_no_orphan_graph_finding_when_edges_exist(self) -> None:
        a, b = _node(KnowledgeNodeType.REQUIREMENT, "a"), _node(KnowledgeNodeType.REQUIREMENT, "b")
        edge = _edge(KnowledgeEdgeType.DEPENDS_ON, a, b)
        subgraphs = SubgraphDetector(_POLICY).detect(_GRAPH_ID, (a, b), (edge,))
        findings = FindingEngine(_POLICY).detect(_GRAPH_ID, (a, b), (edge,), subgraphs)
        assert not any(str(f.category) == "orphan_graph" for f in findings)

    def test_missing_relationship_finding_for_unconnected_recommendation(self) -> None:
        recommendation = _node(KnowledgeNodeType.RECOMMENDATION, "rec")
        requirement = _req("req")
        # recommendation has no GENERATED_BY edge — only an unrelated edge exists
        edge = _edge(KnowledgeEdgeType.RELATED_TO, recommendation, requirement)
        pair = (recommendation, requirement)
        subgraphs = SubgraphDetector(_POLICY).detect(_GRAPH_ID, pair, (edge,))
        findings = FindingEngine(_POLICY).detect(_GRAPH_ID, pair, (edge,), subgraphs)
        missing = next(f for f in findings if str(f.category) == "missing_relationship")
        assert recommendation.node_id in missing.subject_node_ids

    def test_no_missing_relationship_finding_when_generated_by_present(self) -> None:
        recommendation = _node(KnowledgeNodeType.RECOMMENDATION, "rec")
        requirement = _req("req")
        edge = _edge(KnowledgeEdgeType.GENERATED_BY, recommendation, requirement)
        pair = (recommendation, requirement)
        subgraphs = SubgraphDetector(_POLICY).detect(_GRAPH_ID, pair, (edge,))
        findings = FindingEngine(_POLICY).detect(_GRAPH_ID, pair, (edge,), subgraphs)
        assert not any(str(f.category) == "missing_relationship" for f in findings)

    def test_broken_lineage_finding_for_subgraph_without_requirement(self) -> None:
        capability = _node(KnowledgeNodeType.CAPABILITY, "cap")
        document = _node(KnowledgeNodeType.DOCUMENT, "doc")
        edge = _edge(KnowledgeEdgeType.USES, capability, document)
        pair = (capability, document)
        subgraphs = SubgraphDetector(_POLICY).detect(_GRAPH_ID, pair, (edge,))
        findings = FindingEngine(_POLICY).detect(_GRAPH_ID, pair, (edge,), subgraphs)
        broken = next(f for f in findings if str(f.category) == "broken_lineage")
        assert set(broken.subject_node_ids) == {capability.node_id, document.node_id}

    def test_no_broken_lineage_finding_when_requirement_present(self) -> None:
        requirement = _req("req")
        capability = _node(KnowledgeNodeType.CAPABILITY, "cap")
        edge = _edge(KnowledgeEdgeType.IMPLEMENTS, requirement, capability)
        pair = (requirement, capability)
        subgraphs = SubgraphDetector(_POLICY).detect(_GRAPH_ID, pair, (edge,))
        findings = FindingEngine(_POLICY).detect(_GRAPH_ID, pair, (edge,), subgraphs)
        assert not any(str(f.category) == "broken_lineage" for f in findings)

    def test_cycle_finding_for_a_directed_cycle(self) -> None:
        a, b, c = _req("a"), _req("b"), _req("c")
        edges = (
            _edge(_DEPENDS_ON, a, b),
            _edge(_DEPENDS_ON, b, c),
            _edge(_DEPENDS_ON, c, a),
        )
        subgraphs = SubgraphDetector(_POLICY).detect(_GRAPH_ID, (a, b, c), edges)
        findings = FindingEngine(_POLICY).detect(_GRAPH_ID, (a, b, c), edges, subgraphs)
        cycle = next(f for f in findings if str(f.category) == "cycle")
        assert set(cycle.subject_node_ids) == {a.node_id, b.node_id, c.node_id}

    def test_no_cycle_finding_for_an_acyclic_chain(self) -> None:
        a, b, c = _req("a"), _req("b"), _req("c")
        edges = (_edge(_DEPENDS_ON, a, b), _edge(_DEPENDS_ON, b, c))
        subgraphs = SubgraphDetector(_POLICY).detect(_GRAPH_ID, (a, b, c), edges)
        findings = FindingEngine(_POLICY).detect(_GRAPH_ID, (a, b, c), edges, subgraphs)
        assert not any(str(f.category) == "cycle" for f in findings)

    def test_finding_detection_disabled_yields_nothing(self) -> None:
        policy = _policy_with(enable_finding_detection=False)
        isolated = _req("isolated")
        subgraphs = SubgraphDetector(_POLICY).detect(_GRAPH_ID, (isolated,), ())
        assert FindingEngine(policy).detect(_GRAPH_ID, (isolated,), (), subgraphs) == ()

    def test_is_deterministic(self) -> None:
        isolated = _req("isolated")
        subgraphs = SubgraphDetector(_POLICY).detect(_GRAPH_ID, (isolated,), ())
        f1 = FindingEngine(_POLICY).detect(_GRAPH_ID, (isolated,), (), subgraphs)
        f2 = FindingEngine(_POLICY).detect(_GRAPH_ID, (isolated,), (), subgraphs)
        assert f1 == f2

    def test_all_six_finding_categories_are_governed(self) -> None:
        assert {c.value for c in KnowledgeFindingCategory} == {
            "isolated_node",
            "broken_lineage",
            "duplicate_edge",
            "orphan_graph",
            "missing_relationship",
            "cycle",
        }


@pytest.mark.unit
class TestDetectCycle:
    def test_no_edges_no_cycle(self) -> None:
        assert detect_cycle(()) == []

    def test_acyclic_chain_has_no_cycle(self) -> None:
        a, b, c = _req("a"), _req("b"), _req("c")
        edges = (_edge(_DEPENDS_ON, a, b), _edge(_DEPENDS_ON, b, c))
        assert detect_cycle(edges) == []

    def test_self_loop_is_a_cycle(self) -> None:
        a = _req("a")
        edge = _edge(_DEPENDS_ON, a, a)
        cycle = detect_cycle((edge,))
        assert cycle == [a.node_id, a.node_id]

    def test_three_node_cycle_detected(self) -> None:
        a, b, c = _req("a"), _req("b"), _req("c")
        edges = (
            _edge(_DEPENDS_ON, a, b),
            _edge(_DEPENDS_ON, b, c),
            _edge(_DEPENDS_ON, c, a),
        )
        cycle = detect_cycle(edges)
        assert set(cycle) == {a.node_id, b.node_id, c.node_id}

    def test_is_deterministic(self) -> None:
        a, b = _req("a"), _req("b")
        edges = (_edge(_DEPENDS_ON, a, b), _edge(_DEPENDS_ON, b, a))
        assert detect_cycle(edges) == detect_cycle(edges)
