"""SonarQube source connector.

Fetches code-quality issues / quality-gate findings from SonarQube and returns
raw payloads for the SonarQube parser to canonicalise. Logic deferred.
"""

from __future__ import annotations

from typing import Any

from requirement_intelligence.connectors.base import BaseConnector
from shared.enums.base import SourceSystem


class SonarQubeConnector(BaseConnector):
    """Connector for SonarQube."""

    source = SourceSystem.SONARQUBE

    def health_check(self) -> bool:  # noqa: D102 - see base class
        raise NotImplementedError

    def fetch(self, **query: Any) -> list[dict[str, Any]]:  # noqa: D102
        raise NotImplementedError
