"""Low-level Jira client factory (infrastructure boundary).

Wraps SDK/transport construction only. The Requirement Intelligence Jira
*connector* (``requirement_intelligence/connectors/jira``) builds domain
behaviour on top of the client returned here. Implementation deferred.
"""

from __future__ import annotations

# from jira import JIRA
# from app.core.settings import get_settings


def get_jira_client() -> object:
    """Return a configured Jira API client.

    To be implemented: construct and return an authenticated client using
    ``JIRA_*`` settings. Kept as a stub so the structure is importable.
    """
    raise NotImplementedError("Jira client factory not yet implemented")
