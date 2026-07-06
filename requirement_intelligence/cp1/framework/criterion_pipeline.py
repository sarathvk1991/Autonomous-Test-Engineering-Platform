"""CP1 criterion pipeline — orchestrates CP1Criterion execution.

The ``CP1CriterionPipeline`` is the single point of execution for the CP1 engine
framework.  It receives a
:class:`~requirement_intelligence.cp1.framework.criterion_registry.CP1CriterionRegistry`,
asks it for the ordered set of enabled criteria, invokes each against the validated
input, and **collects their findings**.

Deliberate boundary — collection, not aggregation
-------------------------------------------------
This pipeline mirrors the frozen ``ValidationPipeline`` in *structure* (orchestration
only, deterministic ordering, observable-but-inert state, empty run is valid) but is
**intentionally thinner in one respect**:

* The ``ValidationPipeline`` derives an overall *verdict* ("highest severity wins").
* The ``CP1CriterionPipeline`` derives **no verdict** and assembles **no
  ``CP1Result``**.  Aggregating criterion findings into the single CP1 verdict is
  **owned by the future CP1 engine, never by any criterion or by this framework**
  (Engineering Readiness Criteria Catalog §8; ADR-0012).  Producing a verdict here
  would be an engineering-readiness policy decision, which the framework must not
  make.

Therefore :meth:`run` returns the **ordered collection of findings** only.  The
framework knows *how to run criteria deterministically*; it knows **nothing about
engineering readiness**.

Design notes
------------
* **Orchestration only.**  No readiness logic, no policy, no scoring, no thresholds.
* **Deterministic ordering.**  The pipeline trusts the registry for ordering (flat
  registration order — CP1 has no layers) and never re-sorts.
* **Empty run is valid.**  With no criteria registered, :meth:`run` returns an empty
  tuple — a valid execution, not a placeholder.
* **Future parallel execution.**  Criterion Independence guarantees that evaluating
  criteria concurrently cannot change the finding set; the current implementation is
  sequential and the contract is stable for a future concurrent one.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from requirement_intelligence.cp1.framework.criterion import CP1Criterion
from requirement_intelligence.cp1.framework.criterion_registry import CP1CriterionRegistry
from requirement_intelligence.cp1.framework.framework_exceptions import CP1PipelineError
from requirement_intelligence.cp1.framework.framework_metadata import (
    CP1_FRAMEWORK_VERSION,
    CP1_PIPELINE_VERSION,
    CP1_REGISTRY_VERSION,
    DEFAULT_CP1_CRITERIA_CONTRACT_VERSION,
    CP1FrameworkMetadata,
)
from requirement_intelligence.cp1.models.cp1_finding import CP1Finding


class CP1PipelineState(Enum):
    """Observable lifecycle state of a :class:`CP1CriterionPipeline`.

    The state is **informational only** — it is exposed for observability and never
    influences behaviour.  The pipeline never branches on it, and the findings a run
    produces are identical regardless of how the state is read.

    ::

        (construct) ─► CREATED ─► READY ─► RUNNING ─► COMPLETED ─► RUNNING ...
                                              │
                                              └─► FAILED ─► RUNNING ...

        DISPOSED is reserved and is not entered by any current transition.
    """

    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DISPOSED = "disposed"  # reserved — no current transition enters this state


class CP1CriterionPipeline:
    """Orchestrates the execution of registered :class:`CP1Criterion` instances.

    The pipeline is the only component that calls ``criterion.evaluate()``.  All
    other components interact with it through :meth:`run`, which returns the ordered
    collection of findings — **never** a verdict or a ``CP1Result``.
    """

    def __init__(self, registry: CP1CriterionRegistry) -> None:
        """Construct the pipeline from a populated registry.

        Parameters
        ----------
        registry:
            The :class:`CP1CriterionRegistry` that supplies the ordered criterion
            set.  Construction **seals** the registry: criteria cannot be registered
            afterwards, which fixes the pipeline's criterion set for its lifetime.

        Raises
        ------
        CP1PipelineError
            If *registry* is not a :class:`CP1CriterionRegistry` instance.
        """
        self._state: CP1PipelineState = CP1PipelineState.CREATED
        if not isinstance(registry, CP1CriterionRegistry):
            raise CP1PipelineError(
                f"CP1CriterionPipeline requires a CP1CriterionRegistry instance; "
                f"got {type(registry).__name__!r}."
            )
        self._registry = registry
        # Sealing the registry freezes the criterion set for this pipeline's lifetime.
        self._registry.seal()
        self._state = CP1PipelineState.READY

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def state(self) -> CP1PipelineState:
        """The current observable :class:`CP1PipelineState` (informational only)."""
        return self._state

    # ------------------------------------------------------------------
    # Provenance
    # ------------------------------------------------------------------

    def framework_metadata(self) -> CP1FrameworkMetadata:
        """Return the immutable provenance of this framework.

        Pure version provenance for the future CP1 engine to stamp onto a
        ``CP1Result``; it carries no findings and no verdict.
        """
        return CP1FrameworkMetadata(
            framework_version=CP1_FRAMEWORK_VERSION,
            criteria_contract_version=DEFAULT_CP1_CRITERIA_CONTRACT_VERSION,
            pipeline_version=CP1_PIPELINE_VERSION,
            registry_version=CP1_REGISTRY_VERSION,
        )

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    def get_ordered_criteria(self) -> list[CP1Criterion]:
        """Return the ordered set of enabled criteria the pipeline will execute.

        Returns
        -------
        list[CP1Criterion]
            Enabled criteria in deterministic registration order.
        """
        return self._registry.get_enabled_criteria()

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def run(self, cp1_input: Any) -> tuple[CP1Finding, ...]:
        """Execute every enabled criterion against *cp1_input* and collect findings.

        Criteria are executed in the order returned by :meth:`get_ordered_criteria`,
        each receiving the *same* ``cp1_input`` unchanged.  Their findings are
        collected in order and returned as an immutable tuple.

        This method derives **no verdict** and assembles **no ``CP1Result``** — the
        framework collects findings; the future CP1 engine aggregates them into a
        verdict (ADR-0012 §8).  An **empty run** — no criteria registered, or zero
        findings produced — returns an empty tuple and is a valid execution.

        Parameters
        ----------
        cp1_input:
            The validated input, passed unchanged to each criterion.  Typed ``Any``
            so the framework stays input-shape-agnostic; the pipeline never inspects
            or mutates it.

        Returns
        -------
        tuple[CP1Finding, ...]
            The ordered collection of findings the criteria produced (possibly empty).

        Raises
        ------
        Any exception raised by a criterion propagates unchanged after the pipeline
        records the :attr:`CP1PipelineState.FAILED` state — a criterion contract
        failure is an infrastructure error, never a readiness verdict.
        """
        self._state = CP1PipelineState.RUNNING
        try:
            findings: list[CP1Finding] = []
            for criterion in self.get_ordered_criteria():
                findings.extend(criterion.evaluate(cp1_input))
        except BaseException:
            # State is observational; record the failure and re-raise unchanged.
            self._state = CP1PipelineState.FAILED
            raise
        self._state = CP1PipelineState.COMPLETED
        return tuple(findings)
