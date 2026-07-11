"""The :class:`MatchingNormalizer` boundary and its full deterministic default.

``MatchingNormalizer`` is the permanent preprocessing abstraction below every
``GroundingStrategy``: one method, ``normalize(text) -> NormalizedText``. It owns
preprocessing only — no matching, no evidence, no requirements, no strategy logic.

``DefaultMatchingNormalizer`` (CAP-077B) is the full deterministic implementation. It
honours every switch on :class:`NormalizationConfiguration`:

* whitespace normalization (always),
* separator normalization — camelCase / acronym boundaries and ``_-/.:\\`` split,
* lowercase folding,
* punctuation removal,
* tokenization,
* abbreviation expansion (a small governed map),
* stop-word removal (a small governed set),
* duplicate-token removal,

and records pure :class:`NormalizationStatistics`. It is a pure function of ``(text,
configuration)``: no randomness, timestamps, UUIDs, or external state.
"""

from __future__ import annotations

import re
import string
from abc import ABC, abstractmethod

from requirement_intelligence.grounding.normalization.configuration import (
    NormalizationConfiguration,
    default_normalization_configuration,
)
from requirement_intelligence.grounding.normalization.models import (
    NormalizationStatistics,
    NormalizedText,
    NormalizedToken,
)

#: Separator characters normalized to spaces (identifier and path separators).
_SEPARATOR_CHARS = frozenset("_-/.:\\")

#: camelCase boundary: a lower/digit immediately followed by an upper (``authHandler``).
_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
#: Acronym boundary: an upper run followed by an upper+lower (``HTTPServer`` → ``HTTP Server``).
_ACRONYM_BOUNDARY = re.compile(r"(?<=[A-Z])(?=[A-Z][a-z])")

#: Governed stop-word set (lower-case). Small and deterministic; grows under a
#: versioned normalization-configuration change, never ad hoc.
_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "is",
        "it",
        "must",
        "of",
        "on",
        "or",
        "shall",
        "should",
        "that",
        "the",
        "this",
        "to",
        "with",
    }
)

#: Governed abbreviation-expansion map (lower-case). Deterministic; grows under a
#: versioned configuration change.
_ABBREVIATIONS = {
    "admin": "administrator",
    "auth": "authentication",
    "config": "configuration",
    "db": "database",
    "msg": "message",
    "spec": "specification",
}

_PUNCTUATION = frozenset(string.punctuation)


class MatchingNormalizer(ABC):
    """The permanent contract: raw text in, canonical :class:`NormalizedText` out."""

    @abstractmethod
    def normalize(self, text: str) -> NormalizedText:
        """Return the canonical normalized form of *text*. Must be deterministic."""
        raise NotImplementedError


class DefaultMatchingNormalizer(MatchingNormalizer):
    """The full deterministic normalizer, honouring every configuration switch."""

    def __init__(self, configuration: NormalizationConfiguration | None = None) -> None:
        """Store the governed normalization configuration."""
        self._configuration = configuration or default_normalization_configuration()

    @property
    def configuration(self) -> NormalizationConfiguration:
        """The governed configuration this normalizer applies."""
        return self._configuration

    def normalize(self, text: str) -> NormalizedText:
        """Run the deterministic normalization pipeline over *text*."""
        if not isinstance(text, str):
            raise TypeError(f"normalize expects str, got {type(text).__name__}.")

        config = self._configuration
        working = " ".join(text.split())

        separators_normalized = 0
        if config.normalize_separators:
            working, separators_normalized = _normalize_separators(working)

        case_conversions = 0
        if config.lowercase:
            lowered = working.lower()
            case_conversions = sum(1 for a, b in zip(working, lowered, strict=False) if a != b)
            working = lowered

        punctuation_removed = 0
        if config.remove_punctuation:
            working, punctuation_removed = _remove_punctuation(working)

        tokens = working.split()

        if config.expand_abbreviations:
            tokens = [_ABBREVIATIONS.get(token, token) for token in tokens]

        stop_words_removed = 0
        if config.remove_stop_words:
            kept = [token for token in tokens if token not in _STOP_WORDS]
            stop_words_removed = len(tokens) - len(kept)
            tokens = kept

        if config.deduplicate_tokens:
            tokens = _deduplicate(tokens)

        statistics = NormalizationStatistics(
            tokens_produced=len(tokens),
            punctuation_removed=punctuation_removed,
            case_conversions=case_conversions,
            separators_normalized=separators_normalized,
            stop_words_removed=stop_words_removed,
        )
        return NormalizedText(
            original=text,
            normalized=" ".join(tokens),
            tokens=tuple(NormalizedToken(value=token) for token in tokens),
            statistics=statistics,
            version=config.version,
        )


def _normalize_separators(text: str) -> tuple[str, int]:
    """Split camelCase/acronym boundaries and replace separator chars with spaces."""
    with_boundaries = _ACRONYM_BOUNDARY.sub(" ", _CAMEL_BOUNDARY.sub(" ", text))
    boundary_inserts = len(with_boundaries) - len(text)

    replaced = 0
    chars: list[str] = []
    for char in with_boundaries:
        if char in _SEPARATOR_CHARS:
            chars.append(" ")
            replaced += 1
        else:
            chars.append(char)
    return "".join(chars), boundary_inserts + replaced


def _remove_punctuation(text: str) -> tuple[str, int]:
    """Replace punctuation with spaces (preserving token boundaries) and count it."""
    removed = 0
    chars: list[str] = []
    for char in text:
        if char in _PUNCTUATION:
            chars.append(" ")
            removed += 1
        else:
            chars.append(char)
    return "".join(chars), removed


def _deduplicate(tokens: list[str]) -> list[str]:
    """Return *tokens* with duplicates dropped, preserving first-seen order."""
    seen: set[str] = set()
    unique: list[str] = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            unique.append(token)
    return unique
