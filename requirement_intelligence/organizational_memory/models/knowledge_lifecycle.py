"""The :class:`KnowledgeLifecycle` — one governed record of a knowledge object's
current retirement state.

A ``KnowledgeLifecycle`` **records** which governed state — ``ACTIVE``,
``DEPRECATED``, ``HISTORICAL``, or ``ARCHIVED`` — one Experience, Lesson, or
BestPractice currently occupies (ADR-0026 §Stage 7). It is a record, never a
transition: it never moves a subject between states, it only preserves the
current state and why (Recommendation 4 of ADR-0027).

No lifecycle transition happens here — a future engine (CAP-085B, reserved)
decides when to retire or reinstate a subject; this milestone only shapes the
contract.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.organizational_memory.identity import KnowledgeLifecycleId
from requirement_intelligence.organizational_memory.models.enums import KnowledgeLifecycleState
from shared.contracts.base import Schema


class KnowledgeLifecycle(Schema):
    """One governed lifecycle-state record — data only, never a transition.

    ``subject_id`` names the Experience, Lesson, or BestPractice this record
    concerns, by id only — never by embedding that subject's content
    (Recommendation 2/4 of ADR-0027). Retirement changes visibility only; the
    subject itself is never deleted (ADR-0026 §Stage 7).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    lifecycle_id: KnowledgeLifecycleId = Field(
        ..., description="Deterministic identity of this lifecycle record."
    )
    subject_id: str = Field(
        ...,
        min_length=1,
        description="Id of the Experience, Lesson, or BestPractice this record concerns.",
    )
    state: KnowledgeLifecycleState = Field(
        ..., description="The governed lifecycle state this subject currently occupies."
    )
    state_reason: str = Field(
        ..., min_length=1, description="Human-readable reason this state was recorded."
    )
