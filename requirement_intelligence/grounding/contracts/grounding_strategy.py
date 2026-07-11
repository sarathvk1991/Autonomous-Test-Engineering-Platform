"""The :class:`GroundingStrategy` contract — the matching extension point.

The Grounding Service owns orchestration; a ``GroundingStrategy`` owns matching.
This module defines only the **contract**: no strategy is implemented here. The
first implementation — deterministic text matching — arrives in CAP-077B, and
future strategies (semantic, citation, hybrid) plug in behind this same protocol
without disturbing the models or the service.

Contract shape (CAP-077A.2)
---------------------------
``match`` takes a single canonical :class:`MatchingRequest` — one requirement plus
the evidence corpus, configuration, and versions — and returns that requirement's
links. Two reasons this per-request shape was chosen over ``match(context)``:

1. **Canonical inputs only.** A strategy depends solely on the grounding
   subsystem's own models. It never imports ``EngineeringContext``,
   ``AnalysisResult``, ``ParsedResponse``, or any runtime object — the
   ``MatchingContextBuilder`` has already translated those away.
2. **Independent, parallelisable evaluation.** The service fans a
   :class:`MatchingContext` out into N ``MatchingRequest``\\ s
   (``MatchingContext.to_requests``) and evaluates each on its own. A future
   parallel executor needs no change to this contract.

A conforming strategy MUST be a pure, reproducible function of its input: identical
requests produce byte-identical links, independent of iteration order.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from requirement_intelligence.grounding.models.evidence import RequirementEvidenceLink
from requirement_intelligence.grounding.models.matching import MatchingRequest


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

    def match(self, request: MatchingRequest) -> tuple[RequirementEvidenceLink, ...]:
        """Return the requirement-to-evidence links for one :class:`MatchingRequest`.

        Zero links is a valid, meaningful answer (it drives an UNSUPPORTED verdict).
        Implementations must be deterministic: the evidence corpus arrives in
        canonical ``(source_system, source_record_id)`` order and ties are broken by
        that same order.
        """
        ...
