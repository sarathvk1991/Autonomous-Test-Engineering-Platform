"""LiveFeatureRemediator: input assembly, the LLM boundary, and the seam.

No test in this module calls a real LLM. Input assembly (dirty feature
content + lint violations -> prompt) is proven deterministic against a fake
provider that only records the request it received; boundary handling
(provider exception, non-COMPLETED execution_status, empty response, and a
response missing the prompt's own ---FEATURE---/---CHANGES--- output
contract) is proven against a fake provider configured to fail in each of
those four ways. A final integration test proves the live remediator's
output flows through the UNMODIFIED D5 loop exactly like the stub's does --
the two are peers behind one seam.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from contracts.testable_requirement import (
    AcceptanceCriterionInput,
    Category,
    Priority,
    TestableRequirement,
    build_testable_requirement,
)
from feature_engineering.generation import FeatureGenerationError, StubFeatureContentGenerator
from feature_engineering.generation.assembler import generate_feature_file
from feature_engineering.gherkin_lint.models import Violation
from feature_engineering.remediation import (
    LiveFeatureRemediator,
    LiveRemediationError,
    RemediationStatus,
    run_cp2_remediation,
)
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
        "narrative": "n",
        "acceptance_criteria": [
            AcceptanceCriterionInput(category=Category.FUNCTIONAL, statement="A"),
        ],
    }
    defaults.update(overrides)
    return build_testable_requirement(**defaults)  # type: ignore[arg-type]


class FakeProvider(LLMProvider):
    """Records every request it receives; returns/raises what the test
    configures. Hand-written, mirroring
    `test_feature_engineering_live_content_generator.py`'s own fake exactly,
    so this module stays honest about exactly what `LLMProvider` contract
    `LiveFeatureRemediator` actually depends on."""

    def __init__(
        self,
        *,
        text: str = "---FEATURE---\nsome remediated content\n---CHANGES---\n",
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


_VIOLATIONS = (
    Violation(rule="no-trailing-spaces", file="x.feature", line=3, message="trailing space"),
    Violation(rule="indentation", file="x.feature", line=5, message="bad indent"),
)


class TestInputAssemblyDeterminism:
    """Proves (dirty content, violations) -> prompt is correct and
    deterministic, entirely without calling the LLM."""

    def test_prompt_carries_the_governed_template_verbatim(self) -> None:
        provider = FakeProvider()
        remediator = LiveFeatureRemediator(provider)

        remediator.remediate("Feature: x\n", _VIOLATIONS)

        sent_prompt = provider.requests[0].prompt
        assert sent_prompt.startswith(
            "You are a test automation engineer fixing Gherkin lint violations"
        )
        assert "Preserve every @REQ-*, @SCN-*, and @AC-* tag exactly as given" in sent_prompt

    def test_input_block_carries_the_failing_feature_text_verbatim(self) -> None:
        provider = FakeProvider()
        remediator = LiveFeatureRemediator(provider)
        dirty = "@REQ-abc123\nFeature: x\n\n  Scenario: dup\n    Given a\n"

        remediator.remediate(dirty, _VIOLATIONS)

        input_block = provider.requests[0].prompt.split("INPUT:\n", 1)[1]
        payload = json.loads(input_block)
        assert payload["feature_content"] == dirty

    def test_input_block_carries_every_violation_verbatim(self) -> None:
        provider = FakeProvider()
        remediator = LiveFeatureRemediator(provider)

        remediator.remediate("Feature: x\n", _VIOLATIONS)

        input_block = provider.requests[0].prompt.split("INPUT:\n", 1)[1]
        payload = json.loads(input_block)
        assert len(payload["violations"]) == 2
        for sent, violation in zip(payload["violations"], _VIOLATIONS, strict=True):
            assert sent["rule"] == violation.rule
            assert sent["line"] == violation.line
            assert sent["message"] == violation.message
            assert "file" not in sent  # the prompt's INPUT CONTRACT names no such field

    def test_same_inputs_yield_byte_identical_prompt_across_independent_calls(self) -> None:
        dirty = "Feature: x\n"
        first_provider = FakeProvider()
        second_provider = FakeProvider()

        LiveFeatureRemediator(first_provider).remediate(dirty, _VIOLATIONS)
        LiveFeatureRemediator(second_provider).remediate(dirty, _VIOLATIONS)

        assert first_provider.requests[0].prompt == second_provider.requests[0].prompt

    def test_different_violations_yield_different_prompts(self) -> None:
        provider = FakeProvider()
        remediator = LiveFeatureRemediator(provider)

        remediator.remediate("Feature: x\n", _VIOLATIONS)
        remediator.remediate("Feature: x\n", _VIOLATIONS[:1])

        assert provider.requests[0].prompt != provider.requests[1].prompt

    def test_exactly_one_provider_call_per_remediate_no_retry(self) -> None:
        provider = FakeProvider()
        remediator = LiveFeatureRemediator(provider)

        remediator.remediate("Feature: x\n", _VIOLATIONS)

        assert provider.call_count == 1


class TestLlmBoundaryErrorHandling:
    def test_provider_exception_is_wrapped_and_chained(self) -> None:
        provider = FakeProvider(raises=RuntimeError("connection reset"))
        remediator = LiveFeatureRemediator(provider)

        with pytest.raises(LiveRemediationError, match="LLM provider call failed") as excinfo:
            remediator.remediate("Feature: x\n", _VIOLATIONS)
        assert isinstance(excinfo.value.__cause__, RuntimeError)

    def test_non_completed_execution_status_raises(self) -> None:
        provider = FakeProvider(execution_status=ExecutionStatus.TIMEOUT)
        remediator = LiveFeatureRemediator(provider)

        with pytest.raises(LiveRemediationError, match="did not complete"):
            remediator.remediate("Feature: x\n", _VIOLATIONS)

    def test_empty_response_raises(self) -> None:
        provider = FakeProvider(text="")
        remediator = LiveFeatureRemediator(provider)

        with pytest.raises(LiveRemediationError, match="empty response"):
            remediator.remediate("Feature: x\n", _VIOLATIONS)

    def test_whitespace_only_response_raises(self) -> None:
        provider = FakeProvider(text="   \n  \n")
        remediator = LiveFeatureRemediator(provider)

        with pytest.raises(LiveRemediationError, match="empty response"):
            remediator.remediate("Feature: x\n", _VIOLATIONS)

    def test_response_missing_output_contract_markers_raises(self) -> None:
        """The one boundary with no analogue in LiveFeatureContentGenerator:
        generate_feature's output has no structure to violate; fix_gherkin_lint's
        two-part ---FEATURE---/---CHANGES--- contract does."""
        provider = FakeProvider(text="just some prose, no markers at all")
        remediator = LiveFeatureRemediator(provider)

        with pytest.raises(LiveRemediationError, match="output contract"):
            remediator.remediate("Feature: x\n", _VIOLATIONS)

    def test_response_with_empty_feature_section_raises(self) -> None:
        provider = FakeProvider(text="---FEATURE---\n\n---CHANGES---\n")
        remediator = LiveFeatureRemediator(provider)

        with pytest.raises(LiveRemediationError, match="empty"):
            remediator.remediate("Feature: x\n", _VIOLATIONS)

    def test_well_formed_response_extracts_only_the_feature_section(self) -> None:
        provider = FakeProvider(
            text=(
                "---FEATURE---\n"
                "Feature: fixed\n\n  Scenario: ok\n    Given a\n"
                "---CHANGES---\n"
                '{"rule": "indentation", "line": 5, "change": "fixed indent"}\n'
            )
        )
        remediator = LiveFeatureRemediator(provider)

        result = remediator.remediate("Feature: x\n", _VIOLATIONS)

        # The content's own trailing newline (required for `new-line-at-eof`)
        # is preserved -- only the ---FEATURE--- marker's own line
        # terminator is stripped, never the content's trailing whitespace.
        assert result == "Feature: fixed\n\n  Scenario: ok\n    Given a\n"
        assert "---CHANGES---" not in result
        assert "indentation" not in result


class TestSeamCoexistenceWithTheLoop:
    """The live implementation and the stub are peers behind one seam -- the
    UNMODIFIED D5 loop cannot tell them apart."""

    def test_live_remediator_output_flows_through_the_unmodified_loop(self) -> None:
        req = _requirement()
        (ac,) = req.acceptance_criteria
        # Raw, un-assembled duplicate-scenario-name content -- the same
        # technique test_feature_engineering_remediation.py uses to reach a
        # real, remediable dirty feature via the actual generator core
        # (proper Feature: line, real tag hoisting), not a hand-rolled
        # approximation of what the assembler would produce.
        raw = (
            f"@smoke @{ac.criterion_id} @SCN-PENDING\n"
            "Scenario: Duplicate name\n"
            "  Given a\n"
            "  When b\n"
            "  Then c\n"
            "\n"
            f"@regression @{ac.criterion_id} @SCN-PENDING\n"
            "Scenario: Duplicate name\n"
            "  Given d\n"
            "  When e\n"
            "  Then f\n"
        )
        with pytest.raises(FeatureGenerationError) as excinfo:
            generate_feature_file(
                req,
                StubFeatureContentGenerator({req.requirement_id: raw}),
                features_root=Path("/tmp/unused"),
            )
        dirty = excinfo.value.content
        assert dirty is not None
        # Rename only the LAST occurrence of the duplicated scenario name --
        # same technique test_feature_engineering_remediation.py's own
        # `_fixed_content` helper uses.
        head, _sep, tail = dirty.rpartition("Scenario: Duplicate name")
        fixed = head + "Scenario: Renamed second scenario" + tail
        assert fixed.endswith("\n")  # dirty's own trailing newline, carried through `tail`
        # No extra newline inserted before the marker -- `fixed` already ends
        # in its own required trailing newline, which the marker directly follows.
        provider = FakeProvider(text=f"---FEATURE---\n{fixed}---CHANGES---\n")
        remediator = LiveFeatureRemediator(provider)

        result = run_cp2_remediation(
            req, dirty, req_tag=f"@{req.requirement_id}", remediator=remediator
        )

        assert result.status == RemediationStatus.PASSED
        assert result.llm_attempt_count == 1
        assert provider.call_count == 1


class TestNoLlmFactoryElsewhere:
    def test_live_remediator_is_the_only_new_llm_factory_adjacent_user(self) -> None:
        """`LiveFeatureRemediator` (like `LiveFeatureContentGenerator` before
        it) never imports `llm_factory` itself -- it takes an
        already-constructed provider. This proves the ENTIRE
        generation/CP2/remediation surface (loop, stub, live remediator, CP2,
        generator core, live content generator) stays free of it; provider
        selection remains the CLI's job alone."""
        import ast
        from pathlib import Path

        for py_file in [
            *Path("feature_engineering/remediation").glob("*.py"),
            *Path("feature_engineering/cp2").glob("*.py"),
            *Path("feature_engineering/generation").glob("*.py"),
        ]:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "llm_factory" not in alias.name, f"{py_file}: imports {alias.name}"
                elif isinstance(node, ast.ImportFrom) and node.module:
                    assert "llm_factory" not in node.module, (
                        f"{py_file}: imports from {node.module}"
                    )
