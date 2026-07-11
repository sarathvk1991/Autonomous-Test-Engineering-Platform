"""Governed, versioned configuration for matching text normalization.

Following the "policy is data" principle (ADR-0015/0016), the switches that control
normalization live in an immutable, versioned configuration object rather than as
literals inside a normalizer. This lets a normalization change be a governed,
versioned decision, and lets every ``GroundingStrategy`` share one configuration so
they preprocess text identically.

CAP-077A.4 defines the flags and their defaults; the ``DefaultMatchingNormalizer``
honours only the minimal ones (lowercase, whitespace). The richer switches
(punctuation, stop words, deduplication, separators, abbreviations) are reserved for
the full normalizer that lands with the first strategy (CAP-077B), each advancing the
version under the golden re-baseline procedure.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.grounding.identity import MatchingNormalizationVersion
from shared.contracts.base import Schema

#: Version of the governed matching-normalization configuration. 1.0.0 is the
#: CAP-077A.4 foundation: the flags exist, minimal preprocessing is honoured.
MATCHING_NORMALIZATION_VERSION = MatchingNormalizationVersion(1, 0, 0)


class NormalizationConfiguration(Schema):
    """The governed switches that control matching text normalization.

    Flags only — no thresholds, weights, or algorithm literals. Immutable and
    versioned so a normalization result can always be attributed to the rules that
    produced it.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    version: MatchingNormalizationVersion = Field(
        default=MATCHING_NORMALIZATION_VERSION, description="Configuration version."
    )
    lowercase: bool = Field(default=True, description="Fold text to lower case.")
    remove_punctuation: bool = Field(default=True, description="Strip punctuation (CAP-077B).")
    remove_stop_words: bool = Field(default=False, description="Drop stop words (CAP-077B).")
    deduplicate_tokens: bool = Field(
        default=False, description="Collapse duplicate tokens (CAP-077B)."
    )
    normalize_separators: bool = Field(
        default=True, description="Normalize separators, e.g. camelCase/snake_case (CAP-077B)."
    )
    expand_abbreviations: bool = Field(
        default=False, description="Expand known abbreviations (CAP-077B)."
    )


def default_normalization_configuration() -> NormalizationConfiguration:
    """Return the default governed normalization configuration for this milestone."""
    return NormalizationConfiguration()
