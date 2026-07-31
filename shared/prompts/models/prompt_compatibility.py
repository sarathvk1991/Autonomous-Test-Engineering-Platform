"""Prompt compatibility declarations.

Every governed prompt explicitly declares the downstream subsystem versions it
is compatible with.  Compatibility is **metadata only** — it carries no runtime
behaviour and triggers no enforcement.  It is an architectural record that
allows dependency auditing, regression planning, and impact analysis when any
referenced subsystem version advances.

Compatibility contract
-----------------------
A prompt author updates :class:`PromptCompatibility` when a downstream
subsystem advances its governed version *and* the prompt must be verified
against the new version.  The update is part of the normal version bump
process:

* PATCH bump: compatibility metadata unchanged (wording-only fix).
* MINOR bump: compatibility metadata **may** need updating.
* MAJOR bump: compatibility metadata **must** be updated.

Generalized shape (Phase 9, ADR-0044 D8's trigger, discharged here)
---------------------------------------------------------------------
Originally (Phase 7) this model hardcoded five Layer-1-named fields
(``normalization_version``, ``validation_version``, ``cp1_version``,
``golden_dataset_version``, ``output_schema_version``) — meaningful only to
Layer 1's own prompt (``requirement_analysis``), which is validated against
all five real subsystems. Layer 2 became a second consumer
(``feature_engineering/prompts/composition.py``, ADR-0043 D4) with nothing
genuine to declare against four of them, and had no honest option but to
declare each as the literal string ``"n/a"`` — an open item recorded at
``architecture-baseline-v2.md`` §4 item 12(b), with an explicit trigger:
generalize once a third, structurally different consumer needs its own
compatibility dimensions declared. Layer 3 (``automation_engineering``) is
that third consumer (ADR-0044 D8; trigger fired at ADR-0044's Acceptance,
additive note on ADR-0043 D4) — its step-definition generation prompt has no
Layer 1 subsystem to be compatible with at all, and forcing it to declare
five "n/a" values would be a fabricated signal in the model's own field
names, not just in the values.

This model is generalized as a **mapping of named dimensions**, chosen over
per-layer subtypes precisely because it was designed against three real,
structurally different consumers at once, not against Layer 3 alone:

* Layer 1 (``requirement_intelligence``) declares five real dimensions —
  ``normalization_version``, ``validation_version``, ``cp1_version``,
  ``golden_dataset_version``, ``output_schema_version`` — unchanged in name
  and value, now as dict keys instead of named fields (no behaviour change).
* Layer 2 (``feature_engineering``) declares exactly one —
  ``output_schema_version`` — and no longer fabricates the other four as
  ``"n/a"``: a dimension a consumer has nothing to say about is now simply
  *absent* from its ``dimensions`` mapping, not present with a placeholder
  value.
* Layer 3 (``automation_engineering``) declares its own dimensions, meaningful
  to *it* — e.g. ``customqa_profile_version`` (the ``customqa:*`` SonarQube
  quality-profile version the generation constraints were authored against,
  ADR-0044 D5) and ``baseline_convention_version`` (the tracked
  ``test-suite-baseline`` step-definition convention this prompt targets) —
  none of which are Layer-1-shaped, and none of which Layer 1 or Layer 2 ever
  declare.

A per-layer-subtype design (one ``PromptCompatibility`` subclass per layer)
was considered and rejected: it would require a new class (and a new case in
every place ``PromptMetadata.compatibility`` is consumed) for every future
consumer, permanently re-deriving the same "structurally different fields per
layer" problem this generalization exists to solve. A single mapping-shaped
model treats every consumer symmetrically — the *number* of consumers is
unbounded without the model itself changing shape again.

Governed dimensions actually in use (informational, not enforced here)
--------------------------------------------------------------------------
normalization_version
    The ``NORMALIZATION_CONTRACT_VERSION`` a prompt was validated against.
    Governed by ``docs/architecture/response-normalization-contract.md``.
    Layer 1 only.

validation_version
    The ``DEFAULT_VALIDATION_CONTRACT_VERSION`` a prompt was validated
    against.  Governed by ``docs/architecture/ai-response-validation.md``.
    Layer 1 only.

cp1_version
    The ``DEFAULT_CP1_CRITERIA_CONTRACT_VERSION`` a prompt was validated
    against.  Governed by the Engineering Readiness Criteria Catalog
    (ADR-0012). Layer 1 only.

golden_dataset_version
    The ``GOLDEN_DATASET_VERSION`` a prompt's regression suite used.
    Governed by ``docs/productization/golden-baseline.md``. Layer 1 only.

output_schema_version
    The version of the governed output contract a prompt targets (its own
    ``JSON_RESPONSE_REQUIREMENTS`` shape, its own Gherkin/tag-structure
    contract, or its own generated-Java-shape contract, depending on the
    consumer). The one dimension every layer so far declares, since every
    generation prompt targets *some* versioned output shape.

Nothing in this model enforces that any particular dimension is present —
which dimensions are meaningful is entirely the declaring consumer's own
judgement, recorded in its own composition root, not governed centrally here.
"""

from __future__ import annotations

from pydantic import Field

from shared.contracts.base import Schema


class PromptCompatibility(Schema):
    """Explicit compatibility declarations for one versioned prompt.

    A single field, ``dimensions``: an immutable-at-the-field-level mapping
    of dimension name to the governed version string a prompt was verified
    against (e.g. ``{"output_schema_version": "1.0.0"}``). No imports from
    any governed subsystem; no coupling; information only.

    A consumer declares only the dimensions genuinely meaningful to it —
    there is no fixed, required dimension list, and no dimension is ever
    fabricated with a placeholder value for a subsystem a prompt was never
    validated against (see module docstring).
    """

    dimensions: dict[str, str] = Field(default_factory=dict)

    def get(self, dimension: str, default: str | None = None) -> str | None:
        """Return the declared version for ``dimension``, or ``default`` if
        this prompt declares nothing against it."""
        return self.dimensions.get(dimension, default)
