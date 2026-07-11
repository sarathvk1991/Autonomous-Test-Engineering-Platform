"""Canonical text-normalization framework for evidence matching (CAP-077A.4).

Preprocessing only — the permanent boundary that turns raw text into a canonical
``NormalizedText`` every ``GroundingStrategy`` consumes. It performs no matching,
classification, confidence, or ``MatchResult`` production.
"""

from __future__ import annotations

from requirement_intelligence.grounding.normalization.configuration import (
    MATCHING_NORMALIZATION_VERSION,
    NormalizationConfiguration,
    default_normalization_configuration,
)
from requirement_intelligence.grounding.normalization.models import (
    NormalizationStatistics,
    NormalizedText,
    NormalizedToken,
)
from requirement_intelligence.grounding.normalization.normalizer import (
    DefaultMatchingNormalizer,
    MatchingNormalizer,
)

__all__ = [
    "MATCHING_NORMALIZATION_VERSION",
    "DefaultMatchingNormalizer",
    "MatchingNormalizer",
    "NormalizationConfiguration",
    "NormalizationStatistics",
    "NormalizedText",
    "NormalizedToken",
    "default_normalization_configuration",
]
