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

    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
