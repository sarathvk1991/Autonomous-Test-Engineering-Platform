"""Tier 1 — the deterministic formatter (ADR-0043 D5, zero LLM cost).

D5's pipeline: "generate -> deterministic formatter -> lint -> [LLM
remediate -> re-lint], max 2 attempts". This module is that first stage:
"the deterministic formatter fixes the pure-formatting lint rules (the 5
raw-text rules named in D3, plus indentation) at zero LLM cost -- these are
mechanical corrections, not judgement."

Implementation: re-parse the dirty content, then re-render it through the
SAME primitives (:mod:`feature_engineering.generation.render`) the
generator core already uses to assemble a feature from scratch. Those
primitives already hardcode the exact indentation levels, single-blank-line
block separation, and single-trailing-newline discipline
``.gherkin-lintrc`` requires -- re-rendering through them fixes every
formatting violation as a side effect of using already-proven code, not by
adding new formatting logic. Every value that ends up on the page (feature
name, tags, scenario names, step text, table cells) is read verbatim out of
the parsed AST and never altered -- re-rendering can only change
*whitespace and layout*, never content, by construction.

Rule-by-rule honesty (D5 names 5 rule names, citing D3's original -- since
corrected -- enumeration): re-rendering genuinely, safely fixes
``no-trailing-spaces``, ``no-multiple-empty-lines``, ``new-line-at-eof``,
and ``indentation``. It deliberately does **not** claim to fix
``no-partially-commented-tag-lines``: a `#` character embedded in a tag's
own *name* is a content defect (the tag's name itself is malformed), not a
layout one -- "fixing" it would mean guessing how to rename the tag, which
is a semantic decision this formatter has no authority to make. That
violation falls through to Tier 2 (or escalation) unchanged, though no code
path in this platform has ever produced one.
"""

from __future__ import annotations

from typing import Any

from feature_engineering.generation.render import render_background, render_feature, render_scenario
from feature_engineering.gherkin_lint.source import parse_source_text


def _split_leading_comment(content: str) -> tuple[str | None, str]:
    """Peel off a single leading `# ...` comment line, if present.

    Comments are not part of the Gherkin parser's `feature` AST node (the
    full parsed document carries them separately, and
    :func:`~feature_engineering.gherkin_lint.source.parse_source_text` only
    exposes `feature`) -- re-rendering from the AST alone would silently
    drop the one comment this pipeline ever produces (the full-title
    preservation line from
    :func:`~feature_engineering.generation.assembler.derive_feature_name`).
    Handled here, at the text level, rather than by extending the shared
    parser's exposed shape for a single, already-known caller.
    """
    lines = content.split("\n")
    if lines and lines[0].startswith("#"):
        return lines[0], "\n".join(lines[1:])
    return None, content


def _rstrip_step(step: dict[str, Any]) -> dict[str, Any]:
    """Defensive: strip trailing whitespace embedded in step text itself,
    not just line-level padding around it. `no-trailing-spaces` checks raw
    lines; a step whose own text value ends in whitespace would otherwise
    survive re-rendering unchanged (the value is preserved verbatim by
    design) and keep failing the rule this tier exists to close."""
    return {**step, "text": step["text"].rstrip()}


def format_feature_content(content: str) -> str:
    """Deterministically reformat `content`, fixing pure-formatting lint
    violations. Returns `content` unchanged if it does not parse (Tier 2's
    or escalation's problem, not this tier's) or has no `Feature:` block.

    No LLM call, no disk I/O, no network access. Semantics-preserving by
    construction: scenario/step/tag/table VALUES are read from the parsed
    AST and re-emitted verbatim; only indentation, blank-line count, and
    end-of-file newline discipline change.
    """
    leading_comment, body = _split_leading_comment(content)
    source = parse_source_text(body)
    if source.feature is None:
        return content

    feature = source.feature
    feature_tags = [t["name"] for t in feature.get("tags", [])]

    body_blocks: list[str] = []
    for child in feature.get("children", []):
        background = child.get("background")
        if background is not None:
            cleaned_background = {
                **background,
                "steps": [_rstrip_step(s) for s in background.get("steps", [])],
            }
            body_blocks.append(render_background(cleaned_background))
            continue

        scenario = child["scenario"]
        tags = [t["name"].rstrip() for t in scenario.get("tags", [])]
        steps = [_rstrip_step(s) for s in scenario.get("steps", [])]
        body_blocks.append(
            render_scenario(
                keyword=scenario["keyword"],
                name=(scenario.get("name") or "").rstrip(),
                tags=tags,
                steps=steps,
                examples=scenario.get("examples", []),
            )
        )

    return render_feature(
        title=(feature.get("name") or "").rstrip(),
        feature_tags=feature_tags,
        body_blocks=body_blocks,
        comment=leading_comment,
    )


__all__ = ["format_feature_content"]
