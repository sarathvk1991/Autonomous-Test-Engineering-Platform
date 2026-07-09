"""Platform package — centralized construction, metadata, and introspection.

PlatformContext      — dependency factory for platform components.
PlatformCapabilities — platform introspection model.
platform_metadata    — versions, capability/provider/command catalogues.
startup_validation   — fail-fast configuration validation before execution.
connector_health     — operational readiness probe for the ingestion sources.
"""

from requirement_intelligence.platform import platform_metadata
from requirement_intelligence.platform.connector_health import (
    ConnectorHealth,
    HealthReport,
    check_connector_health,
)
from requirement_intelligence.platform.platform_capabilities import (
    PlatformCapabilities,
)
from requirement_intelligence.platform.platform_context import PlatformContext
from requirement_intelligence.platform.startup_validation import (
    StartupCheck,
    StartupReport,
    StartupValidationError,
    validate_startup,
)

__all__ = [
    "ConnectorHealth",
    "HealthReport",
    "PlatformCapabilities",
    "PlatformContext",
    "StartupCheck",
    "StartupReport",
    "StartupValidationError",
    "check_connector_health",
    "platform_metadata",
    "validate_startup",
]
