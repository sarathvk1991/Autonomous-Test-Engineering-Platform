"""SYNTAX-0002 — DuplicateKeysRule, the second Syntax-layer validation rule.

It follows the engineering structure frozen by
``docs/architecture/validation-rule-implementation-contract.md`` and proven by the
Transport rules and ``SYNTAX-0001``, conforms to
``docs/architecture/validation-rule-catalog.md`` (§9.2, §5, §8.2, §14, §15), and is
built per ``docs/development/validation-rule-development-guide.md``.  It reads the
``ValidationInput`` introduced by ADR-0003.

Ownership (Response Normalization Contract §8, §10)
---------------------------------------------------
**Normalization owns duplicate-key detection; validation owns the judgement.**  The
Response Normalization Layer detects duplicate field identifiers and records them as
un-judged ``duplicate_identifier`` :class:`NormalizationObservation` facts on the
``NormalizationResult``.  This rule **never detects** duplicates: it never parses
JSON, never inspects ``generated_text``, never recovers structure, and never infers
duplication.  It reads the recorded facts and decides whether to raise a
``ValidationIssue``.
"""

from __future__ import annotations

from typing import Any

from requirement_intelligence.normalization.models.normalization_observation import (
    OBSERVATION_DUPLICATE_IDENTIFIER,
)
from requirement_intelligence.validation import (
    ValidationIssue,
    ValidationLayer,
    ValidationRule,
    ValidationRuleMetadata,
    ValidationSeverity,
)
from requirement_intelligence.validation.validation_exceptions import ValidationRuleError
from shared.utils.ids import utc_now


class DuplicateKeysRule(ValidationRule):
    """Validate that normalization reported no duplicate field identifiers.

    Purpose:
        Confirm no field identifier is duplicated within a structural object — its
        single concern — by reading the ``duplicate_identifier`` **observations**
        the Response Normalization Layer already recorded.  The rule evaluates
        those facts; it never detects duplicates itself.
    Layer:
        Syntax — a well-formedness concern: duplicate identifiers make the
        structure ambiguous to interpret (Rule Catalog §8.2).
    Inputs:
        The :class:`ValidationInput`, read-only (ADR-0003).  The validation decision
        reads **only** ``normalization_result.observations`` and filters them to the
        ``duplicate_identifier`` type.  The issue's ``correlation_id`` is derived
        from ``analysis_result.execution_id`` (issue provenance, per the Development
        Guide §8) — never a second validation concern.  It never inspects
        ``parsed_response``/``normalized_structure``, ``generated_text``, or any
        provider output.
    Outputs:
        When one or more ``duplicate_identifier`` observations are present, exactly
        **one** ``ValidationIssue`` (the duplicate observations are aggregated into a
        single finding for the one concern) with severity ``CRITICAL`` and
        ``blocking=True`` (Rule Catalog §5, §14, §15).  When none are present, no
        findings (an empty list).
    Failure Conditions:
        Raises nothing for a normal validation outcome.  Duplicate identifiers are a
        **finding** (returned), never an exception.  It raises
        :class:`ValidationRuleError` **only** for an infrastructure failure — a
        structurally broken ``ValidationInput`` whose ``NormalizationResult`` is
        absent, so the observations cannot be read at all.
    Worked Example:
        Pass: a `ValidationInput` whose ``observations`` contain no
        ``duplicate_identifier`` fact → ``[]``.
        Fail: one whose ``observations`` contain one or more
        ``duplicate_identifier`` facts → a single ``CRITICAL`` blocking issue.
    Architecture Reference:
        ``SYNTAX-0002``, Validation Rule Catalog §9.2; ambiguity §8.2; Syntax is
        progression-stopping §5; severity §14; blocking §15; Syntax Layer Design
        Review §10.

    Facts, not exceptions (Implementation Contract §6):
        Duplicate identifiers are a `ValidationIssue`, never a raised exception.
        Only an inability to *read the facts* (a missing `NormalizationResult`)
        raises.

    Independence (Validation Rule Catalog §16; Implementation Contract §7):
        Pure, deterministic, stateless, idempotent, non-mutating, side-effect free.
        It depends only on the `ValidationInput` handed to :meth:`validate`, never on
        another rule.  It detects nothing, parses nothing, and repairs nothing.
    """

    #: Identity is fixed at definition and shared on every access (frozen value).
    _METADATA = ValidationRuleMetadata(
        rule_id="SYNTAX-0002",
        rule_name="Duplicate Keys",
        validation_layer=ValidationLayer.SYNTAX,
    )

    @property
    def metadata(self) -> ValidationRuleMetadata:
        """The rule's immutable identity (see Validation Rule Catalog §9.2)."""
        return self._METADATA

    def validate(self, response: Any) -> list[ValidationIssue]:
        """Return one finding if duplicate-key observations exist; otherwise none.

        The ``ValidationInput`` is treated as read-only.  The validation decision
        reads **only** the recorded observations, filtered to the
        ``duplicate_identifier`` type — never the parsed structure, the generated
        text, or any provider output.  One or more such observations aggregate into
        a single finding; none yields an empty list.
        """
        normalization_result = response.normalization_result
        if normalization_result is None:
            # A structurally broken ValidationInput: the observations cannot be read
            # at all.  This is an infrastructure failure, never a judgement about the
            # response (Implementation Contract §6).
            raise ValidationRuleError(
                "SYNTAX-0002: the ValidationInput carries no NormalizationResult; "
                "the duplicate-identifier observations cannot be read."
            )
        duplicate_count = sum(
            1
            for observation in normalization_result.observations
            if observation.observation_type == OBSERVATION_DUPLICATE_IDENTIFIER
        )
        if duplicate_count == 0:
            return []
        return [self._duplicate_keys_issue(response.analysis_result, duplicate_count)]

    def _duplicate_keys_issue(self, analysis_result: Any, duplicate_count: int) -> ValidationIssue:
        """Build the single, fully-populated issue aggregating the duplicate facts."""
        return ValidationIssue(
            issue_id=f"{self.rule_id}:duplicate_identifier",
            category=self.validation_layer.value,
            severity=ValidationSeverity.CRITICAL,
            validation_layer=self.validation_layer,
            rule_id=self.rule_id,
            rule_version=self.rule_version,
            message="One or more field identifiers are duplicated within a structural object.",
            location="$",
            evidence=(
                f"{duplicate_count} duplicate field identifier observation(s) "
                f"reported during normalization."
            ),
            recommendation=(
                "Regenerate the AI response so that each field identifier is unique "
                "within its structural object."
            ),
            blocking=True,
            correlation_id=analysis_result.execution_id,
            created_at=utc_now(),
        )
