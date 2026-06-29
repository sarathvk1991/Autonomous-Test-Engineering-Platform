"""Requirement Prompt Framework.

Provider-agnostic construction of Requirement Intelligence analysis prompts.
This package knows nothing about Gemini, Azure OpenAI, Anthropic or any specific
model — it only builds prompts.

Public surface
--------------
RequirementPromptBuilder — builds a PromptRequest from a ConsolidatedArtifact
PromptRequest            — the finished, provider-agnostic prompt
"""

from requirement_intelligence.prompts.requirement_prompt_builder import (
    PromptRequest,
    RequirementPromptBuilder,
)

__all__ = [
    "PromptRequest",
    "RequirementPromptBuilder",
]
