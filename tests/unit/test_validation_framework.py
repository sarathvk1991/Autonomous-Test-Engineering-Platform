"""Unit tests for the Response Validation Framework.

Covers
------
* ValidationRule abstract behaviour — cannot instantiate directly; concrete
  subclasses must implement all abstract properties and the validate() method.
* ValidationLayer enum — all nine layers present, LAYER_ORDER is complete.
* ValidationRegistry — registration, duplicate detection, ordering, retrieval
  by layer, enabled filtering.
* ValidationPipeline — construction, ordering delegation to registry,
  run() collects findings from mocked rules.
* Framework exceptions — hierarchy, message propagation.
* README — the documentation file exists alongside the package.

Design constraints
------------------
* No real AI responses are validated.
* No concrete validation rules are defined.
* All rule behaviour is exercised through lightweight mock/stub subclasses
  defined locally in this module.
* External I/O is absent; these tests run entirely in memory.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from requirement_intelligence.analysis.analysis_models import AnalysisResult
from requirement_intelligence.llm.llm_models import LLMResponse
from requirement_intelligence.validation.models import (
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    ValidationVerdict,
)
from requirement_intelligence.validation.validation_exceptions import (
    ValidationFrameworkError,
    ValidationPipelineError,
    ValidationRegistryError,
    ValidationRuleError,
)
from requirement_intelligence.validation.validation_pipeline import (
    PipelineState,
    ValidationPipeline,
)
from requirement_intelligence.validation.validation_registry import (
    RegistryState,
    ValidationRegistry,
)
from requirement_intelligence.validation.validation_rule import (
    LAYER_ORDER,
    ValidationLayer,
    ValidationRule,
)
from requirement_intelligence.validation.validation_rule_metadata import (
    DEFAULT_RULE_VERSION,
    ValidationRuleMetadata,
)
from shared.enums.base import ProviderType

# ---------------------------------------------------------------------------
# Minimal concrete stubs — used exclusively within this test module
# ---------------------------------------------------------------------------

_PACKAGE_DIR = Path(__file__).resolve().parents[2] / "requirement_intelligence" / "validation"

_TS = datetime(2026, 6, 30, 12, 0, 0, tzinfo=UTC)


def _analysis_result(execution_id: str = "EX-1", analysis_id: str = "AN-1") -> AnalysisResult:
    """Build a minimal, valid AnalysisResult for pipeline tests."""
    return AnalysisResult(
        analysis_id=analysis_id,
        execution_id=execution_id,
        source_consolidated_id="C-1",
        prompt_version="1.0",
        reasoning_contract_version="1.0",
        provider=ProviderType.GEMINI,
        model="model",
        started_at=_TS,
        completed_at=_TS,
        duration_ms=1.0,
        llm_response=LLMResponse(provider=ProviderType.GEMINI, model="model", generated_text="x"),
    )


def _issue(
    issue_id: str,
    layer: ValidationLayer,
    *,
    severity: ValidationSeverity = ValidationSeverity.ERROR,
    blocking: bool = False,
    category: str | None = None,
) -> ValidationIssue:
    """Build a minimal, valid ValidationIssue for pipeline tests."""
    return ValidationIssue(
        issue_id=issue_id,
        category=category if category is not None else layer.value,
        severity=severity,
        validation_layer=layer,
        rule_id=f"{layer.value.upper()}-0001",
        rule_version="1.0.0",
        message="finding",
        location="$",
        recommendation="fix it",
        blocking=blocking,
        correlation_id="EX-1",
        created_at=_TS,
    )


class _StubRule(ValidationRule):
    """Minimal concrete rule for testing framework contracts.

    Implements the new single-source-of-truth :attr:`metadata` contract.  The
    legacy identity properties (``rule_id``, ``rule_name``, ``validation_layer``,
    ``enabled``) are provided by :class:`ValidationRule` as convenience wrappers
    over the metadata, so this stub does not implement them directly.

    Returns an empty list from ``validate()`` to satisfy the abstract contract
    without performing any real validation.
    """

    def __init__(
        self,
        rule_id: str,
        rule_name: str,
        layer: ValidationLayer,
        enabled: bool = True,
        findings: list[Any] | None = None,
        rule_version: str = DEFAULT_RULE_VERSION,
    ) -> None:
        self._metadata = ValidationRuleMetadata(
            rule_id=rule_id,
            rule_name=rule_name,
            validation_layer=layer,
            enabled=enabled,
            rule_version=rule_version,
        )
        self._findings: list[Any] = findings if findings is not None else []

    @property
    def metadata(self) -> ValidationRuleMetadata:
        return self._metadata

    def validate(self, response: Any) -> list[Any]:
        return list(self._findings)


# ---------------------------------------------------------------------------
# 1. ValidationLayer enum
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidationLayer:
    """ValidationLayer enum correctness and LAYER_ORDER completeness."""

    def test_all_nine_layers_exist(self) -> None:
        expected = {
            "transport",
            "syntax",
            "schema",
            "structural",
            "content",
            "evidence",
            "traceability",
            "reasoning",
            "business_rule",
        }
        actual = {layer.value for layer in ValidationLayer}
        assert actual == expected

    def test_layer_order_contains_all_layers(self) -> None:
        assert set(LAYER_ORDER) == set(ValidationLayer)

    def test_layer_order_has_no_duplicates(self) -> None:
        assert len(LAYER_ORDER) == len(set(LAYER_ORDER))

    def test_layer_order_transport_is_first(self) -> None:
        assert LAYER_ORDER[0] == ValidationLayer.TRANSPORT

    def test_layer_order_business_rule_is_last(self) -> None:
        assert LAYER_ORDER[-1] == ValidationLayer.BUSINESS_RULE

    def test_layer_order_length(self) -> None:
        assert len(LAYER_ORDER) == 9


# ---------------------------------------------------------------------------
# 2. ValidationRule abstract behaviour
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidationRuleAbstract:
    """ValidationRule cannot be instantiated without implementing all abstract members."""

    def test_cannot_instantiate_abstract_rule(self) -> None:
        with pytest.raises(TypeError):
            ValidationRule()  # type: ignore[abstract]

    def test_concrete_stub_is_validation_rule(self) -> None:
        rule = _StubRule("SYNTAX-0001", "Test rule", ValidationLayer.SYNTAX)
        assert isinstance(rule, ValidationRule)

    def test_rule_id_property(self) -> None:
        rule = _StubRule("TRANSPORT-0001", "Transport stub", ValidationLayer.TRANSPORT)
        assert rule.rule_id == "TRANSPORT-0001"

    def test_rule_name_property(self) -> None:
        rule = _StubRule("SCHEMA-0001", "Schema stub", ValidationLayer.SCHEMA)
        assert rule.rule_name == "Schema stub"

    def test_validation_layer_property(self) -> None:
        rule = _StubRule("CONTENT-0001", "Content stub", ValidationLayer.CONTENT)
        assert rule.validation_layer == ValidationLayer.CONTENT

    def test_enabled_defaults_to_true(self) -> None:
        rule = _StubRule("EVIDENCE-0001", "Evidence stub", ValidationLayer.EVIDENCE)
        assert rule.enabled is True

    def test_enabled_can_be_false(self) -> None:
        rule = _StubRule(
            "TRACEABILITY-0001", "Traceability stub", ValidationLayer.TRACEABILITY, enabled=False
        )
        assert rule.enabled is False

    def test_validate_returns_empty_list_when_no_findings(self) -> None:
        rule = _StubRule("REASONING-0001", "Reasoning stub", ValidationLayer.REASONING)
        result = rule.validate("any response")
        assert result == []

    def test_validate_returns_findings_when_provided(self) -> None:
        rule = _StubRule(
            "SYNTAX-0002", "Syntax stub with finding", ValidationLayer.SYNTAX, findings=["finding"]
        )
        result = rule.validate("any response")
        assert result == ["finding"]

    def test_validate_does_not_mutate_findings_list(self) -> None:
        findings = ["finding-a"]
        rule = _StubRule("SYNTAX-0003", "Isolation stub", ValidationLayer.SYNTAX, findings=findings)
        result = rule.validate("response")
        result.append("mutated")
        # Original findings list must be unchanged
        assert "mutated" not in rule._findings


# ---------------------------------------------------------------------------
# 3. ValidationRegistry — registration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidationRegistryRegistration:
    """Registry correctly stores and rejects rule registrations."""

    def test_empty_registry_has_zero_rules(self) -> None:
        registry = ValidationRegistry()
        assert registry.rule_count() == 0

    def test_register_single_rule(self) -> None:
        registry = ValidationRegistry()
        rule = _StubRule("SYNTAX-0001", "Syntax rule", ValidationLayer.SYNTAX)
        registry.register(rule)
        assert registry.rule_count() == 1

    def test_register_multiple_rules_different_layers(self) -> None:
        registry = ValidationRegistry()
        for layer in ValidationLayer:
            registry.register(_StubRule(f"{layer.value}-0001", f"{layer.value}", layer))
        assert registry.rule_count() == len(ValidationLayer)

    def test_duplicate_rule_id_raises(self) -> None:
        registry = ValidationRegistry()
        registry.register(_StubRule("SYNTAX-0001", "First", ValidationLayer.SYNTAX))
        with pytest.raises(ValidationRegistryError, match="SYNTAX-0001"):
            registry.register(_StubRule("SYNTAX-0001", "Duplicate", ValidationLayer.SYNTAX))

    def test_same_id_different_layer_still_raises(self) -> None:
        """rule_id uniqueness is global, not per-layer."""
        registry = ValidationRegistry()
        registry.register(_StubRule("RULE-0001", "First", ValidationLayer.SYNTAX))
        with pytest.raises(ValidationRegistryError):
            registry.register(_StubRule("RULE-0001", "Conflict", ValidationLayer.SCHEMA))


# ---------------------------------------------------------------------------
# 4. ValidationRegistry — retrieval and ordering
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidationRegistryRetrieval:
    """Registry returns rules in the correct deterministic order."""

    def _populated_registry(self) -> ValidationRegistry:
        """Build a registry with one rule per layer, in reverse layer order."""
        registry = ValidationRegistry()
        # Register in REVERSE of LAYER_ORDER to prove the registry re-orders correctly.
        for layer in reversed(LAYER_ORDER):
            registry.register(_StubRule(f"{layer.value}-0001", layer.value, layer))
        return registry

    def test_get_all_rules_count(self) -> None:
        registry = self._populated_registry()
        assert len(registry.get_all_rules()) == len(ValidationLayer)

    def test_get_all_rules_returns_layer_order(self) -> None:
        registry = self._populated_registry()
        layers = [rule.validation_layer for rule in registry.get_all_rules()]
        assert layers == LAYER_ORDER

    def test_get_enabled_rules_excludes_disabled(self) -> None:
        registry = ValidationRegistry()
        registry.register(_StubRule("SYNTAX-0001", "Enabled syntax", ValidationLayer.SYNTAX))
        registry.register(
            _StubRule("SCHEMA-0001", "Disabled schema", ValidationLayer.SCHEMA, enabled=False)
        )
        enabled = registry.get_enabled_rules()
        assert len(enabled) == 1
        assert enabled[0].rule_id == "SYNTAX-0001"

    def test_get_enabled_rules_ordering_respects_layer_order(self) -> None:
        registry = ValidationRegistry()
        # Register in reverse order.
        registry.register(
            _StubRule("BUSINESS_RULE-0001", "BR rule", ValidationLayer.BUSINESS_RULE)
        )
        registry.register(_StubRule("TRANSPORT-0001", "Transport rule", ValidationLayer.TRANSPORT))
        enabled = registry.get_enabled_rules()
        layers = [rule.validation_layer for rule in enabled]
        assert layers == [ValidationLayer.TRANSPORT, ValidationLayer.BUSINESS_RULE]

    def test_get_rules_by_layer_returns_only_that_layer(self) -> None:
        registry = self._populated_registry()
        syntax_rules = registry.get_rules_by_layer(ValidationLayer.SYNTAX)
        assert len(syntax_rules) == 1
        assert syntax_rules[0].validation_layer == ValidationLayer.SYNTAX

    def test_get_rules_by_layer_empty_for_unregistered_layer(self) -> None:
        registry = ValidationRegistry()
        registry.register(_StubRule("SYNTAX-0001", "Syntax", ValidationLayer.SYNTAX))
        # No evidence rules registered.
        assert registry.get_rules_by_layer(ValidationLayer.EVIDENCE) == []

    def test_get_enabled_rules_by_layer_filters_disabled(self) -> None:
        registry = ValidationRegistry()
        registry.register(
            _StubRule("SYNTAX-0001", "Enabled", ValidationLayer.SYNTAX, enabled=True)
        )
        registry.register(
            _StubRule("SYNTAX-0002", "Disabled", ValidationLayer.SYNTAX, enabled=False)
        )
        enabled = registry.get_enabled_rules_by_layer(ValidationLayer.SYNTAX)
        assert len(enabled) == 1
        assert enabled[0].rule_id == "SYNTAX-0001"

    def test_get_rules_by_layer_preserves_insertion_order_within_layer(self) -> None:
        registry = ValidationRegistry()
        for i in range(3):
            registry.register(_StubRule(f"SYNTAX-{i:04d}", f"Rule {i}", ValidationLayer.SYNTAX))
        ids = [r.rule_id for r in registry.get_rules_by_layer(ValidationLayer.SYNTAX)]
        assert ids == ["SYNTAX-0000", "SYNTAX-0001", "SYNTAX-0002"]

    def test_list_rule_ids_pipeline_order(self) -> None:
        registry = ValidationRegistry()
        registry.register(_StubRule("SCHEMA-0001", "Schema", ValidationLayer.SCHEMA))
        registry.register(_StubRule("SYNTAX-0001", "Syntax", ValidationLayer.SYNTAX))
        ids = registry.list_rule_ids()
        # Syntax layer comes before Schema layer in LAYER_ORDER.
        assert ids == ["SYNTAX-0001", "SCHEMA-0001"]


# ---------------------------------------------------------------------------
# 5. ValidationPipeline — construction
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidationPipelineConstruction:
    """Pipeline construction contracts."""

    def test_pipeline_accepts_registry(self) -> None:
        registry = ValidationRegistry()
        pipeline = ValidationPipeline(registry)
        assert isinstance(pipeline, ValidationPipeline)

    def test_pipeline_rejects_non_registry(self) -> None:
        with pytest.raises(ValidationPipelineError):
            ValidationPipeline("not a registry")  # type: ignore[arg-type]

    def test_pipeline_rejects_none(self) -> None:
        with pytest.raises(ValidationPipelineError):
            ValidationPipeline(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 6. ValidationPipeline — ordering and execution
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidationPipelineOrdering:
    """Pipeline delegates ordering to the registry and returns rules in layer order."""

    def test_get_ordered_rules_returns_registry_enabled_rules(self) -> None:
        registry = ValidationRegistry()
        registry.register(_StubRule("TRANSPORT-0001", "T", ValidationLayer.TRANSPORT))
        registry.register(_StubRule("SYNTAX-0001", "S", ValidationLayer.SYNTAX))
        pipeline = ValidationPipeline(registry)
        ordered = pipeline.get_ordered_rules()
        assert len(ordered) == 2
        assert ordered[0].validation_layer == ValidationLayer.TRANSPORT
        assert ordered[1].validation_layer == ValidationLayer.SYNTAX

    def test_get_ordered_rules_excludes_disabled(self) -> None:
        registry = ValidationRegistry()
        registry.register(
            _StubRule("SYNTAX-0001", "Enabled", ValidationLayer.SYNTAX, enabled=True)
        )
        registry.register(
            _StubRule("SCHEMA-0001", "Disabled", ValidationLayer.SCHEMA, enabled=False)
        )
        pipeline = ValidationPipeline(registry)
        ordered = pipeline.get_ordered_rules()
        assert len(ordered) == 1
        assert ordered[0].rule_id == "SYNTAX-0001"

    def test_run_empty_registry_returns_valid_result(self) -> None:
        registry = ValidationRegistry()
        pipeline = ValidationPipeline(registry)
        result = pipeline.run(_analysis_result())
        assert isinstance(result, ValidationResult)
        assert result.validation_issues == ()
        assert result.overall_verdict == ValidationVerdict.PASSED

    def test_run_collects_issues_from_all_rules(self) -> None:
        registry = ValidationRegistry()
        registry.register(
            _StubRule(
                "TRANSPORT-0001",
                "T",
                ValidationLayer.TRANSPORT,
                findings=[_issue("ISS-T", ValidationLayer.TRANSPORT)],
            )
        )
        registry.register(
            _StubRule(
                "SYNTAX-0001",
                "S",
                ValidationLayer.SYNTAX,
                findings=[_issue("ISS-S", ValidationLayer.SYNTAX)],
            )
        )
        pipeline = ValidationPipeline(registry)
        result = pipeline.run(_analysis_result())
        ids = [issue.issue_id for issue in result.validation_issues]
        assert "ISS-T" in ids
        assert "ISS-S" in ids

    def test_run_respects_rule_execution_order(self) -> None:
        """Issues must appear in layer order, not registration order."""
        registry = ValidationRegistry()
        # Register SCHEMA before SYNTAX intentionally.
        registry.register(
            _StubRule(
                "SCHEMA-0001",
                "Schema",
                ValidationLayer.SCHEMA,
                findings=[_issue("ISS-SCHEMA", ValidationLayer.SCHEMA)],
            )
        )
        registry.register(
            _StubRule(
                "SYNTAX-0001",
                "Syntax",
                ValidationLayer.SYNTAX,
                findings=[_issue("ISS-SYNTAX", ValidationLayer.SYNTAX)],
            )
        )
        pipeline = ValidationPipeline(registry)
        result = pipeline.run(_analysis_result())
        ids = [issue.issue_id for issue in result.validation_issues]
        # SYNTAX layer precedes SCHEMA layer.
        assert ids.index("ISS-SYNTAX") < ids.index("ISS-SCHEMA")

    def test_run_passes_response_to_every_rule(self) -> None:
        """Each rule must receive the same AnalysisResult object."""
        received: list[Any] = []

        class _CapturingRule(ValidationRule):
            def __init__(self, rule_id: str, layer: ValidationLayer) -> None:
                self._metadata = ValidationRuleMetadata(
                    rule_id=rule_id,
                    rule_name=rule_id,
                    validation_layer=layer,
                )

            @property
            def metadata(self) -> ValidationRuleMetadata:
                return self._metadata

            def validate(self, response: Any) -> list[Any]:
                received.append(response)
                return []

        registry = ValidationRegistry()
        registry.register(_CapturingRule("TRANSPORT-0001", ValidationLayer.TRANSPORT))
        registry.register(_CapturingRule("SYNTAX-0001", ValidationLayer.SYNTAX))
        pipeline = ValidationPipeline(registry)

        analysis = _analysis_result()
        pipeline.run(analysis)

        assert received == [analysis, analysis]

    def test_run_preserves_original_analysis_result(self) -> None:
        """The pipeline preserves the exact AnalysisResult on the result."""
        registry = ValidationRegistry()
        registry.register(_StubRule("SYNTAX-0001", "S", ValidationLayer.SYNTAX))
        pipeline = ValidationPipeline(registry)

        analysis = _analysis_result()
        result = pipeline.run(analysis)
        assert result.analysis_result is analysis

    def test_run_rejects_non_analysis_result(self) -> None:
        registry = ValidationRegistry()
        pipeline = ValidationPipeline(registry)
        with pytest.raises(ValidationPipelineError):
            pipeline.run("not an analysis result")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 7. Framework exceptions
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidationExceptions:
    """Exception hierarchy and message behaviour."""

    def test_framework_error_is_base_exception(self) -> None:
        exc = ValidationFrameworkError("base error")
        assert isinstance(exc, Exception)
        assert str(exc) == "base error"

    def test_pipeline_error_is_framework_error(self) -> None:
        exc = ValidationPipelineError("pipeline failed")
        assert isinstance(exc, ValidationFrameworkError)

    def test_registry_error_is_framework_error(self) -> None:
        exc = ValidationRegistryError("registry failed")
        assert isinstance(exc, ValidationFrameworkError)

    def test_rule_error_is_framework_error(self) -> None:
        exc = ValidationRuleError("rule failed")
        assert isinstance(exc, ValidationFrameworkError)

    def test_all_framework_errors_caught_by_base(self) -> None:
        errors = [
            ValidationPipelineError("p"),
            ValidationRegistryError("r"),
            ValidationRuleError("ru"),
        ]
        for exc in errors:
            assert isinstance(exc, ValidationFrameworkError), f"{type(exc).__name__} not caught"

    def test_pipeline_error_message_preserved(self) -> None:
        exc = ValidationPipelineError("cannot build pipeline")
        assert "cannot build pipeline" in str(exc)

    def test_registry_error_message_preserved(self) -> None:
        exc = ValidationRegistryError("duplicate rule_id 'SYNTAX-0001'")
        assert "SYNTAX-0001" in str(exc)


# ---------------------------------------------------------------------------
# 8. Package public API
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPackagePublicApi:
    """The package __init__ exports the expected public names."""

    def test_imports_from_package_root(self) -> None:
        import requirement_intelligence.validation as v

        assert hasattr(v, "ValidationLayer")
        assert hasattr(v, "ValidationRule")
        assert hasattr(v, "ValidationRuleMetadata")
        assert hasattr(v, "ValidationRegistry")
        assert hasattr(v, "RegistryState")
        assert hasattr(v, "ValidationPipeline")
        assert hasattr(v, "PipelineState")
        assert hasattr(v, "ValidationFrameworkError")
        assert hasattr(v, "ValidationPipelineError")
        assert hasattr(v, "ValidationRegistryError")
        assert hasattr(v, "ValidationRuleError")
        assert hasattr(v, "LAYER_ORDER")


# ---------------------------------------------------------------------------
# 9. README existence
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReadmeExists:
    """The README.md documentation file must exist alongside the package."""

    def test_readme_exists(self) -> None:
        readme = _PACKAGE_DIR / "README.md"
        assert readme.exists(), f"README.md not found at {readme}"

    def test_readme_is_not_empty(self) -> None:
        readme = _PACKAGE_DIR / "README.md"
        assert readme.stat().st_size > 0, "README.md exists but is empty"


# ---------------------------------------------------------------------------
# 10. ValidationRuleMetadata — identity model
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidationRuleMetadata:
    """ValidationRuleMetadata is an immutable, correctly-defaulted identity value."""

    def test_active_fields_are_stored(self) -> None:
        meta = ValidationRuleMetadata(
            rule_id="SYNTAX-0001",
            rule_name="Well-formed JSON",
            validation_layer=ValidationLayer.SYNTAX,
        )
        assert meta.rule_id == "SYNTAX-0001"
        assert meta.rule_name == "Well-formed JSON"
        assert meta.validation_layer == ValidationLayer.SYNTAX

    def test_enabled_defaults_to_true(self) -> None:
        meta = ValidationRuleMetadata("E-1", "evidence", ValidationLayer.EVIDENCE)
        assert meta.enabled is True

    def test_enabled_can_be_false(self) -> None:
        meta = ValidationRuleMetadata(
            "E-1", "evidence", ValidationLayer.EVIDENCE, enabled=False
        )
        assert meta.enabled is False

    def test_reserved_fields_have_inert_defaults(self) -> None:
        meta = ValidationRuleMetadata("R-1", "reserved", ValidationLayer.REASONING)
        assert meta.tags == ()
        assert meta.documentation_reference is None
        assert meta.validation_contract_version is None
        assert meta.future_schema_compatibility is None

    def test_reserved_fields_accept_values(self) -> None:
        meta = ValidationRuleMetadata(
            "R-1",
            "reserved",
            ValidationLayer.REASONING,
            tags=("security", "experimental"),
            documentation_reference="docs/rules/R-1.md",
            validation_contract_version="1.1",
            future_schema_compatibility="schema-v2",
        )
        assert meta.tags == ("security", "experimental")
        assert meta.documentation_reference == "docs/rules/R-1.md"
        assert meta.validation_contract_version == "1.1"
        assert meta.future_schema_compatibility == "schema-v2"

    def test_value_equality(self) -> None:
        a = ValidationRuleMetadata("C-1", "content", ValidationLayer.CONTENT)
        b = ValidationRuleMetadata("C-1", "content", ValidationLayer.CONTENT)
        assert a == b

    def test_metadata_is_immutable_rule_id(self) -> None:
        meta = ValidationRuleMetadata("C-1", "content", ValidationLayer.CONTENT)
        with pytest.raises(dataclasses.FrozenInstanceError):
            meta.rule_id = "C-2"  # type: ignore[misc]

    def test_metadata_is_immutable_severity_layer(self) -> None:
        meta = ValidationRuleMetadata("C-1", "content", ValidationLayer.CONTENT)
        with pytest.raises(dataclasses.FrozenInstanceError):
            meta.validation_layer = ValidationLayer.SCHEMA  # type: ignore[misc]

    def test_metadata_is_immutable_enabled(self) -> None:
        meta = ValidationRuleMetadata("C-1", "content", ValidationLayer.CONTENT)
        with pytest.raises(dataclasses.FrozenInstanceError):
            meta.enabled = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 11. Backward-compatibility wrappers — legacy identity properties
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRuleBackwardCompatibility:
    """Legacy identity properties continue to work, reading through metadata."""

    def test_rule_exposes_metadata(self) -> None:
        rule = _StubRule("SYNTAX-0001", "Syntax", ValidationLayer.SYNTAX)
        assert isinstance(rule.metadata, ValidationRuleMetadata)

    def test_rule_id_wrapper_reads_metadata(self) -> None:
        rule = _StubRule("SYNTAX-0001", "Syntax", ValidationLayer.SYNTAX)
        assert rule.rule_id == rule.metadata.rule_id == "SYNTAX-0001"

    def test_rule_name_wrapper_reads_metadata(self) -> None:
        rule = _StubRule("SYNTAX-0001", "Syntax name", ValidationLayer.SYNTAX)
        assert rule.rule_name == rule.metadata.rule_name == "Syntax name"

    def test_validation_layer_wrapper_reads_metadata(self) -> None:
        rule = _StubRule("CONTENT-0001", "Content", ValidationLayer.CONTENT)
        assert rule.validation_layer == rule.metadata.validation_layer == ValidationLayer.CONTENT

    def test_enabled_wrapper_reads_metadata(self) -> None:
        rule = _StubRule("E-1", "disabled", ValidationLayer.EVIDENCE, enabled=False)
        assert rule.enabled is rule.metadata.enabled is False

    def test_registry_orders_rules_via_wrappers(self) -> None:
        """Registry consumes the wrappers; ordering still works post-refactor."""
        registry = ValidationRegistry()
        registry.register(_StubRule("SCHEMA-0001", "Schema", ValidationLayer.SCHEMA))
        registry.register(_StubRule("SYNTAX-0001", "Syntax", ValidationLayer.SYNTAX))
        assert registry.list_rule_ids() == ["SYNTAX-0001", "SCHEMA-0001"]


# ---------------------------------------------------------------------------
# 12. Rule version
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRuleVersion:
    """Rule version is independently carried on metadata and defaulted."""

    def test_default_rule_version_constant(self) -> None:
        assert DEFAULT_RULE_VERSION == "1.0.0"

    def test_metadata_default_rule_version(self) -> None:
        meta = ValidationRuleMetadata("S-1", "syntax", ValidationLayer.SYNTAX)
        assert meta.rule_version == "1.0.0"

    def test_metadata_explicit_rule_version(self) -> None:
        meta = ValidationRuleMetadata(
            "S-1", "syntax", ValidationLayer.SYNTAX, rule_version="2.3.1"
        )
        assert meta.rule_version == "2.3.1"

    def test_rule_version_wrapper_reads_metadata(self) -> None:
        rule = _StubRule("S-1", "syntax", ValidationLayer.SYNTAX, rule_version="4.0.0")
        assert rule.rule_version == rule.metadata.rule_version == "4.0.0"

    def test_rule_version_default_via_wrapper(self) -> None:
        rule = _StubRule("S-1", "syntax", ValidationLayer.SYNTAX)
        assert rule.rule_version == "1.0.0"


# ---------------------------------------------------------------------------
# 13. Registry sealing lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRegistrySealing:
    """Registry lifecycle: open → sealed; registration only while open."""

    def test_new_registry_is_open(self) -> None:
        registry = ValidationRegistry()
        assert registry.state is RegistryState.OPEN
        assert registry.is_sealed is False

    def test_seal_transitions_to_sealed(self) -> None:
        registry = ValidationRegistry()
        registry.seal()
        assert registry.state is RegistryState.SEALED
        assert registry.is_sealed is True

    def test_seal_is_idempotent(self) -> None:
        registry = ValidationRegistry()
        registry.seal()
        registry.seal()  # must not raise
        assert registry.is_sealed is True

    def test_register_allowed_while_open(self) -> None:
        registry = ValidationRegistry()
        registry.register(_StubRule("SYNTAX-0001", "Syntax", ValidationLayer.SYNTAX))
        assert registry.rule_count() == 1

    def test_register_after_seal_raises(self) -> None:
        registry = ValidationRegistry()
        registry.seal()
        with pytest.raises(ValidationRegistryError, match="sealed"):
            registry.register(_StubRule("SYNTAX-0001", "Syntax", ValidationLayer.SYNTAX))

    def test_pipeline_construction_seals_registry(self) -> None:
        registry = ValidationRegistry()
        registry.register(_StubRule("SYNTAX-0001", "Syntax", ValidationLayer.SYNTAX))
        assert registry.is_sealed is False
        ValidationPipeline(registry)
        assert registry.is_sealed is True

    def test_register_after_pipeline_construction_raises(self) -> None:
        registry = ValidationRegistry()
        registry.register(_StubRule("SYNTAX-0001", "Syntax", ValidationLayer.SYNTAX))
        ValidationPipeline(registry)
        with pytest.raises(ValidationRegistryError, match="sealed"):
            registry.register(_StubRule("SCHEMA-0001", "Schema", ValidationLayer.SCHEMA))

    def test_retrieval_still_works_after_seal(self) -> None:
        registry = ValidationRegistry()
        registry.register(_StubRule("SYNTAX-0001", "Syntax", ValidationLayer.SYNTAX))
        registry.seal()
        assert registry.list_rule_ids() == ["SYNTAX-0001"]
        assert len(registry.get_enabled_rules()) == 1


# ---------------------------------------------------------------------------
# 14. Pipeline lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPipelineLifecycle:
    """Pipeline state is observable, informational, and never alters behaviour."""

    def test_all_six_states_exist(self) -> None:
        expected = {"created", "ready", "running", "completed", "failed", "disposed"}
        assert {state.value for state in PipelineState} == expected

    def test_pipeline_is_ready_after_construction(self) -> None:
        registry = ValidationRegistry()
        pipeline = ValidationPipeline(registry)
        assert pipeline.state is PipelineState.READY

    def test_pipeline_completed_after_successful_run(self) -> None:
        registry = ValidationRegistry()
        registry.register(_StubRule("SYNTAX-0001", "Syntax", ValidationLayer.SYNTAX))
        pipeline = ValidationPipeline(registry)
        pipeline.run(_analysis_result())
        assert pipeline.state is PipelineState.COMPLETED

    def test_pipeline_failed_after_rule_raises(self) -> None:
        class _ExplodingRule(ValidationRule):
            @property
            def metadata(self) -> ValidationRuleMetadata:
                return ValidationRuleMetadata(
                    "SYNTAX-0001", "Exploder", ValidationLayer.SYNTAX
                )

            def validate(self, response: Any) -> list[Any]:
                raise ValidationRuleError("boom")

        registry = ValidationRegistry()
        registry.register(_ExplodingRule())
        pipeline = ValidationPipeline(registry)
        with pytest.raises(ValidationRuleError, match="boom"):
            pipeline.run(_analysis_result())
        assert pipeline.state is PipelineState.FAILED

    def test_state_does_not_change_findings(self) -> None:
        """Re-running after COMPLETED yields identical findings (state is inert)."""
        registry = ValidationRegistry()
        registry.register(
            _StubRule(
                "SYNTAX-0001",
                "S",
                ValidationLayer.SYNTAX,
                findings=[_issue("ISS-1", ValidationLayer.SYNTAX)],
            )
        )
        pipeline = ValidationPipeline(registry)
        analysis = _analysis_result()
        first = pipeline.run(analysis)
        assert pipeline.state is PipelineState.COMPLETED
        second = pipeline.run(analysis)
        first_ids = [i.issue_id for i in first.validation_issues]
        second_ids = [i.issue_id for i in second.validation_issues]
        assert first_ids == second_ids == ["ISS-1"]

    def test_invalid_registry_leaves_pipeline_unbuilt(self) -> None:
        with pytest.raises(ValidationPipelineError):
            ValidationPipeline("not a registry")  # type: ignore[arg-type]
