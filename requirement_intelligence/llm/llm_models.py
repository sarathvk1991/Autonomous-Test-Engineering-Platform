"""LLM data models — provider-agnostic request and response contracts.

These models are the only shapes that cross the boundary between the LLM layer
and every downstream component (Prompt Builder, Response Validator, CP1 Engine,
Output Writer).  No provider-specific fields appear here.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from shared.contracts.base import Schema
from shared.enums.base import ExecutionStatus, ProviderType


class LLMRequest(Schema):
    """Input sent to any LLM provider.

    Fields
    ------
    request_id:
        Caller-supplied identifier that follows the request end-to-end —
        Prompt Builder → LLM Provider → Response Validator → CP1 Validation →
        Output Writer → Governance Dashboard.  Must be non-empty; no UUID is
        generated automatically.
    prompt:
        The fully-rendered prompt string produced by the Prompt Builder.
    temperature:
        Sampling temperature forwarded to the provider (0.0 = deterministic).
    metadata:
        Arbitrary key/value pairs the caller wants preserved in the response
        for tracing or auditing purposes.
    """

    request_id: str = Field(min_length=1)
    prompt: str
    temperature: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMUsage(Schema):
    """Token consumption reported by the provider (best-effort; may be None)."""

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class LLMResponse(Schema):
    """Provider-agnostic response returned to every downstream component.

    Fields
    ------
    provider:
        Enum identifier of the provider that produced this response
        (e.g. ``ProviderType.GEMINI``).  Serialises to its string value
        (``"gemini"``) via ``model_dump()``.
    model:
        The specific model name used for generation
        (e.g. ``"gemini-1.5-pro"``).
    generated_text:
        The primary text output from the model.
    raw_response:
        The full, unmodified payload returned by the provider SDK, stored for
        auditing.  Downstream components must not parse this field.
    finish_reason:
        Provider-reported reason the generation stopped
        (e.g. ``"stop"``, ``"max_tokens"``).  Provider-specific; downstream
        components must not interpret it.
    execution_status:
        The **normalized, provider-independent** outcome of the execution
        (e.g. completed, timed out).  Provider adapters map their
        provider-specific termination signals onto this enum; downstream
        validation reads it without any provider knowledge.  Defaults to
        :attr:`~shared.enums.base.ExecutionStatus.COMPLETED` so existing callers
        and providers remain unchanged (backward compatible).
    latency_ms:
        Wall-clock time from request dispatch to response receipt, in
        milliseconds.
    usage:
        Token accounting reported by the provider.
    """

    provider: ProviderType
    model: str
    generated_text: str
    raw_response: dict[str, Any] = Field(default_factory=dict)
    finish_reason: str | None = None
    execution_status: ExecutionStatus = ExecutionStatus.COMPLETED
    latency_ms: float | None = None
    usage: LLMUsage | None = None
