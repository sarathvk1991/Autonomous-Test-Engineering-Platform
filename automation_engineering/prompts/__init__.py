"""Automation Engineering (Layer 3) Prompt Governance.

Public surface
--------------
build_prompt_registry — canonical composition entry point for Layer 3's own
                         sealed :class:`~shared.prompts.framework.prompt_registry.PromptRegistry`.
"""

from __future__ import annotations

from automation_engineering.prompts.composition import build_prompt_registry

__all__ = ["build_prompt_registry"]
