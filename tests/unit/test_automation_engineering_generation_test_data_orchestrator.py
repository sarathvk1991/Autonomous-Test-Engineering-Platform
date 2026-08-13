"""Spec-driven test-data orchestration
(`automation_engineering.generation.test_data_orchestrator`) -- proves,
deterministically and without any live call:

* Generation: a representative `TestDataSpecification` (matching ADR-0043
  D7's own prose contract -- fields + required positive/negative/boundary
  variants) -> the stub seam IS called -> a Java test-data class lands in
  `com.automation.utils`, matching the tracked baseline's own `ConfigReader`
  shape (final class, private constructor, static members).
* THE REUSE RESOLUTION, proven directly: test-data is SPEC-DRIVEN, not
  reuse-first -- there is no NO_MATCH/TRUSTED_REUSE/ESCALATION branching at
  all. EVERY specification calls the generation seam, every time, proven by
  the spy across MULTIPLE DIFFERENT specifications (never a "second
  identical spec reuses the first's output" shortcut).
* customqa:* constraints injected -- ONLY `customqa:long-method` (the
  evidenced one; `customqa:direct-webdriver-action` is deliberately absent,
  test-data never touches WebDriver).
* THE ENV/DATA BOUNDARY, enforced not merely requested: a generated class
  that calls `ConfigReader.env(...)` or references an `env.*` config key
  raises `TestDataBoundaryError` -- proven for both a live-shaped violation
  and a clean pass, and for a bare `env.` string literal (not only a
  `ConfigReader.env(` call) -- deterministic, no Sonar/CP3 dependency.
* Determinism; no live LLM or embedding-provider import anywhere in this
  orchestration.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from automation_engineering.generation.models import GeneratedTestDataClass
from automation_engineering.generation.test_data_generator import StubTestDataGenerator
from automation_engineering.generation.test_data_orchestrator import (
    DEFAULT_CUSTOMQA_TEST_DATA_CONSTRAINTS,
    DEFAULT_TEST_DATA_TARGET_PACKAGE,
    TestDataBoundaryError,
    derive_test_data_class_name,
    generate_test_data_class,
    generate_test_data_classes,
)
from contracts.test_data_specification import TestDataFieldSpec, TestDataSpecification
from contracts.testable_requirement import PolarityHint
from requirement_intelligence.llm.generation_identity import GenerationIdentity

pytestmark = pytest.mark.unit

_COMPLIANT_JAVA = (
    "package com.automation.utils;\n\n"
    "public final class CheckoutTestData {\n\n"
    "    public static final String VALID_USERNAME = ConfigReader.data(\"username\");\n"
    "    public static final String BOUNDARY_USERNAME = "
    "ConfigReader.data(\"username.boundary\");\n\n"
    "    private CheckoutTestData() {\n"
    "    }\n"
    "}\n"
)


def _specification(
    requirement_id: str = "REQ-checkout01",
    fields: tuple[TestDataFieldSpec, ...] | None = None,
) -> TestDataSpecification:
    default_fields = (
        TestDataFieldSpec(
            field_name="username",
            required_variants=(PolarityHint.POSITIVE, PolarityHint.BOUNDARY),
        ),
    )
    return TestDataSpecification(
        requirement_id=requirement_id,
        fields=fields if fields is not None else default_fields,
    )


# ---------------------------------------------------------------------------
# Generation -- always, per specification
# ---------------------------------------------------------------------------


class TestGenerationAlwaysHappens:
    def test_generates_a_test_data_class_in_com_automation_utils(self) -> None:
        spec = _specification()
        generator = StubTestDataGenerator({spec.requirement_id: _COMPLIANT_JAVA})

        outcome = generate_test_data_class(spec, generator)

        assert isinstance(outcome, GeneratedTestDataClass)
        assert outcome.specification == spec
        assert outcome.java_source == _COMPLIANT_JAVA
        assert "final class" in outcome.java_source
        assert "private CheckoutTestData()" in outcome.java_source
        assert (
            outcome.target_package
            == DEFAULT_TEST_DATA_TARGET_PACKAGE
            == "com.automation.utils"
        )
        assert outcome.class_name == derive_test_data_class_name("REQ-checkout01")
        assert generator.call_count == 1

    def test_generator_is_called_exactly_once_per_specification(self) -> None:
        spec = _specification()
        generator = StubTestDataGenerator({spec.requirement_id: _COMPLIANT_JAVA})

        generate_test_data_class(spec, generator)

        assert generator.call_count == 1


class TestReuseResolutionIsSpecDrivenNotReuseFirst:
    """THE reuse-resolution proof this build's verification section
    requires: EVERY specification generates, every time -- there is no
    reuse decision, no catalog lookup, no bind path at all."""

    def test_two_different_specifications_both_generate_independently(self) -> None:
        spec_a = _specification(requirement_id="REQ-a")
        spec_b = _specification(requirement_id="REQ-b")
        generator = StubTestDataGenerator(
            {"REQ-a": _COMPLIANT_JAVA, "REQ-b": _COMPLIANT_JAVA.replace("Checkout", "B")}
        )

        outcomes = generate_test_data_classes([spec_a, spec_b], generator)

        assert len(outcomes) == 2
        assert all(isinstance(o, GeneratedTestDataClass) for o in outcomes)
        assert generator.call_count == 2  # BOTH generated -- no skip, no reuse

    def test_module_never_imports_the_reuse_engine(self) -> None:
        """A structural guard: this orchestrator's own IMPORT statements
        never bring in the reuse engine or its matcher -- the reuse
        resolution is not merely "unused in these tests," it is absent
        from the module's own code (the module's prose docstring is free
        to mention `decide_reuse` by name when explaining why it is never
        called; only actual imports are checked here)."""
        source = Path("automation_engineering/generation/test_data_orchestrator.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        imported_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)
            elif isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)

        assert not any("reuse" in module_name for module_name in imported_modules)

    def test_module_docstring_records_the_reuse_resolution_and_its_reasoning(self) -> None:
        import automation_engineering.generation.test_data_orchestrator as module

        doc = (module.__doc__ or "").lower()
        assert "spec-driven" in doc
        assert "decide_reuse" in doc
        assert "reuse-first" in doc


# ---------------------------------------------------------------------------
# customqa:* constraint injection -- ONLY long-method is evidenced
# ---------------------------------------------------------------------------


class TestCustomqaConstraintsAreInjectedIntoGeneration:
    def test_default_constraints_reach_the_generation_seam(self) -> None:
        spec = _specification()
        generator = StubTestDataGenerator({spec.requirement_id: _COMPLIANT_JAVA})

        generate_test_data_class(spec, generator)

        received = generator.received_contexts[0]
        assert received.customqa_constraints == DEFAULT_CUSTOMQA_TEST_DATA_CONSTRAINTS
        assert any("customqa:long-method" in c for c in received.customqa_constraints)
        # The honest negative: direct-webdriver-action is NOT fabricated here.
        assert not any(
            "customqa:direct-webdriver-action" in c for c in received.customqa_constraints
        )

    def test_caller_supplied_constraints_reach_the_generation_seam(self) -> None:
        spec = _specification()
        generator = StubTestDataGenerator({spec.requirement_id: _COMPLIANT_JAVA})
        custom_constraints = ("custom-rule-one", "custom-rule-two")

        generate_test_data_class(spec, generator, customqa_constraints=custom_constraints)

        received = generator.received_contexts[0]
        assert received.customqa_constraints == custom_constraints

    def test_target_package_is_passed_through_to_the_outcome(self) -> None:
        spec = _specification()
        generator = StubTestDataGenerator({spec.requirement_id: _COMPLIANT_JAVA})

        outcome = generate_test_data_class(spec, generator, target_package="com.custom.utils")

        assert outcome.target_package == "com.custom.utils"


# ---------------------------------------------------------------------------
# THE ENV/DATA BOUNDARY -- enforced deterministically
# ---------------------------------------------------------------------------


class TestEnvDataBoundaryIsEnforced:
    def test_configreader_env_call_raises(self) -> None:
        spec = _specification()
        violating_java = _COMPLIANT_JAVA.replace("ConfigReader.data", "ConfigReader.env")
        generator = StubTestDataGenerator({spec.requirement_id: violating_java})

        with pytest.raises(TestDataBoundaryError, match=r"ConfigReader\.env"):
            generate_test_data_class(spec, generator)

    def test_bare_env_dot_config_key_literal_raises(self) -> None:
        """Not only a `ConfigReader.env(` call -- a bare `"env.something"`
        string literal (e.g. a stray key reference) is caught too."""
        spec = _specification()
        violating_java = (
            "package com.automation.utils;\n\n"
            "public final class CheckoutTestData {\n"
            "    public static final String BASE = \"env.base.url\";\n"
            "    private CheckoutTestData() {\n"
            "    }\n"
            "}\n"
        )
        generator = StubTestDataGenerator({spec.requirement_id: violating_java})

        with pytest.raises(TestDataBoundaryError):
            generate_test_data_class(spec, generator)

    def test_compliant_data_only_source_passes_clean(self) -> None:
        spec = _specification()
        generator = StubTestDataGenerator({spec.requirement_id: _COMPLIANT_JAVA})

        outcome = generate_test_data_class(spec, generator)

        assert isinstance(outcome, GeneratedTestDataClass)
        assert "ConfigReader.data" in outcome.java_source
        assert "ConfigReader.env" not in outcome.java_source

    def test_literal_constant_with_no_config_reader_at_all_also_passes(self) -> None:
        """The boundary only prohibits ENV binding -- a class that never
        touches ConfigReader at all (pure literal constants) is fine."""
        spec = _specification()
        literal_java = (
            "package com.automation.utils;\n\n"
            "public final class CheckoutTestData {\n"
            "    public static final String EXPECTED_LABEL = \"Checkout complete\";\n"
            "    private CheckoutTestData() {\n"
            "    }\n"
            "}\n"
        )
        generator = StubTestDataGenerator({spec.requirement_id: literal_java})

        outcome = generate_test_data_class(spec, generator)

        assert isinstance(outcome, GeneratedTestDataClass)


# ---------------------------------------------------------------------------
# Batch orchestration, determinism, and no live LLM call anywhere here
# ---------------------------------------------------------------------------


class TestBatchOrchestration:
    def test_generate_test_data_classes_processes_each_specification_in_order(self) -> None:
        spec_a = _specification(requirement_id="REQ-a")
        spec_b = _specification(requirement_id="REQ-b")
        spec_c = _specification(requirement_id="REQ-c")
        generator = StubTestDataGenerator(
            {
                "REQ-a": _COMPLIANT_JAVA,
                "REQ-b": _COMPLIANT_JAVA,
                "REQ-c": _COMPLIANT_JAVA,
            }
        )

        outcomes = generate_test_data_classes([spec_a, spec_b, spec_c], generator)

        assert [o.specification.requirement_id for o in outcomes] == ["REQ-a", "REQ-b", "REQ-c"]
        assert generator.call_count == 3


class TestDeterminism:
    def test_same_inputs_yield_the_same_outcome(self) -> None:
        spec = _specification()

        first = generate_test_data_class(
            spec, StubTestDataGenerator({spec.requirement_id: _COMPLIANT_JAVA})
        )
        second = generate_test_data_class(
            spec, StubTestDataGenerator({spec.requirement_id: _COMPLIANT_JAVA})
        )

        assert first == second


class TestNoLiveLlmInvolvementInOrchestration:
    def test_orchestrator_module_never_imports_llm_factory_or_an_embedding_provider(
        self,
    ) -> None:
        source = Path("automation_engineering/generation/test_data_orchestrator.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "llm_factory" not in alias.name
                    assert "embeddings" not in alias.name
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert "llm_factory" not in node.module
                assert "embeddings" not in node.module


class _IdentityCapturingGenerator:
    """A minimal hand-written double exposing exactly the `.generate`/
    `.last_identity` shape `LiveTestDataGenerator` exposes -- see
    `test_automation_engineering_generation_orchestrator.py`'s own identical
    double for the step-definition seam."""

    def __init__(self, java_source: str, identity: GenerationIdentity) -> None:
        self._java_source = java_source
        self.last_identity = identity

    def generate(self, context: object) -> str:
        return self._java_source


class TestGenerationIdentityThreading:
    """The re-run/delta-scoped-regeneration cluster's own pinning foundation
    (2026-08-13) -- purely additive: `StubTestDataGenerator` (every other
    test in this file) has no `last_identity` attribute, degrading to `None`
    via `getattr`, never an `AttributeError`."""

    def test_generated_outcome_carries_the_generators_own_identity(self) -> None:
        spec = _specification()
        identity = GenerationIdentity(
            prompt_id="generate_test_data",
            prompt_version="1.0.0",
            prompt_sha256="0" * 64,
            provider="gemini",
            model="fake-model",
        )
        generator = _IdentityCapturingGenerator(_COMPLIANT_JAVA, identity)

        outcome = generate_test_data_class(spec, generator)

        assert outcome.generation_identity == identity

    def test_stub_generator_with_no_last_identity_attribute_yields_none(self) -> None:
        spec = _specification()
        generator = StubTestDataGenerator({spec.requirement_id: _COMPLIANT_JAVA})

        outcome = generate_test_data_class(spec, generator)

        assert outcome.generation_identity is None
