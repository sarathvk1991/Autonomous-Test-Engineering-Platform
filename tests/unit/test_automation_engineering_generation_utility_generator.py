"""The utility generation seam (`automation_engineering.generation.
utility_generator`) and its two peers: `StubUtilityGenerator` (deterministic
test/dev scaffolding + spy) and `LiveUtilityGenerator` (the provider-backed
live implementation).

No test in this module calls a real LLM. `LiveUtilityGenerator` is proven
against a hand-written fake provider (`FakeProvider`, mirroring
`tests/unit/test_automation_engineering_generation_page_object_generator.py`'s
own pattern) that only records the request it received.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from automation_engineering.catalog.models import StepCapture
from automation_engineering.generation.live_utility_generator import (
    LiveGenerationError,
    LiveUtilityGenerator,
)
from automation_engineering.generation.utility_generator import (
    StubUtilityGenerator,
    UtilityGenerationContext,
)
from automation_engineering.reuse.models import GherkinStepNeed
from requirement_intelligence.llm.llm_models import LLMRequest, LLMResponse, LLMUsage
from requirement_intelligence.llm.providers.base_provider import LLMProvider
from shared.enums.base import ExecutionStatus, ProviderType

pytestmark = pytest.mark.unit


def _need(text: str = "read a test-data value by key") -> GherkinStepNeed:
    return GherkinStepNeed(text=text, step_type="UtilityAction", captures=())


def _context(
    need: GherkinStepNeed | None = None, **overrides: object
) -> UtilityGenerationContext:
    defaults: dict[str, object] = {
        "need": need if need is not None else _need(),
        "class_name": "TestDataReader",
        "target_package": "com.automation.utils",
        "customqa_constraints": ("c1",),
    }
    defaults.update(overrides)
    return UtilityGenerationContext(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# StubUtilityGenerator
# ---------------------------------------------------------------------------


class TestStubUtilityGenerator:
    def test_returns_canned_java_source_for_a_registered_need_text(self) -> None:
        need = _need("read a test-data value by key")
        stub = StubUtilityGenerator({need.text: "package com.automation.utils;\n"})

        result = stub.generate(_context(need))

        assert result == "package com.automation.utils;\n"

    def test_raises_rather_than_inventing_java_for_an_unmapped_need(self) -> None:
        stub = StubUtilityGenerator({})
        with pytest.raises(KeyError):
            stub.generate(_context())

    def test_call_count_and_received_contexts_are_a_spy(self) -> None:
        need_a = _need("read a test-data value by key")
        need_b = _need("format a date")
        stub = StubUtilityGenerator({need_a.text: "A", need_b.text: "B"})

        stub.generate(_context(need_a))
        stub.generate(_context(need_b))

        assert stub.call_count == 2
        assert [c.need.text for c in stub.received_contexts] == [need_a.text, need_b.text]

    def test_is_explicitly_marked_as_non_production(self) -> None:
        doc = StubUtilityGenerator.__doc__ or ""
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
# LiveUtilityGenerator
# ---------------------------------------------------------------------------


class FakeProvider(LLMProvider):
    """Records every request it receives; returns/raises what the test
    configures. A hand-written fake, not a mock-library double, so this test
    module stays honest about exactly what `LLMProvider` contract
    `LiveUtilityGenerator` actually depends on."""

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
        generator = LiveUtilityGenerator(provider)

        generator.generate(_context())

        sent_prompt = provider.requests[0].prompt
        assert sent_prompt.startswith(
            "You are a test automation engineer writing stateless Java utility classes"
        )
        assert "customqa:long-method" in sent_prompt
        # The evidenced boundary is honest, not fabricated as a customqa:* rule.
        assert "customqa:direct-webdriver-action" not in sent_prompt
        assert "webdriver" in sent_prompt.lower()

    def test_input_block_carries_every_field_the_seam_context_names(self) -> None:
        need = GherkinStepNeed(
            text="format a date as yyyy-mm-dd",
            step_type="UtilityAction",
            captures=(StepCapture(index=0, style="cucumber_expression", expression_type="string"),),
        )
        context = _context(
            need,
            class_name="DateFormatter",
            target_package="com.automation.utils",
            customqa_constraints=("rule-a", "rule-b"),
        )
        provider = FakeProvider()
        generator = LiveUtilityGenerator(provider)

        generator.generate(context)

        payload = _sent_input_payload(provider.requests[0].prompt)
        assert payload["action_text"] == need.text
        assert payload["class_name"] == "DateFormatter"
        assert payload["target_package"] == "com.automation.utils"
        assert payload["customqa_constraints"] == ["rule-a", "rule-b"]
        assert payload["captures"] == [
            {"index": 0, "style": "cucumber_expression", "expression_type": "string"}
        ]

    def test_same_context_yields_byte_identical_prompt_across_independent_calls(self) -> None:
        context = _context()
        first_provider = FakeProvider()
        second_provider = FakeProvider()

        LiveUtilityGenerator(first_provider).generate(context)
        LiveUtilityGenerator(second_provider).generate(context)

        assert first_provider.requests[0].prompt == second_provider.requests[0].prompt

    def test_different_needs_yield_different_prompts(self) -> None:
        provider = FakeProvider()
        generator = LiveUtilityGenerator(provider)

        generator.generate(_context(_need("read a test-data value by key")))
        generator.generate(_context(_need("format a date")))

        assert provider.requests[0].prompt != provider.requests[1].prompt

    def test_exactly_one_provider_call_per_generate_no_retry(self) -> None:
        provider = FakeProvider()
        generator = LiveUtilityGenerator(provider)

        generator.generate(_context())

        assert provider.call_count == 1


class TestLlmBoundaryErrorHandling:
    def test_provider_exception_is_wrapped_and_chained(self) -> None:
        provider = FakeProvider(raises=RuntimeError("connection reset"))
        generator = LiveUtilityGenerator(provider)

        with pytest.raises(LiveGenerationError, match="LLM provider call failed") as excinfo:
            generator.generate(_context())
        assert isinstance(excinfo.value.__cause__, RuntimeError)

    def test_non_completed_execution_status_raises(self) -> None:
        provider = FakeProvider(execution_status=ExecutionStatus.TIMEOUT)
        generator = LiveUtilityGenerator(provider)

        with pytest.raises(LiveGenerationError, match="did not complete"):
            generator.generate(_context())

    def test_empty_response_raises(self) -> None:
        provider = FakeProvider(text="")
        generator = LiveUtilityGenerator(provider)

        with pytest.raises(LiveGenerationError, match="empty response"):
            generator.generate(_context())

    def test_whitespace_only_response_raises(self) -> None:
        provider = FakeProvider(text="   \n  \n")
        generator = LiveUtilityGenerator(provider)

        with pytest.raises(LiveGenerationError, match="empty response"):
            generator.generate(_context())

    def test_completed_non_empty_response_is_returned_verbatim(self) -> None:
        java = (
            "package com.automation.utils;\n\n"
            "public final class ConfigReader {\n"
            "    private ConfigReader() {}\n"
            "}\n"
        )
        provider = FakeProvider(text=java)
        generator = LiveUtilityGenerator(provider)

        result = generator.generate(_context())

        assert result == java
