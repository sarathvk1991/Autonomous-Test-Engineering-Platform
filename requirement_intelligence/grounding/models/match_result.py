"""Canonical matching **output** model — the permanent GroundingStrategy result.

Every :class:`~requirement_intelligence.grounding.contracts.grounding_strategy.GroundingStrategy`
returns exactly one immutable :class:`MatchResult` — never a raw tuple of links. A
raw tuple is a frozen shape: the day a matcher wants to report *why* it rejected a
piece of evidence, or *how many* it examined, the return type has to change and every
caller with it. A `MatchResult` is **open for population, closed for redefinition**:
future strategies (deterministic, semantic, citation, hybrid) fill the same fields
with richer values; none redefines the shape.

The frozen contract between Matching and Classification
-------------------------------------------------------
`MatchResult` is the **only** thing Classification (CAP-077C) consumes. Two governed
invariants make that safe:

* **Match score is deterministic evidence similarity — nothing more.** The
  ``match_score`` on each :class:`RequirementEvidenceLink` is *not* confidence, *not*
  probability, *not* certainty, and *not* a support classification. It is the integer
  a Grounding Strategy computed from token overlap under a governed Matching Policy.
  Confidence and classification are computed *from* a `MatchResult`, downstream, and
  live on `GroundedRequirement` / `GroundingResult` — never here.
* **Full explainability without re-running the strategy.** Every fact needed to
  understand why evidence matched, why it failed, and why it ranked is already inside
  the `MatchResult` (links, statistics, and the structured explanation). A consumer
  never needs the strategy, normalizer, or policy again.

Scope boundary
--------------
A `MatchResult` is the **matcher's** output: links, the matcher's statistics, and the
matcher's explanation. :class:`MatchExplanation` (matcher-scoped: matched/unmatched
terms, rejected evidence, the evaluation summary) is deliberately distinct from
``GroundingExplanation`` (requirement-scoped: support, confidence breakdown,
recommendations).

Versioning
----------
:data:`MATCH_RESULT_VERSION` versions the ``MatchResult`` *schema*, carried on every
result as ``result_version``. It is independent of the producing strategy's version:
a strategy may change without changing this schema, and this schema may change without
bumping any strategy.

Determinism
-----------
No timestamps, no UUIDs, no runtime objects, no mutable collections, no service
references. The only execution identifier is ``context_id``, tying a result back to
the request it answered. Identical requests produce equal results.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.grounding.identity import MatchResultVersion
from requirement_intelligence.grounding.models.evidence import (
    EvidenceReference,
    RequirementEvidenceLink,
)
from requirement_intelligence.grounding.models.matching import MatchingRequirement
from shared.contracts.base import Schema

#: Version of the ``MatchResult`` schema (not the strategy). Advances additively;
#: a shape change a prior consumer could misread is MAJOR.
MATCH_RESULT_VERSION = MatchResultVersion(1, 0, 0)


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


class MatchEvaluationSummary(Schema):
    """A structured, deterministic summary of one match evaluation.

    Not generated prose — structured data a consumer (or a report) can read directly:
    how much evidence was seen and matched, the top score and the evidence that earned
    it, and the governed thresholds/ranking the evaluation applied. Every field is a
    pure observation; nothing here is confidence or classification.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    evidence_examined: int = Field(..., ge=0, description="Evidence items considered.")
    evidence_matched: int = Field(..., ge=0, description="Evidence items that produced a link.")
    highest_score: int = Field(
        ..., ge=0, le=100, description="Top match score (0 if none matched)."
    )
    winning_evidence: EvidenceReference | None = Field(
        default=None, description="The top-ranked evidence, or None when nothing matched."
    )
    threshold_summary: str = Field(
        ..., min_length=1, description="The governed thresholds the evaluation applied."
    )
    ranking_summary: str = Field(
        ...,
        min_length=1,
        description="The governed ranking and tie-breaker the evaluation applied.",
    )


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
    evaluation_summary: MatchEvaluationSummary | None = Field(
        default=None, description="Structured, deterministic summary of the evaluation."
    )


class MatchResult(Schema):
    """The complete, deterministic output of one GroundingStrategy execution.

    The permanent return type of ``GroundingStrategy.match`` and the frozen contract
    Classification consumes. It names the requirement it answers, the links it
    produced, the statistics it observed, its explanation, the strategy identity that
    produced it, and the schema version it conforms to.
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
    result_version: MatchResultVersion = Field(
        default=MATCH_RESULT_VERSION,
        description="Version of the MatchResult schema (not the strategy).",
    )
