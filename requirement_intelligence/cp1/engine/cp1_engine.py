"""CP1 Engine (CAP-065).

The CP1 Engine is the **"Aggregate Result"** stage of the CP1 pattern (ADR-0011 §D7).
It **executes the registered governed criteria** (via the ``CP1CriterionPipeline`` it
is given) exactly once and **aggregates their findings into the overall CP1 verdict**,
assembling the single :class:`~requirement_intelligence.cp1.models.cp1_result.CP1Result`.

Orchestration only
------------------
The engine owns orchestration and the **governed verdict aggregation** (ADR-0012 §8)
— and nothing else.  **Criteria own engineering policy; the engine owns orchestration
only.**  It knows no individual criterion; it contains no readiness logic, no
threshold, no heuristic, no scoring, and no engineering/business policy.  It performs
**no** registration, builds **no** registry or pipeline (that is the composition root
— a later milestone), and does **no** CLI, PlatformContext, reporting, persistence,
repair, normalization, or validation.

Determinism, statelessness, thread-safety
-----------------------------------------
The engine holds **no state**; every :meth:`run` call is independent and thread-safe.
Given the same ``CP1Input`` and the same criterion set, it produces the **same
findings and the same verdict**.  The run identity (``cp1_id``) and the wall-clock
timestamps are per-run **provenance** (as in the Validation pipeline), not part of the
deterministic judgement.
"""

from __future__ import annotations

from collections.abc import Sequence

from requirement_intelligence.cp1.framework import CP1CriterionPipeline
from requirement_intelligence.cp1.models import CP1Finding, CP1Input, CP1Result
from shared.enums.base import ValidationVerdict
from shared.utils.ids import new_id, utc_now


class CP1Engine:
    """Stateless orchestrator: execute the criterion pipeline once, aggregate, assemble.

    Holds no state; every :meth:`run` call is independent, deterministic (in its
    findings and verdict), and thread-safe.  It never constructs a registry or
    pipeline — it consumes a pipeline it is handed.
    """

    def run(self, cp1_input: CP1Input, pipeline: CP1CriterionPipeline) -> CP1Result:
        """Execute *pipeline* over *cp1_input* **once** and assemble the ``CP1Result``.

        The engine runs the pipeline a single time to collect the ordered
        ``tuple[CP1Finding, …]``, reads the framework provenance, aggregates the
        findings into the overall verdict (:meth:`_derive_verdict`), and assembles the
        immutable ``CP1Result`` — **preserving** the ``CP1Input`` (referenced, never
        mutated) and the ``CP1FrameworkMetadata``.

        Parameters
        ----------
        cp1_input:
            The validated input (referenced, never copied or mutated).  Its
            ``ValidationResult`` supplies the correlation identities carried on the
            result.
        pipeline:
            The ``CP1CriterionPipeline`` supplying the governed criteria.  The engine
            executes it exactly once; it does **not** build or seal it.

        Returns
        -------
        CP1Result
            The single immutable aggregate output of the CP1 run.

        Notes
        -----
        An exception raised by a criterion propagates unchanged (an infrastructure
        error, never a verdict) — the engine adds no error policy of its own.
        """
        started_at = utc_now()
        findings = pipeline.run(cp1_input)
        framework_metadata = pipeline.framework_metadata()
        completed_at = utc_now()

        validation_result = cp1_input.validation_result
        return CP1Result(
            cp1_id=new_id(),
            validation_id=validation_result.validation_id,
            execution_id=validation_result.execution_id,
            analysis_id=validation_result.analysis_id,
            cp1_input=cp1_input,
            findings=findings,
            framework_metadata=framework_metadata,
            overall_verdict=self._derive_verdict(findings),
            started_at=started_at,
            completed_at=completed_at,
        )

    @staticmethod
    def _derive_verdict(findings: Sequence[CP1Finding]) -> ValidationVerdict:
        """Aggregate finding contributions into the overall CP1 verdict (ADR-0012 §8).

        The **only** governed aggregation — deterministic and order-independent, with
        **no** scoring, weighting, thresholds, percentages, ranking, or heuristics:

        * any finding contributes ``FAIL``  → ``FAIL``
        * else any finding contributes ``WARN`` → ``WARN``
        * else (all ``PASS``, or an empty finding set) → ``PASS``
        """
        if any(f.verdict_contribution == ValidationVerdict.FAIL for f in findings):
            return ValidationVerdict.FAIL
        if any(f.verdict_contribution == ValidationVerdict.WARN for f in findings):
            return ValidationVerdict.WARN
        return ValidationVerdict.PASS
