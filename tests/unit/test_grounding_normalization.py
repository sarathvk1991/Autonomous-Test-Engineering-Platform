"""Unit tests for the canonical matching text-normalization framework (CAP-077A.4).

Cover the models (immutability, serialization, equality, the token-count invariant),
the versioned configuration, the abstract contract and its minimal default, the
PlatformContext registration, and determinism (identical input → equal output).
No matching is performed.
"""

from __future__ import annotations

from abc import ABC

import pytest
from pydantic import ValidationError

from requirement_intelligence.grounding import (
    MATCHING_NORMALIZATION_VERSION,
    DefaultMatchingNormalizer,
    MatchingNormalizationVersion,
    MatchingNormalizer,
    NormalizationConfiguration,
    NormalizationStatistics,
    NormalizedText,
    NormalizedToken,
    default_normalization_configuration,
)
from requirement_intelligence.platform.platform_context import PlatformContext


@pytest.mark.unit
class TestNormalizationModels:
    def test_token_is_immutable(self) -> None:
        token = NormalizedToken(value="nosniff")
        with pytest.raises(ValidationError):
            token.value = "other"  # type: ignore[misc]

    def test_normalized_text_round_trips_camel_case(self) -> None:
        text = DefaultMatchingNormalizer().normalize("Set the Nosniff Header")
        dumped = text.model_dump(mode="json", by_alias=True)
        assert "tokensProduced" in dumped["statistics"]
        assert NormalizedText.model_validate(dumped) == text

    def test_token_count_invariant_is_enforced(self) -> None:
        with pytest.raises(ValidationError):
            NormalizedText(
                original="a b",
                normalized="a b",
                tokens=(NormalizedToken(value="a"), NormalizedToken(value="b")),
                statistics=NormalizationStatistics(tokens_produced=5),
                version=MATCHING_NORMALIZATION_VERSION,
            )

    def test_statistics_are_pure_observations(self) -> None:
        stats = NormalizationStatistics(tokens_produced=3, case_conversions=2)
        assert stats.tokens_produced == 3
        assert stats.stop_words_removed == 0


@pytest.mark.unit
class TestNormalizationConfiguration:
    def test_defaults(self) -> None:
        config = default_normalization_configuration()
        assert config.version == MATCHING_NORMALIZATION_VERSION
        assert config.lowercase is True
        assert config.remove_stop_words is False

    def test_is_versioned_and_immutable(self) -> None:
        config = default_normalization_configuration()
        assert isinstance(config.version, MatchingNormalizationVersion)
        with pytest.raises(ValidationError):
            config.lowercase = False  # type: ignore[misc]


@pytest.mark.unit
class TestMatchingNormalizer:
    def test_contract_is_abstract(self) -> None:
        assert issubclass(MatchingNormalizer, ABC)
        with pytest.raises(TypeError):
            MatchingNormalizer()  # type: ignore[abstract]

    def test_default_lowercases_and_collapses_whitespace(self) -> None:
        result = DefaultMatchingNormalizer().normalize("  Set   the  NOSNIFF  Header ")
        assert result.normalized == "set the nosniff header"
        assert [t.value for t in result.tokens] == ["set", "the", "nosniff", "header"]
        assert result.statistics.tokens_produced == 4
        assert result.statistics.case_conversions > 0

    def test_default_respects_lowercase_disabled(self) -> None:
        config = NormalizationConfiguration(lowercase=False)
        result = DefaultMatchingNormalizer(config).normalize("Keep CASE")
        assert result.normalized == "Keep CASE"
        assert result.statistics.case_conversions == 0

    def test_preserves_original_verbatim(self) -> None:
        raw = "  Weird   Spacing "
        result = DefaultMatchingNormalizer().normalize(raw)
        assert result.original == raw

    def test_empty_text_is_valid(self) -> None:
        result = DefaultMatchingNormalizer().normalize("")
        assert result.normalized == ""
        assert result.tokens == ()
        assert result.statistics.tokens_produced == 0

    def test_non_string_is_rejected(self) -> None:
        with pytest.raises(TypeError):
            DefaultMatchingNormalizer().normalize(None)  # type: ignore[arg-type]


@pytest.mark.unit
class TestDeterminism:
    def test_identical_input_produces_equal_output(self) -> None:
        normalizer = DefaultMatchingNormalizer()
        assert normalizer.normalize("Content-Type-Options") == normalizer.normalize(
            "Content-Type-Options"
        )

    def test_two_normalizer_instances_agree(self) -> None:
        assert DefaultMatchingNormalizer().normalize(
            "Login Page"
        ) == DefaultMatchingNormalizer().normalize("Login Page")


@pytest.mark.unit
class TestPlatformContextRegistration:
    def test_factory_returns_default_normalizer(self) -> None:
        normalizer = PlatformContext().create_matching_normalizer()
        assert isinstance(normalizer, MatchingNormalizer)
        assert isinstance(normalizer, DefaultMatchingNormalizer)
