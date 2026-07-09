"""OWASP ZAP source connector.

Fetches raw OWASP ZAP alerts from the configured source and returns them without
canonical transformation. Mapping is handled by the ZAP mapper layer.

The connector supports two input modes selected via ``inputMode`` in
source-registry.json:

- FILE: reads a previously exported alert report from ``inputPath``.
- API: fetches alerts live from the OWASP ZAP daemon REST API.

Downstream layers must not depend on which mode produced the records. In both
modes the connector returns raw ZAP alert dicts (``{"pluginId": ..., "alert":
..., "risk": ..., ...}``) that the :class:`ZapMapper` consumes; the connector
performs no canonical mapping.
"""

from __future__ import annotations

import logging
from typing import Any

from requirement_intelligence.connectors import api_client, connector_io
from requirement_intelligence.connectors.base import SourceConnector
from requirement_intelligence.connectors.connector_exceptions import (
    ConnectorConfigurationError,
    ConnectorFetchError,
)

logger = logging.getLogger("requirement_intelligence.connectors.api")

# OWASP ZAP core "alerts" view (JSON API).
_ALERTS_PATH = "/JSON/core/view/alerts/"
# Upper bound on total alerts fetched, guarding against unbounded pagination.
_MAX_ALERTS = 50_000


class ZapConnector(SourceConnector):
    """Connector for OWASP ZAP."""

    def get_source_id(self) -> str:
        """Returns the source identifier."""
        return "owasp_zap"

    def get_source_name(self) -> str:
        """Returns the source display name."""
        return "OWASP ZAP"

    def validate_connection(self) -> bool:
        """Validates OWASP ZAP source availability for the configured input mode.

        FILE mode validates that the configured ``inputPath`` exists and is
        readable. API mode validates that the base URL and API key resolve from
        configuration/environment (reachability/auth are exercised during
        :meth:`fetch_raw_records`).

        Raises:
            ConnectorConfigurationError: If ``inputMode`` is invalid/missing or
                required API configuration cannot be resolved.
            ConnectorConnectionError: If the FILE source is unavailable.
        """
        mode = connector_io.get_input_mode(self.source_config)
        if mode == connector_io.FILE_MODE:
            return connector_io.validate_input_file(self.source_config)
        if mode == connector_io.API_MODE:
            self._resolve_api_settings()
            return True
        raise ConnectorConfigurationError(
            f"Unsupported inputMode '{mode}' for OWASP ZAP connector. "
            f"Expected one of {connector_io.SUPPORTED_INPUT_MODES}."
        )

    def fetch_raw_records(self) -> list[dict[str, Any]]:
        """Fetches raw OWASP ZAP alert records for the configured input mode.

        Raises:
            ConnectorConfigurationError: If ``inputMode`` is invalid/missing.
            ConnectorConnectionError: If the source is unavailable.
            ConnectorFetchError: If raw records cannot be fetched.
        """
        mode = connector_io.get_input_mode(self.source_config)
        if mode == connector_io.FILE_MODE:
            return self._fetch_from_file()
        if mode == connector_io.API_MODE:
            return self._fetch_from_api()
        raise ConnectorConfigurationError(
            f"Unsupported inputMode '{mode}' for OWASP ZAP connector. "
            f"Expected one of {connector_io.SUPPORTED_INPUT_MODES}."
        )

    def _fetch_from_file(self) -> list[dict[str, Any]]:
        """Reads raw OWASP ZAP records from the configured ``inputPath``."""
        return connector_io.read_json_records(self.source_config)

    # ------------------------------------------------------------------ #
    # API mode
    # ------------------------------------------------------------------ #
    def _resolve_api_settings(self) -> _ZapApiSettings:
        """Resolve base URL, API key, and query settings for API mode.

        Raises:
            ConnectorConfigurationError: If any required value cannot be
                resolved from configuration/environment.
        """
        connection = self.source_config.get("connection")
        if not isinstance(connection, dict):
            raise ConnectorConfigurationError(
                "[owasp_zap] API mode requires a 'connection' block in configuration."
            )
        api_config = self.source_config.get("api")
        if not isinstance(api_config, dict):
            api_config = {}

        base_url = api_client.resolve_secret_field(
            connection, direct_key="baseUrl", env_key="baseUrlEnv", source_id="owasp_zap"
        )
        api_key = api_client.resolve_secret_field(
            connection, direct_key="apiKey", env_key="apiKeyEnv", source_id="owasp_zap"
        )
        target = api_client.resolve_secret_field(
            connection,
            direct_key="targetUrl",
            env_key="targetUrlEnv",
            source_id="owasp_zap",
            required=False,
        )
        return _ZapApiSettings(
            base_url=base_url,
            api_key=api_key,
            target=target,
            api_config=api_config,
        )

    def _fetch_from_api(self) -> list[dict[str, Any]]:
        """Fetches raw OWASP ZAP alerts from the daemon REST API with pagination.

        Authenticates with the configured API key, pages through the core
        ``alerts`` view via ``start``/``count``, optionally scopes to a target
        ``baseurl``, and returns each raw alert dict verbatim.

        Raises:
            ConnectorConfigurationError: If required configuration is missing.
            ConnectorConnectionError: On authentication or network failure.
            ConnectorFetchError: On HTTP or payload errors.
        """
        settings = self._resolve_api_settings()
        page_size = api_client.resolve_page_size(settings.api_config)
        # ZAP accepts the API key as a query param and as a header; send both so
        # the connector works regardless of the daemon's configured key mode.
        headers = {"X-ZAP-API-Key": settings.api_key}

        alerts: list[dict[str, Any]] = []
        start = 0
        with api_client.ApiClient(
            settings.base_url,
            source_id="owasp_zap",
            timeout_seconds=api_client.resolve_timeout_seconds(settings.api_config),
            retry=api_client.resolve_retry_policy(settings.api_config),
        ) as client:
            while True:
                params: dict[str, Any] = {
                    "apikey": settings.api_key,
                    "start": start,
                    "count": page_size,
                }
                if settings.target:
                    params["baseurl"] = settings.target

                payload = client.get_json(_ALERTS_PATH, params=params, headers=headers)
                if not isinstance(payload, dict):
                    raise ConnectorFetchError(
                        "[owasp_zap] unexpected alerts response: expected an "
                        f"object, got {type(payload).__name__}."
                    )
                batch = [a for a in payload.get("alerts", []) if isinstance(a, dict)]
                alerts.extend(batch)

                if len(batch) < page_size or not batch or len(alerts) >= _MAX_ALERTS:
                    break
                start += page_size

        logger.info(
            "owasp_zap api fetch complete",
            extra={"source": "owasp_zap", "alertCount": len(alerts)},
        )
        return alerts

    def get_metadata(self) -> dict[str, Any]:
        """Returns OWASP ZAP connector metadata."""
        return {
            "sourceId": self.get_source_id(),
            "sourceName": self.get_source_name(),
            "schemaVersion": "1.0",
            "supportedInputModes": ["FILE", "API"],
            "supportedEntities": ["alerts", "findings"],
        }


class _ZapApiSettings:
    """Resolved API-mode settings for the OWASP ZAP connector (internal)."""

    __slots__ = ("api_config", "api_key", "base_url", "target")

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        target: str,
        api_config: dict[str, Any],
    ) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.target = target
        self.api_config = api_config
