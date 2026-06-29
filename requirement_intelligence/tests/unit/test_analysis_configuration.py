"""Unit tests for AnalysisConfiguration — the execution-policy contract."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from requirement_intelligence.analysis.analysis_configuration import (
    AnalysisConfiguration,
)

# ---------------------------------------------------------------------------
# 1. Valid configuration & defaults
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_minimal_valid_configuration_uses_defaults() -> None:
    config = AnalysisConfiguration(reasoning_contract_version="rc-1.0.0")
    assert config.reasoning_contract_version == "rc-1.0.0"
    assert config.temperature == 0.0
    assert config.provider_timeout_seconds is None
    assert config.max_retry_attempts == 0
    assert config.enable_streaming is False
    assert config.response_schema_enabled is False
    assert config.metadata == {}


@pytest.mark.unit
def test_fully_specified_configuration() -> None:
    config = AnalysisConfiguration(
        reasoning_contract_version="rc-2.0.0",
        temperature=1.5,
        provider_timeout_seconds=30,
        max_retry_attempts=3,
        enable_streaming=True,
        response_schema_enabled=True,
        metadata={"team": "qa"},
    )
    assert config.temperature == 1.5
    assert config.provider_timeout_seconds == 30
    assert config.max_retry_attempts == 3
    assert config.enable_streaming is True
    assert config.response_schema_enabled is True
    assert config.metadata["team"] == "qa"


# ---------------------------------------------------------------------------
# 2. reasoning_contract_version validation
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_empty_reasoning_version_raises() -> None:
    with pytest.raises(ValidationError):
        AnalysisConfiguration(reasoning_contract_version="")


@pytest.mark.unit
def test_missing_reasoning_version_raises() -> None:
    with pytest.raises(ValidationError):
        AnalysisConfiguration()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# 3. temperature bounds [0.0, 2.0]
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.parametrize("temperature", [0.0, 1.0, 2.0])
def test_temperature_within_bounds_accepted(temperature: float) -> None:
    config = AnalysisConfiguration(
        reasoning_contract_version="rc-1.0.0", temperature=temperature
    )
    assert config.temperature == temperature


@pytest.mark.unit
@pytest.mark.parametrize("temperature", [-0.1, 2.1, 5.0])
def test_temperature_out_of_bounds_raises(temperature: float) -> None:
    with pytest.raises(ValidationError):
        AnalysisConfiguration(
            reasoning_contract_version="rc-1.0.0", temperature=temperature
        )


# ---------------------------------------------------------------------------
# 4. max_retry_attempts >= 0
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_zero_retry_attempts_accepted() -> None:
    config = AnalysisConfiguration(
        reasoning_contract_version="rc-1.0.0", max_retry_attempts=0
    )
    assert config.max_retry_attempts == 0


@pytest.mark.unit
def test_negative_retry_attempts_raises() -> None:
    with pytest.raises(ValidationError):
        AnalysisConfiguration(
            reasoning_contract_version="rc-1.0.0", max_retry_attempts=-1
        )


# ---------------------------------------------------------------------------
# 5. provider_timeout_seconds > 0 when supplied
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_timeout_none_accepted() -> None:
    config = AnalysisConfiguration(
        reasoning_contract_version="rc-1.0.0", provider_timeout_seconds=None
    )
    assert config.provider_timeout_seconds is None


@pytest.mark.unit
def test_positive_timeout_accepted() -> None:
    config = AnalysisConfiguration(
        reasoning_contract_version="rc-1.0.0", provider_timeout_seconds=1
    )
    assert config.provider_timeout_seconds == 1


@pytest.mark.unit
@pytest.mark.parametrize("timeout", [0, -5])
def test_non_positive_timeout_raises(timeout: int) -> None:
    with pytest.raises(ValidationError):
        AnalysisConfiguration(
            reasoning_contract_version="rc-1.0.0", provider_timeout_seconds=timeout
        )


# ---------------------------------------------------------------------------
# 6. camelCase serialization
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_serializes_camelcase() -> None:
    config = AnalysisConfiguration(
        reasoning_contract_version="rc-1.0.0",
        provider_timeout_seconds=30,
        max_retry_attempts=2,
        enable_streaming=True,
        response_schema_enabled=True,
    )
    data = config.model_dump(by_alias=True)
    for key in (
        "reasoningContractVersion",
        "temperature",
        "providerTimeoutSeconds",
        "maxRetryAttempts",
        "enableStreaming",
        "responseSchemaEnabled",
        "metadata",
    ):
        assert key in data
    assert data["reasoningContractVersion"] == "rc-1.0.0"


@pytest.mark.unit
def test_accepts_camelcase_on_input() -> None:
    # populate_by_name (inherited from Schema) allows alias input too.
    config = AnalysisConfiguration.model_validate(
        {"reasoningContractVersion": "rc-1.0.0", "maxRetryAttempts": 4}
    )
    assert config.reasoning_contract_version == "rc-1.0.0"
    assert config.max_retry_attempts == 4


# ---------------------------------------------------------------------------
# 7. Immutability & strictness
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_configuration_is_immutable() -> None:
    config = AnalysisConfiguration(reasoning_contract_version="rc-1.0.0")
    with pytest.raises((TypeError, ValueError)):
        config.temperature = 1.0  # type: ignore[misc]


@pytest.mark.unit
def test_configuration_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        AnalysisConfiguration(
            reasoning_contract_version="rc-1.0.0", unknown_field="x"
        )


# ---------------------------------------------------------------------------
# 8. metadata default_factory isolation
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_metadata_default_factory_is_isolated() -> None:
    first = AnalysisConfiguration(reasoning_contract_version="rc-1.0.0")
    second = AnalysisConfiguration(reasoning_contract_version="rc-1.0.0")
    assert first.metadata == {}
    assert second.metadata == {}
    # Distinct instances must not share the same default dict object.
    assert first.metadata is not second.metadata
