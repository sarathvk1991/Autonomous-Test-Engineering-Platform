"""ResponseValidator — the exclusive orchestration entry point for validation.

The :class:`ResponseValidator` is the single orchestration boundary into the
Response Validation subsystem, as governed by
``docs/architecture/response-validator.md``.  It coordinates the execution
context, configuration, profile, registry, pipeline, and result into one
repeatable act of validation.

It performs **no validation itself**.  It does not execute rule logic, interpret
the ``ValidationResult``, repair, retry, log, persist, report, or perform CP1.
Whether a response is trustworthy is decided by the rules and assembled by the
framework; the Validator only decides *how the run is conducted* and returns the
single canonical result unchanged.

Single public API
-----------------
:meth:`ResponseValidator.validate` — the one operational entry point.  It returns
a :class:`~requirement_intelligence.validation.models.validation_result.ValidationResult`
and nothing else.  A read-only :attr:`last_execution_context` is exposed for
observability only; it never performs or alters validation.
"""

from __future__ import annotations

from requirement_intelligence.validation.models.validation_configuration import (
    ValidationConfiguration,
)
from requirement_intelligence.validation.models.validation_input import ValidationInput
from requirement_intelligence.validation.models.validation_result import ValidationResult
from requirement_intelligence.validation.response.response_validator_exceptions import (
    ConfigurationResolutionError,
    PipelineConstructionError,
    ResponseValidatorError,
    ValidationExecutionError,
)
from requirement_intelligence.validation.response.validation_execution_context import (
    ValidationExecutionContext,
    build_execution_context,
)
from requirement_intelligence.validation.response.validation_profile import (
    ValidationProfile,
    resolve_profile,
)
from requirement_intelligence.validation.validation_exceptions import ValidationFrameworkError
from requirement_intelligence.validation.validation_pipeline import ValidationPipeline
from requirement_intelligence.validation.validation_registry import ValidationRegistry


