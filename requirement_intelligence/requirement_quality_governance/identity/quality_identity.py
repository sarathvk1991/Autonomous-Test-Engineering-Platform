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


@dataclass(frozen=True)
class AssessmentPolicyId(_StringIdentifier):
    """The permanent, governed identity of an ``AssessmentPolicy``.

    A policy id is an identity, never an alias: two policies may currently express
    identical interpretation rules yet remain distinct ids, mirroring
    ``QualityPolicyId`` and ``MatchingPolicyId``.
    """

    _LABEL: ClassVar[str] = "assessment policy id"


@dataclass(frozen=True)
class QualityAssessmentResultId(_StringIdentifier):
    """The deterministic identity of one :class:`QualityAssessmentResult`.

    A pure function of the :class:`RuleEvaluationResult` it interprets, so the same
    evaluation always yields the same assessment id, run after run.
    """

    _LABEL: ClassVar[str] = "quality assessment result id"

    @classmethod
    def for_evaluation(cls, rule_evaluation_result_id: str) -> QualityAssessmentResultId:
        """Mint the deterministic assessment id for *rule_evaluation_result_id*."""
        evaluation = str(rule_evaluation_result_id).strip()
        if not evaluation:
            raise ValueError(
                "Cannot mint a quality assessment result id from an empty rule "
                "evaluation result id."
            )
        digest = hashlib.sha256(evaluation.encode()).hexdigest()
        return cls(f"qar-{digest[:12]}")


@dataclass(frozen=True)
class DecisionPolicyId(_StringIdentifier):
    """The permanent, governed identity of a ``DecisionPolicy``.

    A policy id is an identity, never an alias: two policies may currently express
    identical decision rules yet remain distinct ids, mirroring ``AssessmentPolicyId``
    and ``QualityPolicyId``.
    """

    _LABEL: ClassVar[str] = "decision policy id"


@dataclass(frozen=True)
class QualityDecisionResultId(_StringIdentifier):
    """The deterministic identity of one :class:`QualityDecisionResult`.

    A pure function of the :class:`QualityAssessmentResult` it decides from, so the
    same assessment always yields the same decision id, run after run.
    """

    _LABEL: ClassVar[str] = "quality decision result id"

    @classmethod
    def for_assessment(cls, assessment_id: str) -> QualityDecisionResultId:
        """Mint the deterministic decision id for *assessment_id*."""
        assessment = str(assessment_id).strip()
        if not assessment:
            raise ValueError(
                "Cannot mint a quality decision result id from an empty assessment id."
            )
        digest = hashlib.sha256(assessment.encode()).hexdigest()
        return cls(f"qdr-{digest[:12]}")


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


@dataclass(frozen=True, order=True)
class QualityRuleVersion(_SemanticVersion):
    """Semantic version of one governed ``QualityRule`` (CAP-080B).

    Versions a single rule's definition independently of every other axis: tuning a
    rule's metadata (its threshold source, comparator, severity) advances this version
    under the golden re-baseline procedure and never forces a change to the catalogue,
    the evaluator, or any result-contract schema (ADR-0017 Recommendation 2).
    """

    _LABEL: ClassVar[str] = "quality rule version"


@dataclass(frozen=True, order=True)
class QualityRuleCatalogVersion(_SemanticVersion):
    """Semantic version of the governed ``QualityRuleCatalog`` (CAP-080B).

    Advances when the governed rule set changes — a rule added, removed, or retuned.
    Independent of the individual ``QualityRuleVersion`` axis and of every
    quality-governance version; a change here never forces any of those, and vice versa.
    """

    _LABEL: ClassVar[str] = "quality rule catalog version"


@dataclass(frozen=True, order=True)
class QualityRuleEvaluatorVersion(_SemanticVersion):
    """Semantic version of a ``QualityRuleEvaluator`` implementation (CAP-080B).

    The evaluator's own identity axis, recorded on every ``RuleEvaluationResult`` so a
    result names the evaluator that produced it. Independent of the policy, catalogue,
    ``RuleEvaluation``, and ``RuleEvaluationResult`` versions (ADR-0017 Recommendation
    5): swapping one evaluator implementation for another advances only this axis.
    """

    _LABEL: ClassVar[str] = "quality rule evaluator version"


@dataclass(frozen=True, order=True)
class AssessmentPolicyVersion(_SemanticVersion):
    """Semantic version of a governed ``AssessmentPolicy``.

    Advances independently of every other axis: tuning the governed interpretation
    rules is a policy-version change that must never force a change to
    ``QualityAssessmentResult`` or the engine contract (ADR-0017 Recommendation 4).
    """

    _LABEL: ClassVar[str] = "assessment policy version"


@dataclass(frozen=True, order=True)
class AssessmentOutcomeVersion(_SemanticVersion):
    """Semantic version of the ``AssessmentOutcome`` **schema**.

    Versions the inner assessment-observation model, independently of the assessment
    result contract, the policy, and every quality-governance axis. This is the
    assessment subsystem's analogue of ``RuleEvaluationVersion``; the name
    ``QualityAssessmentVersion`` is already owned by CAP-080A's governance
    ``QualityAssessment`` (a different model), so the subsystem uses this distinct axis
    to stay collision-free (ADR-0017 §D21).
    """

    _LABEL: ClassVar[str] = "assessment outcome version"


@dataclass(frozen=True, order=True)
class QualityAssessmentResultVersion(_SemanticVersion):
    """Semantic version of the ``QualityAssessmentResult`` **runtime contract** schema.

    The assessment boundary's own version — the canonical contract between the
    ``QualityAssessmentEngine`` and the ``QualityGovernanceService``. Independent of the
    ``AssessmentOutcome`` schema version, the ``AssessmentPolicyVersion``, and every
    other axis; a change here never forces any of those, and vice versa.
    """

    _LABEL: ClassVar[str] = "quality assessment result version"


@dataclass(frozen=True, order=True)
class DecisionPolicyVersion(_SemanticVersion):
    """Semantic version of a governed ``DecisionPolicy``.

    Advances independently of every other axis: tuning the governed release-decision
    rules is a policy-version change that must never force a change to
    ``QualityDecisionResult`` or the engine contract (ADR-0017 Recommendation 4/D24).
    """

    _LABEL: ClassVar[str] = "decision policy version"


@dataclass(frozen=True, order=True)
class DecisionVersion(_SemanticVersion):
    """Semantic version of the ``DecisionExplanation`` **schema**.

    Versions the inner decision-reasoning model, independently of the decision result
    contract, the policy, and every other axis. This is the decision subsystem's
    analogue of ``AssessmentOutcomeVersion`` / ``RuleEvaluationVersion``.
    """

    _LABEL: ClassVar[str] = "decision version"


@dataclass(frozen=True, order=True)
class QualityDecisionResultVersion(_SemanticVersion):
    """Semantic version of the ``QualityDecisionResult`` **runtime contract** schema.

    The decision boundary's own version — the canonical contract between the
    ``QualityDecisionEngine`` and the ``QualityGovernanceService``. Independent of the
    ``DecisionExplanation`` schema version, the ``DecisionPolicyVersion``, and every
    other axis; a change here never forces any of those, and vice versa.
    """

    _LABEL: ClassVar[str] = "quality decision result version"
