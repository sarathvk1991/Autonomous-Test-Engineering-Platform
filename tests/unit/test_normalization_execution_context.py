"""Unit tests for the NormalizationExecutionContext and its builder.

Covers
------
* Construction and required/optional fields.
* Immutability (frozen) and strict construction (extra fields forbidden).
* The deterministic builder: identity, timestamps, version population,
  correlation, and contract-version propagation from configuration.
* Backward compatibility (optional identity/correlation default cleanly).
* camelCase serialisation aliases and round-trip.
* Independence from the Framework Metadata / Statistics / Result concerns:
  the context carries execution identity only — never a verdict, severity,
  observation, or ParsedResponse.

These tests run entirely in memory; no I/O, no parsing, no real responses.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from requirement_intelligence.normalization.models import (
    FRAMEWORK_VERSION,
    NORMALIZATION_CONTRACT_VERSION,
    PIPELINE_VERSION,
    REGISTRY_VERSION,
    RESPONSIBILITY_CATALOG_VERSION,
    NormalizationConfiguration,
)
from requirement_intelligence.normalization.response import (
    NormalizationExecutionContext,
    build_normalization_execution_context,
)

_TS = datetime(2026, 6, 30, 12, 0, 0, tzinfo=UTC)


def _context(**overrides: object) -> NormalizationExecutionContext:
    fields: dict[str, object] = {
        "normalization_id": "N-1",
        "started_at": _TS,
        "framework_version": FRAMEWORK_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "registry_version": REGISTRY_VERSION,
        "responsibility_catalog_version": RESPONSIBILITY_CATALOG_VERSION,
        "normalization_contract_version": NORMALIZATION_CONTRACT_VERSION,
    }
    fields.update(overrides)
    return NormalizationExecutionContext(**fields)  # type: ignore[arg-type]


@pytest.mark.unit
class TestConstruction:
    def test_minimal_construction(self) -> None:
        ctx = _context()
        assert ctx.normalization_id == "N-1"
        assert ctx.started_at == _TS
        assert ctx.framework_version == FRAMEWORK_VERSION

    def test_optional_identity_defaults(self) -> None:
        # Backward compatibility: the upstream/correlation identity is optional.
        ctx = _context()
        assert ctx.execution_id is None
        assert ctx.correlation_id is None
        assert ctx.metadata == {}

    def test_optional_identity_populated(self) -> None:
        ctx = _context(execution_id="EX-9", correlation_id="COR-9")
        assert ctx.execution_id == "EX-9"
        assert ctx.correlation_id == "COR-9"

    def test_metadata_preserved_verbatim(self) -> None:
        ctx = _context(metadata={"trigger": "manual"})
        assert ctx.metadata == {"trigger": "manual"}


@pytest.mark.unit
class TestImmutabilityAndStrictness:
    def test_is_frozen(self) -> None:
        ctx = _context()
        with pytest.raises(ValidationError):
            ctx.framework_version = "9.9.9"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            _context(verdict="passed")  # type: ignore[call-arg]

    def test_missing_required_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            NormalizationExecutionContext(  # type: ignore[call-arg]
                started_at=_TS,
                framework_version=FRAMEWORK_VERSION,
                pipeline_version=PIPELINE_VERSION,
                registry_version=REGISTRY_VERSION,
                responsibility_catalog_version=RESPONSIBILITY_CATALOG_VERSION,
                normalization_contract_version=NORMALIZATION_CONTRACT_VERSION,
            )


@pytest.mark.unit
class TestIndependenceFromOtherConcerns:
    def test_carries_no_judgment_or_facts(self) -> None:
        # Execution identity only — never a verdict/severity (validation), never
        # an observation/outcome/ParsedResponse (result), never telemetry counts
        # (statistics).  Boundary: Response Normalization Contract §10.
        ctx = _context()
        for forbidden in (
            "overall_verdict",
            "severity",
            "observations",
            "parsed_response",
            "outcome",
            "responsibilities_executed",
            "observations_recorded",
            "normalization_duration_ms",
        ):
            assert not hasattr(ctx, forbidden)


@pytest.mark.unit
class TestBuilder:
    def test_generates_fresh_identity_and_timestamp(self) -> None:
        ctx = build_normalization_execution_context()
        assert ctx.normalization_id  # a fresh id was generated
        assert ctx.started_at is not None

    def test_distinct_ids_across_calls(self) -> None:
        first = build_normalization_execution_context()
        second = build_normalization_execution_context()
        assert first.normalization_id != second.normalization_id

    def test_populates_all_versions_from_constants(self) -> None:
        ctx = build_normalization_execution_context()
        assert ctx.framework_version == FRAMEWORK_VERSION
        assert ctx.pipeline_version == PIPELINE_VERSION
        assert ctx.registry_version == REGISTRY_VERSION
        assert ctx.responsibility_catalog_version == RESPONSIBILITY_CATALOG_VERSION
        assert ctx.normalization_contract_version == NORMALIZATION_CONTRACT_VERSION

    def test_contract_version_read_from_configuration(self) -> None:
        config = NormalizationConfiguration(normalization_contract_version="2.5")
        ctx = build_normalization_execution_context(configuration=config)
        assert ctx.normalization_contract_version == "2.5"
        # Other versions remain the framework constants, never the config's.
        assert ctx.framework_version == FRAMEWORK_VERSION

    def test_default_configuration_uses_framework_contract_version(self) -> None:
        ctx = build_normalization_execution_context()
        assert ctx.normalization_contract_version == NORMALIZATION_CONTRACT_VERSION

    def test_identity_and_correlation_propagate(self) -> None:
        ctx = build_normalization_execution_context(
            execution_id="EX-77", correlation_id="COR-77"
        )
        assert ctx.execution_id == "EX-77"
        assert ctx.correlation_id == "COR-77"

    def test_identity_and_correlation_default_to_none(self) -> None:
        ctx = build_normalization_execution_context()
        assert ctx.execution_id is None
        assert ctx.correlation_id is None

    def test_builder_output_is_frozen(self) -> None:
        ctx = build_normalization_execution_context()
        with pytest.raises(ValidationError):
            ctx.normalization_id = "other"  # type: ignore[misc]


@pytest.mark.unit
class TestSerialisation:
    def test_camelcase_aliases(self) -> None:
        dumped = _context(execution_id="EX-1", correlation_id="COR-1").model_dump(
            by_alias=True
        )
        for key in (
            "normalizationId",
            "executionId",
            "correlationId",
            "startedAt",
            "frameworkVersion",
            "pipelineVersion",
            "registryVersion",
            "responsibilityCatalogVersion",
            "normalizationContractVersion",
        ):
            assert key in dumped

    def test_round_trip_from_aliased_dump(self) -> None:
        original = _context(execution_id="EX-1", correlation_id="COR-1")
        dumped = original.model_dump(by_alias=True)
        restored = NormalizationExecutionContext.model_validate(dumped)
        assert restored == original

    def test_populate_by_name_accepts_snake_case(self) -> None:
        # Backward compatibility: snake_case construction still validates.
        ctx = NormalizationExecutionContext.model_validate(
            {
                "normalization_id": "N-1",
                "started_at": _TS,
                "framework_version": FRAMEWORK_VERSION,
                "pipeline_version": PIPELINE_VERSION,
                "registry_version": REGISTRY_VERSION,
                "responsibility_catalog_version": RESPONSIBILITY_CATALOG_VERSION,
                "normalization_contract_version": NORMALIZATION_CONTRACT_VERSION,
            }
        )
        assert ctx.normalization_id == "N-1"
