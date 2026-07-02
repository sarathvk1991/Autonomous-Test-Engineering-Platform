"""SCHEMA-0004 — RequiredArraysRule, the Schema-layer required-collection rule.

It follows the engineering structure frozen by the **Validation Rule Implementation
Contract**, the Schema specialization frozen by the **Schema Validation
Implementation Contract**, and the Schema ↔ Structural ownership boundary set by
**ADR-0004**; it conforms to ``docs/architecture/validation-rule-catalog.md`` (§9.3,
§8.3, §14, §15) and is built per
``docs/development/validation-rule-development-guide.md``.  It reads the
``ValidationInput`` introduced by ADR-0003.

Ownership (ADR-0004; Rule Catalog §9.3; Schema Implementation Contract §3)
--------------------------------------------------------------------------
Schema is the sole owner of machine-readable schema conformance, **including the
existence of required collections**.  This rule owns exactly one concern: *every
required collection declared by the schema exists*.  Within Schema, existence is
partitioned by declared kind so no two rules overlap: a required **non-collection**
section/property is ``SCHEMA-0001`` (RequiredSectionsRule); a field's **type** is
``SCHEMA-0002`` (FieldTypesRule); an **enumerated value** is ``SCHEMA-0003``
(deferred, ADR-0005).  This rule validates none of those — only the **presence** of
each required collection.  It never validates a collection's element type, its
cardinality, its contents, or how it is nested/organized (Structural/Content).

The governed required collections
---------------------------------
The AI response schema (Prompt Framework, ``JSON_RESPONSE_REQUIREMENTS``) declares
six required top-level sections; the single **non-collection** section is the
executive summary (``summary``, owned by ``SCHEMA-0001``).  The five **collections**
are ``functional_requirements``, ``security_requirements``, ``quality_requirements``,
``risks``, and ``recommendations``.  The set is a **fixed, governed constant** — the
shape does not vary, so no collaborator is injected (Schema Implementation Contract
§8).
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

#: The governed required **collections** of the response schema (ADR-0004; Prompt
#: Framework ``JSON_RESPONSE_REQUIREMENTS``).  Fixed and governed — the expected shape
#: does not vary, so it is a constant, never an injected collaborator (Schema
#: Validation Implementation Contract §8).  The required non-collection section
#: (``summary``) is owned by ``SCHEMA-0001`` and is deliberately excluded here.
_REQUIRED_COLLECTIONS: tuple[str, ...] = (
    "functional_requirements",
    "security_requirements",
    "quality_requirements",
    "risks",
    "recommendations",
)


class RequiredArraysRule(ValidationRule):
    """Validate that every required collection declared by the schema is present.

    Purpose:
        Confirm that every required **collection** declared by the schema exists in
        the normalized structure — its single concern (ADR-0004).  It never validates
        non-collection sections, types, enumerations, a collection's element type,
        cardinality, contents, composition, or content.
    Layer:
        Schema — machine-readable shape conformance (collection existence).
    Inputs:
        The :class:`ValidationInput`, read-only (ADR-0003).  The validation decision
        reads **only** ``normalization_result.parsed_response.normalized_structure``.
        The issue's ``correlation_id`` is derived from
        ``analysis_result.execution_id`` (issue provenance, per the Development Guide
        §8) — never a functional input.  It never reads the Normalization Outcome,
        observations, ``generated_text``, provider, ``source_reference``, or metadata.
    Outputs:
        One ``ValidationIssue`` **per missing** required collection (per-occurrence,
        Validation Rule Implementation Contract §5), each with severity ``ERROR`` and
        ``blocking=False`` (Rule Catalog §14 — a missing required collection is
        ``ERROR`` → ``FAILED``, not ``CRITICAL``/``BLOCKED``).  When every required
        collection is present, no findings.
    Failure Conditions:
        Raises nothing for a normal validation outcome.  A missing collection is a
        **finding** (returned), never an exception.  It raises
        :class:`ValidationRuleError` **only** for an infrastructure failure — a
        structurally broken ``ValidationInput`` whose ``ParsedResponse`` is absent.
    Missing normalized structure:
        Schema assumes Syntax has run.  When no structure was recovered
        (``normalized_structure`` is ``None`` — a ``MALFORMED`` response Syntax
        owns), the rule **defers** and returns ``[]``; it never re-reports
        well-formedness (Schema Validation Implementation Contract §10.2).
    Worked Example:
        Pass: a structure containing all five collections → ``[]``.
        Fail: a structure without ``"risks"`` → one ``ERROR`` issue.
    Architecture Reference:
        ``SCHEMA-0004``, Validation Rule Catalog §9.3; existence ownership §8.3 /
        ADR-0004; severity §14; blocking §15.

    Independence (Validation Rule Catalog §16; Implementation Contract §7):
        Pure, deterministic, stateless, idempotent, non-mutating, side-effect free.
        It depends only on the ``ValidationInput`` handed to :meth:`validate`, never
        on another rule.  It normalizes nothing and repairs nothing.
    """

    #: Identity is fixed at definition and shared on every access (frozen value).
    _METADATA = ValidationRuleMetadata(
        rule_id="SCHEMA-0004",
        rule_name="Required Arrays",
        validation_layer=ValidationLayer.SCHEMA,
    )

    @property
    def metadata(self) -> ValidationRuleMetadata:
        """The rule's immutable identity (see Validation Rule Catalog §9.3)."""
        return self._METADATA

    def validate(self, response: Any) -> list[ValidationIssue]:
        """Return one finding per missing required collection.

        The ``ValidationInput`` is treated as read-only.  The validation decision
        reads **only** the normalized structure — never the outcome, observations,
        generated text, or provider output.  A missing required collection is a
        finding; an absent structure defers to ``[]``.
        """
        parsed_response = response.normalization_result.parsed_response
        if parsed_response is None:
            # A broken normalization handoff: the structure cannot be read at all.
            # Infrastructure failure, never a judgement (Implementation Contract §6).
            raise ValidationRuleError(
                "SCHEMA-0004: the NormalizationResult carries no ParsedResponse; "
                "the normalized structure cannot be read."
            )

        normalized_structure = parsed_response.normalized_structure
        if normalized_structure is None:
            # No structure was recovered (a MALFORMED response). Well-formedness is
            # Syntax's concern; Schema defers (Schema Implementation Contract §10.2).
            return []

        analysis_result = response.analysis_result
        return [
            self._missing_collection_issue(analysis_result, collection)
            for collection in _REQUIRED_COLLECTIONS
            if collection not in normalized_structure
        ]

    def _missing_collection_issue(self, analysis_result: Any, collection: str) -> ValidationIssue:
        """Build the single, fully-populated issue for one missing required collection."""
        return ValidationIssue(
            issue_id=f"{self.rule_id}:{collection}",
            category=self.validation_layer.value,
            severity=ValidationSeverity.ERROR,
            validation_layer=self.validation_layer,
            rule_id=self.rule_id,
            rule_version=self.rule_version,
            message=f"The required collection {collection!r} is missing from the response.",
            location=collection,
            evidence=None,
            recommendation=f"Include the required {collection!r} collection in the response.",
            blocking=False,
            correlation_id=analysis_result.execution_id,
            created_at=utc_now(),
        )
