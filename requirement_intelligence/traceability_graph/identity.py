"""Deterministic identity minting for the Traceability Graph.

Mirrors the ADR-0023 Knowledge Graph identity pattern
(`requirement_intelligence/knowledge_graph/identity/knowledge_graph_identity.py`):
every id is a pure function of its own inputs — SHA-256 digested, no UUID, no
clock — so the same requirement set + feature package + on-disk `.feature`
files always mint the same graph.

This module reuses that *pattern* only, at a scale proportionate to this
build's own minimal scope: plain `str` ids, not a dedicated identifier
value-object hierarchy (ADR-0023's `_StringIdentifier` base class and its
eight independent version axes are not reused here — this build does not
call or modify `requirement_intelligence.knowledge_graph`, per the "GRAPHS
DESIGN SURFACED" note in `docs/architecture/mentor-feedback-scoping.md`
item #3: reuse the pattern, never the frozen service).
"""

from __future__ import annotations

import hashlib


def node_id_for(node_type: str, referenced_id: str) -> str:
    """Mint the deterministic id for the node naming *referenced_id* of *node_type*."""
    digest = hashlib.sha256(f"{node_type}:{referenced_id}".encode()).hexdigest()
    return f"tn-{digest[:12]}"


def edge_id_for(edge_type: str, source_node_id: str, target_node_id: str) -> str:
    """Mint the deterministic id for the *edge_type* edge from *source* to *target*."""
    digest = hashlib.sha256(f"{edge_type}:{source_node_id}:{target_node_id}".encode()).hexdigest()
    return f"te-{digest[:12]}"


def graph_id_for(run_id: str) -> str:
    """Mint the deterministic graph id for *run_id*."""
    digest = hashlib.sha256(run_id.encode()).hexdigest()
    return f"tg-{digest[:12]}"


__all__ = ["edge_id_for", "graph_id_for", "node_id_for"]
