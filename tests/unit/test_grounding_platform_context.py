"""Unit tests for Grounding Framework configuration and PlatformContext wiring.

The configuration is registered but **not consumed** by any runtime path in
CAP-077A; these tests assert only that it constructs and is correctly versioned.
"""

from __future__ import annotations

import pytest

from requirement_intelligence.grounding.config import (
    GroundingConfiguration,
    default_grounding_configuration,
)
from requirement_intelligence.grounding.version import (
    GROUNDING_CONFIGURATION_VERSION,
    GROUNDING_FRAMEWORK_VERSION,
)
from requirement_intelligence.platform.platform_context import PlatformContext


@pytest.mark.unit
class TestGroundingConfiguration:
    def test_default_is_versioned(self) -> None:
        config = default_grounding_configuration()
        assert config.version == GROUNDING_CONFIGURATION_VERSION
        assert config.framework_version == GROUNDING_FRAMEWORK_VERSION

    def test_config_is_immutable(self) -> None:
        from pydantic import ValidationError

        config = default_grounding_configuration()
        with pytest.raises(ValidationError):
            config.version = GROUNDING_CONFIGURATION_VERSION  # type: ignore[misc]

    def test_version_serialises_to_plain_string(self) -> None:
        dumped = default_grounding_configuration().model_dump(mode="json", by_alias=True)
        assert dumped == {"version": "1.0.0", "frameworkVersion": "1.0.0"}


@pytest.mark.unit
class TestPlatformContextRegistration:
    def test_create_grounding_configuration_returns_config(self) -> None:
        config = PlatformContext().create_grounding_configuration()
        assert isinstance(config, GroundingConfiguration)
        assert config.version == GROUNDING_CONFIGURATION_VERSION
