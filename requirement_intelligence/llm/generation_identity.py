"""The pinning foundation for Nitin's re-run/delta-scoped-regeneration
cluster (`docs/architecture/mentor-feedback-scoping.md` item #1's re-run
item; the cluster the "DELTA-SCOPED-REGENERATION CLUSTER SURFACED" note
mapped, 2026-08-13): which prompt version and which model produced one
generated artifact.

This is the identical gap-shape :mod:`.token_usage` already closed for
token counts: the identity is already captured at the call site --
:class:`~requirement_intelligence.llm.llm_models.LLMResponse.model`/
``.provider`` on every response, and
:class:`~shared.prompts.models.prompt_metadata.PromptMetadata.sha256` on
every governed prompt -- but every L2/L3 generator has, until this module,
discarded it after reading ``generated_text``. Only L1's own
``TestableRequirementSetProvenance`` (`contracts/testable_requirement.py`)
persists this identity today, once per run. This module is the same
persistence, generalized: purely additive, changes nothing about what any
call site generates, gates, caches, or skips. A caller that never reads
``last_identity`` sees no behavior change at all.

Scope, explicit: this module PERSISTS identity. It does not build a cache,
a cache key, delta-scoped regeneration, or any invalidation logic -- those
are this identity's own future consumers, not built here.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from shared.contracts.base import Schema


class GenerationIdentity(Schema):
    """The prompt + model identity that produced one generated artifact --
    mirrors `TestableRequirementSetProvenance`'s own field shape exactly
    (`contracts/testable_requirement.py`), generalized from "once per run"
    (L1) to "once per generated artifact" (L2/L3).

    Every field is already captured, verbatim, at the call site that
    constructs this object: ``prompt_id``/``prompt_version``/``prompt_sha256``
    from the governed `PromptDefinition.metadata` the generator resolved from
    its `PromptRegistry`; ``provider``/``model`` from the `LLMResponse` the
    provider returned. Nothing here is invented, inferred, or recomputed.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    prompt_id: str = Field(..., min_length=1)
    prompt_version: str = Field(..., min_length=1)
    prompt_sha256: str = Field(..., min_length=1)
    provider: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)


__all__ = ["GenerationIdentity"]
