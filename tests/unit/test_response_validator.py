"""Unit tests for the Response Validator orchestration layer.

Covers
------
* Construction — dependency validation and stored state.
* Configuration resolution — the documented hierarchy; highest precedence wins.
* Profile resolution — canonical profiles, default, unknown name.
* Execution context creation — every provenance field populated.
* Pipeline invocation — the pipeline is run exactly once with the resolved config.
* Registry usage — the registry is held; the Validator adds no rules.
* Exception translation — framework errors never leak; they become orchestration errors.
* Immutability — execution context and profile are frozen.
* Version propagation — centralized version constants reach the context.
* ValidationResult propagation — the pipeline's result is returned unchanged.
* Single pipeline invocation — exactly one run per validate().

Design constraints
------------------
* No validation rules are defined.
* The pipeline's ``run`` is replaced with a recording stub on a *real*
  ``ValidationPipeline`` instance (so the Validator's type check still passes).
* No real AI responses; a minimal ``AnalysisResult`` is built in-memory.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from requirement_intelligence.analysis.analysis_models import AnalysisResult
from requirement_intelligence.llm.llm_models import LLMResponse
from requirement_intelligence.normalization.framework.normalization_pipeline import (
    NormalizationPipeline,
)
from requirement_intelligence.normalization.framework.normalization_registry import (
    NormalizationRegistry,
)
from requirement_intelligence.normalization.models.normalization_configuration import (
    NormalizationConfiguration,
)
from requirement_intelligence.normalization.response import ResponseNormalizer
from requirement_intelligence.validation import (
    ValidationConfiguration,
    ValidationInput,
    ValidationPipeline,
    ValidationRegistry,
)
from requirement_intelligence.validation.models.validation_framework_metadata import (
    FRAMEWORK_VERSION,
)
from requirement_intelligence.validation.response import (
    DEFAULT_PROFILE_NAME,
    PLATFORM_VERSION,
    RULE_CATALOG_VERSION,
    VALIDATOR_VERSION,
    ConfigurationResolutionError,
    PipelineConstructionError,
    ProfileResolutionError,
    ResponseValidator,
    ResponseValidatorError,
    ValidationExecutionContext,
    ValidationExecutionError,
    ValidationProfileName,
    all_profiles,
    build_execution_context,
    resolve_profile,
)
from requirement_intelligence.validation.validation_exceptions import ValidationPipelineError

_TS = datetime(2026, 6, 30, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Builders & recording stub
# ---------------------------------------------------------------------------


def _analysis_result(execution_id: str = "EX-1", analysis_id: str = "AN-1") -> AnalysisResult:
    return AnalysisResult(
        analysis_id=analysis_id,
        execution_id=execution_id,
        source_consolidated_id="C-1",
        prompt_version="p1",
        reasoning_contract_version="r1",
        provider="gemini",
        model="model",
        started_at=_TS,
        completed_at=_TS,
        duration_ms=1.0,
        llm_response=LLMResponse(provider="gemini", model="model", generated_text="x"),
    )


def _validation_input(execution_id: str = "EX-1", analysis_id: str = "AN-1") -> ValidationInput:
    """The canonical validation input: an AnalysisResult bound to its
    NormalizationResult (ADR-0003)."""
    analysis = _analysis_result(execution_id, analysis_id)
    registry = NormalizationRegistry()
    normalizer = ResponseNormalizer(
        registry, NormalizationPipeline(registry), NormalizationConfiguration()
    )
    return ValidationInput(
        analysis_result=analysis,
        normalization_result=normalizer.normalize(analysis.llm_response),
    )


class _RecordingRun:
    """Replaces ``ValidationPipeline.run`` to record calls without real rules."""

    def __init__(
        self, *, result: object | None = None, raises: BaseException | None = None
    ) -> None:
        self.calls: list[tuple[Any, Any]] = []
        self._result = result if result is not None else object()
        self._raises = raises

    @property
    def result(self) -> object:
        return self._result

    def __call__(self, validation_input: Any, configuration: Any = None) -> object:
        self.calls.append((validation_input, configuration))
        if self._raises is not None:
            raise self._raises
        return self._result


def _validator(
    *,
    platform_defaults: ValidationConfiguration | None = None,
    run: _RecordingRun | None = None,
) -> tuple[ResponseValidator, ValidationRegistry, ValidationPipeline, _RecordingRun]:
    registry = ValidationRegistry()
    pipeline = ValidationPipeline(registry)
    recording = run if run is not None else _RecordingRun()
    pipeline.run = recording  # type: ignore[method-assign]
    validator = ResponseValidator(
        registry, pipeline, platform_defaults or ValidationConfiguration()
    )
    return validator, registry, pipeline, recording


# ---------------------------------------------------------------------------
# 1. Construction
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConstruction:
    def test_valid_construction(self) -> None:
        validator, _, _, _ = _validator()
        assert isinstance(validator, ResponseValidator)
        assert validator.last_execution_context is None

    def test_rejects_non_registry(self) -> None:
        registry = ValidationRegistry()
        pipeline = ValidationPipeline(registry)
        with pytest.raises(PipelineConstructionError):
            ResponseValidator("not a registry", pipeline, ValidationConfiguration())  # type: ignore[arg-type]

    def test_rejects_non_pipeline(self) -> None:
        with pytest.raises(PipelineConstructionError):
            ResponseValidator(ValidationRegistry(), "not a pipeline", ValidationConfiguration())  # type: ignore[arg-type]

    def test_rejects_non_configuration(self) -> None:
        registry = ValidationRegistry()
        pipeline = ValidationPipeline(registry)
        with pytest.raises(ConfigurationResolutionError):
            ResponseValidator(registry, pipeline, "not a config")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 2. Configuration resolution
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConfigurationResolution:
    def test_resolves_platform_defaults_into_pipeline(self) -> None:
        platform_defaults = ValidationConfiguration(validation_contract_version="9.9")
        validator, _, _, recording = _validator(platform_defaults=platform_defaults)
        validator.validate(_validation_input())
        _, used_config = recording.calls[0]
        assert used_config is platform_defaults

    def test_highest_precedence_wins(self) -> None:
        validator, _, _, _ = _validator()
        platform = validator._platform_defaults
        profile_cfg = ValidationConfiguration(validation_contract_version="profile")
        exec_cfg = ValidationConfiguration(validation_contract_version="exec")
        override = ValidationConfiguration(validation_contract_version="override")

        # Only platform supplied → platform wins.
        assert validator._resolve_configuration() is platform
        # Profile supplied → profile beats platform.
        assert validator._resolve_configuration(profile_configuration=profile_cfg) is profile_cfg
        # Execution supplied → beats profile.
        assert (
            validator._resolve_configuration(
                profile_configuration=profile_cfg, execution_configuration=exec_cfg
            )
            is exec_cfg
        )
        # Runtime override → highest precedence.
        assert (
            validator._resolve_configuration(
                profile_configuration=profile_cfg,
                execution_configuration=exec_cfg,
                runtime_overrides=override,
            )
            is override
        )


# ---------------------------------------------------------------------------
# 3. Profile resolution
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProfileResolution:
    def test_all_five_profiles_exist(self) -> None:
        names = {p.name for p in all_profiles()}
        assert names == {
            ValidationProfileName.MINIMAL,
            ValidationProfileName.STANDARD,
            ValidationProfileName.STRICT,
            ValidationProfileName.COMPLIANCE,
            ValidationProfileName.ENTERPRISE,
        }

    def test_default_is_standard(self) -> None:
        assert DEFAULT_PROFILE_NAME == ValidationProfileName.STANDARD
        assert resolve_profile().name == ValidationProfileName.STANDARD

    def test_resolve_by_name_value(self) -> None:
        assert resolve_profile("strict").name == ValidationProfileName.STRICT

    def test_resolve_by_enum(self) -> None:
        assert resolve_profile(ValidationProfileName.COMPLIANCE).name == (
            ValidationProfileName.COMPLIANCE
        )

    def test_unknown_profile_raises(self) -> None:
        with pytest.raises(ProfileResolutionError, match="Unknown validation profile"):
            resolve_profile("bogus")

    def test_validator_resolves_standard_into_context(self) -> None:
        validator, _, _, _ = _validator()
        validator.validate(_validation_input())
        assert validator.last_execution_context is not None
        assert validator.last_execution_context.profile.name == ValidationProfileName.STANDARD


# ---------------------------------------------------------------------------
# 4. Execution context creation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExecutionContextCreation:
    def test_build_populates_identity_from_analysis(self) -> None:
        ar = _analysis_result(execution_id="EX-77", analysis_id="AN-77")
        ctx = build_execution_context(
            analysis_result=ar,
            profile=resolve_profile(),
            configuration=ValidationConfiguration(),
        )
        assert ctx.execution_id == "EX-77"
        assert ctx.analysis_id == "AN-77"
        assert ctx.correlation_id == "EX-77"
        assert ctx.validation_id  # a fresh id was generated
        assert ctx.started_at is not None

    def test_build_uses_resolved_profile_and_configuration(self) -> None:
        config = ValidationConfiguration(validation_contract_version="2.5")
        ctx = build_execution_context(
            analysis_result=_analysis_result(),
            profile=resolve_profile("strict"),
            configuration=config,
        )
        assert ctx.profile.name == ValidationProfileName.STRICT
        assert ctx.configuration is config
        assert ctx.validation_contract_version == "2.5"

    def test_validator_records_context(self) -> None:
        validator, _, _, _ = _validator()
        validator.validate(_validation_input())
        assert isinstance(validator.last_execution_context, ValidationExecutionContext)


# ---------------------------------------------------------------------------
# 5. Pipeline invocation & 11. single invocation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPipelineInvocation:
    def test_pipeline_run_invoked_exactly_once(self) -> None:
        validator, _, _, recording = _validator()
        validator.validate(_validation_input())
        assert len(recording.calls) == 1

    def test_pipeline_receives_analysis_and_config(self) -> None:
        platform_defaults = ValidationConfiguration()
        validator, _, _, recording = _validator(platform_defaults=platform_defaults)
        vi = _validation_input()
        validator.validate(vi)
        used_input, used_config = recording.calls[0]
        assert used_input is vi
        assert used_input.analysis_result is vi.analysis_result
        assert used_config is platform_defaults

    def test_repeated_validate_invokes_once_each(self) -> None:
        validator, _, _, recording = _validator()
        validator.validate(_validation_input())
        validator.validate(_validation_input())
        assert len(recording.calls) == 2


# ---------------------------------------------------------------------------
# 6. Registry usage
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRegistryUsage:
    def test_registry_is_held_and_unchanged(self) -> None:
        validator, registry, _, _ = _validator()
        assert validator._registry is registry
        # The Validator adds no rules of its own.
        validator.validate(_validation_input())
        assert registry.rule_count() == 0


# ---------------------------------------------------------------------------
# 7. Exception translation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExceptionTranslation:
    def test_framework_error_translated(self) -> None:
        framework_error = ValidationPipelineError("boom")
        validator, _, _, _ = _validator(run=_RecordingRun(raises=framework_error))
        with pytest.raises(ValidationExecutionError) as excinfo:
            validator.validate(_validation_input())
        # Translated, not leaked: the raised type is an orchestration error.
        assert isinstance(excinfo.value, ResponseValidatorError)
        assert not isinstance(excinfo.value, ValidationPipelineError)
        assert excinfo.value.__cause__ is framework_error

    def test_unexpected_error_translated(self) -> None:
        validator, _, _, _ = _validator(run=_RecordingRun(raises=RuntimeError("unexpected")))
        with pytest.raises(ValidationExecutionError) as excinfo:
            validator.validate(_validation_input())
        assert isinstance(excinfo.value.__cause__, RuntimeError)

    def test_orchestration_error_not_double_wrapped(self) -> None:
        original = ValidationExecutionError("already translated")
        validator, _, _, _ = _validator(run=_RecordingRun(raises=original))
        with pytest.raises(ValidationExecutionError) as excinfo:
            validator.validate(_validation_input())
        assert excinfo.value is original


# ---------------------------------------------------------------------------
# 8. Immutability
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestImmutability:
    def test_execution_context_is_frozen(self) -> None:
        ctx = build_execution_context(
            analysis_result=_analysis_result(),
            profile=resolve_profile(),
            configuration=ValidationConfiguration(),
        )
        with pytest.raises(ValidationError):
            ctx.platform_version = "9.9.9"  # type: ignore[misc]

    def test_profile_is_frozen(self) -> None:
        profile = resolve_profile()
        with pytest.raises(ValidationError):
            profile.description = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 9. Version propagation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestVersionPropagation:
    def test_all_provenance_versions_propagate(self) -> None:
        config = ValidationConfiguration(validation_contract_version="3.3")
        ar = _analysis_result()
        ctx = build_execution_context(
            analysis_result=ar, profile=resolve_profile(), configuration=config
        )
        assert ctx.platform_version == PLATFORM_VERSION
        assert ctx.framework_version == FRAMEWORK_VERSION
        assert ctx.validator_version == VALIDATOR_VERSION
        assert ctx.rule_catalog_version == RULE_CATALOG_VERSION
        assert ctx.validation_contract_version == "3.3"
        assert ctx.prompt_version == ar.prompt_version
        assert ctx.reasoning_contract_version == ar.reasoning_contract_version


# ---------------------------------------------------------------------------
# 10. ValidationResult propagation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidationResultPropagation:
    def test_result_returned_unchanged(self) -> None:
        recording = _RecordingRun()
        validator, _, _, _ = _validator(run=recording)
        returned = validator.validate(_validation_input())
        # The Validator returns exactly what the pipeline produced — unaltered.
        assert returned is recording.result
