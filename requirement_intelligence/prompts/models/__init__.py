"""Prompt Governance Canonical Models.

This package owns the immutable information models for the Prompt Governance
subsystem.  Every consumer of prompt metadata reads from here; no other module
may own prompt metadata.

Architecture role
-----------------
Canonical models are the lowest layer of the Prompt Governance subsystem.  They
carry **information only** — no behaviour, no loading, no I/O.  They are the
single source of truth for what a governed prompt *is*.

Public surface
--------------
PromptVersion       — semantic version value object with ordering and bumping rules
PromptLifecycle     — governed lifecycle states (Draft → Archived)
PromptCompatibility — explicit compatibility declarations (Normalization/Validation/
                      CP1/GoldenDataset/OutputSchema versions)
PromptMetadata      — complete descriptive identity of one versioned prompt
PromptDefinition    — aggregate of metadata + immutable template content
"""

from __future__ import annotations

from requirement_intelligence.prompts.models.prompt_compatibility import PromptCompatibility
from requirement_intelligence.prompts.models.prompt_definition import (
    PROMPT_DEFINITION_VERSION,
    PromptDefinition,
)
from requirement_intelligence.prompts.models.prompt_metadata import (
    PROMPT_METADATA_VERSION,
    PromptMetadata,
)
from requirement_intelligence.prompts.models.prompt_version import PromptLifecycle, PromptVersion

__all__ = [
    "PROMPT_DEFINITION_VERSION",
    "PROMPT_METADATA_VERSION",
    "PromptCompatibility",
    "PromptDefinition",
    "PromptLifecycle",
    "PromptMetadata",
    "PromptVersion",
]
