"""Prompt Governance Framework — Layer 1's composition root.

The generic, behaviour-free framework mechanism (`PromptRegistry`,
`PromptLoader`, exceptions, the governed template contract) relocated to
`shared.prompts.framework` (additive, 2026-07-27, ADR-0043 D4 carve-out-3) —
it carries no Layer-1 judgement logic and is a second-consumer-ready shared
mechanism, not this layer's own content. What remains here is Layer-1-specific:
`build_prompt_registry`, the canonical composition entry point that hardcodes
Layer 1's own governed prompt registrations. See ADR-0014's and ADR-0043 D4's
own relocation notes for the full reasoning.

Public surface
--------------
build_prompt_registry   — canonical composition entry point (Layer 1 content)
"""

from __future__ import annotations

from requirement_intelligence.prompts.framework.composition import build_prompt_registry

__all__ = [
    "build_prompt_registry",
]
