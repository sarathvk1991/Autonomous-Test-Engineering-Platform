"""Abstract base contract for all CP1 engineering-readiness criteria.

This module defines :class:`CP1Criterion` — the stable abstraction the CP1
:class:`~requirement_intelligence.cp1.framework.criterion_registry.CP1CriterionRegistry`
and :class:`~requirement_intelligence.cp1.framework.criterion_pipeline.CP1CriterionPipeline`
depend on.  It mirrors the Response Validation Framework's ``ValidationRule``
contract exactly, adapted to CP1.

**This module contains no engineering-readiness knowledge.**  It defines only the
*shape* of a criterion.  The concrete readiness concern, its policy, and its
judgement live in future criteria governed by the Engineering Readiness Criteria
Catalog (ADR-0012) — the catalog is currently empty, so **no criterion exists yet**.
No criterion is implemented here.

Criterion Independence
----------------------
Every conforming criterion must satisfy the same independence constraints the
platform mandates for validation rules (AI Response Validation Architecture §3.11),
so a CP1 run stays deterministic and reproducible:

1. **Deterministic** — given the same input, a criterion always produces the same
   findings; it never depends on any other criterion's output.
2. **Stateless / non-mutating** — a criterion never mutates its input, accumulates
   state between invocations, or writes to shared mutable structure.
3. **Order-independent** — because criteria neither share state nor observe each
   other, any permutation of the registered criteria yields an identical set of
   findings.  This is the prerequisite for future parallel execution.

These constraints are structural requirements of the contract (not enforced at
runtime); a criterion that violates any of them is non-conforming.

Criterion Documentation Contract
--------------------------------
Every concrete :class:`CP1Criterion` implementation (a future milestone) must
document these sections in its class docstring — a **documentation standard only**,
a conformance requirement for any criterion accepted into the framework:

1. **Purpose** — the single readiness concern the criterion judges.
2. **Criterion Identity** — its ``CP1-NNNN`` id and catalog entry.
3. **Inputs** — what part of the validated input the criterion reads.
4. **Outputs** — what findings (and verdict contribution) it can produce.
5. **Failure Conditions** — when it raises a finding.
6. **Worked Example** — a concrete ready and not-ready case.
7. **Architecture Reference** — the governing catalog section (ADR-0012).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from requirement_intelligence.cp1.framework.criterion_metadata import CP1CriterionMetadata
from requirement_intelligence.cp1.models.cp1_finding import CP1Finding

__all__ = ["CP1Criterion", "CP1CriterionMetadata"]


class CP1Criterion(ABC):
    """Abstract contract every CP1 engineering-readiness criterion must satisfy.

    A ``CP1Criterion`` encapsulates **exactly one readiness concern** and evaluates
    it against the validated input.  It is the fundamental building block of the CP1
    engine — the readiness-domain analogue of the frozen ``ValidationRule``.

    New criteria are added by implementing this class and registering the instance
    with a :class:`~requirement_intelligence.cp1.framework.criterion_registry.CP1CriterionRegistry`;
    no framework code changes.  **No such criterion exists yet** — the Engineering
    Readiness Criteria Catalog is intentionally empty (ADR-0012).

    Identity comes from metadata
    ----------------------------
    A criterion's descriptive identity lives in a single immutable
    :class:`~requirement_intelligence.cp1.framework.criterion_metadata.CP1CriterionMetadata`
    value, exposed through :attr:`metadata`.  The convenience wrappers
    (:attr:`criterion_id`, :attr:`criterion_name`, :attr:`criterion_version`,
    :attr:`enabled`) simply read from it.
    """

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def metadata(self) -> CP1CriterionMetadata:
        """Immutable descriptive identity of this criterion.

        The single source of truth for ``criterion_id``, ``criterion_name``,
        ``criterion_version``, and ``enabled``.  Must be an immutable
        :class:`CP1CriterionMetadata`.
        """

    # ------------------------------------------------------------------
    # Identity — convenience wrappers (read through :attr:`metadata`)
    # ------------------------------------------------------------------

    @property
    def criterion_id(self) -> str:
        """Stable, unique identifier for this criterion (reads :attr:`metadata`).

        Convention: ``CP1-NNNN``.  Must not change once published, because it
        appears in ``CP1Finding`` records.
        """
        return self.metadata.criterion_id

    @property
    def criterion_name(self) -> str:
        """Human-readable name for this criterion (reads :attr:`metadata`)."""
        return self.metadata.criterion_name

    @property
    def criterion_version(self) -> str:
        """The version of this criterion's definition (reads :attr:`metadata`)."""
        return self.metadata.criterion_version

    @property
    def enabled(self) -> bool:
        """Whether this criterion participates in pipeline execution (reads :attr:`metadata`).

        Disabled criteria are registered but skipped by the pipeline, allowing a
        criterion to be deactivated without unregistering it.
        """
        return self.metadata.enabled

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    @abstractmethod
    def evaluate(self, cp1_input: Any) -> list[CP1Finding]:
        """Evaluate this criterion against *cp1_input* and return findings.

        This is the sole place where a criterion's readiness judgement lives (in a
        future concrete criterion — none exists today).  It must satisfy all three
        Criterion Independence constraints (see the module docstring): deterministic,
        non-mutating, and order-independent.

        Parameters
        ----------
        cp1_input:
            The validated input the criterion reads.  Typed ``Any`` so the framework
            contract does not depend on any concrete input shape — the same generic
            signature discipline the frozen ``ValidationRule.validate`` uses.
            Criteria must treat *cp1_input* as **read-only** and must not modify it.

        Returns
        -------
        list[CP1Finding]
            An ordered list of canonical
            :class:`~requirement_intelligence.cp1.models.cp1_finding.CP1Finding`
            findings.  An empty list means this criterion observed no not-ready
            condition worth recording.

        Notes
        -----
        * **Never mutate** *cp1_input* — a criterion observes, it does not edit.
        * **Never read or write shared state** — findings from this call must not
          influence or be influenced by sibling criterion calls.
        * A criterion **contributes** a per-finding verdict; it never decides the
          overall CP1 verdict.  Aggregation is owned by the future CP1 engine
          (ADR-0012 §8), never by a criterion or by this framework.
        """
