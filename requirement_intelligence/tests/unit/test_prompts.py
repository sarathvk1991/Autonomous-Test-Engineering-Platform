"""Unit tests for the Requirement Prompt Framework.

Covers:
- prompt generation (PromptRequest assembly)
- artifact context injection
- JSON / output-format instruction inclusion
- deterministic output
- empty artifact handling
- provider-agnosticism (no Gemini / Azure / model references)

No AI calls are made and no provider is constructed.
"""

from __future__ import annotations

import pytest

from requirement_intelligence.models.consolidated_artifact import ConsolidatedArtifact
from requirement_intelligence.models.enums import (
    RiskLevel,
    SourceCategory,
    SourceSystem,
    SourceType,
)
from requirement_intelligence.models.source_artifact import SourceArtifact
from requirement_intelligence.prompts import PromptRequest, RequirementPromptBuilder
from requirement_intelligence.prompts.prompt_constants import PROMPT_VERSION

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _artifact(
    artifact_id: str,
    category: SourceCategory,
    source_type: SourceType,
    title: str,
    **kwargs: object,
) -> SourceArtifact:
    return SourceArtifact(
        artifact_id=artifact_id,
        source_system=SourceSystem.JIRA,
        source_record_id=f"REC-{artifact_id}",
        source_category=category,
        source_type=source_type,
        title=title,
        **kwargs,  # type: ignore[arg-type]
    )


def _full_consolidated() -> ConsolidatedArtifact:
    return ConsolidatedArtifact(
        consolidated_id="CONS-1",
        module="payments",
        business_area="checkout",
        risk_level=RiskLevel.HIGH,
        consolidation_reason="grouped by module match",
        functional_artifacts=[
            _artifact(
                "F1",
                SourceCategory.FUNCTIONAL,
                SourceType.STORY,
                "User can pay with saved card",
                description="As a user I want to reuse a stored card.",
                priority="High",
                status="Open",
                component="payments-api",
            ),
        ],
        security_artifacts=[
            _artifact(
                "S1",
                SourceCategory.SECURITY,
                SourceType.DAST,
                "Reflected XSS on payment form",
                severity="Critical",
                status="Open",
            ),
        ],
        quality_artifacts=[
            _artifact(
                "Q1",
                SourceCategory.QUALITY,
                SourceType.SAST,
                "Cyclomatic complexity too high",
                severity="Major",
            ),
        ],
    )


def _empty_consolidated() -> ConsolidatedArtifact:
    return ConsolidatedArtifact(
        consolidated_id="CONS-EMPTY",
        module="reporting",
        risk_level=RiskLevel.LOW,
    )


# ---------------------------------------------------------------------------
# 1. Prompt generation
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_build_returns_prompt_request() -> None:
    result = RequirementPromptBuilder().build(_full_consolidated())
    assert isinstance(result, PromptRequest)
    assert result.system_prompt.strip()
    assert result.user_prompt.strip()
    assert result.source_consolidated_id == "CONS-1"


@pytest.mark.unit
def test_full_prompt_combines_system_and_user() -> None:
    result = RequirementPromptBuilder().build(_full_consolidated())
    assert result.system_prompt in result.full_prompt
    assert result.user_prompt in result.full_prompt


@pytest.mark.unit
def test_prompt_includes_analysis_objectives() -> None:
    user_prompt = RequirementPromptBuilder().build(_full_consolidated()).user_prompt
    lowered = user_prompt.lower()
    assert "functional requirements" in lowered
    assert "security findings" in lowered
    assert "quality findings" in lowered
    assert "gap" in lowered
    assert "risk" in lowered
    assert "recommend" in lowered


# ---------------------------------------------------------------------------
# 2. Artifact injection
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_artifact_context_is_injected() -> None:
    user_prompt = RequirementPromptBuilder().build(_full_consolidated()).user_prompt
    # Header metadata
    assert "CONS-1" in user_prompt
    assert "payments" in user_prompt
    assert "checkout" in user_prompt
    assert "grouped by module match" in user_prompt
    # Per-domain artifact titles
    assert "User can pay with saved card" in user_prompt
    assert "Reflected XSS on payment form" in user_prompt
    assert "Cyclomatic complexity too high" in user_prompt
    # A description and a field value
    assert "reuse a stored card" in user_prompt
    assert "Critical" in user_prompt


@pytest.mark.unit
def test_artifact_field_fallback_used_for_missing_values() -> None:
    user_prompt = RequirementPromptBuilder().build(_full_consolidated()).user_prompt
    # The DAST finding has no priority/component → fallback marker present.
    assert "n/a" in user_prompt


