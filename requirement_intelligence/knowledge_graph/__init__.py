"""Knowledge Graph Framework (CAP-084A architecture; CAP-084B deterministic engine).

The second Layer 2 capability defined by ADR-0020 (Platform Evolution Roadmap),
following Continuous Improvement (ADR-0022), and governed by ADR-0021
(Cross-Execution Data Architecture & Historical Intelligence Constitution) and
ADR-0023 (Knowledge Graph Framework). It owns the platform's single structural
authority — nodes, governed relationship edges, subgraphs, observations, and
findings — built from a **Historical Dataset**, never a single execution. It is
a **consumer of Historical Truth only** (ADR-0021 §Stage 8): it never imports a
Layer 1 subsystem, never imports Continuous Improvement, never re-runs
Requirement Enhancement, Grounding, Validation, CP1, Quality Governance, or
Recommendation, and never reaches into the Execution Package.

**Runtime status (CAP-084B):** ``DeterministicKnowledgeGraphEngine`` projects
nodes and edges, detects connected-component subgraphs, generates deterministic
structural observations, and detects deterministic structural findings —
entirely from the governed ``KnowledgeGraphRuleCatalog`` and
``KnowledgeGraphPolicy``, via independent, modular collaborators (never one
large engine). It resolves each ``HistoricalDatasetReference`` through a
private, replaceable ``HistoricalDatasetProvider`` (the Historical Dataset
Resolution Principle, mirrored from ADR-0022 §D9) and never recursively
consumes a prior ``KnowledgeGraphResult`` or any of its constituents. The
subsystem is still **not wired into** any execution pipeline — nothing calls
``build`` at runtime — so runtime behaviour is byte-identical and the golden
baseline is unchanged. Governed by ADR-0023.
"""

from __future__ import annotations

from requirement_intelligence.knowledge_graph.engine import (
    DeterministicHistoricalDatasetProvider,
    DeterministicKnowledgeGraphEngine,
    HistoricalDataset,
    HistoricalDatasetProvider,
    HistoricalExecutionRecord,
)
from requirement_intelligence.knowledge_graph.identity import (
    KnowledgeEdgeId,
    KnowledgeEdgeVersion,
    KnowledgeFindingId,
    KnowledgeGraphFrameworkVersion,
    KnowledgeGraphId,
    KnowledgeGraphResultId,
    KnowledgeGraphResultVersion,
    KnowledgeGraphRuleCatalogVersion,
    KnowledgeGraphRuleVersion,
    KnowledgeNodeId,
    KnowledgeNodeVersion,
    KnowledgeObservationId,
    KnowledgeObservationVersion,
    KnowledgePolicyId,
    KnowledgePolicyVersion,
    KnowledgeSubgraphId,
)
from requirement_intelligence.knowledge_graph.knowledge_graph_service import (
    DeterministicKnowledgeGraphService,
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
from requirement_intelligence.knowledge_graph.rules import (
    KNOWLEDGE_GRAPH_RULE_CATALOG_VERSION,
    KNOWLEDGE_GRAPH_RULE_VERSION,
    KnowledgeGraphPolicyToggle,
    KnowledgeGraphRule,
    KnowledgeGraphRuleBuilder,
    KnowledgeGraphRuleCatalog,
    KnowledgeGraphRuleFamily,
    default_knowledge_graph_rule_catalog,
)
from requirement_intelligence.knowledge_graph.version import (
    KNOWLEDGE_GRAPH_FRAMEWORK_VERSION,
    KNOWLEDGE_POLICY_VERSION,
)

__all__ = [
    "DEFAULT_KNOWLEDGE_GRAPH_POLICY_ID",
    "KNOWLEDGE_GRAPH_FRAMEWORK_VERSION",
    "KNOWLEDGE_GRAPH_RESULT_VERSION",
    "KNOWLEDGE_GRAPH_RULE_CATALOG_VERSION",
    "KNOWLEDGE_GRAPH_RULE_VERSION",
    "KNOWLEDGE_POLICY_VERSION",
    "DeterministicHistoricalDatasetProvider",
    "DeterministicKnowledgeGraphEngine",
    "DeterministicKnowledgeGraphService",
    "HistoricalDataset",
    "HistoricalDatasetProvider",
    "HistoricalDatasetReference",
    "HistoricalExecutionRecord",
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
    "KnowledgeGraphPolicyToggle",
    "KnowledgeGraphResult",
    "KnowledgeGraphResultId",
    "KnowledgeGraphResultVersion",
    "KnowledgeGraphRule",
    "KnowledgeGraphRuleBuilder",
    "KnowledgeGraphRuleCatalog",
    "KnowledgeGraphRuleCatalogVersion",
    "KnowledgeGraphRuleFamily",
    "KnowledgeGraphRuleVersion",
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
    "default_knowledge_graph_rule_catalog",
]
