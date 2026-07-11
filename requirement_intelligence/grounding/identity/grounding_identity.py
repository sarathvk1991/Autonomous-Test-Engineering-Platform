"""Strongly typed identity value objects for the Grounding Framework.

These follow the precedent set by the Engineering Context Orchestration identity
model (ADR-0015): immutable, validated, string-backed identifiers and
semantic-version value objects, each serialising to and validating from a
**plain JSON string**.

The base classes are duplicated here rather than imported from that subsystem on
purpose — ADR-0015 §C already made the same call for ``PolicyVersion``
(duplicating ``PromptVersion`` rather than coupling two subsystems), and names
``shared/`` as the eventual home for both. The Grounding Framework stays
self-contained: it imports no other subsystem's identity model.

Determinism
-----------
:meth:`GroundedRequirementId.for_requirement` and
:meth:`GroundingAssessmentId.for_run` are **pure functions** of their inputs —
no UUID, no clock. The same requirement text always mints the same id, which is
what lets a grounded requirement be compared and de-duplicated across runs.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, ClassVar

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

from requirement_intelligence.models.enums import SourceCategory

# URL- and filename-safe identifier shape, identical to the orchestration
# subsystem's: lower-case, starts and ends alphanumeric, '.', '_', ':' or '-'
# permitted between.
_IDENTIFIER_RE = re.compile(r"^[a-z0-9](?:[a-z0-9._:-]*[a-z0-9])?$")

_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def _normalise_text(text: str) -> str:
    """Collapse whitespace and lower-case, so trivial edits mint the same id."""
    return " ".join(text.split()).lower()


@dataclass(frozen=True)
class _StringIdentifier:
    """Base for immutable, validated, string-backed identifiers."""

    value: str

    #: Human-readable type name used in error messages.
    _LABEL: ClassVar[str] = "identifier"

    def __post_init__(self) -> None:
        """Validate the identifier's shape. Raises :class:`ValueError` if invalid."""
        if not isinstance(self.value, str) or not _IDENTIFIER_RE.match(self.value):
            raise ValueError(
                f"Invalid {self._LABEL} {self.value!r}. Expected a non-empty, "
                f"lower-case string of letters, digits, '.', '_', ':' or '-', "
                f"starting and ending with a letter or digit."
            )

    @classmethod
    def parse(cls, raw: str) -> Any:
        """Build an identifier from *raw*, tolerating surrounding whitespace."""
        if not isinstance(raw, str):
            raise ValueError(f"Invalid {cls._LABEL}: expected a string, got {type(raw).__name__}.")
        return cls(raw.strip())

    def __str__(self) -> str:
        """Return the canonical string form (round-trips through :meth:`parse`)."""
        return self.value

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """Validate from a plain string and serialise back to a plain string."""
        from_string = core_schema.chain_schema(
            [
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(cls.parse),
            ]
        )
        return core_schema.json_or_python_schema(
            json_schema=from_string,
            python_schema=core_schema.union_schema(
                [core_schema.is_instance_schema(cls), from_string]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                str, return_schema=core_schema.str_schema()
            ),
        )


@dataclass(frozen=True)
class GroundedRequirementId(_StringIdentifier):
    """The stable, deterministic identity of one :class:`GroundedRequirement`.

    Minted as a pure function of the requirement's domain and normalised text, so
    the same generated requirement always yields the same id, run after run.
    """

    _LABEL: ClassVar[str] = "grounded requirement id"

    @classmethod
    def for_requirement(cls, domain: SourceCategory | str, text: str) -> GroundedRequirementId:
        """Mint the deterministic id for a requirement of *domain* with *text*."""
        if not text or not text.strip():
            raise ValueError("Cannot mint a grounded requirement id from empty text.")
        domain_slug = str(domain)
        digest = hashlib.sha256(f"{domain_slug}\x1f{_normalise_text(text)}".encode()).hexdigest()
        return cls(f"req-{domain_slug}-{digest[:12]}")


