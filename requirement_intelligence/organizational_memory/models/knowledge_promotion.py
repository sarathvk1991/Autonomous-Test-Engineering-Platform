"""The :class:`KnowledgePromotion` — one governed record of a promotion event.

A ``KnowledgePromotion`` **records** that one or more lower-rung knowledge
objects were promoted into one or more higher-rung ones — Experience → Lesson,
or Lesson → BestPractice (ADR-0026 §Stage 6). It is history, not action: it
never performs a promotion, it only preserves complete provenance of one that
already happened (Recommendation 5 of ADR-0027).

No promotion happens here — a future engine (CAP-085B, reserved) decides when
to promote and constructs the higher-rung object plus this record together;
this milestone only shapes the contract.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.organizational_memory.identity import (
    KnowledgePromotionId,
    OrganizationalMemoryPolicyVersion,
)
from requirement_intelligence.organizational_memory.models.enums import (
    OrganizationalMemoryConfidence,
)
from shared.contracts.base import Schema


class KnowledgePromotion(Schema):
    """One governed promotion record — data only, never the act of promotion itself.

    ``source_ids`` / ``target_ids`` name the lower-rung and higher-rung
    knowledge objects a promotion connected, by id only — never by embedding
    either object's content (Recommendation 2/5 of ADR-0027). Ids are plain
    strings because a promotion may connect ``Experience``, ``Lesson``, or
    ``BestPractice`` objects depending on which promotion step this record
    describes — never a single fixed identity type.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    promotion_id: KnowledgePromotionId = Field(
        ..., description="Deterministic identity of this promotion record."
    )
    source_ids: tuple[str, ...] = Field(
        default=(), description="Lower-rung knowledge object ids this promotion connected."
    )
    target_ids: tuple[str, ...] = Field(
        default=(), description="Higher-rung knowledge object ids this promotion produced."
    )
    rationale: str = Field(
        ..., min_length=1, description="Human-readable reason this promotion occurred."
    )
    promoted_at: datetime = Field(..., description="When this promotion occurred.")
    confidence: OrganizationalMemoryConfidence = Field(
        ..., description="Governed confidence recorded at the moment of promotion."
    )
    policy_version: OrganizationalMemoryPolicyVersion = Field(
        ..., description="Version of the governing policy in force when this promotion occurred."
    )

    @model_validator(mode="after")
    def _validate_promotion(self) -> KnowledgePromotion:
        """A promotion must name at least one source and at least one target."""
        if not self.source_ids:
            raise ValueError(
                f"KnowledgePromotion {self.promotion_id!r} must reference at least one "
                f"source id — a promotion with no traceable origin is not explainable."
            )
        if not self.target_ids:
            raise ValueError(
                f"KnowledgePromotion {self.promotion_id!r} must reference at least one "
                f"target id — a promotion that produced nothing is not a promotion."
            )
        return self
