"""CONTENT-0002 — DuplicateRequirementRule, the Content-layer duplicate rule.

It follows the engineering structure frozen by the **Validation Rule Implementation
Contract** and conforms to ``docs/architecture/validation-rule-catalog.md`` (§9.5,
§8.5, §14, §15); its **duplicate-detection scope is frozen by ADR-0007** and it is
classified **Implementable** by **ADR-0006**.  It reads the ``ValidationInput``
introduced by ADR-0003.

Ownership (Rule Catalog §9.5; scope frozen by ADR-0007)
------------------------------------------------------
This rule owns exactly one concern: *duplicate requirement statements within one
governed requirement collection*.  Per **ADR-0007** the three requirement collections
(``functional_requirements``, ``security_requirements``, ``quality_requirements``) are
evaluated **independently** and are **never pooled** — a statement appearing once in
each collection is **not** a finding, and cross-collection duplication is **outside**
this rule's ownership.  It never validates:

* empty statements — that is ``CONTENT-0001`` (EmptyRequirementRule);
* the **existence** of a collection — that is ``SCHEMA-0004``;
* a field's **type** — that is ``SCHEMA-0002``;
* recommendation duplication — that is ``REASONING-0002``;
* semantic equivalence, paraphrase, or reasoning similarity (Reasoning);
* cross-container relationships (Structural).

Duplicate detection is **byte-exact string equality** — case-sensitive and
whitespace-sensitive, with no trimming, normalization, or lowercasing (ADR-0007).
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

#: The governed **requirement** collections, each evaluated independently (ADR-0007).
#: Fixed and governed — the shape does not vary, so it is a constant, never an injected
#: collaborator.  ``summary``, ``risks``, and ``recommendations`` are excluded: they are
#: not requirement statements and are not this rule's concern.
_REQUIREMENT_COLLECTIONS: tuple[str, ...] = (
    "functional_requirements",
    "security_requirements",
    "quality_requirements",
)


class DuplicateRequirementRule(ValidationRule):
    """Validate that no requirement statement is duplicated within its collection.

    Purpose:
        Confirm that, within each governed requirement collection independently, no
        requirement statement repeats — its single concern (Rule Catalog §9.5; scope
        frozen by ADR-0007).  It never validates emptiness (``CONTENT-0001``),
        existence (``SCHEMA-0004``), type (``SCHEMA-0002``), cross-collection
        duplication (outside its ownership, ADR-0007), or any later-layer concern.
    Layer:
        Content — field-level value presence/validity.
    Inputs:
        The :class:`ValidationInput`, read-only (ADR-0003).  The validation decision
        reads **only** ``normalization_result.parsed_response.normalized_structure``.
        The issue's ``correlation_id`` is derived from
        ``analysis_result.execution_id`` (issue provenance) — never a functional input.
        It never reads the Normalization Outcome, observations, ``generated_text``,
        provider, ``source_reference``, or metadata.
    Outputs:
        One ``ValidationIssue`` **per duplicate occurrence** — the second and each
        subsequent appearance of a value within a collection (per-occurrence,
        Validation Rule Implementation Contract §5), each with severity ``ERROR`` and
        ``blocking=False`` (Rule Catalog §14/§15 — Content is a semantic layer that
        records and never blocks).  The first appearance of a value is never a finding.
    Failure Conditions:
        Raises nothing for a normal validation outcome.  A duplicate is a **finding**
        (returned), never an exception.  It raises :class:`ValidationRuleError`
        **only** for an infrastructure failure — a structurally broken
        ``ValidationInput`` whose ``ParsedResponse`` is absent.
    Missing normalized structure:
        When no structure was recovered (``normalized_structure`` is ``None`` — a
        ``MALFORMED`` response Syntax owns), the rule **defers** and returns ``[]``.
    Boundary discipline:
        A collection that is **absent** is skipped (existence is ``SCHEMA-0004``'s).  A
        present-but-non-list value is skipped (type is ``SCHEMA-0002``'s).  A non-string
        element is skipped (not a requirement statement).  Only a repeated **string**
        within one collection is a finding.
    Worked Example:
        Pass: ``{"functional_requirements": ["A", "B"]}`` → ``[]``.
        Fail: ``{"functional_requirements": ["A", "B", "A", "A"]}`` → two findings (the
        second and third ``"A"``).
        Not a finding: ``{"functional_requirements": ["A"], "risks": ...,
        "security_requirements": ["A"]}`` → ``[]`` (collections are never pooled,
        ADR-0007).
    Architecture Reference:
        ``CONTENT-0002``, Validation Rule Catalog §9.5; scope ADR-0007; layer §8.5;
        severity §14; blocking §15; capability status ADR-0006.

    Independence (Validation Rule Catalog §16; Implementation Contract §7):
        Pure, deterministic, stateless, idempotent, non-mutating, side-effect free.
        It depends only on the ``ValidationInput`` handed to :meth:`validate`, never
        on another rule.  It normalizes nothing and repairs nothing.
    """

    #: Identity is fixed at definition and shared on every access (frozen value).
    _METADATA = ValidationRuleMetadata(
        rule_id="CONTENT-0002",
        rule_name="Duplicate Requirement",
        validation_layer=ValidationLayer.CONTENT,
    )

    @property
    def metadata(self) -> ValidationRuleMetadata:
        """The rule's immutable identity (see Validation Rule Catalog §9.5)."""
        return self._METADATA

    def validate(self, response: Any) -> list[ValidationIssue]:
        """Return one finding per duplicate occurrence, per collection independently.

        The ``ValidationInput`` is treated as read-only.  The validation decision
        reads **only** the normalized structure — never the outcome, observations,
        generated text, or provider output.  A duplicate is a finding; an absent
        structure defers to ``[]``.
        """
        parsed_response = response.normalization_result.parsed_response
        if parsed_response is None:
            # A broken normalization handoff: the structure cannot be read at all.
            # Infrastructure failure, never a judgement (Implementation Contract §6).
            raise ValidationRuleError(
                "CONTENT-0002: the NormalizationResult carries no ParsedResponse; "
                "the normalized structure cannot be read."
            )

        normalized_structure = parsed_response.normalized_structure
        if normalized_structure is None:
            # No structure was recovered (a MALFORMED response). Well-formedness is
            # Syntax's concern; Content defers.
            return []

        analysis_result = response.analysis_result
        issues: list[ValidationIssue] = []
        for collection in _REQUIREMENT_COLLECTIONS:
            # Each collection is evaluated independently and never pooled (ADR-0007).
            issues.extend(
                self._duplicate_issues(
                    analysis_result, collection, normalized_structure.get(collection)
                )
            )
        return issues

    def _duplicate_issues(
        self, analysis_result: Any, collection: str, value: Any
    ) -> list[ValidationIssue]:
        """Findings for one collection: the second+ occurrence of each repeated string.

        An absent collection (``None``) or a present-but-non-list value yields nothing
        (existence is ``SCHEMA-0004``'s; type is ``SCHEMA-0002``'s).  Non-string
        elements are ignored.  Equality is byte-exact (ADR-0007).
        """
        if not isinstance(value, list):
            return []

        seen: set[str] = set()
        issues: list[ValidationIssue] = []
        for index, element in enumerate(value):
            if not isinstance(element, str):
                continue
            if element in seen:
                issues.append(self._duplicate_issue(analysis_result, collection, index))
            else:
                seen.add(element)
        return issues

    def _duplicate_issue(
        self, analysis_result: Any, collection: str, index: int
    ) -> ValidationIssue:
        """Build the single, fully-populated issue for one duplicate occurrence."""
        location = f"{collection}[{index}]"
        return ValidationIssue(
            issue_id=f"{self.rule_id}:{location}",
            category=self.validation_layer.value,
            severity=ValidationSeverity.ERROR,
            validation_layer=self.validation_layer,
            rule_id=self.rule_id,
            rule_version=self.rule_version,
            message=f"The requirement statement at {location} duplicates an earlier "
            f"statement in {collection!r}.",
            location=location,
            evidence=None,
            recommendation=f"Remove the duplicate requirement statement at {location} "
            f"or replace it with a distinct statement.",
            blocking=False,
            correlation_id=analysis_result.execution_id,
            created_at=utc_now(),
        )