@dataclass(frozen=True)
class MatchingPolicyId(_StringIdentifier):
    """The permanent, governed identity of a ``MatchingPolicy``.

    A policy id is an identity, never an alias: two policies may currently express
    identical rules yet remain distinct ids, mirroring ``OrchestrationPolicyId``.
    """

    _LABEL: ClassVar[str] = "matching policy id"


@dataclass(frozen=True)
class GroundingAssessmentId(_StringIdentifier):
    """The deterministic identity of one grounding assessment.

    A pure function of the context identity and the assessed content, so the same
    response over the same context yields the same assessment id.
    """

    _LABEL: ClassVar[str] = "grounding assessment id"

    @classmethod
    def for_run(cls, context_id: str, content: str) -> GroundingAssessmentId:
        """Mint the deterministic assessment id for *content* under *context_id*."""
        ctx = str(context_id).strip()
        if not ctx:
            raise ValueError("Cannot mint a grounding assessment id from an empty context id.")
        digest = hashlib.sha256(content.encode()).hexdigest()
        return cls(f"grnd-{ctx}-{digest[:8]}")


@dataclass(frozen=True, order=True)
class _SemanticVersion:
    """Base for immutable, comparable ``MAJOR.MINOR.PATCH`` version value objects."""

    major: int
    minor: int
    patch: int

    _LABEL: ClassVar[str] = "version"

    def __post_init__(self) -> None:
        """Reject negative components. Raises :class:`ValueError` if invalid."""
        if self.major < 0 or self.minor < 0 or self.patch < 0:
            raise ValueError(
                f"Invalid {self._LABEL} {self.major}.{self.minor}.{self.patch}: "
                f"components must be non-negative."
            )

    @classmethod
    def parse(cls, version_string: str) -> Any:
        """Parse ``MAJOR.MINOR.PATCH`` into a version value object."""
        if not isinstance(version_string, str):
            raise ValueError(
                f"Invalid {cls._LABEL}: expected a string, got {type(version_string).__name__}."
            )
        match = _SEMVER_RE.match(version_string.strip())
        if not match:
            raise ValueError(
                f"Invalid {cls._LABEL} string {version_string!r}. Expected "
                f"MAJOR.MINOR.PATCH with non-negative integers (e.g. '1.0.0')."
            )
        return cls(int(match.group(1)), int(match.group(2)), int(match.group(3)))

    def __str__(self) -> str:
        """Return the canonical ``MAJOR.MINOR.PATCH`` string form."""
        return f"{self.major}.{self.minor}.{self.patch}"

    def is_compatible_with(self, other: _SemanticVersion) -> bool:
        """Return ``True`` when this version is backwards-compatible with *other*."""
        return self.major == other.major

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """Validate from a ``"1.0.0"`` string and serialise back to one."""
        from_string = core_schema.chain_schema(
            [
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(cls.parse),
            ]
        )
        return core_schema.json_or_python_schema(
            json_schema=from_string,
            python_schema=core_schema.union_schema(
                [core_schema.is_instance_schema(cls), from_string]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                str, return_schema=core_schema.str_schema()
            ),
        )


@dataclass(frozen=True, order=True)
class GroundingFrameworkVersion(_SemanticVersion):
    """Semantic version of the Grounding Framework's code/contract."""

    _LABEL: ClassVar[str] = "grounding framework version"


@dataclass(frozen=True, order=True)
class GroundingConfigurationVersion(_SemanticVersion):
    """Semantic version of the governed grounding configuration (weights/thresholds)."""

    _LABEL: ClassVar[str] = "grounding configuration version"


@dataclass(frozen=True, order=True)
class MatchingNormalizationVersion(_SemanticVersion):
    """Semantic version of the governed matching text-normalization configuration."""

    _LABEL: ClassVar[str] = "matching normalization version"


@dataclass(frozen=True, order=True)
class MatchingPolicyVersion(_SemanticVersion):
    """Semantic version of a governed ``MatchingPolicy``."""

    _LABEL: ClassVar[str] = "matching policy version"
