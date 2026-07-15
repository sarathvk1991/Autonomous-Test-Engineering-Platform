"""Strongly typed identity value objects for the Continuous Improvement Framework.

These follow the precedent set by the Engineering Context Orchestration identity
model (ADR-0015), the Grounding Framework identity model (ADR-0016), the Quality
Governance identity model (ADR-0017), the Requirement Enhancement identity model
(ADR-0018), and the Recommendation Framework identity model (ADR-0019): immutable,
validated, string-backed identifiers and semantic-version value objects, each
serialising to and validating from a **plain JSON string**.

The base classes are duplicated here rather than imported from those subsystems on
purpose — ADR-0015 §C, ADR-0016 §D6, ADR-0017 (identity module docstring), ADR-0018
§D5, and ADR-0019 §D5 already made the same call. The Continuous Improvement
Framework stays self-contained: it imports no other subsystem's identity model, and
— unlike every Layer 1 subsystem — it imports no Layer 1 subsystem's identity model
either (ADR-0021 §Stage 8: it consumes Historical Truth only).

Determinism
-----------
Every ``for_*`` factory below is a **pure function** of its inputs — no UUID, no
clock. The same historical dataset always mints the same ids, which is what lets a
future ``ContinuousImprovementResult`` be compared and reproduced across runs over
the same dataset (mirroring ADR-0019 Recommendation 2/3 precedent, lifted to a
cross-execution scope per ADR-0021).
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
class ImprovementPolicyId(_StringIdentifier):
    """The permanent, governed identity of an ``ImprovementPolicy``.

    A policy id is an identity, never an alias: two policies may currently express
    identical rules yet remain distinct ids, mirroring ``RecommendationPolicyId``.
    """

    _LABEL: ClassVar[str] = "improvement policy id"


@dataclass(frozen=True)
class ImprovementFindingId(_StringIdentifier):
    """The deterministic identity of one ``ImprovementFinding``.

    A pure function of the historical dataset it belongs to and a stable
    per-dataset ordinal — no UUID, no clock. A future engine mints these; this
    class only shapes them.
    """

    _LABEL: ClassVar[str] = "improvement finding id"

    @classmethod
    def for_ordinal(cls, dataset_id: str, ordinal: int) -> ImprovementFindingId:
        """Mint the deterministic id for the *ordinal*-th finding of *dataset_id*."""
        dataset = str(dataset_id).strip()
        if not dataset:
            raise ValueError("Cannot mint an improvement finding id from an empty dataset id.")
        if ordinal < 0:
            raise ValueError("Cannot mint an improvement finding id from a negative ordinal.")
        digest = hashlib.sha256(f"{dataset}:{ordinal}".encode()).hexdigest()
        return cls(f"if-{digest[:12]}")


@dataclass(frozen=True)
class ImprovementTrendId(_StringIdentifier):
    """The deterministic identity of one ``ImprovementTrend``.

    A pure function of the historical dataset it belongs to and a stable
    per-dataset ordinal, exactly mirroring :meth:`ImprovementFindingId.for_ordinal`.
    """

    _LABEL: ClassVar[str] = "improvement trend id"

    @classmethod
    def for_ordinal(cls, dataset_id: str, ordinal: int) -> ImprovementTrendId:
        """Mint the deterministic id for the *ordinal*-th trend of *dataset_id*."""
        dataset = str(dataset_id).strip()
        if not dataset:
            raise ValueError("Cannot mint an improvement trend id from an empty dataset id.")
        if ordinal < 0:
            raise ValueError("Cannot mint an improvement trend id from a negative ordinal.")
        digest = hashlib.sha256(f"{dataset}:{ordinal}".encode()).hexdigest()
        return cls(f"it-{digest[:12]}")


@dataclass(frozen=True)
class ImprovementOpportunityId(_StringIdentifier):
    """The deterministic identity of one ``ImprovementOpportunity``.

    A pure function of the historical dataset it belongs to and a stable
    per-dataset ordinal, exactly mirroring :meth:`ImprovementFindingId.for_ordinal`.
    """

    _LABEL: ClassVar[str] = "improvement opportunity id"

    @classmethod
    def for_ordinal(cls, dataset_id: str, ordinal: int) -> ImprovementOpportunityId:
        """Mint the deterministic id for the *ordinal*-th opportunity of *dataset_id*."""
        dataset = str(dataset_id).strip()
        if not dataset:
            raise ValueError("Cannot mint an improvement opportunity id from an empty dataset id.")
        if ordinal < 0:
            raise ValueError("Cannot mint an improvement opportunity id from a negative ordinal.")
        digest = hashlib.sha256(f"{dataset}:{ordinal}".encode()).hexdigest()
        return cls(f"io-{digest[:12]}")


@dataclass(frozen=True)
class ImprovementAssessmentId(_StringIdentifier):
    """The deterministic identity of a future ``ImprovementAssessment`` layer.

    Reserved for a future milestone, exactly as ``RecommendationVersion`` was
    reserved by ADR-0019 §D5 without yet being stamped onto a model field. No
    model in CAP-083A carries this id; it exists so a future assessment layer
    (mirroring Quality Governance's Evaluation → Assessment → Decision layering,
    ADR-0017 §D17-D22) can be added additively.
    """

    _LABEL: ClassVar[str] = "improvement assessment id"

    @classmethod
    def for_ordinal(cls, dataset_id: str, ordinal: int) -> ImprovementAssessmentId:
        """Mint the deterministic id for the *ordinal*-th assessment of *dataset_id*."""
        dataset = str(dataset_id).strip()
        if not dataset:
            raise ValueError("Cannot mint an improvement assessment id from an empty dataset id.")
        if ordinal < 0:
            raise ValueError("Cannot mint an improvement assessment id from a negative ordinal.")
        digest = hashlib.sha256(f"{dataset}:{ordinal}".encode()).hexdigest()
        return cls(f"ia-{digest[:12]}")


@dataclass(frozen=True)
class ContinuousImprovementResultId(_StringIdentifier):
    """The deterministic identity of one ``ContinuousImprovementResult``.

    A pure function of the historical dataset it assembles from, exactly
    mirroring ``RecommendationResultId.for_execution`` — lifted to a
    dataset-scoped (rather than execution-scoped) identity per ADR-0021.
    """

    _LABEL: ClassVar[str] = "continuous improvement result id"

    @classmethod
    def for_dataset(cls, dataset_id: str) -> ContinuousImprovementResultId:
        """Mint the deterministic result id for *dataset_id*."""
        dataset = str(dataset_id).strip()
        if not dataset:
            raise ValueError(
                "Cannot mint a continuous improvement result id from an empty dataset id."
            )
        digest = hashlib.sha256(dataset.encode()).hexdigest()
        return cls(f"cir-{digest[:12]}")


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
class ContinuousImprovementFrameworkVersion(_SemanticVersion):
    """Semantic version of the Continuous Improvement Framework's code/contract."""

    _LABEL: ClassVar[str] = "continuous improvement framework version"


