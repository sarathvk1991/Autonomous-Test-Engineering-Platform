"""Low-level OWASP ZAP HTTP client factory (infrastructure boundary).

Provides an authenticated ``httpx`` client targeting the ZAP REST API. Domain
behaviour lives in the ZAP connector. Implementation deferred.
"""

from __future__ import annotations

# import httpx
# from app.core.settings import get_settings


def get_zap_client() -> object:
    """Return a configured OWASP ZAP HTTP client.

    To be implemented: build an ``httpx.Client`` using ``ZAP_*`` settings.
    """
    raise NotImplementedError("OWASP ZAP client factory not yet implemented")
