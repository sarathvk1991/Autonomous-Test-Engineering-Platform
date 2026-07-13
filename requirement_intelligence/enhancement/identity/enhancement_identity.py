"""Strongly typed identity value objects for the Requirement Intelligence Enhancement
Framework.

These follow the precedent set by the Engineering Context Orchestration identity model
(ADR-0015), the Grounding Framework identity model (ADR-0016), and the Quality Governance
identity model (ADR-0017): immutable, validated, string-backed identifiers and
semantic-version value objects, each serialising to and validating from a **plain JSON
string**.

The base classes are duplicated here rather than imported from those subsystems on
purpose — ADR-0015 §C, ADR-0016 §D6, and ADR-0017 (identity module docstring) already
made the same call. Requirement Enhancement stays self-contained: it imports no other
subsystem's identity model.

Determinism
-----------
:meth:`RequirementEnhancementId.for_run` and
:meth:`RequirementEnhancementResultId.for_enhancement` are **pure functions** of their
inputs — no UUID, no clock. The same analysis and execution always mint the same ids,
which is what lets a future enhancement result be compared and reproduced across runs
(ADR-0018 Recommendation 4/5 precedent).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, ClassVar

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

# URL- and filename-safe identifier shape, identical to the orchestration, grounding,
# and quality-governance subsystems': lower-case, starts and ends alphanumeric, '.',
# '_', ':' or '-' permitted between.
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
class EnhancementPolicyId(_StringIdentifier):
    """The permanent, governed identity of an ``EnhancementPolicy``.

    A policy id is an identity, never an alias: two policies may currently express
    identical rules yet remain distinct ids, mirroring ``QualityPolicyId``.
    """

    _LABEL: ClassVar[str] = "enhancement policy id"


@dataclass(frozen=True)
class RequirementEnhancementId(_StringIdentifier):
    """The deterministic identity of one enhancement run.

    A pure function of the analysis and execution it enhances, so the same run over
    the same upstream inputs always yields the same enhancement id — the enhancement
    analogue of ``QualityAssessmentId``.
    """

    _LABEL: ClassVar[str] = "requirement enhancement id"

    @classmethod
    def for_run(cls, analysis_id: str, execution_id: str) -> RequirementEnhancementId:
        """Mint the deterministic enhancement id for *analysis_id* / *execution_id*."""
        analysis = str(analysis_id).strip()
        execution = str(execution_id).strip()
        if not analysis or not execution:
            raise ValueError(
                "Cannot mint a requirement enhancement id from an empty analysis or "
                "execution id."
            )
        digest = hashlib.sha256(f"{analysis}:{execution}".encode()).hexdigest()
        return cls(f"re-{digest[:12]}")


@dataclass(frozen=True)
class EnhancedRequirementId(_StringIdentifier):
    """The deterministic identity of one :class:`EnhancedRequirement`.

    A pure function of the source requirement it enriches and the enhancement run it
    belongs to, so the same requirement in the same run always yields the same id.
    """

    _LABEL: ClassVar[str] = "enhanced requirement id"

    @classmethod
    def for_requirement(
        cls, enhancement_id: str, requirement_id: str
    ) -> EnhancedRequirementId:
        """Mint the deterministic id for *requirement_id* within *enhancement_id*."""
        enhancement = str(enhancement_id).strip()
        requirement = str(requirement_id).strip()
        if not enhancement or not requirement:
            raise ValueError(
                "Cannot mint an enhanced requirement id from an empty enhancement or "
                "requirement id."
            )
        digest = hashlib.sha256(f"{enhancement}:{requirement}".encode()).hexdigest()
        return cls(f"er-{digest[:12]}")


@dataclass(frozen=True)
class RelationshipGraphId(_StringIdentifier):
    """The deterministic identity of one :class:`RelationshipGraph`.

    A pure function of the enhancement run it belongs to — one graph per enhancement
    result (Recommendation 6: a single canonical relationship store).
    """

    _LABEL: ClassVar[str] = "relationship graph id"

    @classmethod
    def for_enhancement(cls, enhancement_id: str) -> RelationshipGraphId:
        """Mint the deterministic graph id for *enhancement_id*."""
        enhancement = str(enhancement_id).strip()
        if not enhancement:
            raise ValueError("Cannot mint a relationship graph id from an empty enhancement id.")
        digest = hashlib.sha256(enhancement.encode()).hexdigest()
        return cls(f"rg-{digest[:12]}")


@dataclass(frozen=True)
class RequirementObservationId(_StringIdentifier):
    """The deterministic identity of one :class:`RequirementObservation`.

    A pure function of the enhancement run and a stable per-run ordinal — no UUID, no
    clock. A future observation engine mints these; this class only shapes them.
    """

    _LABEL: ClassVar[str] = "requirement observation id"

    @classmethod
    def for_ordinal(cls, enhancement_id: str, ordinal: int) -> RequirementObservationId:
        """Mint the deterministic id for the *ordinal*-th observation of *enhancement_id*."""
        enhancement = str(enhancement_id).strip()
        if not enhancement:
            raise ValueError(
                "Cannot mint a requirement observation id from an empty enhancement id."
            )
        if ordinal < 0:
            raise ValueError("Cannot mint a requirement observation id from a negative ordinal.")
        digest = hashlib.sha256(f"{enhancement}:{ordinal}".encode()).hexdigest()
        return cls(f"ro-{digest[:12]}")


@dataclass(frozen=True)
class RequirementEnhancementResultId(_StringIdentifier):
    """The deterministic identity of one :class:`RequirementEnhancementResult`.

    A pure function of the :class:`RequirementEnhancementId` it assembles from, exactly
    mirroring ``QualityGovernanceResultId.for_assessment``.
    """

    _LABEL: ClassVar[str] = "requirement enhancement result id"

    @classmethod
    def for_enhancement(cls, enhancement_id: str) -> RequirementEnhancementResultId:
        """Mint the deterministic result id for *enhancement_id*."""
        enhancement = str(enhancement_id).strip()
        if not enhancement:
            raise ValueError(
                "Cannot mint a requirement enhancement result id from an empty "
                "enhancement id."
            )
        digest = hashlib.sha256(enhancement.encode()).hexdigest()
        return cls(f"rer-{digest[:12]}")


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
class EnhancementFrameworkVersion(_SemanticVersion):
    """Semantic version of the Requirement Enhancement Framework's code/contract."""

    _LABEL: ClassVar[str] = "enhancement framework version"


