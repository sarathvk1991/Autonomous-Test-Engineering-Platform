"""The :class:`MatchingNormalizer` boundary and its minimal default.

``MatchingNormalizer`` is the permanent preprocessing abstraction that sits below
every ``GroundingStrategy``: one method, ``normalize(text) -> NormalizedText``. It
owns preprocessing only — no matching, no evidence, no requirements, no strategy
logic. Fixing it here means every present and future strategy (deterministic,
semantic, hybrid) consumes *identically* normalized inputs instead of each
re-implementing preprocessing.

``DefaultMatchingNormalizer`` is construction-only and deliberately minimal: it
establishes the API with just lowercase + whitespace normalization. Full tokenization
(punctuation stripping, camelCase/snake_case splitting, stop-word removal,
abbreviation expansion) is **not** implemented here — those governed flags exist on
:class:`NormalizationConfiguration` and are honoured by the full normalizer that lands
with the first strategy (CAP-077B).
"""

from __future__ import annotations

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


class MatchingNormalizer(ABC):
    """The permanent contract: raw text in, canonical :class:`NormalizedText` out."""

    @abstractmethod
    def normalize(self, text: str) -> NormalizedText:
        """Return the canonical normalized form of *text*.

        Implementations must be deterministic: identical input yields an equal
        ``NormalizedText``. They perform preprocessing only — never matching.
        """
        raise NotImplementedError


class DefaultMatchingNormalizer(MatchingNormalizer):
    """Minimal deterministic normalizer establishing the permanent API.

    Honours only ``lowercase`` and whitespace collapse; the richer configuration
    flags are reserved for CAP-077B and are intentionally not applied here.
    """

    def __init__(self, configuration: NormalizationConfiguration | None = None) -> None:
        """Store the governed normalization configuration."""
        self._configuration = configuration or default_normalization_configuration()

    @property
    def configuration(self) -> NormalizationConfiguration:
        """The governed configuration this normalizer applies."""
        return self._configuration

    def normalize(self, text: str) -> NormalizedText:
        """Lowercase (if enabled) and collapse whitespace; split into simple tokens."""
        if not isinstance(text, str):
            raise TypeError(f"normalize expects str, got {type(text).__name__}.")

        collapsed = " ".join(text.split())
        if self._configuration.lowercase:
            normalized = collapsed.lower()
            case_conversions = sum(1 for a, b in zip(collapsed, normalized, strict=False) if a != b)
        else:
            normalized = collapsed
            case_conversions = 0

        tokens = tuple(NormalizedToken(value=word) for word in normalized.split())
        statistics = NormalizationStatistics(
            tokens_produced=len(tokens),
            case_conversions=case_conversions,
        )
        return NormalizedText(
            original=text,
            normalized=normalized,
            tokens=tokens,
            statistics=statistics,
            version=self._configuration.version,
        )
