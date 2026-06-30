"""TRANSPORT-0001 — ResponseExistsRule, the first production validation rule.

This rule establishes the engineering pattern every validation rule follows.  It
conforms to ``docs/architecture/validation-rule-catalog.md`` (§9.1) and is built
per ``docs/development/validation-rule-development-guide.md``.
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
from shared.utils.ids import utc_now


class ResponseExistsRule(ValidationRule):
    """Validate that an ``AnalysisResult`` contains an LLM response.

    Purpose:
        Verify that an ``AnalysisResult`` contains an LLM response object — its
        single concern.  Nothing else is examined.
    Layer:
        Transport — the most foundational concern: was a usable response received
        at all?
    Inputs:
        The analysed response, read-only.  Only the presence of its
        ``llm_response`` is inspected; its content is never read.
    Outputs:
        On absence, exactly one ``ValidationIssue`` with severity ``CRITICAL`` and
        ``blocking=True``.  On presence, no findings (an empty list).
    Failure Conditions:
        Raises nothing for a normal validation outcome.  A missing response is a
        finding (returned), never an exception.
    Worked Example:
        Pass: an ``AnalysisResult`` whose ``llm_response`` is present → ``[]``.
        Fail: an analysed response whose ``llm_response`` is ``None`` → one
        ``CRITICAL`` blocking issue recommending regeneration.
    Architecture Reference:
        ``TRANSPORT-0001``, Validation Rule Catalog §9.1.

    Independence (Validation Rule Catalog §16):
        Pure, deterministic, stateless, idempotent, non-mutating, side-effect
        free.  It depends only on the response handed to :meth:`validate`.
    """

    #: Identity is fixed at definition and shared on every access (frozen value).
    _METADATA = ValidationRuleMetadata(
        rule_id="TRANSPORT-0001",
        rule_name="Response Exists",
        validation_layer=ValidationLayer.TRANSPORT,
        rule_version="1.0.0",
    )

    @property
    def metadata(self) -> ValidationRuleMetadata:
        """The rule's immutable identity (see Validation Rule Catalog §9.1)."""
        return self._METADATA

    def validate(self, response: Any) -> list[ValidationIssue]:
        """Return one finding if the LLM response is absent; otherwise none.

        The response is treated as read-only.  Only the presence of
        ``llm_response`` is examined — never its content, structure, or meaning.
        """
        if response.llm_response is not None:
            return []
        return [self._missing_response_issue(response)]

    def _missing_response_issue(self, response: Any) -> ValidationIssue:
        """Build the single, fully-populated issue for a missing LLM response."""
        return ValidationIssue(
            issue_id=f"{self.rule_id}:llm_response",
            category=self.validation_layer.value,
            severity=ValidationSeverity.CRITICAL,
            validation_layer=self.validation_layer,
            rule_id=self.rule_id,
            rule_version=self.rule_version,
            message="The analysis result does not contain an LLM response.",
            location="llm_response",
            evidence=None,
            recommendation="Regenerate the AI response before continuing.",
            blocking=True,
            correlation_id=response.execution_id,
            created_at=utc_now(),
        )
