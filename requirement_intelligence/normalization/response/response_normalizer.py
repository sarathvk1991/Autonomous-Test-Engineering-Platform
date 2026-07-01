"""ResponseNormalizer — the exclusive orchestration entry point for normalization.

The :class:`ResponseNormalizer` is the single orchestration boundary into the
Response Normalization subsystem — the normalization sibling of the
:class:`~requirement_intelligence.validation.response.response_validator.ResponseValidator`.
It coordinates the execution context, configuration, profile, registry, and
pipeline into one repeatable act of normalization, and returns the single
canonical ``NormalizationResult``
(:mod:`requirement_intelligence.normalization.models.normalization_result`).

It performs **no normalization itself**.  It never parses text, inspects JSON/XML,
recovers structure, determines an outcome, records observations, creates a
``ParsedResponse``, or mutates the ``LLMResponse``.  *What* structure a response
expresses is recovered by the registered ``NORMALIZATION-00NN`` responsibilities
and assembled by the framework; the Normalizer only decides *how the run is
conducted* and returns the framework's result unchanged.

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
    NormalizationResult,
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
        4. Execute the pipeline **exactly once**.
        5. Return the ``NormalizationResult`` unchanged.

        The Normalizer never parses, inspects, recovers structure, records
        observations, creates a ``ParsedResponse``, mutates *llm_response*, or
        interprets the result.

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
        """Invoke the pipeline exactly once and return its result unchanged.

        No retries, no loops, no recursion, no parallel execution.  Any framework
        exception — or unexpected internal error — is translated into a
        ``NormalizationExecutionError`` so that implementation exceptions never
        leak across the orchestration boundary.  The run's correlation identity is
        carried from the execution context onto the result.
        """
        try:
            return self._pipeline.run(
                llm_response,
                configuration,
                correlation_id=context.correlation_id,
            )
        except NormalizationFrameworkError as exc:
            raise NormalizationExecutionError(
                f"Normalization execution failed for run "
                f"{context.normalization_id!r}: {exc}"
            ) from exc
        except NormalizationError:
            raise
        except Exception as exc:
            raise NormalizationExecutionError(
                f"Unexpected error during normalization execution for run "
                f"{context.normalization_id!r}: {exc}"
            ) from exc
