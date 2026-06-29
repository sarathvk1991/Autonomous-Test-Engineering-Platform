"""Platform package — centralized construction, metadata, and introspection.

PlatformContext      — dependency factory for platform components.
PlatformCapabilities — platform introspection model.
platform_metadata    — versions, capability/provider/command catalogues.
"""

from requirement_intelligence.platform import platform_metadata
from requirement_intelligence.platform.platform_capabilities import (
    PlatformCapabilities,
)
from requirement_intelligence.platform.platform_context import PlatformContext

__all__ = ["PlatformCapabilities", "PlatformContext", "platform_metadata"]
