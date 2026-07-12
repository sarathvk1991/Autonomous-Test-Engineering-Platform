"""Strongly typed identity value objects for the Quality Governance Framework.

These follow the precedent set by the Engineering Context Orchestration identity
model (ADR-0015) and the Grounding Framework identity model (ADR-0016): immutable,
validated, string-backed identifiers and semantic-version value objects, each
serialising to and validating from a **plain JSON string**.

The base classes are duplicated here rather than imported from those subsystems on
purpose — ADR-0015 §C and ADR-0016 §D6 already made the same call (duplicating the
version/id primitives rather than coupling subsystems), and name ``shared/`` as the
eventual home. Quality Governance stays self-contained: it imports no other
subsystem's identity model.

Determinism
-----------
:meth:`QualityAssessmentId.for_run` and :meth:`QualityGovernanceResultId.for_run`
are **pure functions** of their inputs — no UUID, no clock. The same analysis and
execution always mint the same ids, which is what lets a governance verdict be
compared and reproduced across runs.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, ClassVar

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

# URL- and filename-safe identifier shape, identical to the orchestration and
# grounding subsystems': lower-case, starts and ends alphanumeric, '.', '_', ':'
# or '-' permitted between.
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
class QualityPolicyId(_StringIdentifier):
    """The permanent, governed identity of a ``QualityPolicy``.

    A policy id is an identity, never an alias: two policies may currently express
    identical thresholds and rules yet remain distinct ids, mirroring
    ``MatchingPolicyId`` and ``OrchestrationPolicyId``.
    """

    _LABEL: ClassVar[str] = "quality policy id"


@dataclass(frozen=True)
class QualityAssessmentId(_StringIdentifier):
    """The deterministic identity of one :class:`QualityAssessment`.

    A pure function of the graded analysis and execution, so the same run over the
    same upstream results always yields the same assessment id.
    """

    _LABEL: ClassVar[str] = "quality assessment id"

    @classmethod
    def for_run(cls, analysis_id: str, execution_id: str) -> QualityAssessmentId:
        """Mint the deterministic assessment id for *analysis_id* / *execution_id*."""
        analysis = str(analysis_id).strip()
        execution = str(execution_id).strip()
        if not analysis or not execution:
            raise ValueError(
                "Cannot mint a quality assessment id from an empty analysis or execution id."
            )
        digest = hashlib.sha256(f"{analysis}\x1f{execution}".encode()).hexdigest()
        return cls(f"qa-{digest[:12]}")


@dataclass(frozen=True)
class QualityGovernanceResultId(_StringIdentifier):
    """The deterministic identity of one :class:`QualityGovernanceResult`.

    A pure function of the assessment identity it carries, so the same governance
    verdict always yields the same result id, run after run.
    """

    _LABEL: ClassVar[str] = "quality governance result id"

    @classmethod
    def for_assessment(cls, assessment_id: str) -> QualityGovernanceResultId:
        """Mint the deterministic result id for *assessment_id*."""
        assessment = str(assessment_id).strip()
        if not assessment:
            raise ValueError(
                "Cannot mint a quality governance result id from an empty assessment id."
            )
        digest = hashlib.sha256(assessment.encode()).hexdigest()
        return cls(f"qg-{digest[:12]}")


@dataclass(frozen=True)
class RuleEvaluationId(_StringIdentifier):
    """The deterministic identity of one evaluated governance rule (:class:`RuleEvaluation`).

    A pure function of the evaluation run and the rule evaluated, so the same rule
    evaluated over the same run always yields the same id.
    """

    _LABEL: ClassVar[str] = "rule evaluation id"

    @classmethod
    def for_rule(cls, result_id: str, rule_id: str) -> RuleEvaluationId:
        """Mint the deterministic id for *rule_id* under evaluation run *result_id*."""
        result = str(result_id).strip()
        rule = str(rule_id).strip()
        if not result or not rule:
            raise ValueError("Cannot mint a rule evaluation id from an empty result or rule id.")
        digest = hashlib.sha256(f"{result}\x1f{rule}".encode()).hexdigest()
        return cls(f"rev-{digest[:12]}")


@dataclass(frozen=True)
class RuleEvaluationResultId(_StringIdentifier):
    """The deterministic identity of one :class:`RuleEvaluationResult`.

    A pure function of the graded analysis and execution, so the same evaluation run
    always yields the same id, run after run.
    """

    _LABEL: ClassVar[str] = "rule evaluation result id"

    @classmethod
    def for_run(cls, analysis_id: str, execution_id: str) -> RuleEvaluationResultId:
        """Mint the deterministic result id for *analysis_id* / *execution_id*."""
        analysis = str(analysis_id).strip()
        execution = str(execution_id).strip()
        if not analysis or not execution:
            raise ValueError(
                "Cannot mint a rule evaluation result id from an empty analysis or execution id."
            )
        digest = hashlib.sha256(f"{analysis}\x1f{execution}".encode()).hexdigest()
        return cls(f"revr-{digest[:12]}")


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
class QualityGovernanceVersion(_SemanticVersion):
    """Semantic version of the Quality Governance Framework's code/contract."""

    _LABEL: ClassVar[str] = "quality governance version"


@dataclass(frozen=True, order=True)
class QualityPolicyVersion(_SemanticVersion):
    """Semantic version of a governed ``QualityPolicy``.

    Advances independently of :class:`QualityGovernanceVersion`,
    :class:`QualityAssessmentVersion`, and :class:`QualityGovernanceResultVersion`:
    tuning governed thresholds or rules is a policy-version change that must never
    force a change to the framework, assessment, or result-contract schemas
    (ADR-0017 Recommendation 2).
    """

    _LABEL: ClassVar[str] = "quality policy version"


@dataclass(frozen=True, order=True)
class QualityAssessmentVersion(_SemanticVersion):
    """Semantic version of the ``QualityAssessment`` **schema**.

    Independent of the framework, policy, and result-contract versions: the
    assessment's shape evolves on its own axis.
    """

    _LABEL: ClassVar[str] = "quality assessment version"


@dataclass(frozen=True, order=True)
class QualityGovernanceResultVersion(_SemanticVersion):
    """Semantic version of the ``QualityGovernanceResult`` **runtime contract** schema.

    The repository-level governance aggregate's own version, independent of the
    framework, policy, and assessment versions. A change here never forces a
    framework or policy version change, and vice versa.
    """

    _LABEL: ClassVar[str] = "quality governance result version"


@dataclass(frozen=True, order=True)
class RuleEvaluationVersion(_SemanticVersion):
    """Semantic version of the ``RuleEvaluation`` **schema**.

    Independent of every other axis: the shape of one evaluated rule evolves on its
    own axis, and a change here never forces a change to the framework, policy,
    assessment, governance-result, or rule-evaluation-result versions.
    """

    _LABEL: ClassVar[str] = "rule evaluation version"


@dataclass(frozen=True, order=True)
class RuleEvaluationResultVersion(_SemanticVersion):
    """Semantic version of the ``RuleEvaluationResult`` **runtime contract** schema.

    The evaluation boundary's own version — the canonical contract between the
    ``QualityRuleEvaluator`` and the ``QualityGovernanceService``. Independent of the
    ``RuleEvaluation`` schema version and of every quality-governance version axis; a
    change here never forces any of those, and vice versa.
    """

    _LABEL: ClassVar[str] = "rule evaluation result version"
