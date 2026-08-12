"""The step-definition generation seam (`automation_engineering.generation.
step_definition_generator`) and its two peers: `StubStepDefinitionGenerator`
(deterministic test/dev scaffolding + spy) and `LiveStepDefinitionGenerator`
(the provider-backed live implementation).

No test in this module calls a real LLM. `LiveStepDefinitionGenerator` is
proven against a hand-written fake provider (`FakeProvider`, mirroring
`tests/unit/test_feature_engineering_live_content_generator.py`'s own
pattern) that only records the request it received.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from automation_engineering.catalog.models import StepCapture
from automation_engineering.generation.live_step_definition_generator import (
    CALL_TYPE,
    LiveGenerationError,
    LiveStepDefinitionGenerator,
)
from automation_engineering.generation.step_definition_generator import (
    StepDefinitionGenerationContext,
    StubStepDefinitionGenerator,
)
from automation_engineering.reuse.models import GherkinStepNeed
from requirement_intelligence.llm.llm_exceptions import ProviderGenerationError
from requirement_intelligence.llm.llm_models import LLMRequest, LLMResponse, LLMUsage
from requirement_intelligence.llm.providers.base_provider import LLMProvider
from requirement_intelligence.llm.token_usage import TokenUsageTracker
from shared.enums.base import ExecutionStatus, ProviderType

pytestmark = pytest.mark.unit


def _need(text: str = "I log in as {string}") -> GherkinStepNeed:
    return GherkinStepNeed(
        text=text,
        step_type="When",
        captures=(StepCapture(index=0, style="cucumber_expression", expression_type="string"),),
    )


def _context(
    need: GherkinStepNeed | None = None, **overrides: object
) -> StepDefinitionGenerationContext:
    defaults: dict[str, object] = {
        "need": need if need is not None else _need(),
        "target_package": "com.automation.steps",
        "customqa_constraints": ("c1", "c2"),
    }
    defaults.update(overrides)
    return StepDefinitionGenerationContext(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# StubStepDefinitionGenerator
# ---------------------------------------------------------------------------


class TestStubStepDefinitionGenerator:
    def test_returns_canned_java_source_for_a_registered_step_text(self) -> None:
        need = _need("I log in as {string}")
        stub = StubStepDefinitionGenerator({need.text: "package com.automation.steps;\n"})

        result = stub.generate(_context(need))

        assert result == "package com.automation.steps;\n"

    def test_raises_rather_than_inventing_java_for_an_unmapped_step(self) -> None:
        stub = StubStepDefinitionGenerator({})
        with pytest.raises(KeyError):
            stub.generate(_context())

    def test_call_count_and_received_contexts_are_a_spy(self) -> None:
        need_a = _need("I log in as {string}")
        need_b = _need("I log out")
        stub = StubStepDefinitionGenerator({need_a.text: "A", need_b.text: "B"})

        stub.generate(_context(need_a))
        stub.generate(_context(need_b))

        assert stub.call_count == 2
        assert [c.need.text for c in stub.received_contexts] == [need_a.text, need_b.text]

    def test_is_explicitly_marked_as_non_production(self) -> None:
        doc = StubStepDefinitionGenerator.__doc__ or ""
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
# LiveStepDefinitionGenerator
# ---------------------------------------------------------------------------


class FakeProvider(LLMProvider):
    """Records every request it receives; returns/raises what the test
    configures. A hand-written fake, not a mock-library double, so this test
    module stays honest about exactly what `LLMProvider` contract
    `LiveStepDefinitionGenerator` actually depends on."""

    def __init__(
        self,
        *,
        text: str = "package com.automation.steps;\n",
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
        generator = LiveStepDefinitionGenerator(provider)

        generator.generate(_context())

        sent_prompt = provider.requests[0].prompt
        assert sent_prompt.startswith(
            "You are a test automation engineer writing Java step-definition glue classes"
        )
        assert "customqa:direct-webdriver-action" in sent_prompt
        assert "customqa:long-method" in sent_prompt

    def test_input_block_carries_every_field_the_seam_context_names(self) -> None:
        need = _need("I log in as {string} with password {string}")
        context = _context(
            need,
            target_package="com.automation.steps",
            customqa_constraints=("rule-a", "rule-b"),
            page_object_interface="com.automation.pages.LoginPage",
        )
        provider = FakeProvider()
        generator = LiveStepDefinitionGenerator(provider)

        generator.generate(context)

        payload = _sent_input_payload(provider.requests[0].prompt)
        assert payload["step_text"] == need.text
        assert payload["step_type"] == "When"
        assert payload["target_package"] == "com.automation.steps"
        assert payload["customqa_constraints"] == ["rule-a", "rule-b"]
        assert payload["page_object_interface"] == "com.automation.pages.LoginPage"
        assert payload["captures"] == [
            {"index": 0, "style": "cucumber_expression", "expression_type": "string"}
        ]

    def test_page_object_interface_null_when_none(self) -> None:
        provider = FakeProvider()
        generator = LiveStepDefinitionGenerator(provider)

        generator.generate(_context())

        payload = _sent_input_payload(provider.requests[0].prompt)
        assert payload["page_object_interface"] is None

    def test_same_context_yields_byte_identical_prompt_across_independent_calls(self) -> None:
        context = _context()
        first_provider = FakeProvider()
        second_provider = FakeProvider()

        LiveStepDefinitionGenerator(first_provider).generate(context)
        LiveStepDefinitionGenerator(second_provider).generate(context)

        assert first_provider.requests[0].prompt == second_provider.requests[0].prompt

    def test_different_step_texts_yield_different_prompts(self) -> None:
        provider = FakeProvider()
        generator = LiveStepDefinitionGenerator(provider)

        generator.generate(_context(_need("I log in as {string}")))
        generator.generate(_context(_need("I log out")))

        assert provider.requests[0].prompt != provider.requests[1].prompt

    def test_exactly_one_provider_call_per_generate_no_retry(self) -> None:
        provider = FakeProvider()
        generator = LiveStepDefinitionGenerator(provider)

        generator.generate(_context())

        assert provider.call_count == 1


class TestLlmBoundaryErrorHandling:
    def test_provider_exception_is_wrapped_and_chained(self) -> None:
        provider = FakeProvider(raises=RuntimeError("connection reset"))
        generator = LiveStepDefinitionGenerator(provider)

        with pytest.raises(LiveGenerationError, match="LLM provider call failed") as excinfo:
            generator.generate(_context())
        assert isinstance(excinfo.value.__cause__, RuntimeError)

    def test_non_completed_execution_status_raises(self) -> None:
        provider = FakeProvider(execution_status=ExecutionStatus.TIMEOUT)
        generator = LiveStepDefinitionGenerator(provider)

        with pytest.raises(LiveGenerationError, match="did not complete"):
            generator.generate(_context())

    def test_a_malformed_response_from_the_provider_escalates_not_crashes(self) -> None:
        """The MALFORMED_RESPONSE crash fix, proven at this boundary: a
        `ProviderGenerationError` (what `GeminiProvider._map_response` now
        raises for a None-text/non-STOP response, instead of letting a raw
        pydantic `ValidationError` escape) is caught by this generator's own
        pre-existing provider-exception boundary EXACTLY like any other
        provider failure -- no crash, a clean, escalatable
        `LiveGenerationError`, the SAME escalate-one-continue path a 429 or
        a timeout already takes."""
        provider = FakeProvider(
            raises=ProviderGenerationError(
                "Gemini returned no text (finish_reason='MALFORMED_RESPONSE') -- "
                "the model completed the call but produced zero usable content, "
                "a provider-side generation failure distinct from a call/"
                "transport failure."
            )
        )
        generator = LiveStepDefinitionGenerator(provider)

        with pytest.raises(LiveGenerationError, match="MALFORMED_RESPONSE") as excinfo:
            generator.generate(_context())

        assert isinstance(excinfo.value.__cause__, ProviderGenerationError)

    def test_empty_response_raises(self) -> None:
        provider = FakeProvider(text="")
        generator = LiveStepDefinitionGenerator(provider)

        with pytest.raises(LiveGenerationError, match="empty response"):
            generator.generate(_context())

    def test_whitespace_only_response_raises(self) -> None:
        provider = FakeProvider(text="   \n  \n")
        generator = LiveStepDefinitionGenerator(provider)

        with pytest.raises(LiveGenerationError, match="empty response"):
            generator.generate(_context())

    def test_completed_non_empty_response_is_returned_verbatim(self) -> None:
        java = "package com.automation.steps;\n\npublic class LoginSteps {}\n"
        provider = FakeProvider(text=java)
        generator = LiveStepDefinitionGenerator(provider)

        result = generator.generate(_context())

        assert result == java


class TestLiveGeneratorConveysTheRealWebDriverLifecycle:
    """Defect 2's own fix, proven directly: v1.0.0's prompt never conveyed
    HOW a step definition obtains a `WebDriver` to hand to a page object's
    constructor-injected constructor (ADR-0041 D5) -- so the platform's
    pre-existing step-defs construct page objects with `new XPage()`
    (no-arg), incompatible with the constructor-injected page objects
    ADR-0041 D5 (and every generated page-object prompt) requires. v1.1.0
    conveys the real, already-implemented mechanism
    (`com.automation.base.DriverFactory`/`Hooks`, proven by the tracked
    baseline's own `SmokeSteps.java`/`SmokePage.java`) and instructs lazy,
    null-guarded construction instead. This is the INPUT-side proof only --
    that the mechanism reaches the built prompt -- not proof the model
    complies (that is the live regeneration re-run's job)."""

    def test_prompt_uses_v110(self) -> None:
        provider = FakeProvider()
        generator = LiveStepDefinitionGenerator(provider)

        generator.generate(_context())

        assert provider.requests[0].metadata["prompt_version"] == "1.1.0"

    def test_prompt_conveys_the_real_driverfactory_and_hooks_mechanism(self) -> None:
        provider = FakeProvider()
        generator = LiveStepDefinitionGenerator(provider)

        generator.generate(_context())

        sent_prompt = provider.requests[0].prompt
        assert "com.automation.base.DriverFactory" in sent_prompt
        assert "com.automation.base.Hooks" in sent_prompt
        assert "DriverFactory.get()" in sent_prompt

    def test_prompt_cites_the_real_smokesteps_precedent(self) -> None:
        provider = FakeProvider()
        generator = LiveStepDefinitionGenerator(provider)

        generator.generate(_context())

        sent_prompt = provider.requests[0].prompt
        assert "SmokeSteps" in sent_prompt
        assert "SmokePage" in sent_prompt

    def test_prompt_instructs_lazy_construction_not_a_no_arg_constructor(self) -> None:
        provider = FakeProvider()
        generator = LiveStepDefinitionGenerator(provider)

        generator.generate(_context())

        sent_prompt = provider.requests[0].prompt
        assert "new XPage()" in sent_prompt  # named as the thing that never compiles
        assert "without an inline initializer" in sent_prompt
        assert "null check" in sent_prompt.lower()


class TestTokenUsageRecording:
    """Token-usage-by-call-type instrumentation (2026-08-12) -- purely
    additive: a generator given no `usage_recorder` behaves exactly as it
    did before this module existed (every other test in this file proves
    that, implicitly, by never passing one)."""

    def test_successful_call_is_recorded_under_this_generators_own_call_type(self) -> None:
        provider = FakeProvider()
        tracker = TokenUsageTracker()
        generator = LiveStepDefinitionGenerator(provider, usage_recorder=tracker)

        generator.generate(_context())

        totals = tracker.by_call_type()["step_definition_generation"]
        assert totals.call_count == 1
        assert totals.total_tokens == 30
        assert totals.prompt_tokens == 10
        assert totals.completion_tokens == 20

    def test_call_type_matches_the_module_level_constant(self) -> None:
        assert CALL_TYPE == "step_definition_generation"

    def test_no_recorder_is_a_no_op(self) -> None:
        provider = FakeProvider()
        generator = LiveStepDefinitionGenerator(provider)  # no usage_recorder

        result = generator.generate(_context())

        assert result  # generation still succeeds, unaffected by the omission

    def test_a_failed_call_records_nothing(self) -> None:
        provider = FakeProvider(raises=ValueError("boom"))
        tracker = TokenUsageTracker()
        generator = LiveStepDefinitionGenerator(provider, usage_recorder=tracker)

        with pytest.raises(LiveGenerationError):
            generator.generate(_context())

        assert tracker.by_call_type() == {}
