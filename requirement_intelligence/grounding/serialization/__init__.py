"""Grounding serialization — pure projections of a ``GroundingResult`` (CAP-077F.1).

Renders the runtime contract into execution artifacts. It computes nothing; it never
re-enters the grounding runtime. See ADR-0016 §D16.
"""

from __future__ import annotations

from requirement_intelligence.grounding.serialization.grounding_serializer import (
    GroundingSerializer,
)

__all__ = ["GroundingSerializer"]
