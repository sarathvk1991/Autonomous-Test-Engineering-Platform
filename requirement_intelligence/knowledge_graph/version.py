"""Canonical version constants for the Knowledge Graph Framework.

Kept in the knowledge_graph package (not ``platform_metadata``) so registering
the framework changes no existing platform catalogue or manifest field, and the
Architecture Version stays 1.2.0 — mirroring ``continuous_improvement/version.py``
(ADR-0022) and ``recommendation/version.py`` (ADR-0019).
"""

from __future__ import annotations

from requirement_intelligence.knowledge_graph.identity import (
    KnowledgeGraphFrameworkVersion,
    KnowledgePolicyVersion,
)

#: Version of the Knowledge Graph Framework code/contract. 1.0.0 is the CAP-084A
#: foundation: canonical models, typed identities, enumerations, the governed
#: policy and its builder, and the dormant Knowledge Graph service contract.
KNOWLEDGE_GRAPH_FRAMEWORK_VERSION = KnowledgeGraphFrameworkVersion(1, 0, 0)

#: Version of the governed default knowledge graph policy. 1.0.0 is the CAP-084A
#: foundation policy (capability switches and deterministic thresholds as data
#: only, no capability exercised — ``enable_deterministic_engine`` reserved off).
KNOWLEDGE_POLICY_VERSION = KnowledgePolicyVersion(1, 0, 0)
