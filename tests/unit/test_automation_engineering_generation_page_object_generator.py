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


#: `LivePageObjectGenerator.generate` now REQUIRES `context.method_name`
#: unconditionally (the defect-1 fix) -- every live-generator test below
#: that doesn't test the ValueError itself supplies one, via `_context(...,
#: method_name=...)`. This default pairs with `_DEFAULT_METHOD_JAVA` below
#: so a bare `FakeProvider()` response satisfies the completeness check for
#: a bare `_context()` call.
_DEFAULT_METHOD_NAME = "clickForgotPasswordLink"


def _single_method_java(method_name: str = _DEFAULT_METHOD_NAME) -> str:
    """A canned, complete single-method page-object response -- contains
    `method_name` so the completeness check (module docstring's own
    "completeness, honestly bounded") passes."""
    return (
        "package com.automation.pages;\n\n"
        "public class ForgotPasswordLinkPage extends BasePage {\n"
        f"    public void {method_name}() {{}}\n"
        "}\n"
    )


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
        text: str = _single_method_java(),
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

        generator.generate(_context(method_name=_DEFAULT_METHOD_NAME))

        sent_prompt = provider.requests[0].prompt
        assert sent_prompt.startswith(
            "You are a test automation engineer writing Java page-object classes"
        )
        assert "customqa:direct-webdriver-action" in sent_prompt
        assert "customqa:long-method" in sent_prompt

    def test_input_block_conveys_the_derived_method_name_verbatim(self) -> None:
        """THE defect-1 proof: a live regeneration run measured 22 of 33
        requested method calls (67%) coming back under a name the model
        invented, because the single-method path never conveyed the
        DERIVED method_name to the model at all. This is the exact
        scenario -- a real requested name (`verifyNamingPatternForElements`,
        the live run's own example) -- proven present in the built prompt
        input, not paraphrasable away."""
        need = GherkinStepNeed(
            text="the report should indicate that all {string} follow the required naming pattern",
            step_type="PageAction",
            captures=(StepCapture(index=0, style="cucumber_expression", expression_type="string"),),
        )
        context = _context(
            need,
            class_name="ReportPage",
            target_package="com.automation.pages",
            customqa_constraints=("rule-a", "rule-b"),
            method_name="verifyNamingPatternForElements",
        )
        provider = FakeProvider(
            text=_single_method_java("verifyNamingPatternForElements")
        )
        generator = LivePageObjectGenerator(provider)

        generator.generate(context)

        payload = _sent_input_payload(provider.requests[0].prompt)
        assert payload["class_name"] == "ReportPage"
        assert payload["target_package"] == "com.automation.pages"
        assert payload["customqa_constraints"] == ["rule-a", "rule-b"]
        methods = payload["methods"]
        assert isinstance(methods, list)
        assert len(methods) == 1
        # The derived name is CONVEYED -- the exact thing v1.0.0 never did.
        assert methods[0]["method_name"] == "verifyNamingPatternForElements"
        assert methods[0]["action_text"] == need.text
        assert methods[0]["captures"] == [
            {"index": 0, "style": "cucumber_expression", "expression_type": "string"}
        ]

    def test_verbatim_naming_instruction_is_present_in_the_prompt(self) -> None:
        """The prompt doesn't just carry the name -- it instructs the model
        to use it VERBATIM (v1.1.0's own OUTPUT CONTRACT language), now
        covering the single-method case too."""
        provider = FakeProvider()
        generator = LivePageObjectGenerator(provider)

        generator.generate(_context(method_name=_DEFAULT_METHOD_NAME))

        sent_prompt = provider.requests[0].prompt
        assert "VERBATIM" in sent_prompt
        assert "method_name" in sent_prompt

    def test_same_context_yields_byte_identical_prompt_across_independent_calls(self) -> None:
        context = _context(method_name=_DEFAULT_METHOD_NAME)
        first_provider = FakeProvider()
        second_provider = FakeProvider()

        LivePageObjectGenerator(first_provider).generate(context)
        LivePageObjectGenerator(second_provider).generate(context)

        assert first_provider.requests[0].prompt == second_provider.requests[0].prompt

    def test_different_needs_yield_different_prompts(self) -> None:
        provider = FakeProvider()
        generator = LivePageObjectGenerator(provider)

        generator.generate(
            _context(_need("click the forgot password link"), method_name=_DEFAULT_METHOD_NAME)
        )
        generator.generate(
            _context(_need("open the checkout page"), method_name=_DEFAULT_METHOD_NAME)
        )

        assert provider.requests[0].prompt != provider.requests[1].prompt

    def test_exactly_one_provider_call_per_generate_no_retry(self) -> None:
        provider = FakeProvider()
        generator = LivePageObjectGenerator(provider)

        generator.generate(_context(method_name=_DEFAULT_METHOD_NAME))

        assert provider.call_count == 1


