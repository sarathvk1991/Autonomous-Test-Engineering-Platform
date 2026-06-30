"""Shared enumerations used across platform layers.

Defined once in the shared kernel so connectors, models, services, and the API
all speak the same vocabulary. String-valued enums serialise cleanly to JSON
and to the database.
"""

from __future__ import annotations

from enum import StrEnum


class SourceSystem(StrEnum):
    """Systems the Requirement Intelligence Layer can ingest from."""

    JIRA = "jira"
    SONARQUBE = "sonarqube"
    OWASP_ZAP = "owasp_zap"


class ProviderType(StrEnum):
    """LLM providers the platform can route generation requests to.

    Only :attr:`GEMINI` is active today; :attr:`AZURE_OPENAI` is a stub. The
    remaining members are reserved so downstream contracts and configuration can
    reference them before the corresponding providers are implemented.
    """

    GEMINI = "gemini"
    AZURE_OPENAI = "azure_openai"

    # Reserved for future activation — no implementation yet.
    ANTHROPIC = "anthropic"
    BEDROCK = "bedrock"
    OLLAMA = "ollama"
    OPENAI = "openai"


class ExecutionStatus(StrEnum):
    """Normalized, provider-independent outcome of an AI execution.

    Every provider adapter (Gemini, Azure OpenAI, Anthropic, Bedrock, Ollama, …)
    maps its provider-specific completion/termination signal onto one of these
    members *before* constructing an :class:`~requirement_intelligence.llm.llm_models.LLMResponse`.
    Downstream components — notably the Response Validation framework — read this
    normalized outcome and never interpret provider-specific codes.

    Each member is a distinct execution outcome owned by exactly one Transport
    validation rule, so the outcomes never overlap:

    * ``COMPLETED`` — the execution finished normally (success).
    * ``TIMEOUT``   — the execution was cut short by a timeout. Consumed by
      ``TRANSPORT-0003`` (TimeoutRule).
    * ``FAILED``    — the execution failed at the delivery boundary: a provider
      or transport error (or refusal) at the call boundary that is **not** a
      timeout. Consumed by the reserved ``TRANSPORT-0004`` (ProviderFailureRule).

    Conceptual normalization mapping (provider-independent — never SDK values)::

        Provider response                    Adapter normalizes to   ExecutionStatus
        ---------------------------------    ---------------------   ---------------
        a normal, finished generation        success              →  COMPLETED
        a deadline / time-limit signal       timed out            →  TIMEOUT
        a transport/provider error or        failed at the        →  FAILED
          refusal at the call boundary         delivery boundary

    ``TIMEOUT`` and ``FAILED`` are **sibling** failure outcomes: a timeout is
    normalized to ``TIMEOUT`` (never ``FAILED``), and any other delivery-boundary
    failure is normalized to ``FAILED``. Keeping them distinct lets each Transport
    rule validate exactly one outcome.

    Members are added additively as new outcomes need representing; absence of a
    member is never inferred from provider strings.
    """

    #: The execution finished normally. Default outcome (backward compatible).
    COMPLETED = "completed"

    #: The execution was cut short by a timeout. Consumed by TRANSPORT-0003.
    TIMEOUT = "timeout"

    #: The execution failed at the delivery boundary — a provider/transport error
    #: that is not a timeout. Consumed by the reserved TRANSPORT-0004.
    FAILED = "failed"


class RequirementType(StrEnum):
    """Classification dimension: the nature of a requirement."""

    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    SECURITY = "security"
    QUALITY = "quality"
    PERFORMANCE = "performance"
    COMPLIANCE = "compliance"
    UNKNOWN = "unknown"


class RequirementPriority(StrEnum):
    """Normalised priority across heterogeneous source systems."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class RequirementStatus(StrEnum):
    """Lifecycle status of a canonical requirement within the platform."""

    INGESTED = "ingested"
    PARSED = "parsed"
    CONSOLIDATED = "consolidated"
    CLASSIFIED = "classified"
    ANALYZED = "analyzed"
    VALIDATED = "validated"
    REJECTED = "rejected"


class ValidationVerdict(StrEnum):
    """Outcome of a validation gate such as CP1."""

    PASS = "pass"  # noqa: S105 - a verdict value, not a secret
    FAIL = "fail"
    WARN = "warn"
