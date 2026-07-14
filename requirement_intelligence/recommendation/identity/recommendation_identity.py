"""Strongly typed identity value objects for the Recommendation Framework.

These follow the precedent set by the Engineering Context Orchestration identity model
(ADR-0015), the Grounding Framework identity model (ADR-0016), the Quality Governance
identity model (ADR-0017), and the Requirement Enhancement identity model (ADR-0018):
immutable, validated, string-backed identifiers and semantic-version value objects,
each serialising to and validating from a **plain JSON string**.

The base classes are duplicated here rather than imported from those subsystems on
purpose — ADR-0015 §C, ADR-0016 §D6, ADR-0017 (identity module docstring), and
ADR-0018 §D5 already made the same call. The Recommendation Framework stays
self-contained: it imports no other subsystem's identity model.

Determinism
-----------
:meth:`RecommendationId.for_ordinal`, :meth:`RecommendationGroupId.for_ordinal`, and
:meth:`RecommendationResultId.for_execution` are **pure functions** of their inputs —
no UUID, no clock. The same execution always mints the same ids, which is what lets a
future recommendation result be compared and reproduced across runs (ADR-0019
Recommendation 2/3 precedent).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, ClassVar

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

# URL- and filename-safe identifier shape, identical to the orchestration, grounding,
# quality-governance, and enhancement subsystems': lower-case, starts and ends
# alphanumeric, '.', '_', ':' or '-' permitted between.
_IDENTIFIER_RE = re.compile(r"^[a-z0-9](?:[a-z0-9._:-]*[a-z0-9])?$")

_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


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
class RecommendationPolicyId(_StringIdentifier):
    """The permanent, governed identity of a ``RecommendationPolicy``.

    A policy id is an identity, never an alias: two policies may currently express
    identical rules yet remain distinct ids, mirroring ``EnhancementPolicyId`` and
    ``QualityPolicyId``.
    """

    _LABEL: ClassVar[str] = "recommendation policy id"


@dataclass(frozen=True)
class RecommendationId(_StringIdentifier):
    """The deterministic identity of one :class:`Recommendation`.

    A pure function of the execution it belongs to and a stable per-execution
    ordinal — no UUID, no clock. A future recommendation engine mints these; this
    class only shapes them.
    """

    _LABEL: ClassVar[str] = "recommendation id"

    @classmethod
    def for_ordinal(cls, execution_id: str, ordinal: int) -> RecommendationId:
        """Mint the deterministic id for the *ordinal*-th recommendation of *execution_id*."""
        execution = str(execution_id).strip()
        if not execution:
            raise ValueError("Cannot mint a recommendation id from an empty execution id.")
        if ordinal < 0:
            raise ValueError("Cannot mint a recommendation id from a negative ordinal.")
        digest = hashlib.sha256(f"{execution}:{ordinal}".encode()).hexdigest()
        return cls(f"rc-{digest[:12]}")


@dataclass(frozen=True)
class RecommendationGroupId(_StringIdentifier):
    """The deterministic identity of one :class:`RecommendationGroup`.

    A pure function of the execution it belongs to and a stable per-execution
    ordinal, exactly mirroring :meth:`RecommendationId.for_ordinal`.
    """

    _LABEL: ClassVar[str] = "recommendation group id"

    @classmethod
    def for_ordinal(cls, execution_id: str, ordinal: int) -> RecommendationGroupId:
        """Mint the deterministic id for the *ordinal*-th group of *execution_id*."""
        execution = str(execution_id).strip()
        if not execution:
            raise ValueError("Cannot mint a recommendation group id from an empty execution id.")
        if ordinal < 0:
            raise ValueError("Cannot mint a recommendation group id from a negative ordinal.")
        digest = hashlib.sha256(f"{execution}:{ordinal}".encode()).hexdigest()
        return cls(f"rg-{digest[:12]}")


@dataclass(frozen=True)
class RecommendationResultId(_StringIdentifier):
    """The deterministic identity of one :class:`RecommendationResult`.

    A pure function of the execution it assembles from, exactly mirroring
    ``RequirementEnhancementResultId.for_enhancement`` and
    ``QualityGovernanceResultId.for_assessment``.
    """

    _LABEL: ClassVar[str] = "recommendation result id"

    @classmethod
    def for_execution(cls, execution_id: str) -> RecommendationResultId:
        """Mint the deterministic result id for *execution_id*."""
        execution = str(execution_id).strip()
        if not execution:
            raise ValueError("Cannot mint a recommendation result id from an empty execution id.")
        digest = hashlib.sha256(execution.encode()).hexdigest()
        return cls(f"rr-{digest[:12]}")


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
class RecommendationFrameworkVersion(_SemanticVersion):
    """Semantic version of the Recommendation Framework's code/contract."""

    _LABEL: ClassVar[str] = "recommendation framework version"


@dataclass(frozen=True, order=True)
class RecommendationPolicyVersion(_SemanticVersion):
    """Semantic version of one governed :class:`RecommendationPolicy`.

    Advances independently of :class:`RecommendationFrameworkVersion`,
    :class:`RecommendationVersion`, and :class:`RecommendationResultVersion`
    (Recommendation 5 of ADR-0019: no shared version axis). Tuning a rule or a
    capability switch is a policy-version change, never a framework change.
    """

    _LABEL: ClassVar[str] = "recommendation policy version"


@dataclass(frozen=True, order=True)
class RecommendationVersion(_SemanticVersion):
    """Semantic version of the ``Recommendation`` / ``RecommendationGroup`` schema.

    Versions the recommendation vocabulary and shape independently of every other
    axis, so a future recommendation type or field can be added without forcing a
    framework, policy, or result-contract change. Reserved for a future milestone,
    exactly as ``RelationshipVersion`` and ``ObservationVersion`` were reserved by
    ADR-0018 without yet being stamped onto a model field.
    """

    _LABEL: ClassVar[str] = "recommendation version"


@dataclass(frozen=True, order=True)
class RecommendationResultVersion(_SemanticVersion):
    """Semantic version of the ``RecommendationResult`` **runtime contract**.

    Independent of the framework, the policy, and the recommendation schema
    version; a change here never forces any of those to change, and vice versa —
    the direct analogue of ``EnhancementResultVersion`` and
    ``QualityGovernanceResultVersion``.
    """

    _LABEL: ClassVar[str] = "recommendation result version"
