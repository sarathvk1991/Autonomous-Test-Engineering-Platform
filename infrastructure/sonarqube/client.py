"""Low-level SonarQube HTTP client factory (infrastructure boundary).

Provides an authenticated ``httpx`` client targeting the SonarQube Web API.
Domain behaviour lives in the SonarQube connector. Implementation deferred.
"""

from __future__ import annotations

# import httpx
# from app.core.settings import get_settings


def get_sonarqube_client() -> object:
    """Return a configured SonarQube HTTP client.

    To be implemented: build an ``httpx.Client`` with base URL and token auth
    from ``SONARQUBE_*`` settings.
    """
    raise NotImplementedError("SonarQube client factory not yet implemented")
