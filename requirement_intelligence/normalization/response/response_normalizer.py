"""ResponseNormalizer — the exclusive orchestration entry point for normalization.

The :class:`ResponseNormalizer` is the single orchestration boundary into the
Response Normalization subsystem — the normalization sibling of the
:class:`~requirement_intelligence.validation.response.response_validator.ResponseValidator`.
It coordinates the execution context, configuration, profile, registry, and
pipeline into one repeatable act of normalization, and returns the single
canonical ``NormalizationResult``
(:mod:`requirement_intelligence.normalization.models.normalization_result`).

It performs **no normalization itself**.  It never parses text, inspects JSON/XML,
recovers structure, determines an outcome, records observations, or mutates the
``LLMResponse``.  *What* structure a response expresses is recovered and assembled
by the five internal normalization **stages** (``NORMALIZATION-0001…0005``),
coordinated **inside this component's boundary** through a transient ``AssemblyState``
(ADR-0002); the framework contributes only the generic ``NormalizationResult``
aggregation (telemetry, framework metadata).  The Normalizer decides *how the run is
conducted*, drives the stage chain, and populates the framework's result with the
assembled ``ParsedResponse`` and the recorded observations within its own boundary.

The internal stage chain (ADR-0002)
-----------------------------------
The five catalog stages are **internal** to this component and are **not** framework
``NormalizationResponsibility`` units.  The Normalizer coordinates the four writing
stages (``0001`` Recover Canonical Structure → ``0002`` Determine Outcome → ``0003``
Capture Observations → ``0004`` Create Source Reference) and then assembles the
immutable ``ParsedResponse`` through the coordinator's **consumer seam** (stage
``0005`` ``AssembleParsedResponse.assemble``).  The ``AssemblyState``, the stages,
and the coordinator never escape this boundary; the framework remains entirely
unaware of them.

Single public API
-----------------
:meth:`ResponseNormalizer.normalize` — the one operational entry point.  It
returns a ``NormalizationResult`` and nothing else.  A read-only
:attr:`last_execution_context` is exposed for observability only; it never
performs or alters normalization.

Mirror, not clone
-----------------
This class mirrors the *architecture* of ``ResponseValidator`` — dependency
injection, the configuration hierarchy, profile resolution, execution-context
provenance, single-invocation execution, and exception translation — but reuses
the normalization framework and the existing ``NormalizationExecutionContext``
builder rather than duplicating any logic.  The deliberate differences track the
subsystem's frozen deviations: the input is a raw ``LLMResponse`` (not an
``AnalysisResult``), which carries no execution/correlation identity, so those
context fields resolve to ``None``; and the output carries **facts**, never a
verdict.
"""

from __future__ import annotations

from requirement_intelligence.llm.llm_models import LLMResponse
from requirement_intelligence.models.parsed_response import ParsedResponse
from requirement_intelligence.normalization.framework.normalization_exceptions import (
    NormalizationFrameworkError,
)
from requirement_intelligence.normalization.framework.normalization_pipeline import (
    NormalizationPipeline,
)
from requirement_intelligence.normalization.framework.normalization_registry import (
    NormalizationRegistry,
)
from requirement_intelligence.normalization.models import (
    NormalizationConfiguration,
    NormalizationObservation,
    NormalizationResult,
)
from requirement_intelligence.normalization.response.assembly import (
    AssembleParsedResponse,
    AssemblyState,
    CaptureNormalizationObservations,
    CreateSourceReference,
    DetermineNormalizationOutcome,
    JsonCanonicalStructureRecoverer,
    NormalizationStageCoordinator,
    NormalizationStageError,
    RecoverCanonicalStructure,
)
from requirement_intelligence.normalization.response.normalization_execution_context import (
    NormalizationExecutionContext,
    build_normalization_execution_context,
)
from requirement_intelligence.normalization.response.normalization_profile import (
    NormalizationProfile,
    resolve_profile,
)
from requirement_intelligence.normalization.response.response_normalizer_exceptions import (
    ConfigurationResolutionError,
    NormalizationError,
    NormalizationExecutionError,
    PipelineConstructionError,
)


