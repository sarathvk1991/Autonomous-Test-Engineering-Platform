"""SCHEMA-0002 — FieldTypesRule, the second Schema-layer validation rule.

It follows the engineering structure frozen by the **Validation Rule Implementation
Contract**, the Schema specialization frozen by the **Schema Validation
Implementation Contract**, and the Schema ↔ Structural ownership boundary set by
**ADR-0004**; it conforms to ``docs/architecture/validation-rule-catalog.md`` (§9.3,
§8.3, §14, §15) and is built per
``docs/development/validation-rule-development-guide.md``.  It reads the
``ValidationInput`` introduced by ADR-0003.

Ownership (Rule Catalog §9.3; Schema Implementation Contract §3)
---------------------------------------------------------------
Within the Schema layer, existence and conformance are partitioned so no two rules
overlap.  This rule owns exactly one concern: *every governed field that is present
is of its expected type*.  It never validates:

* the **existence** of a required non-collection section/property — that is
  ``SCHEMA-0001`` (RequiredSectionsRule);
* the **existence** of a required collection — that is ``SCHEMA-0004``
  (RequiredArraysRule);
* whether an **enumerated** field holds a permitted value — that is ``SCHEMA-0003``
  (EnumerationsRule);
* composition/hierarchy (Structural), or value meaning/quality (Content onward).

The existence boundary matters concretely: a field that is **absent** is *not* this
rule's concern (its presence is owned by ``SCHEMA-0001``/``SCHEMA-0004``).  This rule
judges the type of a field **only when that field is present**.  A present field
whose value is of the wrong type is a type finding; an absent field is skipped.

The governed field-type mapping
-------------------------------
The AI response schema (Prompt Framework, ``JSON_RESPONSE_REQUIREMENTS``) declares
six governed top-level fields and their types: ``summary`` is a **string**;
``functional_requirements``, ``security_requirements``, ``quality_requirements``,
``risks``, and ``recommendations`` are **arrays**.  This mapping is a **fixed,
governed constant** — the expected shape does not vary, so no collaborator is
injected (Schema Implementation Contract §8: inject the shape only if the shape
varies).  Only the **declared top-level type** is validated; element contents inside
a collection are never inspected (Content's concern, not Schema's).
"""

from __future__ import annotations

from typing import Any, NamedTuple

from requirement_intelligence.validation import (
    ValidationIssue,
    ValidationLayer,
    ValidationRule,
    ValidationRuleMetadata,
    ValidationSeverity,
)
from requirement_intelligence.validation.validation_exceptions import ValidationRuleError
from shared.utils.ids import utc_now


class _GovernedFieldType(NamedTuple):
    """One governed field, its expected Python type, and its readable type label."""

    field: str
    expected_type: type
    type_label: str


#: The governed field → expected-type mapping of the response schema (Prompt Framework
#: ``JSON_RESPONSE_REQUIREMENTS``).  Fixed and governed — the expected shape does not
#: vary, so it is a constant, never an injected collaborator (Schema Validation
#: Implementation Contract §8).  Only the declared **top-level** type is checked;
#: existence (``SCHEMA-0001``/``SCHEMA-0004``) and enumerated values (``SCHEMA-0003``)
#: are owned elsewhere and deliberately excluded here.
_GOVERNED_FIELD_TYPES: tuple[_GovernedFieldType, ...] = (
    _GovernedFieldType("summary", str, "string"),
    _GovernedFieldType("functional_requirements", list, "array"),
    _GovernedFieldType("security_requirements", list, "array"),
    _GovernedFieldType("quality_requirements", list, "array"),
    _GovernedFieldType("risks", list, "array"),
    _GovernedFieldType("recommendations", list, "array"),
)


