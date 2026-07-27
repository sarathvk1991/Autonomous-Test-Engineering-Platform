"""Before/after conversion proof for Layer 2's three converted prompts.

Each POC asset (`docs/reference/automation-poc/prompts/*.md`) was an agentic
slash-command with file-IO instructions, shell/VALIDATION sections, and
next-command chaining. ADR-0043 D4 requires all three stripped -- the
platform owns file placement, lint execution, and loop orchestration; the
prompt produces content only. This module proves the strip happened, and
proves the specific structural replacements the conversion required.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_VERSIONS_DIR = Path("feature_engineering/prompts/versions")

_CONVERTED = {
    "generate_feature": _VERSIONS_DIR / "generate_feature_v1.0.0.txt",
    "fix_gherkin_lint": _VERSIONS_DIR / "fix_gherkin_lint_v1.0.0.txt",
    "validate_generated_feature": _VERSIONS_DIR / "validate_generated_feature_v1.0.0.txt",
}

# Patterns lifted directly from what the POC assets actually contained
# (re-verified against docs/reference/automation-poc/prompts/*.md): file-IO
# placeholders, shell/VALIDATION invocations, and next-command chaining.
_FILE_IO_PATTERNS = [
    r"\{\{TARGET_FILE\}\}",
    r"\{\{FILE_PATH\}\}",
    r"\{\{FEATURE_FILE_PATH\}\}",
    r"save (it |the file )?(at|to)\b",
    r"src/test/resources",
    r"src/test/java",
    r"place the output",
]
_SHELL_PATTERNS = [
    r"```bash",
    r"npm run",
    r"mvn clean verify",
    r"mvn\b",
]
_CHAINING_PATTERNS = [
    r"/create-feature",
    r"/create-steps",
    r"/fix-gherkin\b",
    r"/refactor-feature",
    r"/validate-feature",
    r"proceed with",
    r"next recommended action",
]


def _content(prompt_id: str) -> str:
    return _CONVERTED[prompt_id].read_text(encoding="utf-8")


@pytest.mark.parametrize("prompt_id", sorted(_CONVERTED))
class TestNoAgenticScaffoldingSurvivedConversion:
    def test_no_file_io_instruction(self, prompt_id: str) -> None:
        text = _content(prompt_id)
        for pattern in _FILE_IO_PATTERNS:
            assert not re.search(pattern, text, re.IGNORECASE), (
                f"{prompt_id}: found file-IO instruction matching {pattern!r}"
            )

    def test_no_shell_or_validation_command(self, prompt_id: str) -> None:
        text = _content(prompt_id)
        for pattern in _SHELL_PATTERNS:
            assert not re.search(pattern, text, re.IGNORECASE), (
                f"{prompt_id}: found shell/VALIDATION command matching {pattern!r}"
            )

    def test_no_next_command_chaining(self, prompt_id: str) -> None:
        text = _content(prompt_id)
        for pattern in _CHAINING_PATTERNS:
            assert not re.search(pattern, text, re.IGNORECASE), (
                f"{prompt_id}: found next-command chaining matching {pattern!r}"
            )

    def test_no_vendor_named(self, prompt_id: str) -> None:
        text = _content(prompt_id)
        for vendor in ("gemini", "azure openai", "anthropic", "openai", "claude", "gpt-"):
            assert vendor not in text.lower(), f"{prompt_id}: names a vendor ({vendor!r})"


def test_generate_feature_constraints_kept_near_verbatim() -> None:
    """The CONSTRAINTS block is the reusable asset (ADR-0043 D4) -- prove the
    load-bearing lines the ADR itself calls out survived the conversion."""
    text = _content("generate_feature")
    assert "Scenario names must be under 90 characters" in text
    assert "Step names must be under 120 characters" in text
    assert "No duplicate scenario names" in text
    assert "No duplicate tags on the same scenario" in text
    assert "Use Scenario Outline: with Examples: for data-driven cases" in text
    assert "Steps must be business-readable" in text
    assert "avoid overly specific phrasing" in text


def test_generate_feature_input_is_structured_not_a_prose_blob() -> None:
    """The old {{REQUIREMENT}} prose blob is gone; the input contract names
    the actual TestableRequirement fields ADR-0043 D4 specifies."""
    text = _content("generate_feature")
    assert "{{REQUIREMENT}}" not in text
    assert "Requirement:" not in text
    for field in ("title", "narrative", "acceptance_criteria", "polarity_hints", "component"):
        assert field in text


def test_generate_feature_emits_tag_placeholder_structure_not_real_ids() -> None:
    """D2: ids are platform-assigned, never LLM-assigned. The prompt emits
    placeholder tag structure at the right scope; it never invents a value."""
    text = _content("generate_feature")
    assert "@REQ-PENDING" in text
    assert "@SCN-PENDING" in text
    assert "@AC-PENDING" in text
    assert "platform" in text.lower() and "replaces" in text.lower()
    assert "Never write a real REQ-*, SCN-*, or AC-* value" in text
    # And no example of a real-looking id value leaking into the template.
    assert not re.search(r"@(REQ|SCN|AC)-[A-Za-z0-9]", text.replace("PENDING", ""))


def test_fix_gherkin_lint_drops_the_step_definition_constraint() -> None:
    """ADR-0043 D5 explicitly drops this constraint: step definitions don't
    exist at the point CP2 runs, so this check is structurally meaningless
    for Layer 2 and must not be carried forward."""
    text = _content("fix_gherkin_lint")
    assert "step definition" not in text.lower()


def test_fix_gherkin_lint_input_is_structured_violations_not_pasted_text() -> None:
    text = _content("fix_gherkin_lint")
    assert "npm run lint:gherkin:html" not in text
    assert "violations" in text.lower()
    assert "rule" in text.lower() and "line" in text.lower()


def test_validate_generated_feature_is_marked_advisory_only() -> None:
    """ADR-0040 Recommendation 1 / ADR-0043 D5: never gates a control point."""
    text = _content("validate_generated_feature")
    assert "ADVISORY" in text
    assert "never gates" in text.lower()
    assert "human-in-the-loop" in text.lower()


def test_validate_generated_feature_narrows_to_the_two_llm_judged_checks() -> None:
    """Only business_readability and step_reusability require judgment; every
    other POC checklist row (lengths, dupes, single-Feature-block, lint) is
    already owned exactly by the linter/CP2 and must not be re-litigated."""
    text = _content("validate_generated_feature")
    assert "business_readability" in text
    assert "step_reusability" in text
    for deterministic_check in (
        "feature name length",
        "unique scenario names",
        "single feature block",
    ):
        assert deterministic_check not in text.lower()


def test_validate_generated_feature_drops_next_action_routing() -> None:
    """The POC's own 'Next Recommended Action' table chained to another
    slash-command -- the platform owns routing now, not the prompt."""
    text = _content("validate_generated_feature")
    assert "next recommended action" not in text.lower()