class ResponseValidator:
    """Coordinates a single validation run and returns its ``ValidationResult``.

    The Validator is the only component that drives the validation framework on
    behalf of callers.  It validates configuration, resolves the profile, creates
    the execution context, executes the pipeline exactly once, and returns the
    result.

    Construction
    ------------
    The Validator is assembled by dependency injection from a populated registry,
    a constructed pipeline, and the platform-default configuration.  Construction
    validates the dependency types; it never performs validation.

    Parameters
    ----------
    registry:
        The :class:`ValidationRegistry` backing the pipeline.  Held for rule
        discovery as the catalog grows; the Validator adds no rules itself today.
    pipeline:
        The :class:`ValidationPipeline` that executes the registered rules.
    platform_defaults:
        The baseline :class:`ValidationConfiguration` applied when no more
        specific configuration is supplied (§8 configuration hierarchy).

    Raises
    ------
    PipelineConstructionError
        If *registry* or *pipeline* is not of the expected framework type.
    ConfigurationResolutionError
        If *platform_defaults* is not a :class:`ValidationConfiguration`.
    """

    def __init__(
        self,
        registry: ValidationRegistry,
        pipeline: ValidationPipeline,
        platform_defaults: ValidationConfiguration,
    ) -> None:
        if not isinstance(registry, ValidationRegistry):
            raise PipelineConstructionError(
                f"ResponseValidator requires a ValidationRegistry; got {type(registry).__name__!r}."
            )
        if not isinstance(pipeline, ValidationPipeline):
            raise PipelineConstructionError(
                f"ResponseValidator requires a ValidationPipeline; got {type(pipeline).__name__!r}."
            )
        if not isinstance(platform_defaults, ValidationConfiguration):
            raise ConfigurationResolutionError(
                f"ResponseValidator requires a ValidationConfiguration as platform "
                f"defaults; got {type(platform_defaults).__name__!r}."
            )

        self._registry = registry
        self._pipeline = pipeline
        self._platform_defaults = platform_defaults
        self._last_execution_context: ValidationExecutionContext | None = None

    # ------------------------------------------------------------------
    # Observability (read-only; never performs validation)
    # ------------------------------------------------------------------

    @property
    def last_execution_context(self) -> ValidationExecutionContext | None:
        """The orchestration context of the most recent run, or ``None``.

        Exposed for observability only.  Reading it never performs, alters, or
        re-runs validation.
        """
        return self._last_execution_context

    # ------------------------------------------------------------------
    # Single public API
    # ------------------------------------------------------------------

    def validate(self, validation_input: ValidationInput) -> ValidationResult:
        """Validate *validation_input* and return its canonical ``ValidationResult``.

        The canonical input is the :class:`ValidationInput` (ADR-0003): the binding
        of the analysed response (``analysis_result``) and its normalization output
        (``normalization_result``, carrying the shared ``ParsedResponse`` and the
        observations).  The Validator remains the **single** entry point — one
        public method, one input object; the object is simply richer than the bare
        ``AnalysisResult`` it replaced.

        Orchestration sequence (``docs/architecture/response-validator.md`` §5):

        1. Resolve and validate the configuration (§8 hierarchy).
        2. Resolve the Validation Profile (default: Standard).
        3. Create the immutable execution context from the bound ``AnalysisResult``
           (full version provenance).
        4. Execute the pipeline **exactly once** over the ``ValidationInput``.
        5. Return the ``ValidationResult`` unchanged.

        The Validator never inspects, interprets, repairs, retries, logs,
        persists, reports, or normalizes.  It never calls the ``ResponseNormalizer``
        — the ``ValidationInput`` arrives already assembled by the handoff seam
        (ADR-0003 §4).

        Parameters
        ----------
        validation_input:
            The canonical validation input: the ``AnalysisResult`` bound to its
            same-execution ``NormalizationResult`` (ADR-0003).

        Returns
        -------
        ValidationResult
            The single, immutable output of the validation framework.

        Raises
        ------
        ConfigurationResolutionError
            If a valid configuration cannot be resolved.
        ProfileResolutionError
            If the profile cannot be resolved.
        ValidationExecutionError
            If the pipeline run fails; the framework exception is translated and
            preserved as the cause.
        """
        configuration = self._resolve_configuration()
        profile = self._resolve_profile()
        context = build_execution_context(
            analysis_result=validation_input.analysis_result,
            profile=profile,
            configuration=configuration,
        )
        self._last_execution_context = context
        return self._execute(
            validation_input=validation_input,
            configuration=configuration,
            context=context,
        )

    # ------------------------------------------------------------------
    # Configuration resolution (§8 — hierarchy; highest precedence wins)
    # ------------------------------------------------------------------

    def _resolve_configuration(
        self,
        *,
        profile_configuration: ValidationConfiguration | None = None,
        execution_configuration: ValidationConfiguration | None = None,
        runtime_overrides: ValidationConfiguration | None = None,
    ) -> ValidationConfiguration:
        """Resolve the effective configuration along the documented hierarchy.

        Precedence, lowest to highest: **Platform Defaults → Profile → Execution
        Configuration → Runtime Overrides**.  The highest-precedence layer that
        is supplied wins.  Today only platform defaults are wired into the public
        path; the higher layers are accepted here so the hierarchy is complete
        and ready to extend without changing the public contract.

        This is pure resolution — no business logic, no verdict influence.
        """
        layers = (
            self._platform_defaults,
            profile_configuration,
            execution_configuration,
            runtime_overrides,
        )
        resolved: ValidationConfiguration | None = None
        for layer in layers:
            if layer is not None:
                resolved = layer
        if not isinstance(resolved, ValidationConfiguration):
            raise ConfigurationResolutionError(
                "No valid validation configuration could be resolved."
            )
        return resolved

    # ------------------------------------------------------------------
    # Profile resolution (§6 — default Standard)
    # ------------------------------------------------------------------

    def _resolve_profile(self) -> ValidationProfile:
        """Resolve the Validation Profile for the run.

        With the single-argument public API, the Validator applies the default
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
        validation_input: ValidationInput,
        configuration: ValidationConfiguration,
        context: ValidationExecutionContext,
    ) -> ValidationResult:
        """Invoke the pipeline exactly once and return its result unchanged.

        No retries, no loops, no recursion, no parallel execution.  Any framework
        exception — or unexpected internal error — is translated into a
        ``ValidationExecutionError`` so that implementation exceptions never leak
        across the orchestration boundary.
        """
        try:
            return self._pipeline.run(validation_input, configuration)
        except ValidationFrameworkError as exc:
            raise ValidationExecutionError(
                f"Validation execution failed for correlation {context.correlation_id!r}: {exc}"
            ) from exc
        except ResponseValidatorError:
            raise
        except Exception as exc:
            raise ValidationExecutionError(
                f"Unexpected error during validation execution for correlation "
                f"{context.correlation_id!r}: {exc}"
            ) from exc
