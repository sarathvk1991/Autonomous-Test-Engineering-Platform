"""The page-object generation seam (`automation_engineering.generation.
page_object_generator`) and its two peers: `StubPageObjectGenerator`
(deterministic test/dev scaffolding + spy) and `LivePageObjectGenerator`
(the provider-backed live implementation).

No test in this module calls a real LLM. `LivePageObjectGenerator` is
proven against a hand-written fake provider (`FakeProvider`, mirroring
`tests/unit/test_automation_engineering_generation_step_definition_generator.py`'s
own pattern) that only records the request it received.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from automation_engineering.catalog.models import StepCapture
from automation_engineering.generation.live_page_object_generator import (
    LiveGenerationError,
    LivePageObjectGenerator,
)
from automation_engineering.generation.models import PageObjectMethodNeed
from automation_engineering.generation.page_object_generator import (
    PageObjectGenerationContext,
    StubPageObjectGenerator,
)
from automation_engineering.reuse.models import GherkinStepNeed
from requirement_intelligence.llm.llm_models import LLMRequest, LLMResponse, LLMUsage
from requirement_intelligence.llm.providers.base_provider import LLMProvider
from shared.enums.base import ExecutionStatus, ProviderType

pytestmark = pytest.mark.unit


def _need(text: str = "click the forgot password link") -> GherkinStepNeed:
    return GherkinStepNeed(text=text, step_type="PageAction", captures=())


def _context(
    need: GherkinStepNeed | None = None, **overrides: object
) -> PageObjectGenerationContext:
    defaults: dict[str, object] = {
        "need": need if need is not None else _need(),
        "class_name": "ForgotPasswordLinkPage",
        "target_package": "com.automation.pages",
        "customqa_constraints": ("c1", "c2"),
    }
    defaults.update(overrides)
    return PageObjectGenerationContext(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# PageObjectGenerationContext.additional_method_needs -- additive, this build
# ---------------------------------------------------------------------------


class TestPageObjectGenerationContextAdditionalMethodNeeds:
    def test_defaults_to_empty_preserving_every_pre_existing_call_site(self) -> None:
        context = _context()
        assert context.additional_method_needs == ()

    def test_carries_extra_method_needs_when_supplied(self) -> None:
        extra = PageObjectMethodNeed(
            need=_need("enter the password"), method_name="enterPassword"
        )
        context = _context(additional_method_needs=(extra,))
        assert context.additional_method_needs == (extra,)


# ---------------------------------------------------------------------------
# StubPageObjectGenerator
# ---------------------------------------------------------------------------


class TestStubPageObjectGenerator:
    def test_returns_canned_java_source_for_a_registered_need_text(self) -> None:
        need = _need("click the forgot password link")
        stub = StubPageObjectGenerator({need.text: "package com.automation.pages;\n"})

        result = stub.generate(_context(need))

        assert result == "package com.automation.pages;\n"

    def test_raises_rather_than_inventing_java_for_an_unmapped_need(self) -> None:
        stub = StubPageObjectGenerator({})
        with pytest.raises(KeyError):
            stub.generate(_context())

    def test_call_count_and_received_contexts_are_a_spy(self) -> None:
        need_a = _need("click the forgot password link")
        need_b = _need("open the checkout page")
        stub = StubPageObjectGenerator({need_a.text: "A", need_b.text: "B"})

        stub.generate(_context(need_a))
        stub.generate(_context(need_b))

        assert stub.call_count == 2
        assert [c.need.text for c in stub.received_contexts] == [need_a.text, need_b.text]

    def test_is_explicitly_marked_as_non_production(self) -> None:
        doc = StubPageObjectGenerator.__doc__ or ""
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
# LivePageObjectGenerator
# ---------------------------------------------------------------------------


class FakeProvider(LLMProvider):
    """Records every request it receives; returns/raises what the test
    configures. A hand-written fake, not a mock-library double, so this test
    module stays honest about exactly what `LLMProvider` contract
    `LivePageObjectGenerator` actually depends on."""

    def __init__(
        self,
        *,
        text: str = "package com.automation.pages;\n",
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
        generator = LivePageObjectGenerator(provider)

        generator.generate(_context())

        sent_prompt = provider.requests[0].prompt
        assert sent_prompt.startswith(
            "You are a test automation engineer writing Java page-object classes"
        )
        assert "customqa:direct-webdriver-action" in sent_prompt
        assert "customqa:long-method" in sent_prompt

    def test_input_block_carries_every_field_the_seam_context_names(self) -> None:
        need = GherkinStepNeed(
            text="log in with a username and password",
            step_type="PageAction",
            captures=(StepCapture(index=0, style="cucumber_expression", expression_type="string"),),
        )
        context = _context(
            need,
            class_name="LoginPage",
            target_package="com.automation.pages",
            customqa_constraints=("rule-a", "rule-b"),
        )
        provider = FakeProvider()
        generator = LivePageObjectGenerator(provider)

        generator.generate(context)

        payload = _sent_input_payload(provider.requests[0].prompt)
        assert payload["action_text"] == need.text
        assert payload["class_name"] == "LoginPage"
        assert payload["target_package"] == "com.automation.pages"
        assert payload["customqa_constraints"] == ["rule-a", "rule-b"]
        assert payload["captures"] == [
            {"index": 0, "style": "cucumber_expression", "expression_type": "string"}
        ]

    def test_same_context_yields_byte_identical_prompt_across_independent_calls(self) -> None:
        context = _context()
        first_provider = FakeProvider()
        second_provider = FakeProvider()

        LivePageObjectGenerator(first_provider).generate(context)
        LivePageObjectGenerator(second_provider).generate(context)

        assert first_provider.requests[0].prompt == second_provider.requests[0].prompt

    def test_different_needs_yield_different_prompts(self) -> None:
        provider = FakeProvider()
        generator = LivePageObjectGenerator(provider)

        generator.generate(_context(_need("click the forgot password link")))
        generator.generate(_context(_need("open the checkout page")))

        assert provider.requests[0].prompt != provider.requests[1].prompt

    def test_exactly_one_provider_call_per_generate_no_retry(self) -> None:
        provider = FakeProvider()
        generator = LivePageObjectGenerator(provider)

        generator.generate(_context())

        assert provider.call_count == 1


class TestLlmBoundaryErrorHandling:
    def test_provider_exception_is_wrapped_and_chained(self) -> None:
        provider = FakeProvider(raises=RuntimeError("connection reset"))
        generator = LivePageObjectGenerator(provider)

        with pytest.raises(LiveGenerationError, match="LLM provider call failed") as excinfo:
            generator.generate(_context())
        assert isinstance(excinfo.value.__cause__, RuntimeError)

    def test_non_completed_execution_status_raises(self) -> None:
        provider = FakeProvider(execution_status=ExecutionStatus.TIMEOUT)
        generator = LivePageObjectGenerator(provider)

        with pytest.raises(LiveGenerationError, match="did not complete"):
            generator.generate(_context())

    def test_empty_response_raises(self) -> None:
        provider = FakeProvider(text="")
        generator = LivePageObjectGenerator(provider)

        with pytest.raises(LiveGenerationError, match="empty response"):
            generator.generate(_context())

    def test_whitespace_only_response_raises(self) -> None:
        provider = FakeProvider(text="   \n  \n")
        generator = LivePageObjectGenerator(provider)

        with pytest.raises(LiveGenerationError, match="empty response"):
            generator.generate(_context())

    def test_completed_non_empty_response_is_returned_verbatim(self) -> None:
        java = "package com.automation.pages;\n\npublic class LoginPage extends BasePage {}\n"
        provider = FakeProvider(text=java)
        generator = LivePageObjectGenerator(provider)

        result = generator.generate(_context())

        assert result == java


_COMPLETE_LOGIN_PAGE_JAVA = (
    "package com.automation.pages;\n\n"
    "public class LoginPage extends BasePage {\n"
    "    public void enterUsername(String username) {}\n"
    "    public void enterPassword(String password) {}\n"
    "    public void clickLogin() {}\n"
    "}\n"
)


def _multi_method_context(
    *, method_name: str | None = "enterUsername", **overrides: object
) -> PageObjectGenerationContext:
    additional = (
        PageObjectMethodNeed(need=_need("enter the password"), method_name="enterPassword"),
        PageObjectMethodNeed(need=_need("click the login button"), method_name="clickLogin"),
    )
    return _context(
        _need("enter the username"),
        class_name="LoginPage",
        method_name=method_name,
        additional_method_needs=additional,
        **overrides,
    )


def _complete_provider() -> FakeProvider:
    return FakeProvider(text=_COMPLETE_LOGIN_PAGE_JAVA)


class TestLiveGeneratorMultiMethod:
    """`generate_page_objects` v1.1.0 -- the multi-method extension this
    build registers and wires. `LivePageObjectGenerator` no longer raises on
    `context.additional_method_needs`; it builds a `methods`-list prompt
    against v1.1.0 and calls the provider, exactly like the single-method
    path always did against v1.0.0."""

    def test_does_not_raise_and_calls_the_provider_exactly_once(self) -> None:
        provider = _complete_provider()
        generator = LivePageObjectGenerator(provider)

        result = generator.generate(_multi_method_context())

        assert result == _COMPLETE_LOGIN_PAGE_JAVA
        assert provider.call_count == 1

    def test_prompt_uses_the_v110_template_not_v100(self) -> None:
        provider = _complete_provider()
        generator = LivePageObjectGenerator(provider)

        generator.generate(_multi_method_context())

        sent_prompt = provider.requests[0].prompt
        assert "VERBATIM" in sent_prompt  # v1.1.0's own OUTPUT CONTRACT language
        assert provider.requests[0].metadata["prompt_version"] == "1.1.0"

    def test_prompt_input_includes_all_three_method_specs_in_order(self) -> None:
        provider = _complete_provider()
        generator = LivePageObjectGenerator(provider)

        generator.generate(_multi_method_context())

        payload = _sent_input_payload(provider.requests[0].prompt)
        assert payload["class_name"] == "LoginPage"
        methods = payload["methods"]
        assert isinstance(methods, list)
        assert [m["method_name"] for m in methods] == [
            "enterUsername",
            "enterPassword",
            "clickLogin",
        ]
        assert [m["action_text"] for m in methods] == [
            "enter the username",
            "enter the password",
            "click the login button",
        ]

    def test_single_method_call_still_uses_v100_unaffected(self) -> None:
        """Regression: a context with no `additional_method_needs` is
        completely unaffected by this build -- same template, same payload
        shape, no `methods` key at all."""
        provider = FakeProvider()
        generator = LivePageObjectGenerator(provider)

        generator.generate(_context())

        assert provider.requests[0].metadata["prompt_version"] == "1.0.0"
        payload = _sent_input_payload(provider.requests[0].prompt)
        assert "methods" not in payload
        assert payload["action_text"] == _need().text

    def test_response_with_all_requested_methods_is_returned_verbatim(self) -> None:
        provider = _complete_provider()
        generator = LivePageObjectGenerator(provider)

        result = generator.generate(_multi_method_context())

        for method_name in ("enterUsername", "enterPassword", "clickLogin"):
            assert method_name in result

    def test_response_missing_a_requested_method_raises_honestly(self) -> None:
        """The model drops `clickLogin` from its response -- the generator
        surfaces this honestly rather than returning an incomplete class."""
        incomplete_java = (
            "package com.automation.pages;\n\n"
            "public class LoginPage extends BasePage {\n"
            "    public void enterUsername(String username) {}\n"
            "    public void enterPassword(String password) {}\n"
            "}\n"
        )
        provider = FakeProvider(text=incomplete_java)
        generator = LivePageObjectGenerator(provider)

        with pytest.raises(LiveGenerationError, match="missing"):
            generator.generate(_multi_method_context())

    def test_response_missing_a_method_names_exactly_which_are_missing(self) -> None:
        incomplete_java = "package com.automation.pages;\npublic class LoginPage {}\n"
        provider = FakeProvider(text=incomplete_java)
        generator = LivePageObjectGenerator(provider)

        with pytest.raises(LiveGenerationError) as excinfo:
            generator.generate(_multi_method_context())

        message = str(excinfo.value)
        assert "enterUsername" in message
        assert "enterPassword" in message
        assert "clickLogin" in message

    def test_missing_primary_method_name_raises_before_any_provider_call(self) -> None:
        provider = FakeProvider()
        generator = LivePageObjectGenerator(provider)
        context = _multi_method_context(method_name=None)

        with pytest.raises(ValueError, match="method_name"):
            generator.generate(context)

        assert provider.call_count == 0

    def test_determinism_same_context_yields_byte_identical_prompt(self) -> None:
        context = _multi_method_context()
        first_provider = _complete_provider()
        second_provider = _complete_provider()

        LivePageObjectGenerator(first_provider).generate(context)
        LivePageObjectGenerator(second_provider).generate(context)

        assert first_provider.requests[0].prompt == second_provider.requests[0].prompt