@dataclass(frozen=True, order=True)
class ImprovementPolicyVersion(_SemanticVersion):
    """Semantic version of one governed ``ImprovementPolicy``.

    Advances independently of :class:`ContinuousImprovementFrameworkVersion` and
    :class:`ContinuousImprovementResultVersion` (ADR-0021 §Stage 9: no shared
    version axis). Tuning a threshold or a capability switch is a policy-version
    change, never a framework change.
    """

    _LABEL: ClassVar[str] = "improvement policy version"


@dataclass(frozen=True, order=True)
class ImprovementAssessmentVersion(_SemanticVersion):
    """Semantic version of a future ``ImprovementAssessment`` schema.

    Reserved for a future milestone, exactly as ``RecommendationVersion`` was
    reserved by ADR-0019 §D5 without yet being stamped onto a model field.
    """

    _LABEL: ClassVar[str] = "improvement assessment version"


@dataclass(frozen=True, order=True)
class ImprovementTrendVersion(_SemanticVersion):
    """Semantic version of the ``ImprovementTrend`` schema.

    Versions the trend vocabulary and shape independently of every other axis, so
    a future trend direction or field can be added without forcing a framework,
    policy, or result-contract change. Reserved for a future milestone, exactly as
    ``RecommendationVersion`` was reserved by ADR-0019 §D5.
    """

    _LABEL: ClassVar[str] = "improvement trend version"


@dataclass(frozen=True, order=True)
class ContinuousImprovementResultVersion(_SemanticVersion):
    """Semantic version of the ``ContinuousImprovementResult`` **runtime contract**.

    Independent of the framework, the policy, and the trend schema version; a
    change here never forces any of those to change, and vice versa — the direct
    analogue of ``RecommendationResultVersion``.
    """

    _LABEL: ClassVar[str] = "continuous improvement result version"


@dataclass(frozen=True, order=True)
class ImprovementRuleVersion(_SemanticVersion):
    """Semantic version of the governed ``ImprovementRule`` schema (CAP-083B).

    Added additively alongside the ``continuous_improvement/rules/`` package,
    mirroring how ``RecommendationRuleVersion`` was added in CAP-082B — after
    CAP-083A's architecture-freeze milestone, never during it. Advances
    independently of every other Continuous Improvement version axis.
    """

    _LABEL: ClassVar[str] = "improvement rule version"


@dataclass(frozen=True, order=True)
class ImprovementRuleCatalogVersion(_SemanticVersion):
    """Semantic version of the governed default :class:`ImprovementRuleCatalog`.

    Added additively in CAP-083B, mirroring the analogous rule-catalogue version
    type the Recommendation Framework added alongside its own rule package
    (CAP-082B). Tuning the catalogue (adding, removing, or retuning a rule)
    advances this version, never the engine or framework version.
    """

    _LABEL: ClassVar[str] = "improvement rule catalog version"


@dataclass(frozen=True, order=True)
class ImprovementEngineVersion(_SemanticVersion):
    """Semantic version of the Continuous Improvement engine **implementation**.

    Added additively in CAP-083B, mirroring the reserved
    ``RecommendationEngineVersion``. Not stamped onto ``ContinuousImprovementResult``
    (which carries no engine-version field, frozen since CAP-083A); reserved so a
    future engine's implementation identity is independently versionable without
    touching the frozen result contract.
    """

    _LABEL: ClassVar[str] = "improvement engine version"
