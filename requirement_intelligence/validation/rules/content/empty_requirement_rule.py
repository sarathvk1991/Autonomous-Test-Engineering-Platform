"""CONTENT-0001 — EmptyRequirementRule, the first Content-layer validation rule.

It follows the engineering structure frozen by the **Validation Rule Implementation
Contract** and conforms to ``docs/architecture/validation-rule-catalog.md`` (§9.5,
§8.5, §14, §15); it is built per
``docs/development/validation-rule-development-guide.md``.  It reads the
``ValidationInput`` introduced by ADR-0003 and is classified **Implementable** against
the current governed response schema by **ADR-0006** (each requirement is a governed
string, so emptiness is observable).

Ownership (Rule Catalog §9.5, §8.5)
-----------------------------------
The Content layer confirms individual field-level values meet presence/validity
expectations.  This rule owns exactly one concern: *a requirement statement is not
empty*.  It never validates:

* the **existence** of a requirement collection — that is ``SCHEMA-0004``;
* a field's **type** — that is ``SCHEMA-0002``;
* **duplicated** requirements — that is ``CONTENT-0002``;
* a missing **description** or a **confidence** value — ``CONTENT-0003`` / ``CONTENT-0004``
  (both Reserved · Deferred, ADR-0006);
* composition (Structural), grounding (Evidence), traceability (Traceability),
  coherence (Reasoning), or policy (Business).

It validates only **requirement statements** — never ``summary``, ``risks``, or
``recommendations`` (those are not requirements).

The governed requirement collections
-------------------------------------
The AI response schema (Prompt Framework, ``JSON_RESPONSE_REQUIREMENTS``) declares
three requirement collections: ``functional_requirements``, ``security_requirements``,
and ``quality_requirements``.  Each element is a governed string statement.  The set is
a **fixed, governed constant** — the shape does not vary, so no collaborator is injected
(Validation Rule Implementation Contract — inject variation, not ceremony).
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
from shared.utils.ids import utc_now

#: The governed **requirement** collections of the response schema (Prompt Framework
#: ``JSON_RESPONSE_REQUIREMENTS``).  Fixed and governed — the expected shape does not
#: vary, so it is a constant, never an injected collaborator.  ``summary``, ``risks``,
#: and ``recommendations`` are deliberately excluded: they are not requirement
#: statements and are not this rule's concern.
_REQUIREMENT_COLLECTIONS: tuple[str, ...] = (
    "functional_requirements",
    "security_requirements",
    "quality_requirements",
)


class EmptyRequirementRule(ValidationRule):
    """Validate that every requirement statement is not empty.

    Purpose:
        Confirm that each requirement statement in the governed requirement
        collections is non-empty — its single concern (Rule Catalog §9.5, §8.5).  It
        never validates existence (``SCHEMA-0004``), type (``SCHEMA-0002``), duplication
        (``CONTENT-0002``), or any later-layer concern.
    Layer:
        Content — field-level value presence/validity.
    Inputs:
        The :class:`ValidationInput`, read-only (ADR-0003).  The validation decision
        reads **only** ``normalization_result.parsed_response.normalized_structure``.
        The issue's ``correlation_id`` is derived from
        ``analysis_result.execution_id`` (issue provenance, per the Development Guide
        §8) — never a functional input.  It never reads the Normalization Outcome,
        observations, ``generated_text``, provider, ``source_reference``, or metadata.
    Outputs:
        One ``ValidationIssue`` **per empty requirement** (per-occurrence, Validation
        Rule Implementation Contract §5), each with severity ``ERROR`` and
        ``blocking=False`` (Rule Catalog §14 — an empty requirement makes the output
        untrustworthy → ``ERROR``; §15 — Content is a semantic layer that records and
        never blocks).  When every requirement is non-empty, no findings.
    Failure Conditions:
        Raises nothing for a normal validation outcome.  An empty requirement is a
        **finding** (returned), never an exception.  It raises
        :class:`ValidationRuleError` **only** for an infrastructure failure — a
        structurally broken ``ValidationInput`` whose ``ParsedResponse`` is absent.
    Missing normalized structure:
        When no structure was recovered (``normalized_structure`` is ``None`` — a
        ``MALFORMED`` response Syntax owns), the rule **defers** and returns ``[]``;
        it never re-reports well-formedness.
    Boundary discipline:
        A requirement collection that is **absent** is skipped (existence is
        ``SCHEMA-0004``'s concern).  A present-but-non-list value is skipped (type is
        ``SCHEMA-0002``'s concern).  A non-string element is skipped (element emptiness
        applies only to strings).  Only an empty/whitespace-only **string** element is a
        finding.
    Worked Example:
        Pass: ``{"functional_requirements": ["do X"]}`` → ``[]``.
        Fail: ``{"functional_requirements": ["", "  "]}`` → two ``ERROR`` issues.
    Architecture Reference:
        ``CONTENT-0001``, Validation Rule Catalog §9.5; layer §8.5; severity §14;
        blocking §15; capability status ADR-0006.

    Independence (Validation Rule Catalog §16; Implementation Contract §7):
        Pure, deterministic, stateless, idempotent, non-mutating, side-effect free.
        It depends only on the ``ValidationInput`` handed to :meth:`validate`, never
        on another rule.  It normalizes nothing and repairs nothing.
    """

    #: Identity is fixed at definition and shared on every access (frozen value).
    _METADATA = ValidationRuleMetadata(
        rule_id="CONTENT-0001",
        rule_name="Empty Requirement",
        validation_layer=ValidationLayer.CONTENT,
    )

    @property
    def metadata(self) -> ValidationRuleMetadata:
        """The rule's immutable identity (see Validation Rule Catalog §9.5)."""
        return self._METADATA

    def validate(self, response: Any) -> list[ValidationIssue]:
        """Return one finding per empty requirement statement.

        The ``ValidationInput`` is treated as read-only.  The validation decision
        reads **only** the normalized structure — never the outcome, observations,
        generated text, or provider output.  An empty requirement is a finding; an
        absent structure defers to ``[]``.
        """
        parsed_response = response.normalization_result.parsed_response
        if parsed_response is None:
            # A broken normalization handoff: the structure cannot be read at all.
            # Infrastructure failure, never a judgement (Implementation Contract §6).
            raise ValidationRuleError(
                "CONTENT-0001: the NormalizationResult carries no ParsedResponse; "
                "the normalized structure cannot be read."
            )

        normalized_structure = parsed_response.normalized_structure
        if normalized_structure is None:
            # No structure was recovered (a MALFORMED response). Well-formedness is
            # Syntax's concern; Content defers.
            return []

        analysis_result = response.analysis_result
        return [
            self._empty_requirement_issue(analysis_result, collection, index)
            for collection in _REQUIREMENT_COLLECTIONS
            for index, element in self._requirements(normalized_structure.get(collection))
            if isinstance(element, str) and element.strip() == ""
        ]

    @staticmethod
    def _requirements(value: Any) -> list[tuple[int, Any]]:
        """Enumerate a present requirement list.

        An absent collection (``None``) or a present-but-non-list value yields nothing:
        existence is ``SCHEMA-0004``'s concern and type is ``SCHEMA-0002``'s — never
        this rule's.
        """
        if not isinstance(value, list):
            return []
        return list(enumerate(value))

    def _empty_requirement_issue(
        self, analysis_result: Any, collection: str, index: int
    ) -> ValidationIssue:
        """Build the single, fully-populated issue for one empty requirement."""
        location = f"{collection}[{index}]"
        return ValidationIssue(
            issue_id=f"{self.rule_id}:{location}",
            category=self.validation_layer.value,
            severity=ValidationSeverity.ERROR,
            validation_layer=self.validation_layer,
            rule_id=self.rule_id,
            rule_version=self.rule_version,
            message=f"The requirement statement at {location} is empty.",
            location=location,
            evidence=None,
            recommendation=f"Provide a non-empty requirement statement at {location}.",
            blocking=False,
            correlation_id=analysis_result.execution_id,
            created_at=utc_now(),
        )