@dataclass(frozen=True, order=True)
class EnhancementPolicyVersion(_SemanticVersion):
    """Semantic version of one governed :class:`EnhancementPolicy`.

    Advances independently of :class:`EnhancementFrameworkVersion`,
    :class:`EnhancementResultVersion`, :class:`RelationshipVersion`, and
    :class:`ObservationVersion` (Recommendation 4: no shared version axis). Tuning a
    rule or a capability switch is a policy-version change, never a framework change.
    """

    _LABEL: ClassVar[str] = "enhancement policy version"


@dataclass(frozen=True, order=True)
class EnhancementResultVersion(_SemanticVersion):
    """Semantic version of the ``RequirementEnhancementResult`` **runtime contract**.

    Independent of the framework, the policy, and the inner relationship/observation
    schema versions; a change here never forces any of those to change, and vice versa
    — the direct analogue of ``QualityGovernanceResultVersion``.
    """

    _LABEL: ClassVar[str] = "enhancement result version"


@dataclass(frozen=True, order=True)
class RelationshipVersion(_SemanticVersion):
    """Semantic version of the ``RequirementRelationship`` / ``RelationshipGraph`` schema.

    Versions the canonical relationship vocabulary (Recommendation 2) independently of
    every other axis, so a future relationship type can be added without forcing a
    framework, policy, or result-contract change.
    """

    _LABEL: ClassVar[str] = "relationship version"


@dataclass(frozen=True, order=True)
class ObservationVersion(_SemanticVersion):
    """Semantic version of the ``RequirementObservation`` / ``EnhancementFinding`` schema.

    Versions the observation vocabulary (Recommendation 3: observation before
    recommendation) independently of every other axis.
    """

    _LABEL: ClassVar[str] = "observation version"
