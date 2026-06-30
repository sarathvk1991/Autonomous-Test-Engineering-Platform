"""Normalization pipeline — orchestrates NormalizationResponsibility execution.

The NormalizationPipeline is the single point of execution for the Response
Normalization Layer's responsibilities.  It receives a
:class:`~requirement_intelligence.normalization.framework.normalization_registry.NormalizationRegistry`,
asks it for the ordered set of enabled responsibilities, invokes each against the
normalization source, collects the recorded observations, and assembles them into
the canonical
:class:`~requirement_intelligence.normalization.models.normalization_result.NormalizationResult`.

Design notes
------------
* **Orchestration only.**  The pipeline contains **no normalization logic, no
  parsing, no provider knowledge, no validation, and no business rules**.  It
  delegates all behaviour to the responsibilities it executes — exactly as the
  validation pipeline delegates to rules.

* **Deterministic ordering.**  The pipeline trusts the registry for ordering
  (registration order — there are no layers) and never re-sorts.

* **Facts, not judgments.**  Assembling the
  :class:`~requirement_intelligence.normalization.models.normalization_result.NormalizationResult`
  is pure aggregation over the observations the responsibilities recorded.  Unlike
  the validation pipeline there is **no verdict, no summary, and no severity** to
  derive — normalization produces facts, not judgments (Response Normalization
  Contract §10).

* **NormalizationResult is the permanent contract.**  :meth:`run` *always*
  returns a fully-populated ``NormalizationResult`` — including when no
  responsibilities are registered or zero observations are produced.  An empty
  result is a valid execution, not a placeholder: its statistics and framework
  metadata are still populated.

* **The ParsedResponse placeholder.**  The result's ``parsed_response`` field is
  always ``None`` in this Phase-1 framework.  Producing a ``ParsedResponse`` is
  the future ``ResponseNormalizer``'s job, not the framework's; the field exists
  now only to keep the result's API stable until the model lands.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from requirement_intelligence.normalization.framework.normalization_exceptions import (
    NormalizationPipelineError,
)
from requirement_intelligence.normalization.framework.normalization_registry import (
    NormalizationRegistry,
)
from requirement_intelligence.normalization.framework.normalization_responsibility import (
    NormalizationResponsibility,
)
from requirement_intelligence.normalization.models import (
    FRAMEWORK_VERSION,
    PIPELINE_VERSION,
    REGISTRY_VERSION,
    RESPONSIBILITY_CATALOG_VERSION,
    NormalizationConfiguration,
    NormalizationFrameworkMetadata,
    NormalizationObservation,
    NormalizationResult,
    NormalizationStatistics,
)
from shared.utils.ids import new_id, utc_now


class PipelineState(Enum):
    """Observable lifecycle state of a :class:`NormalizationPipeline`.

    The state is **informational only**.  It is exposed for observability and
    debugging; it **never** influences normalization behaviour.  No branching
    decision inside the pipeline is taken on its basis, and the observations a run
    produces are identical regardless of how the state is read.

    Members
    -------
    CREATED
        The pipeline object is being constructed but is not yet ready.
    READY
        Construction succeeded; the registry has been sealed and the ordered
        responsibility set is available.
    RUNNING
        A :meth:`NormalizationPipeline.run` call is in progress.
    COMPLETED
        The most recent :meth:`run` call finished successfully.
    FAILED
        The most recent :meth:`run` call raised before completing.
    DISPOSED
        Reserved for a future explicit teardown step.  Not entered by any current
        transition.

    Transitions
    -----------
    ::

        (construct) ─► CREATED ─► READY ─► RUNNING ─► COMPLETED ─► RUNNING ...
                                              │
                                              └─► FAILED ─► RUNNING ...
    """

    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DISPOSED = "disposed"  # reserved — no current transition enters this state


class NormalizationPipeline:
    """Orchestrates the execution of registered
    :class:`~requirement_intelligence.normalization.framework.normalization_responsibility.NormalizationResponsibility`
    instances against a normalization source.

    The pipeline is the only component that calls
    ``responsibility.normalize()``.  All other components interact through
    :meth:`run`.

    Usage
    -----
    .. code-block:: python

        registry = NormalizationRegistry()
        registry.register(MyResponsibility())

        pipeline = NormalizationPipeline(registry)
        result = pipeline.run(source)
    """

    def __init__(self, registry: NormalizationRegistry) -> None:
        """Construct the pipeline from a populated registry.

        Parameters
        ----------
        registry:
            The :class:`NormalizationRegistry` that supplies the ordered
            responsibility set.  Construction **seals** the registry: nothing can
            be registered afterwards, which guarantees the pipeline's
            responsibility set is fixed for its lifetime.

        Raises
        ------
        NormalizationPipelineError
            If *registry* is not a :class:`NormalizationRegistry` instance.
        """
        self._state: PipelineState = PipelineState.CREATED
        if not isinstance(registry, NormalizationRegistry):
            # Stay in CREATED; construction never reached READY.
            raise NormalizationPipelineError(
                f"NormalizationPipeline requires a NormalizationRegistry instance; "
                f"got {type(registry).__name__!r}."
            )
        self._registry = registry
        # Sealing the registry freezes the responsibility set for this lifetime.
        self._registry.seal()
        self._state = PipelineState.READY

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def state(self) -> PipelineState:
        """The current observable :class:`PipelineState` (informational only)."""
        return self._state

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    def get_ordered_responsibilities(self) -> list[NormalizationResponsibility]:
        """Return the ordered set of enabled responsibilities the pipeline will run.

        Returns them in registration order (there are no layers to sort by).

        Returns
        -------
        list[NormalizationResponsibility]
            Enabled responsibilities in deterministic pipeline order.
        """
        return self._registry.get_enabled_responsibilities()

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def run(
        self,
        source: Any,
        configuration: NormalizationConfiguration | None = None,
        *,
        correlation_id: str | None = None,
    ) -> NormalizationResult:
        """Normalize *source* and return the canonical ``NormalizationResult``.

        Each enabled responsibility is executed in the order returned by
        :meth:`get_ordered_responsibilities`, receiving *source* unchanged.  The
        observations they record are collected, telemetry is gathered, and
        everything is assembled into a single immutable ``NormalizationResult``.

        This is the **permanent framework contract**.  The method *always* returns
        a fully-populated ``NormalizationResult``:

        * With **no responsibilities registered** or **zero observations
          recorded**, the result is still valid — its statistics and framework
          metadata are populated.
        * ``parsed_response`` is **always ``None``** here: the framework produces
          no ``ParsedResponse`` (that is the future ``ResponseNormalizer``'s job).

        The pipeline never inspects, parses, repairs, or mutates *source*; it
        passes it to each responsibility unchanged.

        Parameters
        ----------
        source:
            The normalization input (an ``LLMResponse`` in production, per Response
            Normalization Contract §4.1).  Typed ``Any`` so the framework does not
            couple to any concrete input shape, provider, or format.
        configuration:
            The execution policy that governs the run.  When omitted, a
            fully-defaulted :class:`NormalizationConfiguration` is used.
        correlation_id:
            Optional trace key stitching this run to its originating analysis and
            downstream consumers.  Carried onto the statistics and result.

        Returns
        -------
        NormalizationResult
            The single, immutable output of the framework — always populated.

        Raises
        ------
        NormalizationPipelineError
            If *source* is ``None`` (there is nothing to normalize).

        Any exception raised by a responsibility propagates unchanged after the
        pipeline records the :attr:`PipelineState.FAILED` state — a responsibility
        contract failure is an infrastructure error, never a normalization fact.
        """
        if source is None:
            raise NormalizationPipelineError(
                "NormalizationPipeline.run requires a non-None source to normalize."
            )

        config = (
            configuration if configuration is not None else NormalizationConfiguration()
        )

        self._state = PipelineState.RUNNING
        started_at = utc_now()
        try:
            observations: list[NormalizationObservation] = []
            responsibilities_executed = 0
            for responsibility in self.get_ordered_responsibilities():
                responsibilities_executed += 1
                recorded = responsibility.normalize(source)
                if recorded:
                    observations.extend(recorded)
        except BaseException:
            # State is observational; record the failure and re-raise the original
            # exception unchanged so existing error handling is unaffected.
            self._state = PipelineState.FAILED
            raise
        completed_at = utc_now()

        result = self._assemble_result(
            configuration=config,
            observations=observations,
            responsibilities_executed=responsibilities_executed,
            started_at=started_at,
            completed_at=completed_at,
            correlation_id=correlation_id,
        )
        self._state = PipelineState.COMPLETED
        return result

    # ------------------------------------------------------------------
    # Result assembly (pure aggregation — no judgement, no ParsedResponse)
    # ------------------------------------------------------------------

    def _assemble_result(
        self,
        *,
        configuration: NormalizationConfiguration,
        observations: list[NormalizationObservation],
        responsibilities_executed: int,
        started_at: datetime,
        completed_at: datetime,
        correlation_id: str | None,
    ) -> NormalizationResult:
        """Assemble the canonical ``NormalizationResult`` from recorded observations.

        Pure aggregation: counts the observations, records telemetry, and stamps
        framework provenance.  No verdict, summary, or severity is derived — and
        no ``ParsedResponse`` is created (``parsed_response`` stays ``None``).
        """
        normalization_id = new_id()
        duration_ms = (completed_at - started_at).total_seconds() * 1000.0

        statistics = NormalizationStatistics(
            normalization_duration_ms=duration_ms,
            responsibilities_executed=responsibilities_executed,
            observations_recorded=len(observations),
            started_at=started_at,
            completed_at=completed_at,
            framework_version=FRAMEWORK_VERSION,
            normalization_contract_version=configuration.normalization_contract_version,
            normalization_id=normalization_id,
            correlation_id=correlation_id,
        )

        framework_metadata = NormalizationFrameworkMetadata(
            framework_version=FRAMEWORK_VERSION,
            normalization_contract_version=configuration.normalization_contract_version,
            pipeline_version=PIPELINE_VERSION,
            registry_version=REGISTRY_VERSION,
            responsibility_catalog_version=RESPONSIBILITY_CATALOG_VERSION,
        )

        return NormalizationResult(
            normalization_id=normalization_id,
            correlation_id=correlation_id,
            # Referenced, never copied or mutated — the exact configuration that
            # governed the run.
            normalization_configuration=configuration,
            normalization_framework_metadata=framework_metadata,
            normalization_statistics=statistics,
            observations=tuple(observations),
            parsed_response=None,  # Phase-1 placeholder — framework creates none.
            started_at=started_at,
            completed_at=completed_at,
        )
