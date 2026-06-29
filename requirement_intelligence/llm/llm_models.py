"""LLM data models — provider-agnostic request and response contracts.

These models are the only shapes that cross the boundary between the LLM layer
and every downstream component (Prompt Builder, Response Validator, CP1 Engine,
Output Writer).  No provider-specific fields appear here.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from shared.contracts.base import Schema


class LLMRequest(Schema):
    """Input sent to any LLM provider.

    Fields
    ------
    prompt:
        The fully-rendered prompt string produced by the Prompt Builder.
    temperature:
        Sampling temperature forwarded to the provider (0.0 = deterministic).
    metadata:
        Arbitrary key/value pairs the caller wants preserved in the response
        for tracing or auditing purposes.
    """

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
        Short identifier of the provider that produced this response
        (e.g. ``"gemini"``, ``"azure_openai"``).
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
        (e.g. ``"stop"``, ``"max_tokens"``).
    latency_ms:
        Wall-clock time from request dispatch to response receipt, in
        milliseconds.
    usage:
        Token accounting reported by the provider.
    """

    provider: str
    model: str
    generated_text: str
    raw_response: dict[str, Any] = Field(default_factory=dict)
    finish_reason: str | None = None
    latency_ms: float | None = None
    usage: LLMUsage | None = None
