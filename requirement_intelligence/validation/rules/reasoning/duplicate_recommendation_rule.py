"""REASONING-0002 — DuplicateRecommendationRule, the first Reasoning-layer rule.

It follows the engineering structure frozen by the **Validation Rule Implementation
Contract** and conforms to ``docs/architecture/validation-rule-catalog.md`` (§9.8,
§8.8, §14, §15); its **duplicate-comparison mechanism is frozen by ADR-0008** and it is
classified **Implementable** by **ADR-0006**.  It reads the ``ValidationInput``
introduced by ADR-0003.

Ownership (Rule Catalog §9.8; mechanism frozen by ADR-0008)
----------------------------------------------------------
This rule owns exactly one concern: *duplicate recommendation statements*.  It inspects
only the ``recommendations`` collection.  Per **ADR-0008** the comparison is **byte-exact
string equality** — case-sensitive, whitespace-sensitive, deterministic; no trimming, no
normalization, no Unicode normalization, no semantic similarity, no embeddings, no LLM
judgement, no paraphrase detection.  Semantic "duplicated conclusions" detection is a
future capability behind its own ADR and is **not** performed here.

It never validates:

* requirement duplication — that is ``CONTENT-0002`` (a different owned domain);
* empty/other requirement content (Content);
* the **existence** of ``recommendations`` — that is ``SCHEMA-0004``;
* the **type** of ``recommendations`` — that is ``SCHEMA-0002``;
* contradictions or circular logic — ``REASONING-0001`` / ``REASONING-0003``;
* semantic equivalence or paraphrase (a future capability);
* declared policy/coverage (Business).

Ownership vs ``CONTENT-0002`` (ADR-0008): the two rules share the byte-exact **mechanism**
but own **different domains** — ``CONTENT-0002`` owns duplicate *requirement* statements;
``REASONING-0002`` owns duplicate *recommendation* statements.  They never inspect the same
field, so ownership stays unique (Rule Catalog §3.1).
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

#: The single governed collection this rule inspects (Prompt Framework
#: ``JSON_RESPONSE_REQUIREMENTS``).  Fixed and governed — the shape does not vary, so it is
#: a constant, never an injected collaborator.  ``summary``, the requirement collections,
#: and ``risks`` are excluded: they are not recommendations and are not this rule's concern.
_RECOMMENDATIONS_COLLECTION = "recommendations"


class DuplicateRecommendationRule(ValidationRule):
    """Validate that no recommendation statement is duplicated.

    Purpose:
        Confirm that, within the ``recommendations`` collection, no recommendation
        statement repeats under **byte-exact** equality — its single concern (Rule
        Catalog §9.8; mechanism frozen by ADR-0008).  It never validates requirement
        duplication (``CONTENT-0002``), existence (``SCHEMA-0004``), type
        (``SCHEMA-0002``), contradictions/circularity (``REASONING-0001``/``0003``),
        semantic equivalence, or any other layer's concern.
    Layer:
        Reasoning — internal coherence / self-consistency.
    Inputs:
        The :class:`ValidationInput`, read-only (ADR-0003).  The validation decision
        reads **only** ``normalization_result.parsed_response.normalized_structure``.
        The issue's ``correlation_id`` is derived from
        ``analysis_result.execution_id`` (issue provenance) — never a functional input.
        It never reads the Normalization Outcome, observations, ``generated_text``,
        provider, ``source_reference``, or metadata.
    Outputs:
        One ``ValidationIssue`` **per duplicate occurrence** — the second and each
        subsequent byte-exact appearance of a value in ``recommendations``
        (per-occurrence, Validation Rule Implementation Contract §5), each with severity
        ``ERROR`` and ``blocking=False`` (Rule Catalog §14/§15 — Reasoning is a semantic
        layer that records and never blocks).  The first appearance is never a finding.
    Failure Conditions:
        Raises nothing for a normal validation outcome.  A duplicate is a **finding**
        (returned), never an exception.  It raises :class:`ValidationRuleError`
        **only** for an infrastructure failure — a structurally broken
        ``ValidationInput`` whose ``ParsedResponse`` is absent.
    Missing normalized structure:
        When no structure was recovered (``normalized_structure`` is ``None`` — a
        ``MALFORMED`` response Syntax owns), the rule **defers** and returns ``[]``.
    Boundary discipline:
        An absent ``recommendations`` collection is skipped (existence is
        ``SCHEMA-0004``'s).  A present-but-non-list value is skipped (type is
        ``SCHEMA-0002``'s).  A non-string element is skipped (not a recommendation
        statement).  Only a byte-exact repeated **string** is a finding.
    Worked Example:
        Pass: ``{"recommendations": ["A", "B"]}`` → ``[]``.
        Fail: ``{"recommendations": ["A", "B", "A", "A"]}`` → two findings (the second
        and third ``"A"``).
        Not a finding: ``{"recommendations": ["A", "a", "A "]}`` → ``[]`` (byte-exact,
        case- and whitespace-sensitive; ADR-0008).
    Architecture Reference:
        ``REASONING-0002``, Validation Rule Catalog §9.8; mechanism ADR-0008; layer
        §8.8; severity §14; blocking §15; capability status ADR-0006.

    Independence (Validation Rule Catalog §16; Implementation Contract §7):
        Pure, deterministic, stateless, idempotent, non-mutating, side-effect free.
        It depends only on the ``ValidationInput`` handed to :meth:`validate`, never
        on another rule.  It normalizes nothing and repairs nothing.
    """

    #: Identity is fixed at definition and shared on every access (frozen value).
    _METADATA = ValidationRuleMetadata(
        rule_id="REASONING-0002",
        rule_name="Duplicate Recommendation",
        validation_layer=ValidationLayer.REASONING,
    )

    @property
    def metadata(self) -> ValidationRuleMetadata:
        """The rule's immutable identity (see Validation Rule Catalog §9.8)."""
        return self._METADATA

    def validate(self, response: Any) -> list[ValidationIssue]:
        """Return one finding per byte-exact duplicate recommendation occurrence.

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
                "REASONING-0002: the NormalizationResult carries no ParsedResponse; "
                "the normalized structure cannot be read."
            )

        normalized_structure = parsed_response.normalized_structure
        if normalized_structure is None:
            # No structure was recovered (a MALFORMED response). Well-formedness is
            # Syntax's concern; Reasoning defers.
            return []

        value = normalized_structure.get(_RECOMMENDATIONS_COLLECTION)
        if not isinstance(value, list):
            # Absent collection (existence is SCHEMA-0004's) or a non-list value (type is
            # SCHEMA-0002's) — neither is this rule's concern.
            return []

        analysis_result = response.analysis_result
        seen: set[str] = set()
        issues: list[ValidationIssue] = []
        for index, element in enumerate(value):
            if not isinstance(element, str):
                continue
            if element in seen:  # byte-exact equality (ADR-0008)
                issues.append(self._duplicate_issue(analysis_result, index))
            else:
                seen.add(element)
        return issues

    def _duplicate_issue(self, analysis_result: Any, index: int) -> ValidationIssue:
        """Build the single, fully-populated issue for one duplicate occurrence."""
        location = f"{_RECOMMENDATIONS_COLLECTION}[{index}]"
        return ValidationIssue(
            issue_id=f"{self.rule_id}:{location}",
            category=self.validation_layer.value,
            severity=ValidationSeverity.ERROR,
            validation_layer=self.validation_layer,
            rule_id=self.rule_id,
            rule_version=self.rule_version,
            message=f"The recommendation at {location} duplicates an earlier "
            f"recommendation in {_RECOMMENDATIONS_COLLECTION!r}.",
            location=location,
            evidence=None,
            recommendation=f"Remove the duplicate recommendation at {location} "
            f"or replace it with a distinct recommendation.",
            blocking=False,
            correlation_id=analysis_result.execution_id,
            created_at=utc_now(),
        )
