"""Resilient HTTP transport for live (API-mode) source connectors.

This module provides a thin, source-agnostic HTTP client plus the small set of
configuration/environment resolvers the live connectors share. It is the single
place where the platform's live-ingestion resilience policy lives:

- a configurable request timeout,
- bounded retry with exponential backoff on *transient* failures (network
  errors, HTTP 429, HTTP 5xx),
- structured logging of every attempt and every failure, and
- deterministic mapping of transport/HTTP failures onto the connector
  exception hierarchy (:mod:`connector_exceptions`).

The client performs **raw JSON retrieval only**. It has no knowledge of JIRA,
SonarQube, or OWASP ZAP payload shapes, performs no pagination, and does no
canonical mapping — pagination belongs to the concrete connectors and mapping
belongs to the mapper layer. Nothing here reaches into a vendor schema.

Secrets are never accepted as literals here: base URLs and credentials are
resolved from environment variables named by the source-registry configuration,
so no URL or credential is ever hardcoded in code or committed in configuration.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx

from requirement_intelligence.connectors.connector_exceptions import (
    ConnectorConfigurationError,
    ConnectorConnectionError,
    ConnectorFetchError,
)

logger = logging.getLogger("requirement_intelligence.connectors.api")

# HTTP status codes that represent a *transient* condition worth retrying.
_RETRYABLE_STATUS: frozenset[int] = frozenset({429, 500, 502, 503, 504})
# HTTP status codes that represent an authentication/authorization failure.
_AUTH_STATUS: frozenset[int] = frozenset({401, 403})

# Defaults applied when the source-registry ``api`` block omits a value.
_DEFAULT_TIMEOUT_SECONDS = 30.0
_DEFAULT_MAX_ATTEMPTS = 3
_DEFAULT_BACKOFF_SECONDS = 1.0
_DEFAULT_MAX_BACKOFF_SECONDS = 30.0
_DEFAULT_PAGE_SIZE = 50


# --------------------------------------------------------------------------- #
# Environment / configuration resolution
# --------------------------------------------------------------------------- #
def resolve_secret_field(
    connection: dict[str, Any],
    *,
    direct_key: str,
    env_key: str,
    source_id: str,
    required: bool = True,
) -> str:
    """Resolve one connection value from a direct literal or an env-var name.

    Two forms are accepted so the same connector works both in tests (direct
    literal values) and in production (environment-driven):

    - ``connection[direct_key]`` — a literal value (used only in tests/local
      wiring; production configuration leaves this unset), or
    - ``connection[env_key]`` — the *name* of an environment variable whose
      value is read from :data:`os.environ`.

    Args:
        connection: The source's ``connection`` configuration block.
        direct_key: Key holding a literal value (e.g. ``"baseUrl"``).
        env_key: Key naming the environment variable (e.g. ``"baseUrlEnv"``).
        source_id: Source identifier, used only for error messages.
        required: When True, a missing/empty resolution raises.

    Returns:
        str: The resolved value (empty string only when ``required`` is False).

    Raises:
        ConnectorConfigurationError: If ``required`` and the value cannot be
            resolved to a non-empty string.
    """
    direct = connection.get(direct_key)
    if isinstance(direct, str) and direct.strip():
        return direct.strip()

    env_name = connection.get(env_key)
    if isinstance(env_name, str) and env_name.strip():
        value = os.environ.get(env_name.strip(), "")
        if value.strip():
            return value.strip()
        if required:
            raise ConnectorConfigurationError(
                f"[{source_id}] API mode requires environment variable "
                f"'{env_name.strip()}' (referenced by '{env_key}') to be set."
            )
        return ""

    if required:
        raise ConnectorConfigurationError(
            f"[{source_id}] API mode requires connection field '{direct_key}' "
            f"or '{env_key}' (naming an environment variable)."
        )
    return ""


def _positive_int(value: Any, default: int) -> int:
    """Return ``value`` as a positive int, else ``default``."""
    if isinstance(value, bool):  # bool is an int subclass — reject explicitly.
        return default
    if isinstance(value, int) and value > 0:
        return value
    return default


def _non_negative_float(value: Any, default: float) -> float:
    """Return ``value`` as a non-negative float, else ``default``."""
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)) and value >= 0:
        return float(value)
    return default


@dataclass(frozen=True)
class RetryPolicy:
    """Bounded exponential-backoff retry policy for transient failures."""

    max_attempts: int = _DEFAULT_MAX_ATTEMPTS
    backoff_seconds: float = _DEFAULT_BACKOFF_SECONDS
    max_backoff_seconds: float = _DEFAULT_MAX_BACKOFF_SECONDS

    def delay_for(self, attempt: int) -> float:
        """Return the backoff delay (seconds) before retrying after ``attempt``.

        ``attempt`` is 1-based; the delay grows exponentially and is capped at
        :attr:`max_backoff_seconds`.
        """
        if self.backoff_seconds <= 0:
            return 0.0
        delay = self.backoff_seconds * (2 ** (attempt - 1))
        return min(delay, self.max_backoff_seconds)


def resolve_retry_policy(api_config: dict[str, Any]) -> RetryPolicy:
    """Build a :class:`RetryPolicy` from the source ``api.retry`` block."""
    retry_config = api_config.get("retry")
    if not isinstance(retry_config, dict):
        retry_config = {}
    return RetryPolicy(
        max_attempts=_positive_int(retry_config.get("maxAttempts"), _DEFAULT_MAX_ATTEMPTS),
        backoff_seconds=_non_negative_float(
            retry_config.get("backoffSeconds"), _DEFAULT_BACKOFF_SECONDS
        ),
        max_backoff_seconds=_non_negative_float(
            retry_config.get("maxBackoffSeconds"), _DEFAULT_MAX_BACKOFF_SECONDS
        ),
    )


def resolve_timeout_seconds(api_config: dict[str, Any]) -> float:
    """Resolve the request timeout (seconds) from the source ``api`` block."""
    return (
        _non_negative_float(api_config.get("timeoutSeconds"), _DEFAULT_TIMEOUT_SECONDS)
        or _DEFAULT_TIMEOUT_SECONDS
    )


def resolve_page_size(api_config: dict[str, Any], default: int = _DEFAULT_PAGE_SIZE) -> int:
    """Resolve the pagination page size from the source ``api.pagination`` block."""
    pagination = api_config.get("pagination")
    if not isinstance(pagination, dict):
        pagination = {}
    return _positive_int(pagination.get("pageSize"), default)


# --------------------------------------------------------------------------- #
# HTTP client
# --------------------------------------------------------------------------- #
# Sentinel signalling "retry this attempt". Distinct from any JSON payload
# (``None`` is a valid JSON body, so ``None`` cannot be used as the sentinel).
_RETRY: Any = object()


class ApiClient:
    """Source-agnostic, resilient HTTP GET client returning parsed JSON.

    The client owns *transport* concerns only — timeout, retry/backoff, logging,
    and error translation. It knows nothing about any source's payload shape or
    pagination scheme.
    """

    def __init__(
        self,
        base_url: str,
        *,
        source_id: str = "",
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
        retry: RetryPolicy | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        """Initialize the client.

        Args:
            base_url: Absolute base URL of the source API (no trailing slash
                required). Must be non-empty.
            source_id: Source identifier used in logs and error messages.
            timeout_seconds: Per-request timeout.
            retry: Retry policy; defaults to :class:`RetryPolicy`.
            client: Optional pre-built :class:`httpx.Client` (used by tests to
                inject a mock transport). When omitted, the client is created
                lazily and owned/closed by this instance.

        Raises:
            ConnectorConfigurationError: If ``base_url`` is empty.
        """
        if not isinstance(base_url, str) or not base_url.strip():
            raise ConnectorConfigurationError(
                f"[{source_id}] API mode requires a non-empty base URL."
            )
        self._base_url = base_url.strip().rstrip("/")
        self._source_id = source_id
        self._timeout = timeout_seconds
        self._retry = retry or RetryPolicy()
        self._client = client
        self._owns_client = client is None

    def __enter__(self) -> ApiClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP client if this instance owns it."""
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self._timeout)
        return self._client

    def _full_url(self, path: str) -> str:
        if path.startswith(("http://", "https://")):
            return path
        return f"{self._base_url}/{path.lstrip('/')}"

    def get_json(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        auth: httpx.Auth | tuple[str, str] | None = None,
    ) -> Any:
        """Perform a resilient GET and return the parsed JSON body.

        Transient failures (network errors, timeouts, HTTP 429/5xx) are retried
        per the configured :class:`RetryPolicy`. Authentication failures
        (401/403), not-found (404), and other 4xx are surfaced immediately —
        retrying them cannot succeed.

        Args:
            path: Request path (appended to the base URL) or an absolute URL.
            params: Query parameters.
            headers: Request headers.
            auth: httpx auth object or ``(user, password)`` tuple.

        Returns:
            Any: The decoded JSON payload (typically ``dict`` or ``list``).

        Raises:
            ConnectorConnectionError: On authentication failure or on a network/
                timeout error that persists across all attempts.
            ConnectorFetchError: On a non-retryable HTTP error, a transient HTTP
                error that persists across all attempts, or a malformed JSON
                body.
        """
        url = self._full_url(path)
        attempts = self._retry.max_attempts

        for attempt in range(1, attempts + 1):
            is_last = attempt == attempts
            try:
                response = self._http().get(url, params=params, headers=headers, auth=auth)
            except httpx.RequestError as exc:
                kind = "timeout" if isinstance(exc, httpx.TimeoutException) else "network"
                logger.warning(
                    "connector api request error",
                    extra={
                        "source": self._source_id,
                        "url": url,
                        "attempt": attempt,
                        "maxAttempts": attempts,
                        "errorKind": kind,
                        "error": str(exc),
                    },
                )
                if is_last:
                    raise ConnectorConnectionError(
                        f"[{self._source_id}] {kind} error contacting {url} "
                        f"after {attempts} attempt(s): {exc}"
                    ) from exc
                self._backoff(attempt)
                continue

            outcome = self._handle_response(response, url, attempt, attempts)
            if outcome is _RETRY:
                if is_last:
                    raise ConnectorFetchError(
                        f"[{self._source_id}] transient HTTP "
                        f"{response.status_code} from {url} persisted after "
                        f"{attempts} attempt(s)."
                    )
                self._backoff(attempt)
                continue
            return outcome

        # Loop always returns or raises; this is defensive only.
        raise ConnectorFetchError(
            f"[{self._source_id}] request to {url} failed to produce a response."
        )

    def _handle_response(
        self, response: httpx.Response, url: str, attempt: int, attempts: int
    ) -> Any:
        """Classify a response: return parsed JSON, ``_RETRY``, or raise."""
        status = response.status_code

        if status in _AUTH_STATUS:
            raise ConnectorConnectionError(
                f"[{self._source_id}] authentication/authorization failed "
                f"(HTTP {status}) for {url}. Check the configured credentials."
            )
        if status == 404:
            raise ConnectorFetchError(
                f"[{self._source_id}] resource not found (HTTP 404) for {url}."
            )
        if status in _RETRYABLE_STATUS:
            logger.warning(
                "connector api transient status",
                extra={
                    "source": self._source_id,
                    "url": url,
                    "attempt": attempt,
                    "maxAttempts": attempts,
                    "status": status,
                },
            )
            return _RETRY
        if status >= 400:
            raise ConnectorFetchError(
                f"[{self._source_id}] unexpected HTTP {status} for {url}: {response.text[:200]}"
            )

        try:
            payload = response.json()
        except (ValueError, UnicodeDecodeError) as exc:
            raise ConnectorFetchError(
                f"[{self._source_id}] malformed JSON in response from {url}: {exc}"
            ) from exc

        logger.info(
            "connector api ok",
            extra={
                "source": self._source_id,
                "url": url,
                "attempt": attempt,
                "status": status,
            },
        )
        return payload

    def _backoff(self, attempt: int) -> None:
        delay = self._retry.delay_for(attempt)
        if delay > 0:
            time.sleep(delay)
