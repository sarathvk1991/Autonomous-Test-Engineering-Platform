"""Validation → CP1 handoff seam (CAP-064).

Governing architecture: **ADR-0011 §D4** (the handoff is owned **above both
boundaries** — never by the Response Validator, never by the CP1 engine) and
**ADR-0011 §D5** (the Validation verdict gate).

This seam is **pure orchestration**.  It performs exactly two responsibilities:

1. **Gate** on the Validation verdict (§D5): only ``PASSED`` and
   ``PASSED_WITH_WARNINGS`` proceed; ``FAILED`` and ``BLOCKED`` never reach CP1.
2. **Bind** — when the gate is open — a single immutable
   :class:`~requirement_intelligence.cp1.models.cp1_input.CP1Input` referencing the
   ``ValidationResult`` and the same-execution ``NormalizationResult`` exactly once.

It **never** normalizes, validates, executes CP1, aggregates findings, builds a
``CP1Result``, evaluates criteria, judges readiness, scores, repairs, retries, logs,
reports, or persists.  It knows nothing of CP1 criteria or framework internals.  The
same-execution binding invariant is enforced by ``CP1Input``'s constructor
(ADR-0011 §D3) — this seam does not re-implement it.

Ownership (ADR-0011 §D6)
------------------------
The Validation Platform remains the owner of the ``ValidationResult``; CP1 becomes
the owner of the ``CP1Input``.  This seam owns **only the transfer**.
"""

from __future__ import annotations

from requirement_intelligence.cp1.models import CP1Input
from requirement_intelligence.normalization.models.normalization_result import (
    NormalizationResult,
)
from requirement_intelligence.validation.models import ValidationResult, ValidationVerdict

#: The governed set of Validation verdicts that permit progression to CP1
#: (ADR-0011 §D5).  No other verdict creates a ``CP1Input``.  This is the governed
#: gate set — it is **not** policy this seam invents.
CP1_ELIGIBLE_VALIDATION_VERDICTS: frozenset[ValidationVerdict] = frozenset(
    {ValidationVerdict.PASSED, ValidationVerdict.PASSED_WITH_WARNINGS}
)


class ValidationToCP1Handoff:
    """The Validation → CP1 seam — pure orchestration above both boundaries.

    **Stateless.**  It holds no data between calls; every :meth:`hand_off` call is
    independent, deterministic, and idempotent, and constructs at most one
    ``CP1Input``.  It never mutates or copies its arguments.
    """

    def hand_off(
        self,
        validation_result: ValidationResult,
        normalization_result: NormalizationResult,
    ) -> CP1Input | None:
        """Gate on the Validation verdict, then bind a single ``CP1Input``.

        Parameters
        ----------
        validation_result:
            The Validation Platform's output for the response (referenced, never
            copied).  Its ``overall_verdict`` is the gate input (§D5).
        normalization_result:
            The same-execution normalization aggregate carrying the shared
            ``ParsedResponse`` (referenced, never copied).

        Returns
        -------
        CP1Input | None
            A new immutable ``CP1Input`` binding both arguments **exactly once** when
            ``validation_result.overall_verdict`` is in
            :data:`CP1_ELIGIBLE_VALIDATION_VERDICTS`; otherwise ``None`` — the gate is
            closed and **nothing is constructed** (``FAILED`` / ``BLOCKED`` never reach
            CP1, §D5).

        Notes
        -----
        The seam neither mutates nor copies either argument; ``CP1Input`` references
        them as-is.  A same-execution mismatch is rejected by ``CP1Input``'s
        constructor (ADR-0011 §D3) and propagates unchanged — the seam adds no error
        policy of its own.
        """
        if validation_result.overall_verdict not in CP1_ELIGIBLE_VALIDATION_VERDICTS:
            return None
        return CP1Input(
            validation_result=validation_result,
            normalization_result=normalization_result,
        )
