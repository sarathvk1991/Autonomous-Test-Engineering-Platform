"""Controlled vocabularies for the governed Matching Policy.

Governed data only — these name the keys a matcher may rank on and tie-break by.
They carry no logic; a :class:`GroundingStrategy` reads them and decides how to apply
them.
"""

from __future__ import annotations

from enum import StrEnum


class MatchRankingKey(StrEnum):
    """A key a matcher may rank competing evidence links by, in policy order."""

    MATCH_SCORE = "match_score"
    EXACT_TERMS = "exact_terms"
    TOKEN_OVERLAP = "token_overlap"  # noqa: S105 — a ranking key name, not a secret
    SOURCE_DIVERSITY = "source_diversity"


class MatchTieBreaker(StrEnum):
    """The final total-order key applied when ranking keys tie."""

    SOURCE_RECORD_ID = "source_record_id"
    SOURCE_SYSTEM = "source_system"
