"""The test-data generation seam (`automation_engineering.generation.
test_data_generator`) and its two peers: `StubTestDataGenerator`
(deterministic test/dev scaffolding + spy) and `LiveTestDataGenerator` (the
provider-backed live implementation).

Unlike the other three generators' own seam tests, this module's context
fixtures are built around a `TestDataSpecification` (fields + required
positive/negative/boundary variants), never a `GherkinStepNeed` -- this
generator's own input-shape break (see
`automation_engineering.generation.test_data_orchestrator`'s own module
docstring). `TestDataSpecification` is the REAL Layer 2 -> Layer 3 boundary
contract (`contracts.test_data_specification`) -- it carries no
`target_class_name`/`target_package` (Layer 2's own contract stays
Java-shape-free, ADR-0043 D7), so this module's `_context` fixture supplies
those on `TestDataGenerationContext` directly, the same way the orchestrator
itself does.

No test in this module calls a real LLM. `LiveTestDataGenerator` is proven
against a hand-written fake provider (`FakeProvider`, mirroring
`tests/unit/test_automation_engineering_generation_utility_generator.py`'s
own pattern) that only records the request it received.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from automation_engineering.generation.live_test_data_generator import (
    LiveGenerationError,
    LiveTestDataGenerator,
)
from automation_engineering.generation.test_data_generator import (
    StubTestDataGenerator,
    TestDataGenerationContext,
)
from contracts.test_data_specification import TestDataFieldSpec, TestDataSpecification
from contracts.testable_requirement import PolarityHint
from requirement_intelligence.llm.llm_models import LLMRequest, LLMResponse, LLMUsage
from requirement_intelligence.llm.providers.base_provider import LLMProvider
from shared.enums.base import ExecutionStatus, ProviderType

pytestmark = pytest.mark.unit


def _specification(
    requirement_id: str = "REQ-checkout01",
    fields: tuple[TestDataFieldSpec, ...] | None = None,
) -> TestDataSpecification:
    default_fields = (
        TestDataFieldSpec(field_name="username", required_variants=(PolarityHint.POSITIVE,)),
    )
    return TestDataSpecification(
        requirement_id=requirement_id,
        fields=fields if fields is not None else default_fields,
    )


def _context(
    specification: TestDataSpecification | None = None, **overrides: object
) -> TestDataGenerationContext:
    defaults: dict[str, object] = {
        "specification": specification if specification is not None else _specification(),
        "class_name": "CheckoutTestData",
        "target_package": "com.automation.utils",
        "customqa_constraints": ("c1",),
    }
    defaults.update(overrides)
    return TestDataGenerationContext(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# StubTestDataGenerator
# ---------------------------------------------------------------------------


class TestStubTestDataGenerator:
    def test_returns_canned_java_source_for_a_registered_requirement_id(self) -> None:
        spec = _specification(requirement_id="REQ-checkout01")
        stub = StubTestDataGenerator({"REQ-checkout01": "package com.automation.utils;\n"})

        result = stub.generate(_context(spec))

        assert result == "package com.automation.utils;\n"

    def test_raises_rather_than_inventing_java_for_an_unmapped_requirement(self) -> None:
        stub = StubTestDataGenerator({})
        with pytest.raises(KeyError):
            stub.generate(_context())

    def test_call_count_and_received_contexts_are_a_spy(self) -> None:
        spec_a = _specification(requirement_id="REQ-a")
        spec_b = _specification(requirement_id="REQ-b")
        stub = StubTestDataGenerator({"REQ-a": "A", "REQ-b": "B"})

        stub.generate(_context(spec_a))
        stub.generate(_context(spec_b))

        assert stub.call_count == 2
        assert [c.specification.requirement_id for c in stub.received_contexts] == [
            "REQ-a",
            "REQ-b",
        ]

    def test_is_explicitly_marked_as_non_production(self) -> None:
        doc = StubTestDataGenerator.__doc__ or ""
        assert "test/dev scaffolding" in doc.lower() or "never the production path" in doc.lower()


# ---------------------------------------------------------------------------
# No live LLM involvement in the seam/orchestration modules
# ---------------------------------------------------------------------------


class TestNoLiveLlmInvolvementInTheSeamItself:
    def test_generation_package_never_imports_llm_factory(self) -> None:
        generation_dir = Path("automation_engineering/generation")
        for py_file in generation_dir.glob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "llm_factory" not in alias.name, f"{py_file}: imports {alias.name}"
                elif isinstance(node, ast.ImportFrom) and node.module:
                    assert "llm_factory" not in node.module, (
                        f"{py_file}: imports from {node.module}"
                    )


# ---------------------------------------------------------------------------
# LiveTestDataGenerator
# ---------------------------------------------------------------------------


class FakeProvider(LLMProvider):
    """Records every request it receives; returns/raises what the test
    configures. A hand-written fake, not a mock-library double, so this test
    module stays honest about exactly what `LLMProvider` contract
    `LiveTestDataGenerator` actually depends on."""

    def __init__(
        self,
        *,
        text: str = "package com.automation.utils;\n",
        execution_status: ExecutionStatus = ExecutionStatus.COMPLETED,
        raises: Exception | None = None,
    ) -> None:
        self._text = text
        self._execution_status = execution_status
        self._raises = raises
        self.requests: list[LLMRequest] = []

    @property
    def provider_name(self) -> str:
        return "fake"

    def validate_connection(self) -> bool:
        return True

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        if self._raises is not None:
            raise self._raises
        return LLMResponse(
            provider=ProviderType.GEMINI,
            model="fake-model",
            generated_text=self._text,
            execution_status=self._execution_status,
            usage=LLMUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        )

    @property
    def call_count(self) -> int:
        return len(self.requests)


def _sent_input_payload(prompt: str) -> dict[str, object]:
    """Extract the JSON input block substituted for `{artifact_context}` --
    the first (and, by the template's own contract, only) `{` in the
    rendered prompt starts it."""
    decoder = json.JSONDecoder()
    payload: dict[str, object]
    payload, _ = decoder.raw_decode(prompt, prompt.index("{"))
    return payload


class TestInputAssemblyDeterminism:
    def test_prompt_carries_the_governed_template_verbatim(self) -> None:
        provider = FakeProvider()
        generator = LiveTestDataGenerator(provider)

        generator.generate(_context())

        sent_prompt = provider.requests[0].prompt
        assert sent_prompt.startswith(
            "You are a test automation engineer writing Java test-data classes"
        )
        assert "customqa:long-method" in sent_prompt
        # The env/data boundary is asked for at the prompt level too.
        assert "configreader.env" in sent_prompt.lower()

    def test_input_block_carries_every_field_the_seam_context_names(self) -> None:
        spec = _specification(
            requirement_id="REQ-login01",
            fields=(
                TestDataFieldSpec(
                    field_name="username",
                    required_variants=(PolarityHint.POSITIVE, PolarityHint.BOUNDARY),
                ),
            ),
        )
        context = _context(
            spec,
            class_name="LoginTestData",
            target_package="com.automation.utils",
            customqa_constraints=("rule-a", "rule-b"),
        )
        provider = FakeProvider()
        generator = LiveTestDataGenerator(provider)

        generator.generate(context)

        payload = _sent_input_payload(provider.requests[0].prompt)
        assert payload["requirement_id"] == "REQ-login01"
        assert payload["target_class_name"] == "LoginTestData"
        assert payload["target_package"] == "com.automation.utils"
        assert payload["customqa_constraints"] == ["rule-a", "rule-b"]
        assert payload["fields"] == [
            {"field_name": "username", "required_variants": ["boundary", "positive"]}
        ]

    def test_same_context_yields_byte_identical_prompt_across_independent_calls(self) -> None:
        context = _context()
        first_provider = FakeProvider()
        second_provider = FakeProvider()

        LiveTestDataGenerator(first_provider).generate(context)
        LiveTestDataGenerator(second_provider).generate(context)

        assert first_provider.requests[0].prompt == second_provider.requests[0].prompt

    def test_different_specifications_yield_different_prompts(self) -> None:
        provider = FakeProvider()
        generator = LiveTestDataGenerator(provider)

        generator.generate(_context(_specification(requirement_id="REQ-a")))
        generator.generate(_context(_specification(requirement_id="REQ-b")))

        assert provider.requests[0].prompt != provider.requests[1].prompt

    def test_exactly_one_provider_call_per_generate_no_retry(self) -> None:
        provider = FakeProvider()
        generator = LiveTestDataGenerator(provider)

        generator.generate(_context())

        assert provider.call_count == 1


class TestLlmBoundaryErrorHandling:
    def test_provider_exception_is_wrapped_and_chained(self) -> None:
        provider = FakeProvider(raises=RuntimeError("connection reset"))
        generator = LiveTestDataGenerator(provider)

        with pytest.raises(LiveGenerationError, match="LLM provider call failed") as excinfo:
            generator.generate(_context())
        assert isinstance(excinfo.value.__cause__, RuntimeError)

    def test_non_completed_execution_status_raises(self) -> None:
        provider = FakeProvider(execution_status=ExecutionStatus.TIMEOUT)
        generator = LiveTestDataGenerator(provider)

        with pytest.raises(LiveGenerationError, match="did not complete"):
            generator.generate(_context())

    def test_empty_response_raises(self) -> None:
        provider = FakeProvider(text="")
        generator = LiveTestDataGenerator(provider)

        with pytest.raises(LiveGenerationError, match="empty response"):
            generator.generate(_context())

    def test_whitespace_only_response_raises(self) -> None:
        provider = FakeProvider(text="   \n  \n")
        generator = LiveTestDataGenerator(provider)

        with pytest.raises(LiveGenerationError, match="empty response"):
            generator.generate(_context())

    def test_completed_non_empty_response_is_returned_verbatim(self) -> None:
        java = (
            "package com.automation.utils;\n\n"
            "public final class CheckoutTestData {\n"
            "    private CheckoutTestData() {}\n"
            "}\n"
        )
        provider = FakeProvider(text=java)
        generator = LiveTestDataGenerator(provider)

        result = generator.generate(_context())

        assert result == java