# ---------------------------------------------------------------------------
# 3. JSON instruction inclusion
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_json_contract_keys_included() -> None:
    user_prompt = RequirementPromptBuilder().build(_full_consolidated()).user_prompt
    for key in (
        '"summary"',
        '"functional_requirements"',
        '"security_requirements"',
        '"quality_requirements"',
        '"risks"',
        '"recommendations"',
    ):
        assert key in user_prompt


@pytest.mark.unit
def test_prompt_forbids_markdown_and_prose() -> None:
    user_prompt = RequirementPromptBuilder().build(_full_consolidated()).user_prompt
    lowered = user_prompt.lower()
    assert "json" in lowered
    assert "markdown" in lowered
    assert "code fence" in lowered
    assert "outside the json" in lowered


# ---------------------------------------------------------------------------
# 4. Deterministic output
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_prompt_generation_is_deterministic() -> None:
    builder = RequirementPromptBuilder()
    artifact = _full_consolidated()
    first = builder.build(artifact)
    second = builder.build(artifact)
    assert first.system_prompt == second.system_prompt
    assert first.user_prompt == second.user_prompt
    assert first.full_prompt == second.full_prompt


@pytest.mark.unit
def test_prompt_preserves_artifact_order() -> None:
    artifact = ConsolidatedArtifact(
        consolidated_id="CONS-ORDER",
        module="m",
        risk_level=RiskLevel.MEDIUM,
        functional_artifacts=[
            _artifact("A", SourceCategory.FUNCTIONAL, SourceType.STORY, "First story"),
            _artifact("B", SourceCategory.FUNCTIONAL, SourceType.STORY, "Second story"),
        ],
    )
    user_prompt = RequirementPromptBuilder().build(artifact).user_prompt
    assert user_prompt.index("First story") < user_prompt.index("Second story")


# ---------------------------------------------------------------------------
# 5. Empty artifact handling
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_empty_artifact_produces_valid_prompt() -> None:
    result = RequirementPromptBuilder().build(_empty_consolidated())
    assert isinstance(result, PromptRequest)
    assert result.user_prompt.count("(none provided)") == 3
    # Output / JSON instructions are still present for an empty artifact.
    assert '"recommendations"' in result.user_prompt
    assert "business area: n/a" in result.user_prompt.lower()


# ---------------------------------------------------------------------------
# 6. Provider-agnosticism
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_prompt_has_no_provider_references() -> None:
    result = RequirementPromptBuilder().build(_full_consolidated())
    blob = result.full_prompt.lower()
    for forbidden in ("gemini", "azure", "openai", "anthropic", "bedrock", "ollama"):
        assert forbidden not in blob


# ---------------------------------------------------------------------------
# 7. PromptRequest → LLMRequest bridge (provider-agnostic contract)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_to_llm_request_bridges_to_contract() -> None:
    from requirement_intelligence.llm.llm_models import LLMRequest

    result = RequirementPromptBuilder().build(_full_consolidated())
    llm_request = result.to_llm_request(request_id="trace-1", temperature=0.2)

    assert isinstance(llm_request, LLMRequest)
    assert llm_request.request_id == "trace-1"
    assert llm_request.temperature == 0.2
    assert llm_request.prompt == result.full_prompt
    assert llm_request.metadata["source_consolidated_id"] == "CONS-1"


@pytest.mark.unit
def test_to_llm_request_merges_metadata() -> None:
    result = RequirementPromptBuilder().build(_full_consolidated())
    llm_request = result.to_llm_request(
        request_id="trace-2", metadata={"run": "abc"}
    )
    assert llm_request.metadata["run"] == "abc"
    assert llm_request.metadata["source_consolidated_id"] == "CONS-1"


# ---------------------------------------------------------------------------
# 8. Prompt versioning
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_prompt_request_contains_prompt_version() -> None:
    result = RequirementPromptBuilder().build(_full_consolidated())
    assert result.prompt_version == PROMPT_VERSION


@pytest.mark.unit
def test_prompt_version_propagates_to_llm_request() -> None:
    result = RequirementPromptBuilder().build(_full_consolidated())
    llm_request = result.to_llm_request(request_id="trace-ver")
    assert llm_request.metadata["prompt_version"] == PROMPT_VERSION


@pytest.mark.unit
def test_framework_metadata_overrides_user_metadata() -> None:
    result = RequirementPromptBuilder().build(_full_consolidated())
    llm_request = result.to_llm_request(
        request_id="trace-override",
        metadata={"prompt_version": "999", "source_consolidated_id": "BAD"},
    )
    # Framework-controlled keys always win over caller-supplied values.
    assert llm_request.metadata["prompt_version"] == PROMPT_VERSION
    assert llm_request.metadata["source_consolidated_id"] == "CONS-1"
