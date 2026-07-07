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

Defensive robustness ≠ engineering-readiness policy
---------------------------------------------------
Under the governed **Validation → CP1 handoff (ADR-0011 §D5)**, CP1 runs **only** on
responses the seam admitted (verdict ``PASSED`` / ``PASSED_WITH_WARNINGS``), which
**guarantees a ``NORMALIZED`` structure is present** (ADR-0013 §D3).  A malformed or
absent normalized structure is therefore **not expected to reach this criterion** — it
is impossible under the governed handoff, not a governed input case.

Where this module nonetheless copes with a non-mapping structure, an absent parsed
response, or an absent collection (each contributing zero to the pooled count), that is
**defensive programming only** — implementation robustness against a state the seam
already precludes.  It is deliberately **not** an engineering-readiness policy: the
criterion invents no readiness rule for malformed input; it simply treats engineering
input as *absent* and lets the one governed policy — the ≥ 1 availability floor (ADR-0013
§D2/§D4) — decide the verdict, exactly as it would for a well-formed empty response.  The
single governed readiness policy is the availability floor and nothing else.
"""

from __future__ import annotations

from typing import Any

from requirement_intelligence.cp1.framework import CP1Criterion, CP1CriterionMetadata
from requirement_intelligence.cp1.models import CP1Finding
from shared.enums.base import ValidationVerdict
from shared.utils.ids import new_id, utc_now

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

        The **only** governed readiness policy applied here is the ≥ 1 availability
        floor (ADR-0013 §D2/§D4).  Under the governed Validation → CP1 handoff
        (ADR-0011 §D5) the normalized structure is always present, so any handling of a
        malformed or absent structure below is **defensive robustness, not readiness
        policy** — see the module docstring.
        """
        if self._pooled_requirement_count(self._normalized_structure(cp1_input)) >= 1:
            return []
        return [self._no_engineering_input_finding(cp1_input)]

    @staticmethod
    def _normalized_structure(cp1_input: Any) -> Any:
        """The normalized structure reached through ``CP1Input`` (``None`` if absent).

        The governed handoff (ADR-0011 §D5) guarantees a present structure, so the
        ``None`` branch is **defensive only** — never an expected readiness-policy path.
        """
        parsed_response = cp1_input.normalization_result.parsed_response
        if parsed_response is None:
            return None
        return parsed_response.normalized_structure

    @staticmethod
    def _pooled_requirement_count(normalized_structure: Any) -> int:
        """Total element count across the three governed requirement collections.

        Deterministic.  A non-mapping structure, an absent collection, or a
        present-but-non-list value contributes zero.  That tolerance is **defensive
        robustness, not engineering-readiness policy**: such structures cannot arise
        under the governed Validation → CP1 handoff (ADR-0011 §D5), and no readiness
        rule is invented for them — they simply yield a pooled count of zero, which the
        one governed policy (the ≥ 1 availability floor) then evaluates.
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
        """Build the single FAIL finding (ADR-0013 §D4/§D5).

        Identity ownership is kept strictly separated (no meaning is duplicated):

        * ``finding_id`` — the **occurrence** identity of *this* finding, minted from
          the repository's canonical shared generator (:func:`shared.utils.ids.new_id`,
          the same mechanism the CP1 engine uses for ``cp1_id``).  It identifies the
          single finding occurrence, nothing more, and is deliberately **not** derived
          from ``CP1-0001`` — the criterion identity already lives in ``criterion_id``.
        * ``criterion_id`` — the **criterion** identity (``CP1-0001``).
        * ``correlation_id`` — the **execution** correlation (the validation run).
        """
        return CP1Finding(
            finding_id=new_id(),
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
