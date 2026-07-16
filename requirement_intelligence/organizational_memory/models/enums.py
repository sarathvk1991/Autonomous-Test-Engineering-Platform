"""Controlled vocabularies for the Organizational Memory Framework.

String-valued (:class:`~enum.StrEnum`) members serialise cleanly to JSON and
compare equal to their plain-string value, matching the convention of every
prior subsystem's ``models.enums`` module. These enums carry **no runtime
logic**; they are the governed vocabulary the models are classified against.
No experience is captured, no lesson is promoted, no best practice is
institutionalized, and no lifecycle transition happens here — that is a future
engine's job (CAP-085B, reserved).
"""

from __future__ import annotations

from enum import StrEnum


class OrganizationalMemorySourceLayer(StrEnum):
    """The governed vocabulary of which completed Layer 2 peer an ``Experience``
    was captured from.

    Organizational Memory is the fan-in consumer of both Continuous Improvement
    and Knowledge Graph (ADR-0025 §Stage 7/8) — every ``Experience`` names
    exactly one of these two sources, by reference only (Recommendation 2 of
    ADR-0027).
    """

    CONTINUOUS_IMPROVEMENT = "continuous_improvement"
    KNOWLEDGE_GRAPH = "knowledge_graph"


class OrganizationalMemoryConfidence(StrEnum):
    """The governed confidence vocabulary (ADR-0026 §Stage 8).

    Confidence is metadata, never truth (Recommendation 5 of ADR-0027): it
    describes how strongly the referenced evidence supports a claim, and is
    tracked independently of the claim's own immutable content.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERIFIED = "verified"


class KnowledgeLifecycleState(StrEnum):
    """The governed lifecycle-state vocabulary (ADR-0026 §Stage 7).

    Retirement changes visibility only; nothing is ever deleted (Recommendation
    4 of ADR-0027). No engine exists yet to transition a subject between these
    states — that is CAP-085B's job; this vocabulary only names the governed
    states a future ``KnowledgeLifecycle`` record may hold.
    """

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    HISTORICAL = "historical"
    ARCHIVED = "archived"