def _observed_type_label(value: Any) -> str:
    """A deterministic, JSON-oriented label for the *observed* type of *value*.

    Used only to describe a finding; it never affects whether a finding is raised.
    ``bool`` is checked before ``int`` because ``bool`` is a subclass of ``int``.
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, (int, float)):
        return "number"
    return type(value).__name__


class FieldTypesRule(ValidationRule):
    """Validate that every governed field that is present is of its expected type.

    Purpose:
        Confirm that each governed top-level field declared by the schema, **when
        present**, holds a value of its expected type — its single concern (Rule
        Catalog §9.3, §8.3).  It never validates existence (``SCHEMA-0001``/
        ``SCHEMA-0004``), enumerations (``SCHEMA-0003``), composition (Structural),
        or content (Content onward).
    Layer:
        Schema — machine-readable shape conformance (type).
    Inputs:
        The :class:`ValidationInput`, read-only (ADR-0003).  The validation decision
        reads **only** ``normalization_result.parsed_response.normalized_structure``.
        The issue's ``correlation_id`` is derived from
        ``analysis_result.execution_id`` (issue provenance, per the Development Guide
        §8) — never a functional input.  It never reads the Normalization Outcome,
        observations, ``generated_text``, provider, ``source_reference``, or metadata.
    Outputs:
        One ``ValidationIssue`` **per governed field of the wrong type**
        (per-occurrence, Validation Rule Implementation Contract §5), each with
        severity ``ERROR`` and ``blocking=False`` (Rule Catalog §14 — a schema shape
        defect is ``ERROR`` → ``FAILED``, not ``CRITICAL``/``BLOCKED``).  When every
        present governed field is of the correct type, no findings.
    Failure Conditions:
        Raises nothing for a normal validation outcome.  A wrong type is a **finding**
        (returned), never an exception.  It raises :class:`ValidationRuleError`
        **only** for an infrastructure failure — a structurally broken
        ``ValidationInput`` whose ``ParsedResponse`` is absent.
    Missing normalized structure:
        Schema assumes Syntax has run.  When no structure was recovered
        (``normalized_structure`` is ``None`` — a ``MALFORMED`` response Syntax
        owns), the rule **defers** and returns ``[]``; it never re-reports
        well-formedness (Schema Validation Implementation Contract §10.2).
    Worked Example:
        Pass: ``{"summary": "s", "risks": []}`` → ``[]`` (types correct; absent
        fields are not this rule's concern).
        Fail: ``{"summary": [], "risks": "oops"}`` → two ``ERROR`` issues (a string
        expected but an array found; an array expected but a string found).
    Architecture Reference:
        ``SCHEMA-0002``, Validation Rule Catalog §9.3; type ownership §8.3; severity
        §14; blocking §15.

    Independence (Validation Rule Catalog §16; Implementation Contract §7):
        Pure, deterministic, stateless, idempotent, non-mutating, side-effect free.
        It depends only on the ``ValidationInput`` handed to :meth:`validate`, never
        on another rule.  It normalizes nothing and repairs nothing.
    """

    #: Identity is fixed at definition and shared on every access (frozen value).
    _METADATA = ValidationRuleMetadata(
        rule_id="SCHEMA-0002",
        rule_name="Field Types",
        validation_layer=ValidationLayer.SCHEMA,
    )

    @property
    def metadata(self) -> ValidationRuleMetadata:
        """The rule's immutable identity (see Validation Rule Catalog §9.3)."""
        return self._METADATA

    def validate(self, response: Any) -> list[ValidationIssue]:
        """Return one finding per governed field present with the wrong type.

        The ``ValidationInput`` is treated as read-only.  The validation decision
        reads **only** the normalized structure — never the outcome, observations,
        generated text, or provider output.  A present field of the wrong type is a
        finding; an **absent** field is skipped (existence is not this rule's
        concern); an absent structure defers to ``[]``.
        """
        parsed_response = response.normalization_result.parsed_response
        if parsed_response is None:
            # A broken normalization handoff: the structure cannot be read at all.
            # Infrastructure failure, never a judgement (Implementation Contract §6).
            raise ValidationRuleError(
                "SCHEMA-0002: the NormalizationResult carries no ParsedResponse; "
                "the normalized structure cannot be read."
            )

        normalized_structure = parsed_response.normalized_structure
        if normalized_structure is None:
            # No structure was recovered (a MALFORMED response). Well-formedness is
            # Syntax's concern; Schema defers (Schema Implementation Contract §10.2).
            return []

        analysis_result = response.analysis_result
        return [
            self._wrong_type_issue(analysis_result, governed, normalized_structure[governed.field])
            for governed in _GOVERNED_FIELD_TYPES
            if governed.field in normalized_structure
            and not isinstance(normalized_structure[governed.field], governed.expected_type)
        ]

    def _wrong_type_issue(
        self, analysis_result: Any, governed: _GovernedFieldType, value: Any
    ) -> ValidationIssue:
        """Build the single, fully-populated issue for one field of the wrong type."""
        observed = _observed_type_label(value)
        return ValidationIssue(
            issue_id=f"{self.rule_id}:{governed.field}",
            category=self.validation_layer.value,
            severity=ValidationSeverity.ERROR,
            validation_layer=self.validation_layer,
            rule_id=self.rule_id,
            rule_version=self.rule_version,
            message=(
                f"The field {governed.field!r} must be of type {governed.type_label}, "
                f"but a {observed} was found."
            ),
            location=governed.field,
            evidence=None,
            recommendation=(f"Provide the {governed.field!r} field as a {governed.type_label}."),
            blocking=False,
            correlation_id=analysis_result.execution_id,
            created_at=utc_now(),
        )
