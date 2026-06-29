"""Platform package — centralized construction and metadata.

PlatformContext      — dependency factory for platform components.
platform_metadata    — versions, capability/provider/command catalogues.
"""

from requirement_intelligence.platform import platform_metadata
from requirement_intelligence.platform.platform_context import PlatformContext

__all__ = ["PlatformContext", "platform_metadata"]