class ResponseNormalizer:
    """Coordinates a single normalization run and returns its ``NormalizationResult``.

    The Normalizer is the only component that drives the normalization framework
    on behalf of callers.  It validates configuration, resolves the profile,
    creates the execution context, executes the pipeline exactly once, and returns
    the result.

    Construction
    ------------
    The Normalizer is assembled by dependency injection from a populated registry,
    a constructed pipeline, and the platform-default configuration.  Construction
    validates the dependency types; it never performs normalization.

    Parameters
    ----------
    registry:
        The :class:`NormalizationRegistry` backing the pipeline.  Held for
        responsibility discovery as the catalog grows; the Normalizer registers no
        responsibilities itself today.
    pipeline:
        The :class:`NormalizationPipeline` that executes the registered
        responsibilities.
    platform_defaults:
        The baseline :class:`NormalizationConfiguration` applied when no more
        specific configuration is supplied (the configuration hierarchy).

    Raises
    ------
    PipelineConstructionError
        If *registry* or *pipeline* is not of the expected framework type.
    ConfigurationResolutionError
        If *platform_defaults* is not a :class:`NormalizationConfiguration`.
    """

    def __init__(
        self,
        registry: NormalizationRegistry,
        pipeline: NormalizationPipeline,
        platform_defaults: NormalizationConfiguration,
    ) -> None:
        if not isinstance(registry, NormalizationRegistry):
            raise PipelineConstructionError(
                f"ResponseNormalizer requires a NormalizationRegistry; "
                f"got {type(registry).__name__!r}."
            )
        if not isinstance(pipeline, NormalizationPipeline):
            raise PipelineConstructionError(
                f"ResponseNormalizer requires a NormalizationPipeline; "
                f"got {type(pipeline).__name__!r}."
            )
        if not isinstance(platform_defaults, NormalizationConfiguration):
            raise ConfigurationResolutionError(
                f"ResponseNormalizer requires a NormalizationConfiguration as "
                f"platform defaults; got {type(platform_defaults).__name__!r}."
            )

        self._registry = registry
        self._pipeline = pipeline
        self._platform_defaults = platform_defaults
        self._last_execution_context: NormalizationExecutionContext | None = None

        # The internal normalization stage chain (ADR-0002), coordinated inside this
        # component's boundary. The four writing stages run in the coordinator's
        # loop; stage 0005 assembles the ParsedResponse through the consumer seam.
        # The stages are stateless and reusable, so the chain is built once. The
        # JSON recovery mechanism is an implementation detail of stage 0001 — the
        # single place a serialization format is known — kept out of the orchestrator
        # so the orchestrator stays format-independent (Catalog §2.2, §3.4).
        self._stage_coordinator = NormalizationStageCoordinator(
            [
                RecoverCanonicalStructure(JsonCanonicalStructureRecoverer()),
                DetermineNormalizationOutcome(),
                CaptureNormalizationObservations(),
                CreateSourceReference(),
            ]
        )
        self._parsed_response_assembler = AssembleParsedResponse()

    # ------------------------------------------------------------------
    # Observability (read-only; never performs normalization)
    # ------------------------------------------------------------------

    @property
    def last_execution_context(self) -> NormalizationExecutionContext | None:
        """The execution identity of the most recent run, or ``None``.

        Exposed for observability only.  Reading it never performs, alters, or
        re-runs normalization.
        """
        return self._last_execution_context

    # ------------------------------------------------------------------
    # Single public API
    # ------------------------------------------------------------------

    def normalize(self, llm_response: LLMResponse) -> NormalizationResult:
        """Normalize *llm_response* and return its canonical ``NormalizationResult``.

        Orchestration sequence (mirroring the Response Validator):

        1. Resolve and validate the configuration (the configuration hierarchy).
        2. Resolve the Normalization Profile (default: Standard).
        3. Create the immutable execution context (full version provenance).
        4. Execute the framework pipeline **exactly once** (the generic result
           envelope) and coordinate the internal stage chain **exactly once** (the
           ``ParsedResponse`` and observations).
        5. Populate the framework result with the assembled ``ParsedResponse`` and
           the recorded observations, and return it.

        The Normalizer's orchestration logic never parses, inspects, recovers
        structure, determines an outcome, records observations, or mutates
        *llm_response*; those are performed by the internal stages within its
        boundary (ADR-0002).

        Parameters
        ----------
        llm_response:
            The provider-independent ``LLMResponse`` to normalize.

        Returns
        -------
        NormalizationResult
            The single, immutable output of the normalization framework.

        Raises
        ------
        ConfigurationResolutionError
            If a valid configuration cannot be resolved.
        ProfileResolutionError
            If the profile cannot be resolved.
        NormalizationExecutionError
            If the pipeline run fails; the framework exception is translated and
            preserved as the cause.
        """
        configuration = self._resolve_configuration()
        # Resolve (and validate) the Normalization Profile for this run. Unlike the
        # ValidationExecutionContext, the frozen NormalizationExecutionContext carries
        # **no profile field** (a deliberate deviation — normalization has no profile
        # analogue on the context), and no responsibility selects by profile yet, so
        # the profile is validated here and reserved for future responsibility
        # selection. A bad profile still surfaces as ``ProfileResolutionError``.
        self._resolve_profile()
        context = build_normalization_execution_context(configuration=configuration)
        self._last_execution_context = context
        return self._execute(
            llm_response=llm_response,
            configuration=configuration,
            context=context,
        )

    # ------------------------------------------------------------------
    # Configuration resolution (hierarchy; highest precedence wins)
    # ------------------------------------------------------------------

    def _resolve_configuration(
        self,
        *,
        profile_configuration: NormalizationConfiguration | None = None,
        execution_configuration: NormalizationConfiguration | None = None,
        runtime_overrides: NormalizationConfiguration | None = None,
    ) -> NormalizationConfiguration:
        """Resolve the effective configuration along the documented hierarchy.

        Precedence, lowest to highest: **Platform Defaults → Profile → Execution
        Configuration → Runtime Overrides**.  The highest-precedence layer that is
        supplied wins.  Today only platform defaults are wired into the public
        path; the higher layers are accepted here so the hierarchy is complete and
        ready to extend without changing the public contract.

        This is pure resolution — no normalization logic, no fact influence.
        """
        layers = (
            self._platform_defaults,
            profile_configuration,
            execution_configuration,
            runtime_overrides,
        )
        resolved: NormalizationConfiguration | None = None
        for layer in layers:
            if layer is not None:
                resolved = layer
        if not isinstance(resolved, NormalizationConfiguration):
            raise ConfigurationResolutionError(
                "No valid normalization configuration could be resolved."
            )
        return resolved

    # ------------------------------------------------------------------
    # Profile resolution (default Standard)
    # ------------------------------------------------------------------

    def _resolve_profile(self) -> NormalizationProfile:
        """Resolve the Normalization Profile for the run.

        With the single-argument public API, the Normalizer applies the default
        profile (Standard).  Profile resolution failures surface as
        ``ProfileResolutionError`` (raised by :func:`resolve_profile`).
        """
        return resolve_profile()

    # ------------------------------------------------------------------
    # Execution (pipeline invoked exactly once; framework errors translated)
    # ------------------------------------------------------------------

    def _execute(
        self,
        *,
        llm_response: LLMResponse,
        configuration: NormalizationConfiguration,
        context: NormalizationExecutionContext,
    ) -> NormalizationResult:
        """Run the framework pipeline and the internal stage chain, and populate the result.

        The framework pipeline runs **exactly once** to produce the generic
        ``NormalizationResult`` (telemetry, framework metadata); the internal stage
        chain runs **exactly once** to produce the ``ParsedResponse`` and the
        recorded observations.  The generic result is then populated, **within this
        boundary**, with those two products (ADR-0002 §7).  Framework statistics are
        left **unchanged** — they describe the framework pass, not the internal
        stages.

        No retries, no loops, no recursion, no parallel execution.  A framework
        exception, an internal-stage infrastructure failure, or any unexpected error
        is translated into a ``NormalizationExecutionError`` so that implementation
        exceptions never leak across the orchestration boundary.
        """
        try:
            framework_result = self._pipeline.run(
                llm_response,
                configuration,
                correlation_id=context.correlation_id,
            )
            parsed_response, observations = self._assemble_within_boundary(llm_response)
            # Populate the generic framework result with the internal-chain products.
            # ``model_copy`` yields a new immutable result; statistics and framework
            # metadata are carried through untouched (decision: framework telemetry
            # describes framework execution, not the internal stages).
            return framework_result.model_copy(
                update={
                    "parsed_response": parsed_response,
                    "observations": observations,
                }
            )
        except NormalizationFrameworkError as exc:
            raise NormalizationExecutionError(
                f"Normalization execution failed for run "
                f"{context.normalization_id!r}: {exc}"
            ) from exc
        except NormalizationStageError as exc:
            # An internal-stage infrastructure/ordering failure (never a MALFORMED
            # fact) — translated so component internals never leak to callers.
            raise NormalizationExecutionError(
                f"Normalization stage execution failed for run "
                f"{context.normalization_id!r}: {exc}"
            ) from exc
        except NormalizationError:
            raise
        except Exception as exc:
            raise NormalizationExecutionError(
                f"Unexpected error during normalization execution for run "
                f"{context.normalization_id!r}: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Internal stage chain (ADR-0002; never escapes this boundary)
    # ------------------------------------------------------------------

    def _assemble_within_boundary(
        self, llm_response: LLMResponse
    ) -> tuple[ParsedResponse, tuple[NormalizationObservation, ...]]:
        """Run the internal stage chain and return the ``ParsedResponse`` + observations.

        The coordinator runs the four writing stages over a fresh, boundary-local
        ``AssemblyState`` and then invokes the **consumer seam** to assemble the
        ``ParsedResponse`` (stage ``0005``).  The consumer returns **only** the
        ``ParsedResponse`` (its assembly contract is unchanged); the observations are
        snapshotted independently from the completed ``AssemblyState`` for the
        ``NormalizationResult`` — they are never bundled into the consumer's return
        value and never carried on the ``ParsedResponse`` (Assembly Contract §5, §6).
        The ``AssemblyState`` itself never escapes this method.
        """
        captured_observations: list[NormalizationObservation] = []

        def _consume(assembly_state: AssemblyState) -> ParsedResponse:
            captured_observations.extend(assembly_state.observations)
            return self._parsed_response_assembler.assemble(assembly_state)

        parsed_response = self._stage_coordinator.coordinate(llm_response, _consume)
        return parsed_response, tuple(captured_observations)
