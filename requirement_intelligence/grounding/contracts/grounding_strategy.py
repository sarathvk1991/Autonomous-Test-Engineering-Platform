"""The :class:`GroundingStrategy` contract — the matching extension point.

The Grounding Service owns orchestration; a ``GroundingStrategy`` owns matching.
This module defines only the **contract**: no strategy is implemented here. The
first implementation — deterministic text matching — arrives in CAP-077B, and
future strategies (semantic, citation, hybrid) plug in behind this same protocol
without disturbing the models or the service.

Frozen contract shape (CAP-077A.2 input, CAP-077A.3 output)
-----------------------------------------------------------
``match`` takes a single canonical :class:`MatchingRequest` — one requirement plus
the evidence corpus, configuration, and versions — and returns a single canonical
:class:`MatchResult`. **This signature is frozen**: CAP-077B and every later strategy
implement it without changing it.

* **Canonical inputs only.** A strategy depends solely on the grounding subsystem's
  own models. It never imports ``EngineeringContext``, ``AnalysisResult``,
  ``ParsedResponse``, or any runtime object — the ``MatchingContextBuilder`` has
  already translated those away.
* **A canonical result, not a raw tuple.** Returning :class:`MatchResult` (rather than
  ``tuple[RequirementEvidenceLink, ...]``) means a matcher can report statistics and a
  structured explanation the day it needs to, with **no change to the return type or
  any caller**. The result is open for population, closed for redefinition.
* **Independent, parallelisable evaluation.** The service fans a
  :class:`MatchingContext` out into N ``MatchingRequest``\\ s
  (``MatchingContext.to_requests``) and evaluates each on its own. A future parallel
  executor needs no change to this contract.

A conforming strategy MUST be a pure, reproducible function of its input: identical
requests produce equal results, independent of iteration order.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from requirement_intelligence.grounding.models.match_result import MatchResult
from requirement_intelligence.grounding.models.matching import MatchingRequest


@runtime_checkable
class GroundingStrategy(Protocol):
    """Decide which evidence supports a requirement, and how.

    A strategy answers exactly one question and owns nothing else — it does not
    classify, score confidence, explain (at requirement scope), or emit grounding
    metrics; those belong to the Grounding Service.
    """

    @property
    def name(self) -> str:
        """Stable identifier of this strategy (recorded on the result)."""
        ...

    def match(self, request: MatchingRequest) -> MatchResult:
        """Return the canonical :class:`MatchResult` for one :class:`MatchingRequest`.

        A result with zero links is valid and meaningful (it drives an UNSUPPORTED
        verdict downstream). Implementations must be deterministic: the evidence corpus
        arrives in canonical ``(source_system, source_record_id)`` order and ties are
        broken by that same order.
        """
        ...
