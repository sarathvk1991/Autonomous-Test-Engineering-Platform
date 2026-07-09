"""JIRA source connector.

Fetches raw JIRA issues from the configured source and returns them without
canonical transformation. Mapping is handled by the JIRA mapper layer.

The connector supports two input modes selected via ``inputMode`` in
source-registry.json:

- FILE: reads a previously exported issue dump from ``inputPath``.
- API: fetches issues live from the JIRA Cloud/Server REST API.

Downstream layers must not depend on which mode produced the records. In both
modes the connector returns raw JIRA issue dicts (``{"key": ..., "self": ...,
"fields": { ... }}``) that the :class:`JiraMapper` knows how to consume; the
connector performs no field renaming, flattening, or canonical mapping.
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

# JIRA REST search endpoint (v2 is stable across Cloud and Server/DC).
_SEARCH_PATH = "/rest/api/2/search"
# Upper bound on total issues fetched, guarding against unbounded pagination.
_MAX_ISSUES = 10_000


class JiraConnector(SourceConnector):
    """Connector for JIRA."""

    def get_source_id(self) -> str:
        """Returns the source identifier."""
        return "jira"

    def get_source_name(self) -> str:
        """Returns the source display name."""
        return "JIRA"

    def validate_connection(self) -> bool:
        """Validates JIRA source availability for the configured input mode.

        FILE mode validates that the configured ``inputPath`` exists and is
        readable. API mode validates that the base URL and credentials resolve
        from configuration/environment (no live call is made here; reachability
        and auth are exercised during :meth:`fetch_raw_records`).

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
            f"Unsupported inputMode '{mode}' for JIRA connector. "
            f"Expected one of {connector_io.SUPPORTED_INPUT_MODES}."
        )

    def fetch_raw_records(self) -> list[dict[str, Any]]:
        """Fetches raw JIRA issue records for the configured input mode.

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
            f"Unsupported inputMode '{mode}' for JIRA connector. "
            f"Expected one of {connector_io.SUPPORTED_INPUT_MODES}."
        )

    def _fetch_from_file(self) -> list[dict[str, Any]]:
        """Reads raw JIRA records from the configured ``inputPath``."""
        return connector_io.read_json_records(self.source_config)

    # ------------------------------------------------------------------ #
    # API mode
    # ------------------------------------------------------------------ #
    def _resolve_api_settings(self) -> _JiraApiSettings:
        """Resolve base URL, credentials, and query settings for API mode.

        Raises:
            ConnectorConfigurationError: If any required value cannot be
                resolved from configuration/environment.
        """
        connection = self.source_config.get("connection")
        if not isinstance(connection, dict):
            raise ConnectorConfigurationError(
                "[jira] API mode requires a 'connection' block in configuration."
            )
        api_config = self.source_config.get("api")
        if not isinstance(api_config, dict):
            api_config = {}

        base_url = api_client.resolve_secret_field(
            connection, direct_key="baseUrl", env_key="baseUrlEnv", source_id="jira"
        )
        email = api_client.resolve_secret_field(
            connection, direct_key="authUser", env_key="authUserEnv", source_id="jira"
        )
        token = api_client.resolve_secret_field(
            connection, direct_key="authToken", env_key="authTokenEnv", source_id="jira"
        )
        project_key = api_client.resolve_secret_field(
            connection,
            direct_key="projectKey",
            env_key="projectKeyEnv",
            source_id="jira",
            required=False,
        )
        return _JiraApiSettings(
            base_url=base_url,
            email=email,
            token=token,
            project_key=project_key,
            api_config=api_config,
        )

    def _build_jql(self, settings: _JiraApiSettings) -> str:
        """Build the JQL query, honouring optional incremental retrieval."""
        clauses: list[str] = []
        if settings.project_key:
            clauses.append(f'project = "{settings.project_key}"')

        incremental = settings.api_config.get("incremental")
        if isinstance(incremental, dict) and incremental.get("enabled"):
            extra = incremental.get("jql")
            if isinstance(extra, str) and extra.strip():
                clauses.append(extra.strip())

        where = " AND ".join(clauses)
        if where:
            return f"{where} ORDER BY created ASC"
        return "ORDER BY created ASC"

    def _fetch_from_api(self) -> list[dict[str, Any]]:
        """Fetches raw JIRA issues from the REST API with pagination.

        Uses HTTP Basic authentication (account email + API token / PAT),
        pages through ``/rest/api/2/search`` via ``startAt``/``maxResults``, and
        returns each raw issue dict verbatim. Optional incremental retrieval is
        expressed as an extra JQL clause in the ``api.incremental`` block.

        Raises:
            ConnectorConfigurationError: If required configuration is missing.
            ConnectorConnectionError: On authentication or network failure.
            ConnectorFetchError: On HTTP or payload errors.
        """
        settings = self._resolve_api_settings()
        jql = self._build_jql(settings)
        page_size = api_client.resolve_page_size(settings.api_config)
        auth = httpx.BasicAuth(settings.email, settings.token)

        issues: list[dict[str, Any]] = []
        start_at = 0
        with api_client.ApiClient(
            settings.base_url,
            source_id="jira",
            timeout_seconds=api_client.resolve_timeout_seconds(settings.api_config),
            retry=api_client.resolve_retry_policy(settings.api_config),
        ) as client:
            while True:
                payload = client.get_json(
                    _SEARCH_PATH,
                    params={
                        "jql": jql,
                        "startAt": start_at,
                        "maxResults": page_size,
                        "fields": "*all",
                    },
                    auth=auth,
                )
                if not isinstance(payload, dict):
                    raise ConnectorFetchError(
                        "[jira] unexpected search response: expected an object, "
                        f"got {type(payload).__name__}."
                    )
                page = [i for i in payload.get("issues", []) if isinstance(i, dict)]
                issues.extend(page)

                total = payload.get("total")
                fetched = start_at + len(page)
                if (
                    not page
                    or (isinstance(total, int) and fetched >= total)
                    or len(issues) >= _MAX_ISSUES
                ):
                    break
                start_at = fetched

        logger.info(
            "jira api fetch complete",
            extra={"source": "jira", "issueCount": len(issues)},
        )
        return issues

    def get_metadata(self) -> dict[str, Any]:
        """Returns JIRA connector metadata."""
        return {
            "sourceId": self.get_source_id(),
            "sourceName": self.get_source_name(),
            "schemaVersion": "1.0",
            "supportedInputModes": ["FILE", "API"],
            "supportedEntities": ["issues", "epics", "stories", "defects"],
        }


class _JiraApiSettings:
    """Resolved API-mode settings for the JIRA connector (internal)."""

    __slots__ = ("api_config", "base_url", "email", "project_key", "token")

    def __init__(
        self,
        *,
        base_url: str,
        email: str,
        token: str,
        project_key: str,
        api_config: dict[str, Any],
    ) -> None:
        self.base_url = base_url
        self.email = email
        self.token = token
        self.project_key = project_key
        self.api_config = api_config
