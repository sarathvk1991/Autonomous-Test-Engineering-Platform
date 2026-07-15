"""Deterministic node and edge projection (CAP-084B). Engine-internal only."""

from __future__ import annotations

from requirement_intelligence.knowledge_graph.engine.projection.edge_projector import EdgeProjector
from requirement_intelligence.knowledge_graph.engine.projection.node_projector import NodeProjector

__all__ = ["EdgeProjector", "NodeProjector"]
