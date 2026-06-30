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

    Execution semantics — interpretable vs. opaque fields
    -----------------------------------------------------
    Every field on this model is already **normalized** by the provider adapter
    (see *Provider Normalization Contract* below).  Fields fall into three kinds:

    * **Provider-independent (downstream MAY interpret).** Normalized values that
      every downstream component — validators, CP1, output writer — may read and
      reason about:

      - ``generated_text`` — the normalized primary text output.
      - ``execution_status`` — the normalized execution outcome
        (:class:`~shared.enums.base.ExecutionStatus`).
      - ``usage`` — normalized token accounting (:class:`LLMUsage`).
      - ``latency_ms`` — normalized wall-clock duration metric.

    * **Provider-specific (downstream must NEVER interpret).** Opaque, retained
      for audit/observability only; reasoning over them would couple a component
      to a provider:

      - ``finish_reason`` — a provider-reported string (e.g. ``"stop"``,
        ``"max_tokens"``). **Never** parse it to infer an outcome; read
        ``execution_status`` instead.
      - ``raw_response`` — the full, unmodified provider payload. **Never** parse
        it. It exists for auditing.

    * **Identity (informational).** ``provider`` and ``model`` identify the
      origin for routing/observability; they are not validation signals.

    Provider Normalization Contract
    -------------------------------
    A provider adapter is the **only** place normalization happens. Before
    constructing an ``LLMResponse``, every adapter must normalize:

    * the **execution outcome** → :class:`~shared.enums.base.ExecutionStatus`,
    * **token usage** → :class:`LLMUsage`,
    * **latency** → ``latency_ms``,
    * the **generated text** → ``generated_text``.

    **No downstream component, no validator, and no validation rule performs
    normalization.** They consume the already-normalized, provider-independent
    fields. A new provider conforms by normalizing into these same fields — no
    downstream change is required.

    Fields
    ------
    provider:
        Identity. Enum identifier of the provider that produced this response
        (e.g. ``ProviderType.GEMINI``).  Serialises to its string value
        (``"gemini"``) via ``model_dump()``.
    model:
        Identity. The specific model name used for generation
        (e.g. ``"gemini-1.5-pro"``).
    generated_text:
        Provider-independent. The normalized primary text output from the model.
    raw_response:
        Provider-specific. The full, unmodified payload returned by the provider
        SDK, stored for auditing.  Downstream components must **never** parse it.
    finish_reason:
        Provider-specific. Provider-reported reason the generation stopped
        (e.g. ``"stop"``, ``"max_tokens"``).  Downstream components must **never**
        interpret it; read ``execution_status`` instead.
    execution_status:
        Provider-independent. The **normalized** outcome of the execution
        (completed, timed out, failed).  Provider adapters map their
        provider-specific termination signals onto this enum; downstream
        validation reads it without any provider knowledge.  Defaults to
        :attr:`~shared.enums.base.ExecutionStatus.COMPLETED` so existing callers
        and providers remain unchanged (backward compatible).
    latency_ms:
        Provider-independent. Normalized wall-clock time from request dispatch to
        response receipt, in milliseconds.
    usage:
        Provider-independent. Normalized token accounting reported by the provider.
    """

    provider: ProviderType
    model: str
    generated_text: str
    raw_response: dict[str, Any] = Field(default_factory=dict)
    finish_reason: str | None = None
    execution_status: ExecutionStatus = ExecutionStatus.COMPLETED
    latency_ms: float | None = None
    usage: LLMUsage | None = None
