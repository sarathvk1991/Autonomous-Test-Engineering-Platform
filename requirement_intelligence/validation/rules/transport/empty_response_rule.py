"""TRANSPORT-0002 — EmptyResponseRule, the second production validation rule.

It follows the exact engineering pattern established by ``TRANSPORT-0001``
(:class:`~requirement_intelligence.validation.rules.transport.response_exists_rule.ResponseExistsRule`).
It conforms to ``docs/architecture/validation-rule-catalog.md`` (§9.1) and is
built per ``docs/development/validation-rule-development-guide.md``.
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


class EmptyResponseRule(ValidationRule):
    """Validate that an existing LLM response contains usable generated content.

    Purpose:
        Verify that the generated response contains usable content — its single
        concern.  Nothing else is examined.
    Layer:
        Transport — the most foundational concern, after existence: does the
        received response actually carry content?
    Inputs:
        The analysed response, read-only.  Only ``llm_response.generated_text`` is
        inspected for emptiness; its meaning, structure, and schema are never read.
    Outputs:
        On empty content, exactly one ``ValidationIssue`` with severity
        ``CRITICAL`` and ``blocking=True``.  On usable content, no findings.
    Failure Conditions:
        Raises nothing for a normal validation outcome.  Empty or whitespace-only
        content is a finding (returned), never an exception.  When the response
        object itself is absent, this rule defers to ``TRANSPORT-0001`` and
        returns no findings (existence is not this rule's concern).
    Worked Example:
        Pass: generated content ``"Refunds require manager approval."`` → ``[]``.
        Fail: generated content ``""`` or ``"   "`` → one ``CRITICAL`` blocking
        issue recommending regeneration.
    Architecture Reference:
        ``TRANSPORT-0002``, Validation Rule Catalog §9.1.

    Independence (Validation Rule Catalog §16):
        Pure, deterministic, stateless, idempotent, non-mutating, side-effect
        free.  It depends only on the response handed to :meth:`validate`, never
        on another rule.
    """

    #: Identity is fixed at definition and shared on every access (frozen value).
    _METADATA = ValidationRuleMetadata(
        rule_id="TRANSPORT-0002",
        rule_name="Empty Response",
        validation_layer=ValidationLayer.TRANSPORT,
        rule_version="1.0.0",
    )

    @property
    def metadata(self) -> ValidationRuleMetadata:
        """The rule's immutable identity (see Validation Rule Catalog §9.1)."""
        return self._METADATA

    def validate(self, response: Any) -> list[ValidationIssue]:
        """Return one finding if the generated content is empty; otherwise none.

        The response is treated as read-only.  Only the emptiness of
        ``llm_response.generated_text`` is examined — never its meaning, structure,
        or schema.  Response *existence* is the concern of ``TRANSPORT-0001``;
        when ``llm_response`` is absent this rule defers and returns no findings.
        """
        llm_response = response.llm_response
        if llm_response is None:
            return []
        generated_text = llm_response.generated_text
        if generated_text and generated_text.strip():
            return []
        return [self._empty_content_issue(response)]

    def _empty_content_issue(self, response: Any) -> ValidationIssue:
        """Build the single, fully-populated issue for empty generated content."""
        return ValidationIssue(
            issue_id=f"{self.rule_id}:generated_text",
            category=self.validation_layer.value,
            severity=ValidationSeverity.CRITICAL,
            validation_layer=self.validation_layer,
            rule_id=self.rule_id,
            rule_version=self.rule_version,
            message="The LLM response contains no generated content.",
            location="generated_text",
            evidence=None,
            recommendation="Regenerate the AI response before continuing.",
            blocking=True,
            correlation_id=response.execution_id,
            created_at=utc_now(),
        )
