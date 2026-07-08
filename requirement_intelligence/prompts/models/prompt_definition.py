"""PromptDefinition — the aggregate root of a governed prompt.

:class:`PromptDefinition` is the single governed unit that the
:class:`~requirement_intelligence.prompts.framework.prompt_registry.PromptRegistry`
stores and the
:class:`~requirement_intelligence.prompts.framework.prompt_loader.PromptLoader`
assembles.  It pairs the immutable :class:`PromptMetadata` (identity) with the
immutable template content (substance).

Ownership
---------
Once created, a :class:`PromptDefinition` is **permanently immutable**.  The
underlying ``Schema`` base sets ``frozen=True``, which means field values are
write-protected by Pydantic — any attempt to reassign a field raises
``ValidationError`` / ``FrozenInstanceError``.

No business logic
-----------------
:class:`PromptDefinition` carries **no behaviour**.  It does not assemble the
runtime prompt (that is :class:`RequirementPromptBuilder`'s responsibility), it
does not invoke any LLM, and it knows nothing about providers.  It is an
information container only.

Version
-------
:data:`PROMPT_DEFINITION_VERSION` versions the **shape** of this class.  It
advances additively; breaking changes are ADR-gated.
"""

from __future__ import annotations

from requirement_intelligence.prompts.models.prompt_metadata import PromptMetadata
from shared.contracts.base import Schema

#: Version of the :class:`PromptDefinition` *shape* — owned here as the single
#: source of truth.  Advances additively; breaking changes are ADR-gated.
PROMPT_DEFINITION_VERSION = "1.0"


class PromptDefinition(Schema):
    """Immutable aggregate of a governed prompt's identity and template content.

    Fields
    ------
    metadata:
        The canonical identity and provenance of this prompt version.  Owned
        exclusively by the :class:`PromptMetadata` model; never duplicated.
    content:
        The raw template text loaded from ``prompts/versions/``.  This is the
        *static* template — it contains a ``{artifact_context}`` placeholder
        where the runtime artifact context is injected by
        :class:`~requirement_intelligence.prompts.requirement_prompt_builder.RequirementPromptBuilder`.
        The SHA-256 of this content's bytes (UTF-8 encoded) must equal
        ``metadata.sha256``.

    Invariants
    ----------
    * ``content`` is never empty.
    * ``metadata.sha256`` is the SHA-256 of the UTF-8-encoded ``content``
      (verified at load time by :class:`PromptLoader`; carried here for
      downstream auditability).
    * The definition is **immutable** after construction.
    """

    metadata: PromptMetadata
    content: str