class TestLlmBoundaryErrorHandling:
    def test_provider_exception_is_wrapped_and_chained(self) -> None:
        provider = FakeProvider(raises=RuntimeError("connection reset"))
        generator = LivePageObjectGenerator(provider)

        with pytest.raises(LiveGenerationError, match="LLM provider call failed") as excinfo:
            generator.generate(_context(method_name=_DEFAULT_METHOD_NAME))
        assert isinstance(excinfo.value.__cause__, RuntimeError)

    def test_non_completed_execution_status_raises(self) -> None:
        provider = FakeProvider(execution_status=ExecutionStatus.TIMEOUT)
        generator = LivePageObjectGenerator(provider)

        with pytest.raises(LiveGenerationError, match="did not complete"):
            generator.generate(_context(method_name=_DEFAULT_METHOD_NAME))

    def test_empty_response_raises(self) -> None:
        provider = FakeProvider(text="")
        generator = LivePageObjectGenerator(provider)

        with pytest.raises(LiveGenerationError, match="empty response"):
            generator.generate(_context(method_name=_DEFAULT_METHOD_NAME))

    def test_whitespace_only_response_raises(self) -> None:
        provider = FakeProvider(text="   \n  \n")
        generator = LivePageObjectGenerator(provider)

        with pytest.raises(LiveGenerationError, match="empty response"):
            generator.generate(_context(method_name=_DEFAULT_METHOD_NAME))

    def test_missing_method_name_raises_before_any_provider_call(self) -> None:
        """The defect-1 fix's own safety net: `method_name` is now required
        UNCONDITIONALLY (previously only for a multi-method request)."""
        provider = FakeProvider()
        generator = LivePageObjectGenerator(provider)

        with pytest.raises(ValueError, match="method_name"):
            generator.generate(_context())  # method_name defaults to None

        assert provider.call_count == 0

    def test_completed_non_empty_response_is_returned_verbatim(self) -> None:
        java = (
            "package com.automation.pages;\n\n"
            "public class LoginPage extends BasePage {\n"
            f"    public void {_DEFAULT_METHOD_NAME}() {{}}\n"
            "}\n"
        )
        provider = FakeProvider(text=java)
        generator = LivePageObjectGenerator(provider)

        result = generator.generate(_context(method_name=_DEFAULT_METHOD_NAME))

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
    """`generate_page_objects` v1.1.0 -- the multi-method extension. Since
    the defect-1 fix, v1.1.0 is ALSO the single-method path (the divergence
    that caused defect 1 -- v1.0.0 never conveying `method_name` -- is
    retired; see `TestSingleMethodNowRoutesThroughV110` below for that
    proof specifically)."""

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


class TestSingleMethodNowRoutesThroughV110:
    """THE defect-1 fix, proven directly: a single-method context (no
    `additional_method_needs`) used to hit v1.0.0's own payload shape
    (`action_text`/`captures` at the top level, no `method_name` anywhere)
    -- now it hits the SAME v1.1.0 path a multi-method context does, as a
    length-one `methods` list, with `method_name` conveyed. No more
    divergence between the two paths -- the root cause of defect 1."""

    def test_uses_v110_not_v100(self) -> None:
        provider = FakeProvider()
        generator = LivePageObjectGenerator(provider)

        generator.generate(_context(method_name=_DEFAULT_METHOD_NAME))

        assert provider.requests[0].metadata["prompt_version"] == "1.1.0"

    def test_payload_is_a_length_one_methods_list_carrying_method_name(self) -> None:
        provider = FakeProvider()
        generator = LivePageObjectGenerator(provider)

        generator.generate(_context(method_name=_DEFAULT_METHOD_NAME))

        payload = _sent_input_payload(provider.requests[0].prompt)
        assert "action_text" not in payload  # the OLD v1.0.0 top-level shape is gone
        methods = payload["methods"]
        assert isinstance(methods, list)
        assert len(methods) == 1
        assert methods[0]["method_name"] == _DEFAULT_METHOD_NAME
        assert methods[0]["action_text"] == _need().text

    def test_produces_one_class_one_method_the_right_name_no_regression(self) -> None:
        java = _single_method_java(_DEFAULT_METHOD_NAME)
        provider = FakeProvider(text=java)
        generator = LivePageObjectGenerator(provider)

        result = generator.generate(_context(method_name=_DEFAULT_METHOD_NAME))

        assert result == java
        assert result.count("public void") == 1  # one class, one method
        assert _DEFAULT_METHOD_NAME in result

    def test_response_under_the_wrong_name_is_caught_not_silently_accepted(self) -> None:
        """Contrast with the OLD (defect-1) behavior: previously, a
        single-method response was returned VERBATIM no matter what name
        the model actually used -- there was no completeness check on this
        path at all. Now, a response using a DIFFERENT name than requested
        (exactly what the live run measured 67% of the time) is caught."""
        paraphrased_java = (
            "package com.automation.pages;\n\n"
            "public class ForgotPasswordLinkPage extends BasePage {\n"
            "    public void resetPasswordLink() {}\n"  # NOT the requested name
            "}\n"
        )
        provider = FakeProvider(text=paraphrased_java)
        generator = LivePageObjectGenerator(provider)

        with pytest.raises(LiveGenerationError, match="missing"):
            generator.generate(_context(method_name=_DEFAULT_METHOD_NAME))
