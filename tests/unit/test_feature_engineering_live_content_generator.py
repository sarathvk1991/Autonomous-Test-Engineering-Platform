"""LiveFeatureContentGenerator: input assembly, the LLM boundary, and the seam.

No test in this module calls a real LLM. Input assembly (TestableRequirement
-> prompt) is proven deterministic against a fake provider that only records
the request it received; boundary handling (provider exception, non-COMPLETED
execution_status, empty response) is proven against a fake provider configured
to fail in each of those three ways. A final integration test proves the live
generator's output flows through the unmodified generator core exactly like
the stub's does -- the two are peers behind one seam.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from contracts.testable_requirement import (
    AcceptanceCriterionInput,
    Category,
    PolarityHint,
    Priority,
    TestableRequirement,
    build_testable_requirement,
)
from feature_engineering.generation import (
    LiveFeatureContentGenerator,
    LiveGenerationError,
    StubFeatureContentGenerator,
    generate_feature_file,
)
from feature_engineering.prompts.composition import build_prompt_registry
from requirement_intelligence.llm.llm_models import LLMRequest, LLMResponse, LLMUsage
from requirement_intelligence.llm.providers.base_provider import LLMProvider
from shared.enums.base import ExecutionStatus, ProviderType


def _requirement(**overrides: object) -> TestableRequirement:
    defaults: dict[str, object] = {
        "title": "User can reset password",
        "component": "auth",
        "functional_tag": "@auth",
        "priority": Priority.HIGH,
        "traces_to": (),
        "narrative": "Users need a self-service password reset flow.",
        "acceptance_criteria": [
            AcceptanceCriterionInput(
                category=Category.FUNCTIONAL,
                statement="User receives a reset email",
                polarity_hints=(PolarityHint.POSITIVE,),
            ),
            AcceptanceCriterionInput(
                category=Category.FUNCTIONAL,
                statement="Expired reset link is rejected",
                polarity_hints=(PolarityHint.NEGATIVE, PolarityHint.BOUNDARY),
            ),
        ],
    }
    defaults.update(overrides)
    return build_testable_requirement(**defaults)  # type: ignore[arg-type]


class FakeProvider(LLMProvider):
    """Records every request it receives; returns/raises what the test configures.

    Not a mock library double on purpose -- a hand-written fake keeps this
    test module honest about exactly what :class:`LLMProvider` contract
    :class:`LiveFeatureContentGenerator` actually depends on.
    """

    def __init__(
        self,
        *,
        text: str = "some generated content",
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


class TestInputAssemblyDeterminism:
    """Proves TestableRequirement -> prompt is correct and deterministic,
    entirely without calling the LLM (only the fake provider's recorded
    request is inspected)."""

    def test_prompt_carries_the_governed_template_verbatim(self) -> None:
        req = _requirement()
        provider = FakeProvider()
        generator = LiveFeatureContentGenerator(provider)

        generator.generate(req)

        sent_prompt = provider.requests[0].prompt
        assert sent_prompt.startswith(
            "You are a test automation engineer writing Gherkin feature files"
        )
        assert "Never place a tag immediately before a Background: block" in sent_prompt

    def test_input_block_carries_every_field_the_prompt_contract_names(self) -> None:
        req = _requirement()
        provider = FakeProvider()
        generator = LiveFeatureContentGenerator(provider)

        generator.generate(req)

        sent_prompt = provider.requests[0].prompt
        input_block = sent_prompt.split("INPUT:\n", 1)[1]
        payload = json.loads(input_block)

        assert payload["title"] == req.title
        assert payload["narrative"] == req.narrative
        assert payload["component"] == req.component
        assert len(payload["acceptance_criteria"]) == len(req.acceptance_criteria)
        for sent_ac, ac in zip(
            payload["acceptance_criteria"], req.acceptance_criteria, strict=True
        ):
            assert sent_ac["ac_id"] == ac.criterion_id
            assert sent_ac["statement"] == ac.statement
            assert sent_ac["polarity_hints"] == list(ac.polarity_hints)

    def test_input_block_omits_risks(self) -> None:
        """generate_feature v1.1.0's own INPUT CONTRACT never names `risks` --
        and TestableRequirement.risks is always empty in contract_version
        1.0.0 (ADR-0042's structural correction note; risk data lives on
        TestableRequirementSet, not per-requirement). Nothing honest to send."""
        req = _requirement()
        provider = FakeProvider()
        generator = LiveFeatureContentGenerator(provider)

        generator.generate(req)

        input_block = provider.requests[0].prompt.split("INPUT:\n", 1)[1]
        payload = json.loads(input_block)
        assert "risks" not in payload

    def test_same_requirement_yields_byte_identical_prompt_across_independent_calls(
        self,
    ) -> None:
        req = _requirement()
        first_provider = FakeProvider()
        second_provider = FakeProvider()

        LiveFeatureContentGenerator(first_provider).generate(req)
        LiveFeatureContentGenerator(second_provider).generate(req)

        assert first_provider.requests[0].prompt == second_provider.requests[0].prompt

    def test_different_requirements_yield_different_prompts(self) -> None:
        req_a = _requirement(title="User can reset password")
        req_b = _requirement(title="User can change email address")
        provider = FakeProvider()
        generator = LiveFeatureContentGenerator(provider)

        generator.generate(req_a)
        generator.generate(req_b)

        assert provider.requests[0].prompt != provider.requests[1].prompt

    def test_exactly_one_provider_call_per_generate_no_retry(self) -> None:
        req = _requirement()
        provider = FakeProvider()
        generator = LiveFeatureContentGenerator(provider)

        generator.generate(req)

        assert provider.call_count == 1


class TestLlmBoundaryErrorHandling:
    def test_provider_exception_is_wrapped_and_chained(self) -> None:
        req = _requirement()
        provider = FakeProvider(raises=RuntimeError("connection reset"))
        generator = LiveFeatureContentGenerator(provider)

        with pytest.raises(LiveGenerationError, match="LLM provider call failed") as excinfo:
            generator.generate(req)
        assert isinstance(excinfo.value.__cause__, RuntimeError)

    def test_non_completed_execution_status_raises(self) -> None:
        req = _requirement()
        provider = FakeProvider(execution_status=ExecutionStatus.TIMEOUT)
        generator = LiveFeatureContentGenerator(provider)

        with pytest.raises(LiveGenerationError, match="did not complete"):
            generator.generate(req)

    def test_empty_response_raises(self) -> None:
        req = _requirement()
        provider = FakeProvider(text="")
        generator = LiveFeatureContentGenerator(provider)

        with pytest.raises(LiveGenerationError, match="empty response"):
            generator.generate(req)

    def test_whitespace_only_response_raises(self) -> None:
        req = _requirement()
        provider = FakeProvider(text="   \n  \n")
        generator = LiveFeatureContentGenerator(provider)

        with pytest.raises(LiveGenerationError, match="empty response"):
            generator.generate(req)

    def test_completed_non_empty_response_is_returned_verbatim(self) -> None:
        req = _requirement()
        provider = FakeProvider(text="@AC-x @SCN-PENDING\nScenario: ok\n  Given a thing\n")
        generator = LiveFeatureContentGenerator(provider)

        result = generator.generate(req)

        assert result == "@AC-x @SCN-PENDING\nScenario: ok\n  Given a thing\n"


class TestSeamCoexistenceWithTheCore:
    """The live implementation and the stub are peers behind one seam -- the
    unmodified generator core cannot tell them apart."""

    def test_live_generator_output_flows_through_the_unmodified_core(
        self, tmp_path: Path
    ) -> None:
        req = _requirement()
        ac1, ac2 = req.acceptance_criteria
        raw_content = (
            f"@smoke @{ac1.criterion_id} @SCN-PENDING\n"
            "Scenario: User receives a password reset email\n"
            "  Given a registered user requests a password reset\n"
            "  When the reset request is submitted\n"
            "  Then a reset email is sent\n"
            "\n"
            f"@regression @{ac2.criterion_id} @SCN-PENDING\n"
            "Scenario: Expired reset link is rejected\n"
            "  Given a user has an expired password reset link\n"
            "  When the user opens the reset link\n"
            "  Then the system rejects the expired link\n"
        )
        provider = FakeProvider(text=raw_content)
        live_generator = LiveFeatureContentGenerator(provider)

        result = generate_feature_file(req, live_generator, features_root=tmp_path)

        assert result.fully_covered
        assert result.lint_result.is_clean
        assert result.req_tag in result.content

    def test_stub_still_works_unchanged_alongside_the_live_implementation(
        self, tmp_path: Path
    ) -> None:
        req = _requirement()
        raw_content = (
            f"@{req.acceptance_criteria[0].criterion_id} @SCN-PENDING\n"
            "Scenario: A canned stub scenario\n"
            "  Given a stubbed precondition\n"
            "  When the stubbed action happens\n"
            "  Then the stubbed outcome holds\n"
        )
        stub = StubFeatureContentGenerator({req.requirement_id: raw_content})

        result = generate_feature_file(req, stub, features_root=tmp_path)

        assert result.lint_result.is_clean


class TestGenerationIdentityCapture:
    """The re-run/delta-scoped-regeneration cluster's own pinning foundation
    (2026-08-13) -- purely additive (mirrors `LiveStepDefinitionGenerator`'s
    own `last_identity` discipline)."""

    def test_no_identity_before_any_call(self) -> None:
        generator = LiveFeatureContentGenerator(FakeProvider())

        assert generator.last_identity is None

    def test_successful_call_captures_prompt_and_model_identity(self) -> None:
        req = _requirement()
        provider = FakeProvider()
        generator = LiveFeatureContentGenerator(provider)
        expected_definition = build_prompt_registry().get("generate_feature", "1.1.0")

        generator.generate(req)

        identity = generator.last_identity
        assert identity is not None
        assert identity.model == "fake-model"
        assert identity.provider == str(ProviderType.GEMINI)
        assert identity.prompt_id == expected_definition.metadata.prompt_id
        assert identity.prompt_version == expected_definition.metadata.version
        assert identity.prompt_sha256 == expected_definition.metadata.sha256

    def test_a_failed_call_leaves_identity_unset(self) -> None:
        req = _requirement()
        provider = FakeProvider(raises=ValueError("boom"))
        generator = LiveFeatureContentGenerator(provider)

        with pytest.raises(LiveGenerationError):
            generator.generate(req)

        assert generator.last_identity is None

    def test_generate_feature_file_threads_identity_onto_generated_feature(
        self, tmp_path: Path
    ) -> None:
        """The orchestrator-level thread (`assembler.generate_feature_file`)
        carries the SAME identity `LiveFeatureContentGenerator.last_identity`
        captured onto its own `GeneratedFeature.generation_identity` --
        never re-derived."""
        req = _requirement()
        raw_content = (
            f"@{req.acceptance_criteria[0].criterion_id} @SCN-PENDING\n"
            "Scenario: A generated scenario\n"
            "  Given a precondition\n"
            "  When an action occurs\n"
            "  Then an outcome holds\n"
        )
        provider = FakeProvider(text=raw_content)
        generator = LiveFeatureContentGenerator(provider)

        result = generate_feature_file(req, generator, features_root=tmp_path)

        assert result.generation_identity is not None
        assert result.generation_identity == generator.last_identity
