"""Deterministic candidate consolidation (CAP-086B).

``LearningCandidateClusterer`` is the **sole clustering authority**: it is
the only component that groups or consolidates :class:`LearningCandidate`
instances. It consumes **candidates only** (ADR-0029 D10) — never the
consumed ``OrganizationalMemoryResult``, and never a ``Learning``.

Consolidation is **deterministic equality only** — candidates that share
byte-identical ``proposed_change`` text are merged into one surviving
candidate; nothing else. This is never semantic similarity, never fuzzy
matching, never an embedding, never a probabilistic judgement (ADR-0029
Stage 4 of the CAP-086B brief, D18). Merging unions the merged candidates'
``source_best_practice_ids`` — no provenance reference is ever dropped
(ADR-0028 Recommendation 5, ADR-0029 D10) — and keeps the surviving
candidate's own identity (the lowest candidate id, a deterministic,
order-independent tie-break): this is a duplicate-elimination update to an
existing object's non-identity fields, never the construction of a new
candidate (ADR-0029 D10/Recommendation 19: only
:class:`~requirement_intelligence.learning.engine.
learning_candidate_collector.LearningCandidateCollector` constructs
:class:`LearningCandidate`).
"""

from __future__ import annotations

from collections import defaultdict

from requirement_intelligence.learning.models.learning_candidate import LearningCandidate


class LearningCandidateClusterer:
    """Consolidate duplicate-proposal candidates by equality. No semantic similarity."""

    def cluster(
        self, candidates: tuple[LearningCandidate, ...]
    ) -> tuple[LearningCandidate, ...]:
        """Deterministically merge candidates sharing identical proposed_change text."""
        groups: dict[str, list[LearningCandidate]] = defaultdict(list)
        for candidate in candidates:
            groups[candidate.proposed_change].append(candidate)

        consolidated: list[LearningCandidate] = []
        for group in groups.values():
            if len(group) == 1:
                consolidated.append(group[0])
                continue
            ordered = sorted(group, key=lambda candidate: str(candidate.candidate_id))
            survivor = ordered[0]
            merged_ids: list[str] = []
            seen: set[str] = set()
            for candidate in ordered:
                for source_id in candidate.source_best_practice_ids:
                    if source_id not in seen:
                        seen.add(source_id)
                        merged_ids.append(source_id)
            consolidated.append(
                survivor.model_copy(update={"source_best_practice_ids": tuple(merged_ids)})
            )

        consolidated.sort(key=lambda candidate: str(candidate.candidate_id))
        return tuple(consolidated)
