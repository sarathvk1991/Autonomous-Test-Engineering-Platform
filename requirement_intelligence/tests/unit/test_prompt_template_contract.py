"""Governed runtime template contract (CAP-075 Part 2).

The runtime reconstructs a system prompt and a user prompt from a single
governed template file.  That reconstruction relies on the template's
*structure*, so the structure is itself governed and is verified here.

Covered
-------
1. Every governed template shipped in ``versions/`` conforms to the contract.
2. The contract admits exactly one split point and exactly one placeholder.
3. Malformed, missing-placeholder and duplicate-placeholder templates fail
   construction rather than producing a silently wrong prompt.
4. ``RequirementPromptBuilder`` reconstructs the two sections losslessly.
5. Substitution never treats the embedded JSON braces as format fields.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from requirement_intelligence.prompts.framework.composition import build_prompt_registry
from requirement_intelligence.prompts.framework.prompt_exceptions import (
    PromptTemplateContractError,
)
from requirement_intelligence.prompts.framework.prompt_registry import PromptRegistry
from requirement_intelligence.prompts.framework.prompt_template_contract import (
    ARTIFACT_CONTEXT_PLACEHOLDER,
    SECTION_SEPARATOR,
    parse_governed_template,
)
from requirement_intelligence.prompts.models.prompt_compatibility import PromptCompatibility
from requirement_intelligence.prompts.models.prompt_definition import PromptDefinition
from requirement_intelligence.prompts.models.prompt_metadata import PromptMetadata
from requirement_intelligence.prompts.models.prompt_version import PromptLifecycle
from requirement_intelligence.prompts.requirement_prompt_builder import (
    RUNTIME_PROMPT_ID,
    RequirementPromptBuilder,
)

_VERSIONS_DIR = Path(__file__).resolve().parents[2] / "prompts" / "versions"

_COMPAT = PromptCompatibility(
    normalization_version="1.0",
    validation_version="1.0",
    cp1_version="1.0",
    golden_dataset_version="1.0.0",
    output_schema_version="1.0.0",
)


def _registry_with(content: str, version: str = "1.0.0") -> PromptRegistry:
    """Return a sealed registry holding a single definition with *content*."""
    registry = PromptRegistry()
    metadata = PromptMetadata(
        prompt_id=RUNTIME_PROMPT_ID,
        name="Fixture Prompt",
        version=version,
        owner="Test",
        lifecycle=PromptLifecycle.PRODUCTION,
        description="Fixture prompt used to exercise the template contract.",
        sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        compatibility=_COMPAT,
        release_introduced="1.0.0",
    )
    registry.register(PromptDefinition(metadata=metadata, content=content))
    registry.seal()
    return registry


# ---------------------------------------------------------------------------
# 1. The shipped governed templates conform
# ---------------------------------------------------------------------------


def _shipped_templates() -> list[Path]:
    return sorted(_VERSIONS_DIR.glob("*.txt"))


def test_versions_dir_ships_at_least_one_template() -> None:
    assert _shipped_templates()


@pytest.mark.parametrize("path", _shipped_templates(), ids=lambda p: p.name)
def test_shipped_template_conforms_to_contract(path: Path) -> None:
    parse_governed_template(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", _shipped_templates(), ids=lambda p: p.name)
def test_shipped_template_has_exactly_one_placeholder(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    assert content.count(ARTIFACT_CONTEXT_PLACEHOLDER) == 1


@pytest.mark.parametrize("path", _shipped_templates(), ids=lambda p: p.name)
def test_shipped_template_has_exactly_one_split_point(path: Path) -> None:
    """The split is the first blank line; the system section never contains one."""
    template = parse_governed_template(path.read_text(encoding="utf-8"))
    assert SECTION_SEPARATOR not in template.system_prompt


def test_split_point_is_unique_by_construction() -> None:
    """Later blank lines are user-prompt paragraph breaks, not extra split points."""
    template = parse_governed_template("SYSTEM\n\nA\n\nB {artifact_context}\n\nC")
    assert template.system_prompt == "SYSTEM"
    assert template.user_template == "A\n\nB {artifact_context}\n\nC"
    assert SECTION_SEPARATOR not in template.system_prompt


def test_multi_paragraph_system_prompt_is_structurally_undetectable() -> None:
    """Documents the contract's known blind spot (see module docstring).

    A template authored with a two-paragraph system prompt parses "successfully":
    the second paragraph silently becomes the head of the user prompt.  No
    structural check can catch this, so it is a review-time governance rule.
    If this test ever fails, the contract gained a detection mechanism and the
    module docstring's "Limit of structural enforcement" section must be updated.
    """
    template = parse_governed_template(
        "SYSTEM PARA ONE\n\nSYSTEM PARA TWO\n\nUSER {artifact_context}"
    )
    assert template.system_prompt == "SYSTEM PARA ONE"
    assert template.user_template.startswith("SYSTEM PARA TWO")


@pytest.mark.parametrize("path", _shipped_templates(), ids=lambda p: p.name)
def test_shipped_template_sections_are_non_empty(path: Path) -> None:
    template = parse_governed_template(path.read_text(encoding="utf-8"))
    assert template.system_prompt.strip()
    assert template.user_template.strip()


# ---------------------------------------------------------------------------
# 2. Lossless reconstruction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", _shipped_templates(), ids=lambda p: p.name)
def test_sections_reconstruct_the_template(path: Path) -> None:
    """system + separator + user_template == the template's significant content."""
    content = path.read_text(encoding="utf-8")
    template = parse_governed_template(content)
    rebuilt = template.system_prompt + SECTION_SEPARATOR + template.user_template
    assert rebuilt == content.rstrip("\n")


