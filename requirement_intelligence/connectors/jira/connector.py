"""Jira source connector.

Fetches issues/requirements from Jira via the infrastructure Jira client and
returns raw payloads for the Jira parser to canonicalise. Logic deferred.
"""

from __future__ import annotations

from typing import Any

from requirement_intelligence.connectors.base import BaseConnector
from shared.enums.base import SourceSystem


class JiraConnector(BaseConnector):
    """Connector for Atlassian Jira."""

    source = SourceSystem.JIRA

    def health_check(self) -> bool:  # noqa: D102 - see base class
        raise NotImplementedError

    def fetch(self, **query: Any) -> list[dict[str, Any]]:  # noqa: D102
        raise NotImplementedError
