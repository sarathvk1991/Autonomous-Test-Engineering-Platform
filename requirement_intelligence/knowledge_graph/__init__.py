"""Knowledge Graph Framework (CAP-084A architecture & governance freeze).

The second Layer 2 capability defined by ADR-0020 (Platform Evolution Roadmap),
following Continuous Improvement (ADR-0022), and governed by ADR-0021
(Cross-Execution Data Architecture & Historical Intelligence Constitution) and
ADR-0023 (Knowledge Graph Framework). It will own the platform's single
structural authority — nodes, governed relationship edges, subgraphs,
observations, and findings — built from a **Historical Dataset**, never a single
execution. It is a **consumer of Historical Truth only** (ADR-0021 §Stage 8): it
never imports a Layer 1 subsystem, never imports Continuous Improvement, never
re-runs Requirement Enhancement, Grounding, Validation, CP1, Quality Governance,
or Recommendation, and never reaches into the Execution Package.

**Runtime status (CAP-084A):** architecture-only. ``KnowledgeGraphService`` is an
abstract contract; ``DormantKnowledgeGraphService`` raises ``NotImplementedError``
on every call. No node is ingested, no edge is ingested, no subgraph is
partitioned, no observation is recorded, no finding is detected. Nothing is wired
into any execution pipeline — no CLI phase, no Execution Package field, no
serializer. Runtime behaviour is unchanged; the golden baseline is unchanged; the
Architecture Version remains 1.2.0. Governed by ADR-0023.
"""

from __future__ import annotations

from requirement_intelligence.knowledge_graph.identity import (
    KnowledgeEdgeId,
    KnowledgeEdgeVersion,
    KnowledgeFindingId,
    KnowledgeGraphFrameworkVersion,
    KnowledgeGraphId,
    KnowledgeGraphResultId,
    KnowledgeGraphResultVersion,
    KnowledgeNodeId,
    KnowledgeNodeVersion,
    KnowledgeObservationId,
    KnowledgeObservationVersion,
    KnowledgePolicyId,
    KnowledgePolicyVersion,
    KnowledgeSubgraphId,
)
from requirement_intelligence.knowledge_graph.knowledge_graph_service import (
    DormantKnowledgeGraphService,
    KnowledgeGraphService,
)
from requirement_intelligence.knowledge_graph.models import (
    KNOWLEDGE_GRAPH_RESULT_VERSION,
    HistoricalDatasetReference,
    KnowledgeEdge,
    KnowledgeEdgeType,
    KnowledgeFinding,
    KnowledgeFindingCategory,
    KnowledgeGraphResult,
    KnowledgeMetrics,
    KnowledgeNode,
    KnowledgeNodeType,
    KnowledgeObservation,
    KnowledgeObservationCategory,
    KnowledgeSeverity,
    KnowledgeSubgraph,
    KnowledgeSummary,
)
from requirement_intelligence.knowledge_graph.policy import (
    DEFAULT_KNOWLEDGE_GRAPH_POLICY_ID,
    KnowledgeGraphCapabilitySwitches,
    KnowledgeGraphPolicy,
    KnowledgeGraphPolicyBuilder,
    KnowledgeGraphThresholds,
    default_knowledge_graph_policy,
)
from requirement_intelligence.knowledge_graph.version import (
    KNOWLEDGE_GRAPH_FRAMEWORK_VERSION,
    KNOWLEDGE_POLICY_VERSION,
)

__all__ = [
    "DEFAULT_KNOWLEDGE_GRAPH_POLICY_ID",
    "KNOWLEDGE_GRAPH_FRAMEWORK_VERSION",
    "KNOWLEDGE_GRAPH_RESULT_VERSION",
    "KNOWLEDGE_POLICY_VERSION",
    "DormantKnowledgeGraphService",
    "HistoricalDatasetReference",
    "KnowledgeEdge",
    "KnowledgeEdgeId",
    "KnowledgeEdgeType",
    "KnowledgeEdgeVersion",
    "KnowledgeFinding",
    "KnowledgeFindingCategory",
    "KnowledgeFindingId",
    "KnowledgeGraphCapabilitySwitches",
    "KnowledgeGraphFrameworkVersion",
    "KnowledgeGraphId",
    "KnowledgeGraphPolicy",
    "KnowledgeGraphPolicyBuilder",
    "KnowledgeGraphResult",
    "KnowledgeGraphResultId",
    "KnowledgeGraphResultVersion",
    "KnowledgeGraphService",
    "KnowledgeGraphThresholds",
    "KnowledgeMetrics",
    "KnowledgeNode",
    "KnowledgeNodeId",
    "KnowledgeNodeType",
    "KnowledgeNodeVersion",
    "KnowledgeObservation",
    "KnowledgeObservationCategory",
    "KnowledgeObservationId",
    "KnowledgeObservationVersion",
    "KnowledgePolicyId",
    "KnowledgePolicyVersion",
    "KnowledgeSeverity",
    "KnowledgeSubgraph",
    "KnowledgeSubgraphId",
    "KnowledgeSummary",
    "default_knowledge_graph_policy",
]
