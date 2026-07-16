"""Strongly typed identity value objects for the Organizational Memory Framework.

These follow the precedent set by the Engineering Context Orchestration identity
model (ADR-0015), the Grounding Framework identity model (ADR-0016), the Quality
Governance identity model (ADR-0017), the Requirement Enhancement identity model
(ADR-0018), the Recommendation Framework identity model (ADR-0019), the
Continuous Improvement Framework identity model (ADR-0022), and the Knowledge
Graph Framework identity model (ADR-0023): immutable, validated, string-backed
identifiers and semantic-version value objects, each serialising to and
validating from a **plain JSON string**.

The base classes are duplicated here rather than imported from those subsystems
on purpose — ADR-0015 §C, ADR-0016 §D6, ADR-0017 (identity module docstring),
ADR-0018 §D5, ADR-0019 §D5, ADR-0022 (identity module docstring), and ADR-0023
(identity module docstring) already made the same call. The Organizational
Memory Framework stays self-contained: it imports no other subsystem's identity
model — including Continuous Improvement's and Knowledge Graph's own, even
though this framework's *models* legitimately reference their frozen runtime
contracts directly (ADR-0025 §Stage 7/8's fan-in exception; ADR-0027 §D2).

Determinism
-----------
Every ``for_*`` factory below is a **pure function** of its inputs — no UUID, no
clock. The same pair of consumed Layer 2 results, and the same experience/lesson/
best-practice/promotion/lifecycle ordinal, always mints the same id, which is
what lets an ``OrganizationalMemoryResult`` be compared and reproduced across
builds over the same inputs (mirroring ADR-0022's ``ContinuousImprovementResultId
.for_dataset`` and ADR-0023's ``KnowledgeGraphResultId.for_graph`` precedent).

Version axis independence (frozen, CAP-085A, ADR-0027 §D3/§D6)
-----------------------------------------------------------------
Six distinct version types exist, each evolving on its own axis — tuning one
never forces a change to any other, and vice versa:

* :class:`OrganizationalMemoryFrameworkVersion` — the framework's code/contract.
* :class:`OrganizationalMemoryPolicyVersion` — one governed
  ``OrganizationalMemoryPolicy``.
* :class:`LessonVersion` — the ``Lesson`` schema (reserved; not yet stamped onto
  a model field, exactly as a sibling reserved schema axis was reserved by
  ADR-0022/ADR-0023 before any model carried it).
* :class:`BestPracticeVersion` — the ``BestPractice`` schema (reserved).
* :class:`KnowledgeLifecycleVersion` — the ``KnowledgeLifecycle`` schema
  (reserved).
* :class:`OrganizationalMemoryResultVersion` — the ``OrganizationalMemoryResult``
  runtime contract (the only axis actually stamped onto a model today,
  ``OrganizationalMemoryResult.result_version``).

``Experience``, ``KnowledgePromotion``, and ``OrganizationalMemorySummary`` /
``OrganizationalMemoryMetrics`` carry no version field of their own by the same
design choice ADR-0019 made for ``RecommendationGroup`` / ``RecommendationSummary``,
ADR-0022 made for ``ImprovementFinding`` / ``ImprovementSummary``, and ADR-0023
made for ``KnowledgeSubgraph`` / ``KnowledgeFinding`` / ``KnowledgeSummary`` — no
new version type is invented here to cover them.
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
class OrganizationalMemoryPolicyId(_StringIdentifier):
    """The permanent, governed identity of an ``OrganizationalMemoryPolicy``.

    A policy id is an identity, never an alias: two policies may currently
    express identical rules yet remain distinct ids, mirroring
    ``ImprovementPolicyId`` and ``KnowledgePolicyId``.
    """

    _LABEL: ClassVar[str] = "organizational memory policy id"


@dataclass(frozen=True)
class OrganizationalMemoryId(_StringIdentifier):
    """The deterministic identity of one Organizational Memory build.

    A pure function of the two Layer 2 result ids this build consumed — the
    same pair of ``ContinuousImprovementResult`` / ``KnowledgeGraphResult`` ids
    always names the same memory build, mirroring ``KnowledgeGraphId.for_dataset``.
    """

    _LABEL: ClassVar[str] = "organizational memory id"

    @classmethod
    def for_inputs(
        cls, continuous_improvement_result_id: str, knowledge_graph_result_id: str
    ) -> OrganizationalMemoryId:
        """Mint the deterministic memory id for the consumed pair of result ids."""
        ci_id = str(continuous_improvement_result_id).strip()
        kg_id = str(knowledge_graph_result_id).strip()
        if not ci_id:
            raise ValueError(
                "Cannot mint an organizational memory id from an empty "
                "continuous improvement result id."
            )
        if not kg_id:
            raise ValueError(
                "Cannot mint an organizational memory id from an empty knowledge graph result id."
            )
        digest = hashlib.sha256(f"{ci_id}:{kg_id}".encode()).hexdigest()
        return cls(f"om-{digest[:12]}")


@dataclass(frozen=True)
class ExperienceId(_StringIdentifier):
    """The deterministic identity of one ``Experience``.

    A pure function of the governed source layer and the referenced Continuous
    Improvement / Knowledge Graph object id it was captured from — no UUID, no
    clock. A future engine mints these; this class only shapes them.
    """

    _LABEL: ClassVar[str] = "experience id"

    @classmethod
    def for_source(cls, source_layer: str, source_reference_id: str) -> ExperienceId:
        """Mint the deterministic id for the experience naming *source_reference_id*."""
        layer = str(source_layer).strip()
        reference = str(source_reference_id).strip()
        if not layer:
            raise ValueError("Cannot mint an experience id from an empty source layer.")
        if not reference:
            raise ValueError("Cannot mint an experience id from an empty source reference id.")
        digest = hashlib.sha256(f"{layer}:{reference}".encode()).hexdigest()
        return cls(f"ex-{digest[:12]}")


@dataclass(frozen=True)
class LessonId(_StringIdentifier):
    """The deterministic identity of one ``Lesson``.

    A pure function of the memory build it belongs to and a stable per-build
    ordinal, exactly mirroring ``KnowledgeFindingId.for_ordinal``.
    """

    _LABEL: ClassVar[str] = "lesson id"

    @classmethod
    def for_ordinal(cls, memory_id: str, ordinal: int) -> LessonId:
        """Mint the deterministic id for the *ordinal*-th lesson of *memory_id*."""
        memory = str(memory_id).strip()
        if not memory:
            raise ValueError("Cannot mint a lesson id from an empty memory id.")
        if ordinal < 0:
            raise ValueError("Cannot mint a lesson id from a negative ordinal.")
        digest = hashlib.sha256(f"{memory}:{ordinal}".encode()).hexdigest()
        return cls(f"ls-{digest[:12]}")


@dataclass(frozen=True)
class BestPracticeId(_StringIdentifier):
    """The deterministic identity of one ``BestPractice``.

    A pure function of the memory build it belongs to and a stable per-build
    ordinal, exactly mirroring ``LessonId.for_ordinal``.
    """

    _LABEL: ClassVar[str] = "best practice id"

    @classmethod
    def for_ordinal(cls, memory_id: str, ordinal: int) -> BestPracticeId:
        """Mint the deterministic id for the *ordinal*-th best practice of *memory_id*."""
        memory = str(memory_id).strip()
        if not memory:
            raise ValueError("Cannot mint a best practice id from an empty memory id.")
        if ordinal < 0:
            raise ValueError("Cannot mint a best practice id from a negative ordinal.")
        digest = hashlib.sha256(f"{memory}:{ordinal}".encode()).hexdigest()
        return cls(f"bp-{digest[:12]}")


@dataclass(frozen=True)
class KnowledgePromotionId(_StringIdentifier):
    """The deterministic identity of one ``KnowledgePromotion`` record.

    A pure function of the memory build it belongs to and a stable per-build
    ordinal, exactly mirroring ``LessonId.for_ordinal``.
    """

    _LABEL: ClassVar[str] = "knowledge promotion id"

    @classmethod
    def for_ordinal(cls, memory_id: str, ordinal: int) -> KnowledgePromotionId:
        """Mint the deterministic id for the *ordinal*-th promotion of *memory_id*."""
        memory = str(memory_id).strip()
        if not memory:
            raise ValueError("Cannot mint a knowledge promotion id from an empty memory id.")
        if ordinal < 0:
            raise ValueError("Cannot mint a knowledge promotion id from a negative ordinal.")
        digest = hashlib.sha256(f"{memory}:{ordinal}".encode()).hexdigest()
        return cls(f"kp-{digest[:12]}")


@dataclass(frozen=True)
class KnowledgeLifecycleId(_StringIdentifier):
    """The deterministic identity of one ``KnowledgeLifecycle`` record.

    A pure function of the memory build it belongs to and a stable per-build
    ordinal, exactly mirroring ``LessonId.for_ordinal``.
    """

    _LABEL: ClassVar[str] = "knowledge lifecycle id"

    @classmethod
    def for_ordinal(cls, memory_id: str, ordinal: int) -> KnowledgeLifecycleId:
        """Mint the deterministic id for the *ordinal*-th lifecycle record of *memory_id*."""
        memory = str(memory_id).strip()
        if not memory:
            raise ValueError("Cannot mint a knowledge lifecycle id from an empty memory id.")
        if ordinal < 0:
            raise ValueError("Cannot mint a knowledge lifecycle id from a negative ordinal.")
        digest = hashlib.sha256(f"{memory}:{ordinal}".encode()).hexdigest()
        return cls(f"kl-{digest[:12]}")


@dataclass(frozen=True)
class OrganizationalMemoryResultId(_StringIdentifier):
    """The deterministic identity of one ``OrganizationalMemoryResult``.

    A pure function of the memory build it was assembled for, exactly mirroring
    ``KnowledgeGraphResultId.for_graph`` — one level down the reference chain
    (the consumed Layer 2 result ids name the memory build, this id names one
    build's result).
    """

    _LABEL: ClassVar[str] = "organizational memory result id"

    @classmethod
    def for_memory(cls, memory_id: str) -> OrganizationalMemoryResultId:
        """Mint the deterministic result id for *memory_id*."""
        memory = str(memory_id).strip()
        if not memory:
            raise ValueError(
                "Cannot mint an organizational memory result id from an empty memory id."
            )
        digest = hashlib.sha256(memory.encode()).hexdigest()
        return cls(f"omr-{digest[:12]}")


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
class OrganizationalMemoryFrameworkVersion(_SemanticVersion):
    """Semantic version of the Organizational Memory Framework's code/contract."""

    _LABEL: ClassVar[str] = "organizational memory framework version"


@dataclass(frozen=True, order=True)
class OrganizationalMemoryPolicyVersion(_SemanticVersion):
    """Semantic version of one governed ``OrganizationalMemoryPolicy``.

    Advances independently of :class:`OrganizationalMemoryFrameworkVersion` and
    :class:`OrganizationalMemoryResultVersion` (ADR-0021 §Stage 9: no shared
    version axis). Tuning a threshold or a capability switch is a
    policy-version change, never a framework change.
    """

    _LABEL: ClassVar[str] = "organizational memory policy version"


@dataclass(frozen=True, order=True)
class LessonVersion(_SemanticVersion):
    """Semantic version of the ``Lesson`` schema.

    Reserved for a future milestone, exactly as ``ImprovementTrendVersion`` was
    reserved by ADR-0022 §D5 and ``KnowledgeNodeVersion`` by ADR-0023 §D5,
    without yet being stamped onto a model field.
    """

    _LABEL: ClassVar[str] = "lesson version"


@dataclass(frozen=True, order=True)
class BestPracticeVersion(_SemanticVersion):
    """Semantic version of the ``BestPractice`` schema. Reserved (see
    :class:`LessonVersion`)."""

    _LABEL: ClassVar[str] = "best practice version"


@dataclass(frozen=True, order=True)
class KnowledgeLifecycleVersion(_SemanticVersion):
    """Semantic version of the ``KnowledgeLifecycle`` schema. Reserved."""

    _LABEL: ClassVar[str] = "knowledge lifecycle version"


@dataclass(frozen=True, order=True)
class OrganizationalMemoryResultVersion(_SemanticVersion):
    """Semantic version of the ``OrganizationalMemoryResult`` **runtime contract**.

    Independent of the framework, the policy, and every lesson/best-practice/
    lifecycle schema version; a change here never forces any of those to
    change, and vice versa — the direct analogue of
    ``ContinuousImprovementResultVersion`` and ``KnowledgeGraphResultVersion``.
    """

    _LABEL: ClassVar[str] = "organizational memory result version"
