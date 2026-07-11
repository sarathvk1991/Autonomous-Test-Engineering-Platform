"""The :class:`GroundingStrategy` contract — the matching extension point.

The Grounding Service (a later milestone) owns orchestration; a ``GroundingStrategy``
owns matching. This module defines only the **contract**: no strategy is implemented
here (CAP-077A performs no matching). The first implementation — deterministic text
matching — arrives in CAP-077B, and future strategies (semantic, citation, hybrid)
plug in behind this same protocol without disturbing the models or the service.

A conforming strategy MUST be a pure, reproducible function of its inputs: identical
inputs produce byte-identical links, independent of iteration order.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from requirement_intelligence.grounding.models.evidence import (
    EvidenceReference,
    RequirementEvidenceLink,
)
from requirement_intelligence.models.enums import SourceCategory


@runtime_checkable
class GroundingStrategy(Protocol):
    """Decide which evidence supports a requirement, and how.

    A strategy answers exactly one question and owns nothing else — it does not
    classify, score confidence, explain, or emit metrics; those belong to the
    Grounding Service.
    """

    @property
    def name(self) -> str:
        """Stable identifier of this strategy (recorded on the result)."""
        ...

    def match(
        self,
        requirement_text: str,
        requirement_domain: SourceCategory,
        evidence: Sequence[EvidenceReference],
    ) -> tuple[RequirementEvidenceLink, ...]:
        """Return the requirement-to-evidence links for one requirement.

        Zero links is a valid, meaningful answer (it drives an UNSUPPORTED verdict).
        Implementations must be deterministic: evidence is supplied in canonical
        ``(source_system, source_record_id)`` order and ties broken by that order.
        """
        ...
