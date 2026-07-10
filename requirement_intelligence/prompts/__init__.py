"""Requirement Prompt Framework.

Provider-agnostic construction and governance of Requirement Intelligence prompts.
This package knows nothing about Gemini, Azure OpenAI, Anthropic or any specific
model — it only builds and governs prompts.

Public surface
--------------
Existing (unchanged):
RequirementPromptBuilder — builds a PromptRequest from a ConsolidatedArtifact
PromptRequest            — the finished, provider-agnostic prompt

Prompt Governance (new - Phase 2-9):
PromptDefinition         — immutable aggregate of metadata + template content
PromptMetadata           — canonical identity of one versioned governed prompt
PromptCompatibility      — explicit compatibility declarations per prompt
PromptVersion            — semantic version value object with comparison + bumping
PromptLifecycle          — governed lifecycle states (Draft → Archived)
PromptRegistry           — explicit, deterministic, sealable prompt registry
PromptRegistryState      — lifecycle state of the registry (OPEN / SEALED)
PromptLoader             — file-based prompt loader with SHA-256 verification
GovernedTemplate         — a governed template parsed into its runtime sections
parse_governed_template  — the governed runtime template contract (CAP-075)
PromptFrameworkError     — base exception for all framework errors
PromptRegistryError      — registry-level failures
PromptLoaderError        — file loading / integrity failures
PromptNotFoundError      — lookup failures
PromptTemplateContractError — template structure violations
build_prompt_registry    — canonical composition entry point
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
from requirement_intelligence.prompts.models.prompt_compatibility import PromptCompatibility
from requirement_intelligence.prompts.models.prompt_definition import PromptDefinition
from requirement_intelligence.prompts.models.prompt_metadata import PromptMetadata
from requirement_intelligence.prompts.models.prompt_version import PromptLifecycle, PromptVersion
from requirement_intelligence.prompts.requirement_prompt_builder import (
    PromptRequest,
    RequirementPromptBuilder,
)

__all__ = [
    "ARTIFACT_CONTEXT_PLACEHOLDER",
    "GovernedTemplate",
    "PromptCompatibility",
    "PromptDefinition",
    "PromptFrameworkError",
    "PromptLifecycle",
    "PromptLoader",
    "PromptLoaderError",
    "PromptMetadata",
    "PromptNotFoundError",
    "PromptRegistry",
    "PromptRegistryError",
    "PromptRegistryState",
    "PromptRequest",
    "PromptTemplateContractError",
    "PromptVersion",
    "RequirementPromptBuilder",
    "build_prompt_registry",
    "parse_governed_template",
]
