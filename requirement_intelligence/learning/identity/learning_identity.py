"""Strongly typed identity value objects for the Learning Framework.

These follow the precedent set by the Engineering Context Orchestration
identity model (ADR-0015), the Grounding Framework identity model (ADR-0016),
the Quality Governance identity model (ADR-0017), the Requirement Enhancement
identity model (ADR-0018), the Recommendation Framework identity model
(ADR-0019), the Continuous Improvement Framework identity model (ADR-0022),
the Knowledge Graph Framework identity model (ADR-0023), and the
Organizational Memory Framework identity model (ADR-0027): immutable,
validated, string-backed identifiers and semantic-version value objects, each
serialising to and validating from a **plain JSON string**.

The base classes are duplicated here rather than imported from those
subsystems on purpose — ADR-0015 §C, ADR-0016 §D6, ADR-0017 (identity module
docstring), ADR-0018 §D5, ADR-0019 §D5, ADR-0022 (identity module docstring),
ADR-0023 (identity module docstring), and ADR-0027 (identity module
docstring) already made the same call. The Learning Framework stays
self-contained: it imports no other subsystem's identity model — including
Organizational Memory's own — even though this framework's *models*
legitimately reference `OrganizationalMemoryResult` (and, by id only, its
`BestPractice` records) directly (ADR-0028 §Stage 12, ADR-0029 §D2).

Determinism
-----------
Every ``for_*`` factory below is a **pure function** of its inputs — no UUID,
no clock. The same consumed `OrganizationalMemoryResult` id, and the same
candidate/learning/validation/confidence/lifecycle ordinal, always mints the
same id, which is what lets a ``LearningResult`` be compared and reproduced
across builds over the same input (mirroring ADR-0022's
``ContinuousImprovementResultId.for_dataset``, ADR-0023's
``KnowledgeGraphResultId.for_graph``, and ADR-0027's
``OrganizationalMemoryResultId.for_memory`` precedent).

Version axis independence (frozen, CAP-086A, ADR-0029 §D3/§D5)
-----------------------------------------------------------------
Six distinct version types exist, each evolving on its own axis — tuning one
never forces a change to any other, and vice versa:

* :class:`LearningFrameworkVersion` — the framework's code/contract.
* :class:`LearningPolicyVersion` — one governed ``LearningPolicy``.
* :class:`LearningVersion` — the ``Learning`` schema (reserved; not yet
  stamped onto a model field, exactly as a sibling reserved schema axis was
  reserved by ADR-0022/ADR-0023/ADR-0027 before any model carried it).
* :class:`LearningLifecycleVersion` — the ``LearningLifecycle`` schema
  (reserved).
* :class:`LearningValidationVersion` — the ``LearningValidation`` schema
  (reserved).
* :class:`LearningResultVersion` — the ``LearningResult`` runtime contract
  (the only axis actually stamped onto a model today,
  ``LearningResult.result_version``).

``LearningCandidate``, ``LearningConfidence``, and ``LearningSummary`` /
``LearningMetrics`` carry no version field of their own by the same design
choice ADR-0019 made for ``RecommendationGroup`` / ``RecommendationSummary``,
ADR-0022 made for ``ImprovementFinding`` / ``ImprovementSummary``, ADR-0023
made for ``KnowledgeSubgraph`` / ``KnowledgeFinding`` / ``KnowledgeSummary``,
and ADR-0027 made for ``Experience`` / ``KnowledgePromotion`` /
``OrganizationalMemorySummary`` / ``OrganizationalMemoryMetrics`` — no new
version type is invented here to cover them.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, ClassVar

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

# URL- and filename-safe identifier shape, identical to every prior subsystem's:
# lower-case, starts and ends alphanumeric, '.', '_', ':' or '-' permitted between.
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
class LearningPolicyId(_StringIdentifier):
    """The permanent, governed identity of a ``LearningPolicy``.

    A policy id is an identity, never an alias: two policies may currently
    express identical rules yet remain distinct ids, mirroring
    ``OrganizationalMemoryPolicyId``.
    """

    _LABEL: ClassVar[str] = "learning policy id"


@dataclass(frozen=True)
class LearningCandidateId(_StringIdentifier):
    """The deterministic identity of one ``LearningCandidate``.

    A pure function of the source ``BestPractice`` id it was proposed from —
    no UUID, no clock. A future engine mints these; this class only shapes
    them, mirroring ``ExperienceId.for_source``.
    """

    _LABEL: ClassVar[str] = "learning candidate id"

    @classmethod
    def for_source(cls, source_best_practice_id: str) -> LearningCandidateId:
        """Mint the deterministic id for the candidate naming *source_best_practice_id*."""
        source = str(source_best_practice_id).strip()
        if not source:
            raise ValueError(
                "Cannot mint a learning candidate id from an empty source best practice id."
            )
        digest = hashlib.sha256(source.encode()).hexdigest()
        return cls(f"lc-{digest[:12]}")


@dataclass(frozen=True)
class LearningValidationId(_StringIdentifier):
    """The deterministic identity of one ``LearningValidation`` record.

    A pure function of the seed id it belongs to and a stable per-build
    ordinal, exactly mirroring ``KnowledgePromotionId.for_ordinal``.
    """

    _LABEL: ClassVar[str] = "learning validation id"

    @classmethod
    def for_ordinal(cls, seed_id: str, ordinal: int) -> LearningValidationId:
        """Mint the deterministic id for the *ordinal*-th validation of *seed_id*."""
        seed = str(seed_id).strip()
        if not seed:
            raise ValueError("Cannot mint a learning validation id from an empty seed id.")
        if ordinal < 0:
            raise ValueError("Cannot mint a learning validation id from a negative ordinal.")
        digest = hashlib.sha256(f"{seed}:{ordinal}".encode()).hexdigest()
        return cls(f"lv-{digest[:12]}")


@dataclass(frozen=True)
class LearningConfidenceId(_StringIdentifier):
    """The deterministic identity of one ``LearningConfidence`` record.

    A pure function of the seed id it belongs to and a stable per-build
    ordinal, exactly mirroring ``KnowledgePromotionId.for_ordinal``.
    """

    _LABEL: ClassVar[str] = "learning confidence id"

    @classmethod
    def for_ordinal(cls, seed_id: str, ordinal: int) -> LearningConfidenceId:
        """Mint the deterministic id for the *ordinal*-th confidence record of *seed_id*."""
        seed = str(seed_id).strip()
        if not seed:
            raise ValueError("Cannot mint a learning confidence id from an empty seed id.")
        if ordinal < 0:
            raise ValueError("Cannot mint a learning confidence id from a negative ordinal.")
        digest = hashlib.sha256(f"{seed}:{ordinal}".encode()).hexdigest()
        return cls(f"lf-{digest[:12]}")


@dataclass(frozen=True)
class LearningId(_StringIdentifier):
    """The deterministic identity of one ``Learning`` object.

    A pure function of the seed id it belongs to and a stable per-build
    ordinal, exactly mirroring ``LessonId.for_ordinal``.
    """

    _LABEL: ClassVar[str] = "learning id"

    @classmethod
    def for_ordinal(cls, seed_id: str, ordinal: int) -> LearningId:
        """Mint the deterministic id for the *ordinal*-th learning of *seed_id*."""
        seed = str(seed_id).strip()
        if not seed:
            raise ValueError("Cannot mint a learning id from an empty seed id.")
        if ordinal < 0:
            raise ValueError("Cannot mint a learning id from a negative ordinal.")
        digest = hashlib.sha256(f"{seed}:{ordinal}".encode()).hexdigest()
        return cls(f"lg-{digest[:12]}")


@dataclass(frozen=True)
class LearningLifecycleId(_StringIdentifier):
    """The deterministic identity of one ``LearningLifecycle`` record.

    A pure function of the seed id it belongs to and a stable per-build
    ordinal, exactly mirroring ``KnowledgeLifecycleId.for_ordinal``.
    """

    _LABEL: ClassVar[str] = "learning lifecycle id"

    @classmethod
    def for_ordinal(cls, seed_id: str, ordinal: int) -> LearningLifecycleId:
        """Mint the deterministic id for the *ordinal*-th lifecycle record of *seed_id*."""
        seed = str(seed_id).strip()
        if not seed:
            raise ValueError("Cannot mint a learning lifecycle id from an empty seed id.")
        if ordinal < 0:
            raise ValueError("Cannot mint a learning lifecycle id from a negative ordinal.")
        digest = hashlib.sha256(f"{seed}:{ordinal}".encode()).hexdigest()
        return cls(f"ll-{digest[:12]}")


@dataclass(frozen=True)
class LearningResultId(_StringIdentifier):
    """The deterministic identity of one ``LearningResult``.

    A pure function of the single consumed ``OrganizationalMemoryResult`` id
    this build was built from — no UUID, no clock. Unlike
    ``OrganizationalMemoryId.for_inputs`` (a pure function of *two* consumed
    Layer 2 result ids, ADR-0025 §Stage 7/8's fan-in exception), Learning
    consumes exactly one input (ADR-0028 §Stage 12, ADR-0029 §D2), so a
    single-argument factory is the correct, permanent shape — never a
    simplification pending a future widening.
    """

    _LABEL: ClassVar[str] = "learning result id"

    @classmethod
    def for_source(cls, organizational_memory_result_id: str) -> LearningResultId:
        """Mint the deterministic result id for *organizational_memory_result_id*."""
        source = str(organizational_memory_result_id).strip()
        if not source:
            raise ValueError(
                "Cannot mint a learning result id from an empty organizational memory result id."
            )
        digest = hashlib.sha256(source.encode()).hexdigest()
        return cls(f"lr-{digest[:12]}")


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
class LearningFrameworkVersion(_SemanticVersion):
    """Semantic version of the Learning Framework's code/contract."""

    _LABEL: ClassVar[str] = "learning framework version"


@dataclass(frozen=True, order=True)
class LearningPolicyVersion(_SemanticVersion):
    """Semantic version of one governed ``LearningPolicy``.

    Advances independently of :class:`LearningFrameworkVersion` and
    :class:`LearningResultVersion` (ADR-0021 §Stage 9: no shared version
    axis). Tuning a threshold or a capability switch is a policy-version
    change, never a framework change.
    """

    _LABEL: ClassVar[str] = "learning policy version"


@dataclass(frozen=True, order=True)
class LearningVersion(_SemanticVersion):
    """Semantic version of the ``Learning`` schema.

    Reserved for a future milestone, exactly as ``LessonVersion`` was
    reserved by ADR-0027 §D3 without yet being stamped onto a model field.
    """

    _LABEL: ClassVar[str] = "learning version"


@dataclass(frozen=True, order=True)
class LearningLifecycleVersion(_SemanticVersion):
    """Semantic version of the ``LearningLifecycle`` schema. Reserved."""

    _LABEL: ClassVar[str] = "learning lifecycle version"


@dataclass(frozen=True, order=True)
class LearningValidationVersion(_SemanticVersion):
    """Semantic version of the ``LearningValidation`` schema. Reserved."""

    _LABEL: ClassVar[str] = "learning validation version"


@dataclass(frozen=True, order=True)
class LearningResultVersion(_SemanticVersion):
    """Semantic version of the ``LearningResult`` **runtime contract**.

    Independent of the framework, the policy, and every learning/lifecycle/
    validation schema version; a change here never forces any of those to
    change, and vice versa — the direct analogue of
    ``OrganizationalMemoryResultVersion``.
    """

    _LABEL: ClassVar[str] = "learning result version"
