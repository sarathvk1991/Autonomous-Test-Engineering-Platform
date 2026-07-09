"""SonarQube source connector.

Fetches raw SonarQube issues from the configured source and returns them without
canonical transformation. Mapping is handled by the SonarQube mapper layer.

The connector supports two input modes selected via ``inputMode`` in
source-registry.json:

- FILE: reads a previously exported issues report from ``inputPath``.
- API: fetches issues live from the SonarQube Web API.

Downstream layers must not depend on which mode produced the records. In both
modes the connector returns raw SonarQube issue dicts (``{"key": ..., "rule":
..., "message": ..., ...}``) that the :class:`SonarMapper` consumes; the
connector performs no canonical mapping.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from requirement_intelligence.connectors import api_client, connector_io
from requirement_intelligence.connectors.base import SourceConnector
from requirement_intelligence.connectors.connector_exceptions import (
    ConnectorConfigurationError,
    ConnectorFetchError,
)

logger = logging.getLogger("requirement_intelligence.connectors.api")

# SonarQube Web API issue-search endpoint.
_SEARCH_PATH = "/api/issues/search"
# SonarQube caps ``ps`` at 500 and the total returned window at 10000.
_MAX_PAGE_SIZE = 500
_MAX_ISSUES = 10_000


class SonarQubeConnector(SourceConnector):
    """Connector for SonarQube."""

    def get_source_id(self) -> str:
        """Returns the source identifier."""
        return "sonarqube"

    def get_source_name(self) -> str:
        """Returns the source display name."""
        return "SonarQube"

    def validate_connection(self) -> bool:
        """Validates SonarQube source availability for the configured input mode.

        FILE mode validates that the configured ``inputPath`` exists and is
        readable. API mode validates that the base URL and token resolve from
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
            f"Unsupported inputMode '{mode}' for SonarQube connector. "
            f"Expected one of {connector_io.SUPPORTED_INPUT_MODES}."
        )

    def fetch_raw_records(self) -> list[dict[str, Any]]:
        """Fetches raw SonarQube issue records for the configured input mode.

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
            f"Unsupported inputMode '{mode}' for SonarQube connector. "
            f"Expected one of {connector_io.SUPPORTED_INPUT_MODES}."
        )

    def _fetch_from_file(self) -> list[dict[str, Any]]:
        """Reads raw SonarQube records from the configured ``inputPath``."""
        return connector_io.read_json_records(self.source_config)

    # ------------------------------------------------------------------ #
    # API mode
    # ------------------------------------------------------------------ #
    def _resolve_api_settings(self) -> _SonarApiSettings:
        """Resolve base URL, token, and query settings for API mode.

        Raises:
            ConnectorConfigurationError: If any required value cannot be
                resolved from configuration/environment.
        """
        connection = self.source_config.get("connection")
        if not isinstance(connection, dict):
            raise ConnectorConfigurationError(
                "[sonarqube] API mode requires a 'connection' block in configuration."
            )
        api_config = self.source_config.get("api")
        if not isinstance(api_config, dict):
            api_config = {}

        base_url = api_client.resolve_secret_field(
            connection, direct_key="baseUrl", env_key="baseUrlEnv", source_id="sonarqube"
        )
        token = api_client.resolve_secret_field(
            connection, direct_key="authToken", env_key="authTokenEnv", source_id="sonarqube"
        )
        project_key = api_client.resolve_secret_field(
            connection,
            direct_key="projectKey",
            env_key="projectKeyEnv",
            source_id="sonarqube",
        )
        branch = api_client.resolve_secret_field(
            connection,
            direct_key="branch",
            env_key="branchEnv",
            source_id="sonarqube",
            required=False,
        )
        return _SonarApiSettings(
            base_url=base_url,
            token=token,
            project_key=project_key,
            branch=branch,
            api_config=api_config,
        )

    def _build_params(
        self, settings: _SonarApiSettings, page: int, page_size: int
    ) -> dict[str, Any]:
        """Build issue-search query params for one page."""
        params: dict[str, Any] = {
            "componentKeys": settings.project_key,
            "p": page,
            "ps": page_size,
        }
        if settings.branch:
            params["branch"] = settings.branch

        incremental = settings.api_config.get("incremental")
        if isinstance(incremental, dict) and incremental.get("enabled"):
            created_after = incremental.get("createdAfter")
            if isinstance(created_after, str) and created_after.strip():
                params["createdAfter"] = created_after.strip()
        return params

    def _fetch_from_api(self) -> list[dict[str, Any]]:
        """Fetches raw SonarQube issues from the Web API with pagination.

        Authenticates with the SonarQube token as the HTTP Basic username (empty
        password), pages through ``/api/issues/search`` via ``p``/``ps``,
        supports an optional analysis ``branch`` and optional incremental
        retrieval (``createdAfter``), and returns each raw issue dict verbatim.

        Raises:
            ConnectorConfigurationError: If required configuration is missing.
            ConnectorConnectionError: On authentication or network failure.
            ConnectorFetchError: On HTTP or payload errors.
        """
        settings = self._resolve_api_settings()
        page_size = min(api_client.resolve_page_size(settings.api_config), _MAX_PAGE_SIZE)
        # SonarQube authenticates a token as the Basic-auth username, no password.
        auth = httpx.BasicAuth(settings.token, "")

        issues: list[dict[str, Any]] = []
        page = 1
        with api_client.ApiClient(
            settings.base_url,
            source_id="sonarqube",
            timeout_seconds=api_client.resolve_timeout_seconds(settings.api_config),
            retry=api_client.resolve_retry_policy(settings.api_config),
        ) as client:
            while True:
                payload = client.get_json(
                    _SEARCH_PATH,
                    params=self._build_params(settings, page, page_size),
                    auth=auth,
                )
                if not isinstance(payload, dict):
                    raise ConnectorFetchError(
                        "[sonarqube] unexpected search response: expected an "
                        f"object, got {type(payload).__name__}."
                    )
                batch = [i for i in payload.get("issues", []) if isinstance(i, dict)]
                issues.extend(batch)

                total = self._resolve_total(payload)
                if (
                    not batch
                    or (total is not None and len(issues) >= total)
                    or len(issues) >= _MAX_ISSUES
                ):
                    break
                page += 1

        logger.info(
            "sonarqube api fetch complete",
            extra={"source": "sonarqube", "issueCount": len(issues)},
        )
        return issues

    @staticmethod
    def _resolve_total(payload: dict[str, Any]) -> int | None:
        """Extract the total issue count from a search response, if present."""
        paging = payload.get("paging")
        if isinstance(paging, dict) and isinstance(paging.get("total"), int):
            return paging["total"]
        if isinstance(payload.get("total"), int):
            return payload["total"]
        return None

    def get_metadata(self) -> dict[str, Any]:
        """Returns SonarQube connector metadata."""
        return {
            "sourceId": self.get_source_id(),
            "sourceName": self.get_source_name(),
            "schemaVersion": "1.0",
            "supportedInputModes": ["FILE", "API"],
            "supportedEntities": ["issues", "quality_gate", "measures"],
        }


class _SonarApiSettings:
    """Resolved API-mode settings for the SonarQube connector (internal)."""

    __slots__ = ("api_config", "base_url", "branch", "project_key", "token")

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        project_key: str,
        branch: str,
        api_config: dict[str, Any],
    ) -> None:
        self.base_url = base_url
        self.token = token
        self.project_key = project_key
        self.branch = branch
        self.api_config = api_config
