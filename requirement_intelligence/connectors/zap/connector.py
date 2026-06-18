"""OWASP ZAP source connector.

Fetches security alerts/findings from an OWASP ZAP instance and returns raw
payloads for the ZAP parser to canonicalise. Logic deferred.
"""

from __future__ import annotations

from typing import Any

from requirement_intelligence.connectors.base import BaseConnector
from shared.enums.base import SourceSystem


class ZapConnector(BaseConnector):
    """Connector for OWASP ZAP."""

    source = SourceSystem.OWASP_ZAP

    def health_check(self) -> bool:  # noqa: D102 - see base class
        raise NotImplementedError

    def fetch(self, **query: Any) -> list[dict[str, Any]]:  # noqa: D102
        raise NotImplementedError
