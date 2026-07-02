"""SYNTAX-0001 — ValidStructureRule, the first Syntax-layer validation rule.

It follows the engineering structure frozen by
``docs/architecture/validation-rule-implementation-contract.md`` and proven by the
Transport rules, conforms to ``docs/architecture/validation-rule-catalog.md``
(§9.2, §14, §15), and is built per
``docs/development/validation-rule-development-guide.md``.  It reads the
``ValidationInput`` introduced by ADR-0003.
"""

from __future__ import annotations

from typing import Any

from requirement_intelligence.validation import (
    ValidationIssue,
    ValidationLayer,
    ValidationRule,
    ValidationRuleMetadata,
    ValidationSeverity,
)
from requirement_intelligence.validation.validation_exceptions import ValidationRuleError
from shared.enums.base import NormalizationOutcome
from shared.utils.ids import utc_now


class ValidStructureRule(ValidationRule):
    """Validate that the response normalized into well-formed structured data.

    Purpose:
        Confirm the response is well-formed structured data — its single concern —
        by reading the **Normalization Outcome** the Response Normalization Layer
        already produced.  The rule judges only whether the outcome is
        ``MALFORMED``; it never recovers, inspects, or interprets the structure.
    Layer:
        Syntax — the first layer to read the normalized representation, immediately
        after Transport's delivery guarantees.
    Inputs:
        The :class:`ValidationInput`, read-only (ADR-0003).  The validation
        decision reads **only**
        ``normalization_result.parsed_response.normalization_outcome``.  The issue's
        ``correlation_id`` is derived from ``analysis_result.execution_id`` (issue
        provenance, per the Development Guide §8) — never a second validation
        concern.  It never reads ``normalized_structure`` or the observations
        (those belong to Schema onward, and to ``SYNTAX-0002``/``SYNTAX-0003``).
    Outputs:
        On a ``MALFORMED`` outcome, exactly one ``ValidationIssue`` with severity
        ``CRITICAL`` and ``blocking=True`` (Rule Catalog §14, §15).  On any other
        outcome (``NORMALIZED``), no findings (an empty list).
    Failure Conditions:
        Raises nothing for a normal validation outcome.  A ``MALFORMED`` outcome is
        a **finding** (returned), never an exception.  It raises
        :class:`ValidationRuleError` **only** for an infrastructure failure — a
        ``ValidationInput`` whose ``NormalizationResult`` carries no
        ``ParsedResponse`` (a broken normalization handoff), an uninterpretable
        internal state the rule cannot judge.
    Worked Example:
        Pass: a `ValidationInput` whose Normalization Outcome is ``NORMALIZED`` →
        ``[]``.
        Fail: one whose Normalization Outcome is ``MALFORMED`` → one ``CRITICAL``
        blocking issue recommending regeneration.
    Architecture Reference:
        ``SYNTAX-0001``, Validation Rule Catalog §9.2; severity §14; blocking §15;
        Syntax Layer Design Review §10.

    Facts, not exceptions (Implementation Contract §6):
        A malformed response is a `ValidationIssue`, never a raised exception.  Only
        an inability to *perform the check* (a missing `ParsedResponse`) raises.

    Independence (Validation Rule Catalog §16; Implementation Contract §7):
        Pure, deterministic, stateless, idempotent, non-mutating, side-effect free.
        It depends only on the `ValidationInput` handed to :meth:`validate`, never on
        another rule.  It normalizes nothing, recovers nothing, and repairs nothing.
    """

    #: Identity is fixed at definition and shared on every access (frozen value).
    _METADATA = ValidationRuleMetadata(
        rule_id="SYNTAX-0001",
        rule_name="Valid Structure",
        validation_layer=ValidationLayer.SYNTAX,
    )

    @property
    def metadata(self) -> ValidationRuleMetadata:
        """The rule's immutable identity (see Validation Rule Catalog §9.2)."""
        return self._METADATA

    def validate(self, response: Any) -> list[ValidationIssue]:
        """Return one finding if the response is malformed; otherwise none.

        The ``ValidationInput`` is treated as read-only.  The validation decision
        reads **only** the Normalization Outcome — never the normalized structure,
        the observations, the raw JSON, or any provider output.  A ``MALFORMED``
        outcome is a finding; any other outcome passes.
        """
        parsed_response = response.normalization_result.parsed_response
        if parsed_response is None:
            # A broken normalization handoff: the outcome cannot be read at all.
            # This is an infrastructure failure, never a judgement about the
            # response (Implementation Contract §6).
            raise ValidationRuleError(
                "SYNTAX-0001: the NormalizationResult carries no ParsedResponse; "
                "the normalization handoff is incomplete."
            )
        if parsed_response.normalization_outcome == NormalizationOutcome.MALFORMED:
            return [self._malformed_issue(response.analysis_result)]
        return []

    def _malformed_issue(self, analysis_result: Any) -> ValidationIssue:
        """Build the single, fully-populated issue for a malformed response."""
        return ValidationIssue(
            issue_id=f"{self.rule_id}:normalization_outcome",
            category=self.validation_layer.value,
            severity=ValidationSeverity.CRITICAL,
            validation_layer=self.validation_layer,
            rule_id=self.rule_id,
            rule_version=self.rule_version,
            message="The response could not be normalized into well-formed structured data.",
            location="normalization_outcome",
            evidence=None,
            recommendation="Regenerate the AI response so it returns well-formed structured data.",
            blocking=True,
            correlation_id=analysis_result.execution_id,
            created_at=utc_now(),
        )