def test_trailing_newline_is_not_prompt_content() -> None:
    body = "SYSTEM\n\nUSER {artifact_context}"
    assert parse_governed_template(body) == parse_governed_template(body + "\n\n\n")


# ---------------------------------------------------------------------------
# 3. Malformed templates fail construction
# ---------------------------------------------------------------------------


def test_template_without_split_point_is_rejected() -> None:
    with pytest.raises(PromptTemplateContractError, match="no split point"):
        parse_governed_template("SYSTEM only, no blank line {artifact_context}")


def test_template_with_empty_system_section_is_rejected() -> None:
    with pytest.raises(PromptTemplateContractError, match="empty system prompt"):
        parse_governed_template("   \n\nUSER {artifact_context}")


def test_template_with_empty_user_section_is_rejected() -> None:
    with pytest.raises(PromptTemplateContractError, match="empty user prompt"):
        parse_governed_template("SYSTEM\n\n   ")


def test_template_with_missing_placeholder_is_rejected() -> None:
    with pytest.raises(PromptTemplateContractError, match="exactly one"):
        parse_governed_template("SYSTEM\n\nUSER with no placeholder")


def test_template_with_duplicate_placeholder_is_rejected() -> None:
    with pytest.raises(PromptTemplateContractError, match="found 2"):
        parse_governed_template("SYSTEM\n\n{artifact_context} and {artifact_context}")


# ---------------------------------------------------------------------------
# 4. The builder enforces the contract at construction, not mid-execution
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_content",
    [
        pytest.param("SYSTEM only {artifact_context}", id="no-split-point"),
        pytest.param("SYSTEM\n\nUSER with no placeholder", id="missing-placeholder"),
        pytest.param("SYSTEM\n\n{artifact_context}{artifact_context}", id="duplicate-placeholder"),
        pytest.param("SYSTEM\n\n   ", id="empty-user-section"),
        pytest.param("   \n\nUSER {artifact_context}", id="empty-system-section"),
    ],
)
def test_builder_construction_fails_on_malformed_template(bad_content: str) -> None:
    with pytest.raises(PromptTemplateContractError):
        RequirementPromptBuilder(registry=_registry_with(bad_content))


def test_builder_construction_succeeds_on_conforming_template() -> None:
    builder = RequirementPromptBuilder(registry=_registry_with("SYSTEM\n\nUSER {artifact_context}"))
    assert builder.prompt_definition.metadata.prompt_id == RUNTIME_PROMPT_ID


# ---------------------------------------------------------------------------
# 5. Substitution semantics
# ---------------------------------------------------------------------------


def test_substitution_preserves_literal_json_braces() -> None:
    """The governed template embeds a JSON contract; braces are not format fields."""
    template = parse_governed_template('SYSTEM\n\n{"summary": ""}\n{artifact_context}')
    rendered = template.render_user_prompt("CTX")
    assert '{"summary": ""}' in rendered
    assert "CTX" in rendered
    assert ARTIFACT_CONTEXT_PLACEHOLDER not in rendered


def test_production_template_json_contract_survives_substitution() -> None:
    """Regression: str.format on the real template would raise KeyError('summary')."""
    builder = RequirementPromptBuilder(registry=build_prompt_registry())
    template = parse_governed_template(builder.prompt_definition.content)
    rendered = template.render_user_prompt("ARTIFACT-CONTEXT-SENTINEL")
    assert '"summary": ""' in rendered
    assert '"recommendations": []' in rendered
    assert "ARTIFACT-CONTEXT-SENTINEL" in rendered
    assert ARTIFACT_CONTEXT_PLACEHOLDER not in rendered


def test_artifact_context_is_injected_at_the_placeholder_position() -> None:
    template = parse_governed_template("SYSTEM\n\nBEFORE\n{artifact_context}\nAFTER")
    rendered = template.render_user_prompt("MIDDLE")
    assert rendered == "BEFORE\nMIDDLE\nAFTER"
