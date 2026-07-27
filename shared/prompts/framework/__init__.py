"""Prompt Governance Framework.

This package provides the reusable, behaviour-free infrastructure that a
Prompt Governance subsystem plugs into: a registry with an explicit registration
contract, a loader that verifies template integrity, exceptions, and the
governed template contract.

The framework knows nothing about:
- Gemini, Azure OpenAI, Anthropic, Ollama, or any other LLM provider
- The Requirement Analysis Service
- The Response Validation subsystem
- The CP1 subsystem
- The Normalization subsystem
- Any specific layer's own prompt content or composition root

It only governs prompts.

Relocation note (additive, 2026-07-27, ADR-0043 D4 carve-out-3).
------------------------------------------------------------------
This package relocated here from `requirement_intelligence.prompts.framework`
as a no-behavior-change move: it is generic infrastructure with no Layer-1
judgement logic. `build_prompt_registry` (a Layer-1-specific composition
entry point, not part of this generic mechanism) stays behind, still
importable from `requirement_intelligence.prompts.framework.composition`.
See ADR-0014's and ADR-0043 D4's own relocation notes for the full reasoning.

Public surface
--------------
PromptRegistryState     — lifecycle state of the registry (OPEN / SEALED)
PromptRegistry          — explicit, deterministic, sealable prompt registry
PromptLoader            — file-based prompt loader with SHA-256 verification
PromptFrameworkError    — base exception for all framework errors
PromptRegistryError     — registry-level failures
PromptLoaderError       — file loading / integrity failures
PromptNotFoundError     — lookup failures
"""

from __future__ import annotations

from shared.prompts.framework.prompt_exceptions import (
    PromptFrameworkError,
    PromptLoaderError,
    PromptNotFoundError,
    PromptRegistryError,
    PromptTemplateContractError,
)
from shared.prompts.framework.prompt_loader import PromptLoader
from shared.prompts.framework.prompt_registry import (
    PromptRegistry,
    PromptRegistryState,
)
from shared.prompts.framework.prompt_template_contract import (
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
    "parse_governed_template",
]
