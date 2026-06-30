"""Unit tests for the Response Normalization information models.

Covers
------
* Immutability (frozen) and strict construction (extra fields forbidden).
* camelCase serialisation aliases.
* NormalizationObservation is a *fact*: it has no severity, verdict,
  recommendation, or blocking flag.
* Defaults across configuration, statistics, framework metadata, and result.
* The ParsedResponse placeholder on NormalizationResult.

These tests run entirely in memory; no I/O, no parsing, no real responses.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from requirement_intelligence.normalization.models import (
    FRAMEWORK_VERSION,
    NORMALIZATION_CONTRACT_VERSION,
    OBSERVATION_DUPLICATE_IDENTIFIER,
    OBSERVATION_ENCODING,
    OBSERVATION_MALFORMED_REPRESENTATION,
    PIPELINE_VERSION,
    REGISTRY_VERSION,
    RESPONSIBILITY_CATALOG_VERSION,
    NormalizationConfiguration,
    NormalizationFrameworkMetadata,
    NormalizationObservation,
    NormalizationResult,
    NormalizationStatistics,
)

_TS = datetime(2026, 6, 30, 12, 0, 0, tzinfo=UTC)


def _observation(obs_id: str = "OBS-1") -> NormalizationObservation:
    return NormalizationObservation(
        observation_id=obs_id,
        observation_type=OBSERVATION_DUPLICATE_IDENTIFIER,
        detail="a duplicate identifier was observed",
        created_at=_TS,
    )


def _statistics() -> NormalizationStatistics:
    return NormalizationStatistics(
        normalization_duration_ms=1.5,
        responsibilities_executed=2,
        observations_recorded=1,
        started_at=_TS,
        completed_at=_TS,
        framework_version=FRAMEWORK_VERSION,
        normalization_contract_version=NORMALIZATION_CONTRACT_VERSION,
        normalization_id="N-1",
    )


def _framework_metadata() -> NormalizationFrameworkMetadata:
    return NormalizationFrameworkMetadata(
        framework_version=FRAMEWORK_VERSION,
        normalization_contract_version=NORMALIZATION_CONTRACT_VERSION,
        pipeline_version=PIPELINE_VERSION,
        registry_version=REGISTRY_VERSION,
        responsibility_catalog_version=RESPONSIBILITY_CATALOG_VERSION,
    )


def _result() -> NormalizationResult:
    return NormalizationResult(
        normalization_id="N-1",
        normalization_configuration=NormalizationConfiguration(),
        normalization_framework_metadata=_framework_metadata(),
        normalization_statistics=_statistics(),
        observations=(_observation(),),
        started_at=_TS,
        completed_at=_TS,
    )


class TestNormalizationObservation:
    def test_is_a_fact_not_a_judgment(self) -> None:
        obs = _observation()
        # Facts carry none of validation's judgment fields (Contract §10).
        for forbidden in ("severity", "verdict", "recommendation", "blocking"):
            assert not hasattr(obs, forbidden)

    def test_is_frozen(self) -> None:
        obs = _observation()
        with pytest.raises(ValidationError):
            obs.detail = "changed"  # type: ignore[misc]

    def test_optional_fields_default(self) -> None:
        obs = _observation()
        assert obs.location is None
        assert obs.evidence is None
        assert obs.correlation_id is None
        assert obs.metadata == {}

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            NormalizationObservation(
                observation_id="OBS-1",
                observation_type="x",
                detail="y",
                created_at=_TS,
                severity="critical",  # type: ignore[call-arg]
            )

    def test_camelcase_serialisation(self) -> None:
        dumped = _observation().model_dump(by_alias=True)
        assert "observationId" in dumped
        assert "observationType" in dumped
        assert "createdAt" in dumped

    def test_well_known_observation_type_constants(self) -> None:
        assert OBSERVATION_DUPLICATE_IDENTIFIER == "duplicate_identifier"
        assert OBSERVATION_MALFORMED_REPRESENTATION == "malformed_representation"
        assert OBSERVATION_ENCODING == "encoding_observation"


class TestNormalizationConfiguration:
    def test_defaults(self) -> None:
        cfg = NormalizationConfiguration()
        assert cfg.normalization_contract_version == NORMALIZATION_CONTRACT_VERSION
        assert cfg.collect_statistics is True
        assert cfg.collect_observations is True
        assert cfg.collect_metadata is True
        assert cfg.future_extensions == {}

    def test_has_no_layer_or_severity_policy(self) -> None:
        # Deliberate deviation from ValidationConfiguration.
        cfg = NormalizationConfiguration()
        assert not hasattr(cfg, "enabled_layers")
        assert not hasattr(cfg, "minimum_severity")

    def test_is_frozen(self) -> None:
        cfg = NormalizationConfiguration()
        with pytest.raises(ValidationError):
            cfg.collect_statistics = False  # type: ignore[misc]

    def test_camelcase_serialisation(self) -> None:
        dumped = NormalizationConfiguration().model_dump(by_alias=True)
        assert "normalizationContractVersion" in dumped
        assert "collectObservations" in dumped


class TestNormalizationStatistics:
    def test_fact_oriented_fields(self) -> None:
        stats = _statistics()
        # Deviation: counts of facts, not pass/fail.
        assert stats.responsibilities_executed == 2
        assert stats.observations_recorded == 1
        assert not hasattr(stats, "rules_passed")
        assert not hasattr(stats, "rules_failed")

    def test_negative_counts_rejected(self) -> None:
        with pytest.raises(ValidationError):
            NormalizationStatistics(
                normalization_duration_ms=0.0,
                responsibilities_executed=-1,
                observations_recorded=0,
                started_at=_TS,
                completed_at=_TS,
                framework_version=FRAMEWORK_VERSION,
                normalization_contract_version=NORMALIZATION_CONTRACT_VERSION,
                normalization_id="N-1",
            )

    def test_camelcase_serialisation(self) -> None:
        dumped = _statistics().model_dump(by_alias=True)
        assert "normalizationDurationMs" in dumped
        assert "responsibilitiesExecuted" in dumped
        assert "observationsRecorded" in dumped


class TestNormalizationFrameworkMetadata:
    def test_carries_all_five_versions(self) -> None:
        meta = _framework_metadata()
        assert meta.framework_version == FRAMEWORK_VERSION
        assert meta.normalization_contract_version == NORMALIZATION_CONTRACT_VERSION
        assert meta.pipeline_version == PIPELINE_VERSION
        assert meta.registry_version == REGISTRY_VERSION
        assert meta.responsibility_catalog_version == RESPONSIBILITY_CATALOG_VERSION

    def test_camelcase_serialisation(self) -> None:
        dumped = _framework_metadata().model_dump(by_alias=True)
        assert "responsibilityCatalogVersion" in dumped
        assert "normalizationContractVersion" in dumped


class TestNormalizationResult:
    def test_parsed_response_placeholder_defaults_none(self) -> None:
        assert _result().parsed_response is None

    def test_has_no_verdict_or_summary(self) -> None:
        result = _result()
        assert not hasattr(result, "overall_verdict")
        assert not hasattr(result, "validation_summary")

    def test_is_frozen(self) -> None:
        result = _result()
        with pytest.raises(ValidationError):
            result.normalization_id = "other"  # type: ignore[misc]

    def test_owns_observations_as_tuple(self) -> None:
        result = _result()
        assert isinstance(result.observations, tuple)
        assert len(result.observations) == 1

    def test_camelcase_serialisation_round_trip(self) -> None:
        dumped = _result().model_dump(by_alias=True)
        assert "parsedResponse" in dumped
        assert "normalizationFrameworkMetadata" in dumped
        # Re-validate from the aliased dump (populate_by_name + aliases).
        restored = NormalizationResult.model_validate(dumped)
        assert restored.normalization_id == "N-1"
