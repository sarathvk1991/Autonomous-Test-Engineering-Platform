"""CP1-0001 — EngineeringInputAvailabilityCriterion (CAP-067A).

The first engineering-readiness criterion, governed by **ADR-0013 (Accepted)** and the
**Engineering Readiness Criteria Catalog** §9.1.  It owns exactly one concern —
**Engineering Input Availability** — and answers *"Can downstream engineering begin?"*,
never *"Is the artifact valid?"* (Validation owns artifact correctness; ADR-0013 §D6).

Deterministic evaluation (ADR-0013 §D2)
---------------------------------------
Pool the three governed requirement collections — ``functional_requirements``,
``security_requirements``, ``quality_requirements`` — in the normalized structure and
count total elements:

* count ≥ 1 → **PASS** (engineering input exists): **no finding**.
* count == 0 → **FAIL** (no engineering input exists): **exactly one** ``CP1Finding``.

Pure element counting — deterministic, stateless, idempotent, thread-safe, and
**non-mutating**.  No semantics, NLP, LLM, "quality", "coverage", weighting, ``WARN``,
or threshold other than ≥ 1.  It **never** aggregates (the engine does; ADR-0012 §8),
reports, persists, accesses PlatformContext/CLI, or reads the Validation subsystem's
logic.  It consumes only ``CP1Input`` through public attributes.
"""

from __future__ import annotations

from typing import Any

from requirement_intelligence.cp1.framework import CP1Criterion, CP1CriterionMetadata
from requirement_intelligence.cp1.models import CP1Finding
from shared.enums.base import ValidationVerdict
from shared.utils.ids import utc_now

#: The three governed **requirement** collections (Prompt Framework
#: ``JSON_RESPONSE_REQUIREMENTS``; the set ADR-0007 fixed for ``CONTENT-0002``).
#: ``summary``, ``risks``, and ``recommendations`` are not requirements and are excluded.
_REQUIREMENT_COLLECTIONS: tuple[str, ...] = (
    "functional_requirements",
    "security_requirements",
    "quality_requirements",
)

#: The exact accepted recommendation wording (ADR-0013 §D5).
_RECOMMENDATION = (
    "The validated response contains no engineering requirements. Add at least one "
    "functional, security, or quality requirement before downstream engineering can begin."
)


class EngineeringInputAvailabilityCriterion(CP1Criterion):
    """CP1-0001 — is there engineering input from which downstream engineering may begin?

    Single concern: **Engineering Input Availability** (ADR-0013 §D1).  Deterministic
    pooled requirement count ≥ 1 → PASS (no finding); == 0 → FAIL (one finding).
    """

    #: Immutable identity, fixed at definition and shared on every access.
    _METADATA = CP1CriterionMetadata(
        criterion_id="CP1-0001",
        criterion_name="EngineeringInputAvailabilityCriterion",
        criterion_version="1.0.0",
    )

    @property
    def metadata(self) -> CP1CriterionMetadata:
        """The criterion's immutable identity (Catalog §9.1)."""
        return self._METADATA

    def evaluate(self, cp1_input: Any) -> list[CP1Finding]:
        """Return no finding when engineering input exists, else exactly one FAIL finding.

        Reads only ``cp1_input`` (the normalized structure and the correlation id),
        read-only.  It never mutates the input, never aggregates, and never reads the
        Validation subsystem's logic.
        """
        if self._pooled_requirement_count(self._normalized_structure(cp1_input)) >= 1:
            return []
        return [self._no_engineering_input_finding(cp1_input)]

    @staticmethod
    def _normalized_structure(cp1_input: Any) -> Any:
        """The normalized structure reached through ``CP1Input`` (``None`` if absent)."""
        parsed_response = cp1_input.normalization_result.parsed_response
        if parsed_response is None:
            return None
        return parsed_response.normalized_structure

    @staticmethod
    def _pooled_requirement_count(normalized_structure: Any) -> int:
        """Total element count across the three governed requirement collections.

        Deterministic and defensive: a non-mapping structure, an absent collection, or a
        present-but-non-list value contributes zero — no policy is invented.
        """
        if not isinstance(normalized_structure, dict):
            return 0
        total = 0
        for collection in _REQUIREMENT_COLLECTIONS:
            value = normalized_structure.get(collection)
            if isinstance(value, list):
                total += len(value)
        return total

    def _no_engineering_input_finding(self, cp1_input: Any) -> CP1Finding:
        """Build the single FAIL finding (ADR-0013 §D4/§D5)."""
        return CP1Finding(
            finding_id=f"{self.criterion_id}:no-engineering-input",
            criterion_id=self.criterion_id,
            criterion_version=self.criterion_version,
            verdict_contribution=ValidationVerdict.FAIL,
            message=(
                "No engineering input exists: the validated response contains no "
                "requirements across functional_requirements, security_requirements, "
                "or quality_requirements."
            ),
            location="functional_requirements+security_requirements+quality_requirements",
            evidence="pooled requirement count: 0",
            recommendation=_RECOMMENDATION,
            correlation_id=cp1_input.validation_result.execution_id,
            created_at=utc_now(),
        )
