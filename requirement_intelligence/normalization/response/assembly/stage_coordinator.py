"""The internal stage coordinator — the execution engine for the assembly stages.

:class:`NormalizationStageCoordinator` is the permanent execution engine that
coordinates the internal normalization stages (``NORMALIZATION-0001 … 0005``)
inside the ``ResponseNormalizer`` boundary.  It realises the assembly **lifecycle**
governed by the Normalization Assembly Contract (§5): create the Assembly State,
execute the stages in order over it, and dispose of it once execution completes.

Where it lives (ADR-0002)
-------------------------
The coordinator lives **entirely inside the ``ResponseNormalizer`` boundary** — in
the ``assembly`` package alongside the stages and the Assembly State.  It is **not**
part of the generic Response Normalization Framework, and the framework's
:class:`~requirement_intelligence.normalization.framework.normalization_pipeline.NormalizationPipeline`
is unaware of it.

Not the framework pipeline
--------------------------
The coordinator is **structurally similar** to the framework pipeline (both invoke
a sequence of units) but **semantically distinct** (ADR-0002):

* the framework pipeline executes **generic, order-independent**
  ``NormalizationResponsibility`` units that share no state and produce
  observations aggregated into a ``NormalizationResult``;
* the coordinator executes **forward-dependent stages** that share one
  :class:`~requirement_intelligence.normalization.response.assembly.assembly_state.AssemblyState`
  and, together, will produce the ``ParsedResponse`` (assembled by stage
  ``0005`` — not by the coordinator).

The coordinator therefore **duplicates no framework behaviour**; it provides the
internal-stage engine the framework deliberately does not.

What it owns — and does not
---------------------------
Owns: stage ordering (the *supplied* order — it never sorts), stage invocation,
the Assembly State lifecycle (create → execute → dispose), stage execution, and
exception propagation.

Does **not** own: normalization logic, parsing, validation, ``ParsedResponse``
assembly, observations, or the framework lifecycle.  It never inspects a stage's
internals, interprets a stage's output, or mutates the ``LLMResponse``.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeVar

from requirement_intelligence.llm.llm_models import LLMResponse
from requirement_intelligence.normalization.response.assembly.assembly_state import (
    AssemblyState,
)
from requirement_intelligence.normalization.response.assembly.normalization_stage import (
    NormalizationStage,
)
from requirement_intelligence.normalization.response.assembly.stage_exceptions import (
    StageCoordinationError,
)

#: The type a caller's consumer extracts from the completed Assembly State.
_T = TypeVar("_T")


class NormalizationStageCoordinator:
    """Coordinates the sequential execution of internal normalization stages.

    The coordinator is assembled by **constructor injection**: it executes exactly
    the stages it is given, in exactly the order it is given.  It holds **no**
    registry, singleton, reflection, discovery, or global state, so the same
    coordinator can run any stage list and is fully reusable.

    Parameters
    ----------
    stages:
        The ordered stages to execute.  Each must be a
        :class:`~requirement_intelligence.normalization.response.assembly.normalization_stage.NormalizationStage`.
        The sequence is captured as an **immutable tuple** in the supplied order;
        the coordinator never reorders or sorts it (preserving the frozen assembly
        chain — ADR-0002; Assembly Contract §5).

    Raises
    ------
    StageCoordinationError
        If any supplied element is not a ``NormalizationStage`` (a wiring error,
        never a normalization fact).
    """

    def __init__(self, stages: Sequence[NormalizationStage]) -> None:
        for index, stage in enumerate(stages):
            if not isinstance(stage, NormalizationStage):
                raise StageCoordinationError(
                    f"NormalizationStageCoordinator requires every element to be a "
                    f"NormalizationStage; element {index} is "
                    f"{type(stage).__name__!r}."
                )
        # Captured in supplied order; never reordered.
        self._stages: tuple[NormalizationStage, ...] = tuple(stages)

    @property
    def stages(self) -> tuple[NormalizationStage, ...]:
        """The injected stages, in the supplied (execution) order."""
        return self._stages

    def coordinate(
        self,
        llm_response: LLMResponse,
        consumer: Callable[[AssemblyState], _T],
    ) -> _T:
        """Run the stages over a fresh Assembly State and return the consumer's result.

        Lifecycle (Assembly Contract §5):

        1. **Create** a fresh, execution-local
           :class:`~requirement_intelligence.normalization.response.assembly.assembly_state.AssemblyState`.
        2. **Execute** each stage **once**, in the supplied order, passing the
           *same* ``LLMResponse`` and the *same* Assembly State.  An exception from
           any stage **stops execution immediately** and propagates unchanged — the
           coordinator never retries, never continues, and never swallows it (a
           stage's infrastructure failure is never a normalization fact — Assembly
           Contract §8).
        3. **Extract** the products by handing the completed Assembly State to
           *consumer* — the caller's in-boundary extraction (e.g. building the
           ``ParsedResponse`` / observations).  The coordinator itself never
           assembles a ``ParsedResponse`` or interprets any fact.
        4. **Dispose** — the coordinator retains **no** reference to the Assembly
           State after this call; it is execution-local and never cached, reused,
           stored, or returned raw.  The raw Assembly State never escapes the
           coordinator (only *consumer*'s result does — Assembly Contract §9).

        Parameters
        ----------
        llm_response:
            The provider-independent ``LLMResponse`` under normalization, passed to
            each stage unchanged.  The coordinator never mutates it.
        consumer:
            A caller-supplied function that reads the completed Assembly State and
            returns the products the caller needs.  It must extract what it needs
            and **not retain** the Assembly State (Assembly Contract §9).

        Returns
        -------
        The value returned by *consumer* — never the raw Assembly State.

        Raises
        ------
        Exception
            Any exception raised by a stage propagates unchanged; the remaining
            stages are not executed and *consumer* is not called.
        """
        # 1. Create.
        assembly_state = AssemblyState()

        # 2. Execute in supplied order; a stage exception stops the run immediately.
        for stage in self._stages:
            stage.execute(llm_response, assembly_state)

        # 3. Extract products within the boundary. 4. Dispose: the local reference
        # is dropped when this method returns; the coordinator keeps no state.
        return consumer(assembly_state)
