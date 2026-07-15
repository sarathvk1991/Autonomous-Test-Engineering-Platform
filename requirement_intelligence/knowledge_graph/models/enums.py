"""Controlled vocabularies for the Knowledge Graph Framework.

String-valued (:class:`~enum.StrEnum`) members serialise cleanly to JSON and
compare equal to their plain-string value, matching the convention of every prior
subsystem's ``models.enums`` module. These enums carry **no runtime logic**; they
are the governed vocabulary the models are classified against. No node, edge,
observation, or finding is derived here — that is a future engine's job (CAP-084B).
"""

from __future__ import annotations

from enum import StrEnum


class KnowledgeNodeType(StrEnum):
    """The governed vocabulary of what one ``KnowledgeNode`` represents.

    Each member names one platform entity type the node references by id only —
    never the entity's own content (Recommendation 2 of ADR-0023).
    """

    REQUIREMENT = "requirement"
    MODULE = "module"
    COMPONENT = "component"
    EXECUTION = "execution"
    FINDING = "finding"
    RECOMMENDATION = "recommendation"
    CAPABILITY = "capability"
    DATASET = "dataset"
    DOCUMENT = "document"


class KnowledgeEdgeType(StrEnum):
    """The governed vocabulary of what one ``KnowledgeEdge`` relates.

    No free-form edge type is permitted (Recommendation 3 of ADR-0023): every
    relationship the graph records is one of these governed members.
    """

    DEPENDS_ON = "depends_on"
    IMPLEMENTS = "implements"
    GENERATED_BY = "generated_by"
    REFERENCES = "references"
    TRACEABLE_TO = "traceable_to"
    DERIVED_FROM = "derived_from"
    RELATED_TO = "related_to"
    BELONGS_TO = "belongs_to"
    USES = "uses"


class KnowledgeSeverity(StrEnum):
    """The severity of a ``KnowledgeFinding``. Recorded, never computed."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class KnowledgeFindingCategory(StrEnum):
    """The governed vocabulary of what a ``KnowledgeFinding`` names.

    Each member names one deterministically distinguishable structural issue —
    never a probabilistic judgement (Recommendation 7 of ADR-0023).
    """

    ISOLATED_NODE = "isolated_node"
    BROKEN_LINEAGE = "broken_lineage"
    DUPLICATE_EDGE = "duplicate_edge"
    ORPHAN_GRAPH = "orphan_graph"
    MISSING_RELATIONSHIP = "missing_relationship"
    CYCLE = "cycle"


class KnowledgeObservationCategory(StrEnum):
    """The governed vocabulary of what a ``KnowledgeObservation`` records.

    Observation only, never a judgement — a fact about the graph's structure, not
    a problem with it (that is the corresponding, disjoint ``KnowledgeFinding``
    vocabulary above).
    """

    NODE_COVERAGE = "node_coverage"
    EDGE_COVERAGE = "edge_coverage"
    LINEAGE_DEPTH = "lineage_depth"
    STRUCTURAL_CONSISTENCY = "structural_consistency"
