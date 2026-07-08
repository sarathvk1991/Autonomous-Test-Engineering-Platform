"""Prompt metadata — descriptive identity of one versioned governed prompt.

:class:`PromptMetadata` is the canonical identity model for a governed prompt.
It consolidates every descriptive property into one **immutable** value: who
the prompt is, what version it carries, where it stands in its lifecycle,
what it fingerprints to, and which downstream subsystem versions it was
validated against.

Why a dedicated metadata model?
---------------------------------
Without a canonical model, prompt identity is scattered:
``PROMPT_VERSION`` sits in ``prompt_constants``, lifecycle is undeclared, the
SHA256 is recomputed on the fly, and compatibility is nowhere.  Once metadata
is a canonical model it can appear safely in audit records, observability
signals, registries, and test assertions without any risk of post-hoc mutation.

This mirrors the design of :class:`ValidationRuleMetadata` (validation layer),
:class:`CP1FrameworkMetadata` (CP1 layer), and the general canonical-models
philosophy described in ``docs/architecture/validation-canonical-models.md``.

Version
-------
:data:`PROMPT_METADATA_VERSION` versions the **shape** of this class.  It
advances additively; breaking changes are ADR-gated.
"""

from __future__ import annotations

from requirement_intelligence.prompts.models.prompt_compatibility import PromptCompatibility
from requirement_intelligence.prompts.models.prompt_version import PromptLifecycle
from shared.contracts.base import Schema

#: Version of the :class:`PromptMetadata` *shape* — owned here as the single
#: source of truth.  Advances additively; breaking changes are ADR-gated.
PROMPT_METADATA_VERSION = "1.0"


class PromptMetadata(Schema):
    """Immutable descriptive identity of one versioned governed prompt.

    Field names are ``snake_case`` in Python and serialise to ``camelCase``
    when converted to a dict/JSON via ``.model_dump(by_alias=True)``.

    Fields
    ------
    prompt_id:
        Stable, machine-readable identifier (e.g. ``"requirement_analysis"``).
        Never changes across versions of the same prompt family.
    name:
        Human-readable display name (e.g. ``"Requirement Analysis Prompt"``).
    version:
        Semantic version string (e.g. ``"1.0.0"``).  The single source of
        truth for which version of this prompt the metadata describes.
    owner:
        Architectural owner of this prompt (e.g. ``"Prompt Framework"``).
        Identifies who is responsible for maintaining and governing it.
    lifecycle:
        Current lifecycle state.  Must be :attr:`~PromptLifecycle.PRODUCTION`
        before the prompt can serve live analysis runs.
    description:
        Human-readable description of what this prompt does and why it exists.
    sha256:
        Hex SHA-256 fingerprint of the versioned template file stored in
        ``prompts/versions/``.  This is the **governed fingerprint** of the
        static template (Phase 8).  It is distinct from the per-execution
        ``promptSha256`` recorded in ``manifest.json``, which fingerprints the
        fully assembled prompt including the injected artifact context.
    compatibility:
        Explicit compatibility declarations — which downstream subsystem
        versions this prompt was verified against (Phase 7).
    release_introduced:
        Platform release in which this prompt version first appeared
        (e.g. ``"1.0.0"``).
    release_deprecated:
        Platform release in which this prompt version was deprecated, if any.
        ``None`` while the prompt is active.
    """

    prompt_id: str
    name: str
    version: str
    owner: str
    lifecycle: PromptLifecycle
    description: str
    sha256: str
    compatibility: PromptCompatibility
    release_introduced: str
    release_deprecated: str | None = None
