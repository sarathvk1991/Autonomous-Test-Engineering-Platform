"""Unit tests for the Response Normalizer orchestration layer.

Covers
------
* Construction — dependency validation and stored state.
* Dependency injection — the injected registry and pipeline are used, not rebuilt.
* Configuration resolution — the documented hierarchy; highest precedence wins.
* Profile resolution — canonical profiles, default, unknown name.
* Execution context creation — provenance populated; source-decoupled identity.
* Exception translation — framework errors never leak; they become orchestration errors.
* Pipeline invocation — the pipeline is run exactly once with the resolved config.
* Observability — ``last_execution_context`` reflects the most recent run only.
* Immutability — execution context and profile are frozen.
* Backward compatibility — a fully-defaulted configuration normalizes cleanly.

Design constraints
------------------
* No normalization responsibilities are defined.
* The pipeline's ``run`` is replaced with a recording stub on a *real*
  ``NormalizationPipeline`` instance (so the Normalizer's type check still passes).
* No real AI responses; a minimal ``LLMResponse`` is built in-memory.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from requirement_intelligence.llm.llm_models import LLMResponse
from requirement_intelligence.models.parsed_response import ParsedResponse
from requirement_intelligence.normalization.framework import (
    NormalizationPipeline,
    NormalizationPipelineError,
    NormalizationRegistry,
)
from requirement_intelligence.normalization.models import (
    FRAMEWORK_VERSION,
    NORMALIZATION_CONTRACT_VERSION,
    PIPELINE_VERSION,
    REGISTRY_VERSION,
    RESPONSIBILITY_CATALOG_VERSION,
    NormalizationConfiguration,
    NormalizationResult,
)
from requirement_intelligence.normalization.response import (
    DEFAULT_PROFILE_NAME,
    ConfigurationResolutionError,
    NormalizationError,
    NormalizationExecutionContext,
    NormalizationExecutionError,
    NormalizationProfileName,
    PipelineConstructionError,
    ProfileResolutionError,
    ResponseNormalizer,
    all_profiles,
    build_normalization_execution_context,
    resolve_profile,
)

# ---------------------------------------------------------------------------
# Builders & recording stub
# ---------------------------------------------------------------------------


def _llm_response(text: str = "x") -> LLMResponse:
    return LLMResponse(provider="gemini", model="model", generated_text=text)


def _framework_result() -> NormalizationResult:
    """A real, minimal ``NormalizationResult`` (an empty framework pass).

    The Normalizer now populates the framework result with the assembled
    ``ParsedResponse`` and observations (via ``model_copy``), so the stubbed
    ``pipeline.run`` must return a real result rather than a bare sentinel.
    """
    return NormalizationPipeline(NormalizationRegistry()).run(_llm_response())


class _RecordingRun:
    """Replaces ``NormalizationPipeline.run`` to record calls without responsibilities."""

    def __init__(
        self, *, result: object | None = None, raises: BaseException | None = None
    ) -> None:
        self.calls: list[tuple[Any, Any, Any]] = []
        self._result = result if result is not None else _framework_result()
        self._raises = raises

    @property
    def result(self) -> object:
        return self._result

    def __call__(
        self, source: Any, configuration: Any = None, *, correlation_id: Any = None
    ) -> object:
        self.calls.append((source, configuration, correlation_id))
        if self._raises is not None:
            raise self._raises
        return self._result


def _normalizer(
    *,
    platform_defaults: NormalizationConfiguration | None = None,
    run: _RecordingRun | None = None,
) -> tuple[ResponseNormalizer, NormalizationRegistry, NormalizationPipeline, _RecordingRun]:
    registry = NormalizationRegistry()
    pipeline = NormalizationPipeline(registry)
    recording = run if run is not None else _RecordingRun()
    pipeline.run = recording  # type: ignore[method-assign]
    normalizer = ResponseNormalizer(
        registry, pipeline, platform_defaults or NormalizationConfiguration()
    )
    return normalizer, registry, pipeline, recording


# ---------------------------------------------------------------------------
# 1. Construction
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConstruction:
    def test_valid_construction(self) -> None:
        normalizer, _, _, _ = _normalizer()
        assert isinstance(normalizer, ResponseNormalizer)
        assert normalizer.last_execution_context is None

    def test_rejects_non_registry(self) -> None:
        registry = NormalizationRegistry()
        pipeline = NormalizationPipeline(registry)
        with pytest.raises(PipelineConstructionError):
            ResponseNormalizer("not-a-registry", pipeline, NormalizationConfiguration())  # type: ignore[arg-type]

    def test_rejects_non_pipeline(self) -> None:
        registry = NormalizationRegistry()
        with pytest.raises(PipelineConstructionError):
            ResponseNormalizer(registry, "not-a-pipeline", NormalizationConfiguration())  # type: ignore[arg-type]

    def test_rejects_non_configuration(self) -> None:
        registry = NormalizationRegistry()
        pipeline = NormalizationPipeline(registry)
        with pytest.raises(ConfigurationResolutionError):
            ResponseNormalizer(registry, pipeline, "not-a-config")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 2. Dependency injection
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDependencyInjection:
    def test_injected_registry_and_pipeline_are_used(self) -> None:
        normalizer, registry, pipeline, _ = _normalizer()
        assert normalizer._registry is registry
        assert normalizer._pipeline is pipeline

    def test_registry_unchanged_normalizer_adds_no_responsibilities(self) -> None:
        normalizer, registry, _, _ = _normalizer()
        normalizer.normalize(_llm_response())
        assert registry.responsibility_count() == 0


# ---------------------------------------------------------------------------
# 3. Configuration resolution (hierarchy; highest precedence wins)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConfigurationResolution:
    def test_platform_defaults_flow_by_default(self) -> None:
        defaults = NormalizationConfiguration()
        normalizer, _, _, _ = _normalizer(platform_defaults=defaults)
        assert normalizer._resolve_configuration() is defaults

    def test_highest_precedence_layer_wins(self) -> None:
        defaults = NormalizationConfiguration()
        runtime = NormalizationConfiguration(normalization_contract_version="9.9")
        normalizer, _, _, _ = _normalizer(platform_defaults=defaults)
        # Precedence: platform < profile < execution < runtime.
        assert normalizer._resolve_configuration(runtime_overrides=runtime) is runtime
        assert (
            normalizer._resolve_configuration(execution_configuration=runtime) is runtime
        )

    def test_resolved_configuration_reaches_pipeline(self) -> None:
        defaults = NormalizationConfiguration()
        normalizer, _, _, recording = _normalizer(platform_defaults=defaults)
        normalizer.normalize(_llm_response())
        _, used_config, _ = recording.calls[0]
        assert used_config is defaults


# ---------------------------------------------------------------------------
# 4. Profile resolution
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProfileResolution:
    def test_default_profile_is_standard(self) -> None:
        assert DEFAULT_PROFILE_NAME == NormalizationProfileName.STANDARD
        assert resolve_profile().name == NormalizationProfileName.STANDARD

    def test_four_canonical_profiles(self) -> None:
        names = {p.name for p in all_profiles()}
        assert names == {
            NormalizationProfileName.MINIMAL,
            NormalizationProfileName.STANDARD,
            NormalizationProfileName.STRICT,
            NormalizationProfileName.ENTERPRISE,
        }

    def test_no_compliance_profile(self) -> None:
        # Deliberate deviation from Validation Profiles: no COMPLIANCE.
        # ``Schema`` uses ``use_enum_values=True`` so ``name`` is the string value.
        assert "compliance" not in {p.name for p in all_profiles()}

    def test_unknown_profile_raises(self) -> None:
        with pytest.raises(ProfileResolutionError):
            resolve_profile("nonexistent")


# ---------------------------------------------------------------------------
# 5. Execution context creation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExecutionContextCreation:
    def test_normalize_records_context(self) -> None:
        normalizer, _, _, _ = _normalizer()
        normalizer.normalize(_llm_response())
        assert isinstance(normalizer.last_execution_context, NormalizationExecutionContext)

    def test_context_carries_version_provenance(self) -> None:
        normalizer, _, _, _ = _normalizer()
        normalizer.normalize(_llm_response())
        ctx = normalizer.last_execution_context
        assert ctx is not None
        assert ctx.framework_version == FRAMEWORK_VERSION
        assert ctx.pipeline_version == PIPELINE_VERSION
        assert ctx.registry_version == REGISTRY_VERSION
        assert ctx.responsibility_catalog_version == RESPONSIBILITY_CATALOG_VERSION
        assert ctx.normalization_contract_version == NORMALIZATION_CONTRACT_VERSION
        assert ctx.normalization_id  # a fresh id was generated
        assert ctx.started_at is not None

    def test_context_identity_is_source_decoupled(self) -> None:
        # An LLMResponse carries no execution/correlation identity, so both are None.
        normalizer, _, _, _ = _normalizer()
        normalizer.normalize(_llm_response())
        ctx = normalizer.last_execution_context
        assert ctx is not None
        assert ctx.execution_id is None
        assert ctx.correlation_id is None

    def test_contract_version_flows_from_configuration(self) -> None:
        defaults = NormalizationConfiguration(normalization_contract_version="2.5")
        normalizer, _, _, _ = _normalizer(platform_defaults=defaults)
        normalizer.normalize(_llm_response())
        ctx = normalizer.last_execution_context
        assert ctx is not None
        assert ctx.normalization_contract_version == "2.5"


# ---------------------------------------------------------------------------
# 6. Pipeline invocation & single invocation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPipelineInvocation:
    def test_pipeline_run_invoked_exactly_once(self) -> None:
        normalizer, _, _, recording = _normalizer()
        normalizer.normalize(_llm_response())
        assert len(recording.calls) == 1

    def test_pipeline_receives_llm_response_and_config(self) -> None:
        defaults = NormalizationConfiguration()
        normalizer, _, _, recording = _normalizer(platform_defaults=defaults)
        response = _llm_response()
        normalizer.normalize(response)
        used_source, used_config, used_correlation = recording.calls[0]
        assert used_source is response
        assert used_config is defaults
        assert used_correlation is None  # context correlation is None today

    def test_framework_result_is_populated_with_parsed_response(self) -> None:
        # The framework result is populated within the boundary with the assembled
        # ParsedResponse; the framework telemetry (statistics, framework metadata) is
        # carried through unchanged.
        framework_result = _framework_result()
        normalizer, _, _, _ = _normalizer(run=_RecordingRun(result=framework_result))
        result = normalizer.normalize(_llm_response())
        assert isinstance(result, NormalizationResult)
        assert isinstance(result.parsed_response, ParsedResponse)
        # Framework telemetry is unchanged (same objects, not reinterpreted).
        assert result.normalization_statistics is framework_result.normalization_statistics
        assert (
            result.normalization_framework_metadata
            is framework_result.normalization_framework_metadata
        )
        assert result.normalization_id == framework_result.normalization_id

    def test_repeated_normalize_invokes_once_each(self) -> None:
        normalizer, _, _, recording = _normalizer()
        normalizer.normalize(_llm_response())
        normalizer.normalize(_llm_response())
        assert len(recording.calls) == 2


# ---------------------------------------------------------------------------
# 7. Exception translation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExceptionTranslation:
    def test_framework_error_translated(self) -> None:
        framework_error = NormalizationPipelineError("boom")
        normalizer, _, _, _ = _normalizer(run=_RecordingRun(raises=framework_error))
        with pytest.raises(NormalizationExecutionError) as excinfo:
            normalizer.normalize(_llm_response())
        # Translated, not leaked: the raised type is an orchestration error.
        assert isinstance(excinfo.value, NormalizationError)
        assert not isinstance(excinfo.value, NormalizationPipelineError)
        assert excinfo.value.__cause__ is framework_error

    def test_unexpected_error_translated(self) -> None:
        normalizer, _, _, _ = _normalizer(run=_RecordingRun(raises=RuntimeError("unexpected")))
        with pytest.raises(NormalizationExecutionError) as excinfo:
            normalizer.normalize(_llm_response())
        assert isinstance(excinfo.value.__cause__, RuntimeError)

    def test_orchestration_error_not_double_wrapped(self) -> None:
        original = NormalizationExecutionError("already translated")
        normalizer, _, _, _ = _normalizer(run=_RecordingRun(raises=original))
        with pytest.raises(NormalizationExecutionError) as excinfo:
            normalizer.normalize(_llm_response())
        assert excinfo.value is original


# ---------------------------------------------------------------------------
# 8. Observability
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestObservability:
    def test_context_none_before_first_run(self) -> None:
        normalizer, _, _, _ = _normalizer()
        assert normalizer.last_execution_context is None

    def test_context_reflects_latest_run(self) -> None:
        normalizer, _, _, _ = _normalizer()
        normalizer.normalize(_llm_response())
        first = normalizer.last_execution_context
        normalizer.normalize(_llm_response())
        second = normalizer.last_execution_context
        assert first is not None and second is not None
        assert first.normalization_id != second.normalization_id

    def test_last_execution_context_is_read_only(self) -> None:
        normalizer, _, _, _ = _normalizer()
        with pytest.raises(AttributeError):
            normalizer.last_execution_context = None  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 9. Immutability
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestImmutability:
    def test_execution_context_is_frozen(self) -> None:
        ctx = build_normalization_execution_context()
        with pytest.raises(ValidationError):
            ctx.framework_version = "9.9.9"  # type: ignore[misc]

    def test_profile_is_frozen(self) -> None:
        profile = resolve_profile()
        with pytest.raises(ValidationError):
            profile.description = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 10. Backward compatibility
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBackwardCompatibility:
    def test_default_configuration_normalizes(self) -> None:
        # A fully-defaulted platform configuration produces a run with no error.
        normalizer, _, _, recording = _normalizer()
        normalizer.normalize(_llm_response())
        assert len(recording.calls) == 1

    def test_builder_still_available_standalone(self) -> None:
        # The pre-existing execution-context builder remains callable directly.
        ctx = build_normalization_execution_context()
        assert isinstance(ctx, NormalizationExecutionContext)
