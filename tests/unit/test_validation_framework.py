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

from pathlib import Path
from typing import Any

import pytest

from requirement_intelligence.validation.validation_exceptions import (
    ValidationFrameworkError,
    ValidationPipelineError,
    ValidationRegistryError,
    ValidationRuleError,
)
from requirement_intelligence.validation.validation_pipeline import ValidationPipeline
from requirement_intelligence.validation.validation_registry import ValidationRegistry
from requirement_intelligence.validation.validation_rule import (
    LAYER_ORDER,
    ValidationLayer,
    ValidationRule,
)

# ---------------------------------------------------------------------------
# Minimal concrete stubs — used exclusively within this test module
# ---------------------------------------------------------------------------

_PACKAGE_DIR = Path(__file__).resolve().parents[2] / "requirement_intelligence" / "validation"


class _StubRule(ValidationRule):
    """Minimal concrete rule for testing framework contracts.

    Returns an empty list from validate() to satisfy the abstract contract
    without performing any real validation.
    """

    def __init__(
        self,
        rule_id: str,
        rule_name: str,
        layer: ValidationLayer,
        enabled: bool = True,
        findings: list[Any] | None = None,
    ) -> None:
        self._rule_id = rule_id
        self._rule_name = rule_name
        self._layer = layer
        self._enabled = enabled
        self._findings: list[Any] = findings if findings is not None else []

    @property
    def rule_id(self) -> str:
        return self._rule_id

    @property
    def rule_name(self) -> str:
        return self._rule_name

    @property
    def validation_layer(self) -> ValidationLayer:
        return self._layer

    @property
    def enabled(self) -> bool:
        return self._enabled

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

    def test_run_empty_registry_returns_empty_list(self) -> None:
        registry = ValidationRegistry()
        pipeline = ValidationPipeline(registry)
        result = pipeline.run("any response")
        assert result == []

    def test_run_collects_findings_from_all_rules(self) -> None:
        registry = ValidationRegistry()
        registry.register(
            _StubRule(
                "TRANSPORT-0001", "T", ValidationLayer.TRANSPORT, findings=["finding-t"]
            )
        )
        registry.register(
            _StubRule("SYNTAX-0001", "S", ValidationLayer.SYNTAX, findings=["finding-s"])
        )
        pipeline = ValidationPipeline(registry)
        result = pipeline.run("any response")
        assert "finding-t" in result
        assert "finding-s" in result

    def test_run_respects_rule_execution_order(self) -> None:
        """Findings must appear in layer order, not registration order."""
        registry = ValidationRegistry()
        # Register SCHEMA before SYNTAX intentionally.
        registry.register(
            _StubRule("SCHEMA-0001", "Schema", ValidationLayer.SCHEMA, findings=["schema-finding"])
        )
        registry.register(
            _StubRule(
                "SYNTAX-0001", "Syntax", ValidationLayer.SYNTAX, findings=["syntax-finding"]
            )
        )
        pipeline = ValidationPipeline(registry)
        result = pipeline.run("response")
        # SYNTAX layer precedes SCHEMA layer.
        assert result.index("syntax-finding") < result.index("schema-finding")

    def test_run_passes_response_to_every_rule(self) -> None:
        """Each rule must receive the same response object."""
        received: list[Any] = []

        class _CapturingRule(ValidationRule):
            def __init__(self, rule_id: str, layer: ValidationLayer) -> None:
                self._id = rule_id
                self._layer = layer

            @property
            def rule_id(self) -> str:
                return self._id

            @property
            def rule_name(self) -> str:
                return self._id

            @property
            def validation_layer(self) -> ValidationLayer:
                return self._layer

            def validate(self, response: Any) -> list[Any]:
                received.append(response)
                return []

        registry = ValidationRegistry()
        registry.register(_CapturingRule("TRANSPORT-0001", ValidationLayer.TRANSPORT))
        registry.register(_CapturingRule("SYNTAX-0001", ValidationLayer.SYNTAX))
        pipeline = ValidationPipeline(registry)

        sentinel = object()
        pipeline.run(sentinel)

        assert received == [sentinel, sentinel]

    def test_run_does_not_modify_response(self) -> None:
        """The pipeline must not mutate the response object."""
        registry = ValidationRegistry()
        registry.register(_StubRule("SYNTAX-0001", "S", ValidationLayer.SYNTAX))
        pipeline = ValidationPipeline(registry)

        response = {"key": "original_value"}
        pipeline.run(response)
        assert response == {"key": "original_value"}


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
        assert hasattr(v, "ValidationRegistry")
        assert hasattr(v, "ValidationPipeline")
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
