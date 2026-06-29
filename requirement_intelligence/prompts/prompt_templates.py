"""Reusable prompt section templates.

Each function assembles centralised constants (and, where relevant, an already
rendered context string) into a finished prompt section.  Templates are pure:
they take strings, return strings, and contain no business logic, no iteration
over domain models, and no provider-specific formatting.
"""

from __future__ import annotations

from requirement_intelligence.prompts.prompt_constants import (
    ANALYSIS_OBJECTIVES,
    CP1_PREPARATION_GUIDANCE,
    JSON_RESPONSE_REQUIREMENTS,
    OUTPUT_REQUIREMENTS,
    SYSTEM_ROLE,
)

_SECTION_SEPARATOR = "\n\n"


def build_system_prompt() -> str:
    """Return the system prompt that establishes the model's role."""
    return SYSTEM_ROLE


def build_analysis_prompt(artifact_context: str) -> str:
    """Return the analysis prompt: objectives followed by the artifact context.

    Parameters
    ----------
    artifact_context:
        A pre-rendered, provider-agnostic description of the consolidated
        artifact produced by the builder.
    """
    return _SECTION_SEPARATOR.join([ANALYSIS_OBJECTIVES, artifact_context])


def build_output_format_prompt() -> str:
    """Return the output-format prompt: rules, JSON contract and CP1 guidance."""
    return _SECTION_SEPARATOR.join(
        [
            OUTPUT_REQUIREMENTS,
            JSON_RESPONSE_REQUIREMENTS,
            CP1_PREPARATION_GUIDANCE,
        ]
    )
