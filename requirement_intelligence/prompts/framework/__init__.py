"""Prompt Governance Framework.

This package provides the reusable, behaviour-free infrastructure that the
Prompt Governance subsystem plugs into: a registry with an explicit registration
contract, a loader that verifies template integrity, exceptions, and composition
helpers.

The framework knows nothing about:
- Gemini, Azure OpenAI, Anthropic, Ollama, or any other LLM provider
- The Requirement Analysis Service
- The Response Validation subsystem
- The CP1 subsystem
- The Normalization subsystem

It only governs prompts.

Public surface
--------------
PromptRegistryState     — lifecycle state of the registry (OPEN / SEALED)
PromptRegistry          — explicit, deterministic, sealable prompt registry
PromptLoader            — file-based prompt loader with SHA-256 verification
PromptFrameworkError    — base exception for all framework errors
PromptRegistryError     — registry-level failures
PromptLoaderError       — file loading / integrity failures
PromptNotFoundError     — lookup failures
build_prompt_registry   — canonical composition entry point
"""

from __future__ import annotations

from requirement_intelligence.prompts.framework.composition import build_prompt_registry
from requirement_intelligence.prompts.framework.prompt_exceptions import (
    PromptFrameworkError,
    PromptLoaderError,
    PromptNotFoundError,
    PromptRegistryError,
    PromptTemplateContractError,
)
from requirement_intelligence.prompts.framework.prompt_loader import PromptLoader
from requirement_intelligence.prompts.framework.prompt_registry import (
    PromptRegistry,
    PromptRegistryState,
)
from requirement_intelligence.prompts.framework.prompt_template_contract import (
    ARTIFACT_CONTEXT_PLACEHOLDER,
    GovernedTemplate,
    parse_governed_template,
)

__all__ = [
    "ARTIFACT_CONTEXT_PLACEHOLDER",
    "GovernedTemplate",
    "PromptFrameworkError",
    "PromptLoader",
    "PromptLoaderError",
    "PromptNotFoundError",
    "PromptRegistry",
    "PromptRegistryError",
    "PromptRegistryState",
    "PromptTemplateContractError",
    "build_prompt_registry",
    "parse_governed_template",
]
