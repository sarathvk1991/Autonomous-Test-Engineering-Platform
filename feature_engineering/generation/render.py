"""Deterministic Gherkin text rendering, indented to match the committed
``.gherkin-lintrc`` exactly (Feature 0, Background 2, Scenario 2, Step 4,
Examples 4, example 6) — re-rendering from parsed AST data, rather than
reusing whatever raw formatting the content generator produced, is what
guarantees the assembled file's indentation is always correct regardless of
how the stub (or a future LLM) formatted its own output.
"""

from __future__ import annotations

from typing import Any

FEATURE_INDENT = 0
BACKGROUND_INDENT = 2
SCENARIO_INDENT = 2
STEP_INDENT = 4
EXAMPLES_INDENT = 4
EXAMPLE_ROW_INDENT = 6


def render_tags_line(tags: list[str], indent: int) -> str:
    if not tags:
        return ""
    return " " * indent + " ".join(tags) + "\n"


def render_step(step: dict[str, Any], indent: int = STEP_INDENT) -> str:
    keyword: str = step["keyword"]
    text: str = step["text"]
    return " " * indent + keyword + text + "\n"


def render_table_row(cells: list[str], indent: int = EXAMPLE_ROW_INDENT) -> str:
    return " " * indent + "| " + " | ".join(cells) + " |\n"


def render_examples(example: dict[str, Any]) -> str:
    lines = [" " * EXAMPLES_INDENT + "Examples:\n"]
    header = example.get("tableHeader")
    if header:
        lines.append(render_table_row([cell["value"] for cell in header["cells"]]))
        for row in example.get("tableBody", []):
            lines.append(render_table_row([cell["value"] for cell in row["cells"]]))
    return "".join(lines)


def render_background(background: dict[str, Any]) -> str:
    name = background.get("name")
    header = f"Background: {name}\n" if name else "Background:\n"
    lines = [" " * BACKGROUND_INDENT + header]
    for step in background.get("steps", []):
        lines.append(render_step(step))
    return "".join(lines)


def render_scenario(
    *,
    keyword: str,
    name: str,
    tags: list[str],
    steps: list[dict[str, Any]],
    examples: list[dict[str, Any]],
) -> str:
    lines = [
        render_tags_line(tags, SCENARIO_INDENT),
        " " * SCENARIO_INDENT + f"{keyword}: {name}\n",
    ]
    for step in steps:
        lines.append(render_step(step))
    for example in examples:
        lines.append(render_examples(example))
    return "".join(lines)


def render_feature(
    *,
    title: str,
    feature_tags: list[str],
    body_blocks: list[str],
) -> str:
    """Assemble the full file: Feature-level tags, the Feature: line, then
    each already-rendered body block (background/scenario), blank-line
    separated, ending with a single trailing newline (new-line-at-eof: yes)."""
    lines = [
        render_tags_line(feature_tags, FEATURE_INDENT),
        " " * FEATURE_INDENT + f"Feature: {title}\n",
    ]
    for block in body_blocks:
        lines.append("\n")
        lines.append(block)
    return "".join(lines)
