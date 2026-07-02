"""SYNTAX-0003 — EncodingRule, the third (final) Syntax-layer validation rule.

It follows the engineering structure frozen by
``docs/architecture/validation-rule-implementation-contract.md`` and proven by the
Transport rules, ``SYNTAX-0001``, and ``SYNTAX-0002``; conforms to
``docs/architecture/validation-rule-catalog.md`` (§9.2, §5, §8.2, §14, §15); and is
built per ``docs/development/validation-rule-development-guide.md``.  It reads the
``ValidationInput`` introduced by ADR-0003.

Ownership (Response Normalization Contract §8, §10)
---------------------------------------------------
**Normalization owns encoding detection; validation owns the judgement.**  The
Response Normalization Layer detects character-encoding integrity problems and
records them as un-judged ``encoding_observation`` :class:`NormalizationObservation`
facts on the ``NormalizationResult``.  This rule **never detects** encoding
problems: it never inspects ``generated_text``, the provider, the
``ParsedResponse``, or the normalized structure.  It reads the recorded facts and
decides whether to raise a ``ValidationIssue``.
"""

from __future__ import annotations

from typing import Any

from requirement_intelligence.normalization.models.normalization_observation import (
    OBSERVATION_ENCODING,
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


class EncodingRule(ValidationRule):
    """Validate that normalization reported no character-encoding integrity problems.

    Purpose:
        Confirm the response's character encoding is intact — its single concern —
        by reading the ``encoding_observation`` **observations** the Response
        Normalization Layer already recorded.  The rule evaluates those facts; it
        never detects encoding problems itself.
    Layer:
        Syntax — a well-formedness concern: a lossy or corrupt decode makes the
        response's characters untrustworthy to interpret (Rule Catalog §8.2).
    Inputs:
        The :class:`ValidationInput`, read-only (ADR-0003).  The validation decision
        reads **only** ``normalization_result.observations`` and filters them to the
        ``encoding_observation`` type.  The issue's ``correlation_id`` is derived
        from ``analysis_result.execution_id`` (issue provenance, per the Development
        Guide §8) — never a functional validation input.  It never inspects
        ``generated_text``, the provider, the ``ParsedResponse``, or the normalized
        structure.
    Outputs:
        When one or more ``encoding_observation`` observations are present, exactly
        **one** ``ValidationIssue`` (the encoding observations are aggregated into a
        single finding for the one concern) with severity ``CRITICAL`` and
        ``blocking=True`` (Rule Catalog §5, §14, §15).  When none are present, no
        findings (an empty list).
    Failure Conditions:
        Raises nothing for a normal validation outcome.  Encoding problems are a
        **finding** (returned), never an exception.  It raises
        :class:`ValidationRuleError` **only** for an infrastructure failure — a
        structurally broken ``ValidationInput`` whose ``NormalizationResult`` is
        absent, so the observations cannot be read at all.
    Worked Example:
        Pass: a `ValidationInput` whose ``observations`` contain no
        ``encoding_observation`` fact → ``[]``.
        Fail: one whose ``observations`` contain one or more ``encoding_observation``
        facts → a single ``CRITICAL`` blocking issue.
    Architecture Reference:
        ``SYNTAX-0003``, Validation Rule Catalog §9.2; encoding integrity §8.2;
        Syntax is progression-stopping §5; severity §14; blocking §15; Syntax Layer
        Design Review §10.

    Facts, not exceptions (Implementation Contract §6):
        Encoding problems are a `ValidationIssue`, never a raised exception.  Only an
        inability to *read the facts* (a missing `NormalizationResult`) raises.

    Independence (Validation Rule Catalog §16; Implementation Contract §7):
        Pure, deterministic, stateless, idempotent, non-mutating, side-effect free.
        It depends only on the `ValidationInput` handed to :meth:`validate`, never on
        another rule.  It detects nothing, inspects no text, and repairs nothing.
    """

    #: Identity is fixed at definition and shared on every access (frozen value).
    _METADATA = ValidationRuleMetadata(
        rule_id="SYNTAX-0003",
        rule_name="Encoding",
        validation_layer=ValidationLayer.SYNTAX,
    )

    @property
    def metadata(self) -> ValidationRuleMetadata:
        """The rule's immutable identity (see Validation Rule Catalog §9.2)."""
        return self._METADATA

    def validate(self, response: Any) -> list[ValidationIssue]:
        """Return one finding if encoding observations exist; otherwise none.

        The ``ValidationInput`` is treated as read-only.  The validation decision
        reads **only** the recorded observations, filtered to the
        ``encoding_observation`` type — never the parsed structure, the generated
        text, or any provider output.  One or more such observations aggregate into a
        single finding; none yields an empty list.
        """
        normalization_result = response.normalization_result
        if normalization_result is None:
            # A structurally broken ValidationInput: the observations cannot be read
            # at all.  This is an infrastructure failure, never a judgement about the
            # response (Implementation Contract §6).
            raise ValidationRuleError(
                "SYNTAX-0003: the ValidationInput carries no NormalizationResult; "
                "the encoding observations cannot be read."
            )
        encoding_count = sum(
            1
            for observation in normalization_result.observations
            if observation.observation_type == OBSERVATION_ENCODING
        )
        if encoding_count == 0:
            return []
        return [self._encoding_issue(response.analysis_result, encoding_count)]

    def _encoding_issue(self, analysis_result: Any, encoding_count: int) -> ValidationIssue:
        """Build the single, fully-populated issue aggregating the encoding facts."""
        return ValidationIssue(
            issue_id=f"{self.rule_id}:encoding",
            category=self.validation_layer.value,
            severity=ValidationSeverity.CRITICAL,
            validation_layer=self.validation_layer,
            rule_id=self.rule_id,
            rule_version=self.rule_version,
            message="The response's character encoding is not intact.",
            location="$",
            evidence=(
                f"{encoding_count} encoding-integrity observation(s) reported during normalization."
            ),
            recommendation=(
                "Regenerate the AI response using a lossless character encoding "
                "(e.g. UTF-8) so no characters are corrupted."
            ),
            blocking=True,
            correlation_id=analysis_result.execution_id,
            created_at=utc_now(),
        )
