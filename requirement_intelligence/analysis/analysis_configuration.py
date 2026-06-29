"""Analysis execution configuration — the stable execution-policy contract.

:class:`AnalysisConfiguration` captures the *execution policy* for AI analyses:
how an analysis should be run, not what is being analysed. It is the single
dependency the Requirement Analysis Service takes for run-time policy, so that
future policies (timeouts, retries, streaming, schema mode, provider failover,
…) can be added here without changing the service's public constructor.

What this model is **not**:

* It does **not** describe the analysis itself (that is the consolidated
  artifact and the resulting ``AnalysisResult``).
* It does **not** contain prompt content (owned by the Prompt Framework).
* It does **not** contain provider implementations or provider-specific settings
  (owned by the LLM Provider Framework).
* It is **not** request-specific — one configuration governs many analyses.
"""

from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from shared.contracts.base import Schema


class AnalysisConfiguration(Schema):
    """Immutable, strictly-validated execution policy for AI analysis.

    Field names serialise as ``camelCase`` (``reasoningContractVersion``,
    ``providerTimeoutSeconds``, …); Python attributes stay ``snake_case``.

    Fields
    ------
    reasoning_contract_version:
        Version of the AI Reasoning Contract in force for executions governed by
        this configuration. Required and non-empty.
    temperature:
        Sampling temperature to forward to the provider (0.0 = deterministic).
        Must be within ``[0.0, 2.0]``.
    provider_timeout_seconds:
        Reserved for a future phase. Per-request provider timeout; when supplied
        it must be greater than zero. Not yet consumed by the service.
    max_retry_attempts:
        Reserved for a future phase. Number of retry attempts; must be ``>= 0``.
        Not yet consumed by the service.
    enable_streaming:
        Reserved for a future phase. Whether streaming responses are requested.
        Not yet consumed by the service.
    response_schema_enabled:
        Reserved for a future phase. Whether a structured response schema is
        requested. Not yet consumed by the service.
    metadata:
        Free-form execution metadata the caller wishes to associate with the
        configuration. Preserved verbatim.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    # --- Required policy ------------------------------------------------------
    reasoning_contract_version: str = Field(min_length=1)

    # --- Active optional policy ----------------------------------------------
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)

    # --- Reserved for future phases (preserved, not yet consumed) ------------
    provider_timeout_seconds: int | None = Field(default=None, gt=0)
    max_retry_attempts: int = Field(default=0, ge=0)
    enable_streaming: bool = False
    response_schema_enabled: bool = False

    metadata: dict[str, Any] = Field(default_factory=dict)
