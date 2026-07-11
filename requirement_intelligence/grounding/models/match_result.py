"""Canonical matching **output** model — the permanent GroundingStrategy result.

Every :class:`~requirement_intelligence.grounding.contracts.grounding_strategy.GroundingStrategy`
returns exactly one immutable :class:`MatchResult` — never a raw tuple of links. A
raw tuple is a frozen shape: the day a matcher wants to report *why* it rejected a
piece of evidence, or *how many* it examined, the return type has to change and every
caller with it. A `MatchResult` is **open for population, closed for redefinition**:
future strategies (deterministic, semantic, citation, hybrid) fill the same fields
with richer values; none redefines the shape.

Scope boundary
--------------
A `MatchResult` is the **matcher's** output. It carries links, the matcher's own
statistics, and the matcher's own explanation. It carries **no** classification,
confidence, or grounding metrics — those are the Grounding Service's job, computed
*from* a `MatchResult`, and they live on `GroundedRequirement` / `GroundingResult`.
:class:`MatchExplanation` (matcher-scoped: matched/unmatched terms, rejected
evidence) is deliberately distinct from ``GroundingExplanation`` (requirement-scoped:
support, confidence breakdown, recommendations).

Determinism
-----------
No timestamps, no UUIDs, no runtime objects, no mutable collections, no service
references. The only execution identifier is ``context_id``, tying a result back to
the request it answered. Identical requests produce equal results.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.grounding.models.evidence import (
    EvidenceReference,
    RequirementEvidenceLink,
)
from requirement_intelligence.grounding.models.matching import MatchingRequirement
from shared.contracts.base import Schema


class MatchStatistics(Schema):
    """Deterministic, non-judgemental measurements taken during one match.

    Pure observations only — counts, never scores, percentages, confidence, or
    classifications. They exist so a match is auditable ("it examined 20 evidence
    items, matched 3, rejected 17") without re-running the matcher.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    evidence_examined: int = Field(..., ge=0, description="Evidence items the matcher considered.")
    evidence_matched: int = Field(..., ge=0, description="Evidence items that produced a link.")
    evidence_rejected: int = Field(..., ge=0, description="Evidence items considered and dropped.")
    matched_term_count: int = Field(..., ge=0, description="Distinct terms that earned a match.")
    exact_matches: int = Field(default=0, ge=0, description="Matches by exact term equality.")
    partial_matches: int = Field(default=0, ge=0, description="Matches by partial term overlap.")
    normalization_operations: int = Field(
        default=0, ge=0, description="Text-normalisation steps performed (observation only)."
    )

    @model_validator(mode="after")
    def _validate_statistics(self) -> MatchStatistics:
        """Counts must be internally coherent — pure arithmetic, no judgement."""
        if self.evidence_matched > self.evidence_examined:
            raise ValueError("evidence_matched cannot exceed evidence_examined.")
        if self.evidence_rejected > self.evidence_examined:
            raise ValueError("evidence_rejected cannot exceed evidence_examined.")
        if self.exact_matches + self.partial_matches > self.evidence_matched:
            raise ValueError("exact + partial matches cannot exceed evidence_matched.")
        return self


class MatchExplanation(Schema):
    """Structured, matcher-scoped explainability for one match.

    Architectural data only — no generated prose, no confidence reasoning, no
    hallucination judgement. The Grounding Service turns this, later, into the
    requirement-scoped ``GroundingExplanation``.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    summary: str = Field(default="", description="Short, factual matcher summary (may be empty).")
    matched_terms: tuple[str, ...] = Field(
        default=(), description="Terms that produced at least one link."
    )
    unmatched_terms: tuple[str, ...] = Field(
        default=(), description="Requirement terms that found no evidence."
    )
    rejected_evidence: tuple[EvidenceReference, ...] = Field(
        default=(), description="Evidence the matcher considered and dropped."
    )
    notes: tuple[str, ...] = Field(default=(), description="Free-form matcher observations.")


class MatchResult(Schema):
    """The complete, deterministic output of one GroundingStrategy execution.

    The permanent return type of ``GroundingStrategy.match``. It names the requirement
    it answers, the links it produced, the statistics it observed, its explanation, and
    the strategy identity that produced it.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    context_id: str = Field(..., min_length=1, description="Id of the context this result answers.")
    requirement: MatchingRequirement = Field(..., description="The requirement that was matched.")
    links: tuple[RequirementEvidenceLink, ...] = Field(
        default=(), description="The requirement-to-evidence links found (may be empty)."
    )
    statistics: MatchStatistics = Field(..., description="Deterministic match observations.")
    explanation: MatchExplanation = Field(..., description="Structured matcher explainability.")
    strategy_name: str = Field(
        ..., min_length=1, description="Stable name of the producing strategy."
    )
    strategy_version: str = Field(
        ..., min_length=1, description="Self-declared version of the producing strategy."
    )
