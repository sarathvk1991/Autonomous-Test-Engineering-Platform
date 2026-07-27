"""Feature Engineering (Layer 2) Prompt Governance composition root.

This module is the **canonical composition root** for Layer 2's own governed
prompts, mirroring `requirement_intelligence.prompts.framework.composition`
(Layer 1's composition root) exactly — same shared mechanism
(:class:`~shared.prompts.framework.prompt_loader.PromptLoader`,
:class:`~shared.prompts.framework.prompt_registry.PromptRegistry`), same
metadata-in-Python-not-in-the-template discipline, same OPEN→SEALED lifecycle.
Layer 2 is a second **consumer** of the shared mechanism (ADR-0043 D4); it
owns its own prompt *content* the same way Layer 1 owns
`requirement_analysis`'s — this package's `versions/` directory, never
Layer 1's.

Responsibilities
-----------------
1. Define the canonical metadata for every governed Layer 2 prompt (hardcoded,
   explicit — no reflection, no filesystem discovery).
2. Invoke :class:`PromptLoader` to load and verify each versioned template
   from this package's own `versions/`.
3. Assemble :class:`PromptDefinition` instances.
4. Register them in a :class:`PromptRegistry`.
5. Seal the registry to prevent further modification.
6. Return the sealed registry.

Non-responsibilities
---------------------
* This module knows nothing about LLM providers.
* It does not invoke any LLM — no generation logic lives here.
* It does not build CP2 or the remediation loop (ADR-0043 D5) — those are
  later, separate milestones that will *consume* this registry's prompts.

Compatibility caveat (recorded, not resolved here)
----------------------------------------------------
:class:`~shared.prompts.models.prompt_compatibility.PromptCompatibility`'s
five fields (`normalization_version`, `validation_version`, `cp1_version`,
`golden_dataset_version`, `output_schema_version`) are Layer-1-subsystem
names (open item, `architecture-baseline-v2.md` §4 item 12). None of the
first four apply to a Layer 2 prompt — Layer 2 prompts are never validated
against Layer 1's Normalization, Validation, CP1, or golden-dataset
contracts, so claiming a version there would be a fabricated compatibility
signal. Each Layer 2 prompt below declares those four as the literal string
`"n/a"` — an honest absence, not a copied Layer 1 value — and gives only
`output_schema_version` a real value: the version of *this prompt's own*
output contract (the Gherkin/tag-structure or check-report shape it targets).
"""

from __future__ import annotations

from pathlib import Path

from shared.prompts.framework.prompt_loader import PromptLoader
from shared.prompts.framework.prompt_registry import PromptRegistry
from shared.prompts.models.prompt_compatibility import PromptCompatibility
from shared.prompts.models.prompt_definition import PromptDefinition
from shared.prompts.models.prompt_metadata import PromptMetadata
from shared.prompts.models.prompt_version import PromptLifecycle

# ---------------------------------------------------------------------------
# Canonical versions directory
# ---------------------------------------------------------------------------

_VERSIONS_DIR: Path = Path(__file__).parent / "versions"

#: Not applicable to any Layer 2 prompt (see module docstring) — an explicit,
#: honest absence rather than a fabricated or copied Layer 1 value.
_NOT_APPLICABLE = "n/a"

_GENERATE_FEATURE_COMPATIBILITY = PromptCompatibility(
    normalization_version=_NOT_APPLICABLE,
    validation_version=_NOT_APPLICABLE,
    cp1_version=_NOT_APPLICABLE,
    golden_dataset_version=_NOT_APPLICABLE,
    # This prompt's own output contract: scenario content plus the
    # @REQ-PENDING/@SCN-PENDING/@AC-PENDING tag-placeholder structure (D2).
    output_schema_version="1.0.0",
)

_FIX_GHERKIN_LINT_COMPATIBILITY = PromptCompatibility(
    normalization_version=_NOT_APPLICABLE,
    validation_version=_NOT_APPLICABLE,
    cp1_version=_NOT_APPLICABLE,
    golden_dataset_version=_NOT_APPLICABLE,
    # This prompt's own output contract: a ---FEATURE---/---CHANGES--- pair.
    output_schema_version="1.0.0",
)

_VALIDATE_GENERATED_FEATURE_COMPATIBILITY = PromptCompatibility(
    normalization_version=_NOT_APPLICABLE,
    validation_version=_NOT_APPLICABLE,
    cp1_version=_NOT_APPLICABLE,
    golden_dataset_version=_NOT_APPLICABLE,
    # This prompt's own output contract: the two-line advisory check report,
    # not the Gherkin/tag-structure contract the other two prompts target.
    output_schema_version="1.0.0",
)

# ---------------------------------------------------------------------------
# Canonical composition entry point
# ---------------------------------------------------------------------------


def build_prompt_registry(versions_dir: Path | None = None) -> PromptRegistry:
    """Build and return Layer 2's own sealed :class:`PromptRegistry`.

    Loads every governed Layer 2 prompt from this package's versioned
    storage directory, verifies SHA-256 integrity via the shared
    :class:`PromptLoader`, assembles :class:`PromptDefinition` objects,
    registers them, seals the registry, and returns it. Independent of
    Layer 1's own registry instance (`requirement_intelligence.prompts.
    framework.composition.build_prompt_registry`) — registries carry no
    shared state.

    Parameters
    ----------
    versions_dir:
        Override the default `feature_engineering/prompts/versions/`
        directory. Used in tests to point at a temporary fixture directory.

    Raises
    ------
    PromptLoaderError
        If any versioned file fails to load or its SHA-256 does not match
        the manifest.
    """
    resolved_dir = versions_dir if versions_dir is not None else _VERSIONS_DIR

    loader = PromptLoader()
    registry = PromptRegistry()

    # --- generate_feature v1.0.0 (superseded — kept registered, historical) ---
    # Structural defect found while building the first real consumer (the
    # generation core): v1.0.0 asked the LLM for @REQ-PENDING/@AC-PENDING
    # placeholders for ids that ADR-0043 D2 says are *already* platform-minted
    # by Layer 1 before Layer 2 ever runs (REQ-*/AC-*/RSK-* "already carry"
    # the platform-assigned discipline; only SCN-* is genuinely deferred,
    # "assigned after the remediation loop"). Kept registered rather than
    # rewritten in place, mirroring Layer 1's own requirement_analysis
    # v1.0.0/v1.1.0 precedent: a wrong or superseded version stays as a
    # historical, SHA-verified record; a new version carries the fix.
    loaded = loader.load(
        prompt_id="generate_feature",
        version="1.0.0",
        versions_dir=resolved_dir,
    )
    registry.register(
        PromptDefinition(
            metadata=PromptMetadata(
                prompt_id="generate_feature",
                name="Generate Feature File",
                version="1.0.0",
                owner="Feature Engineering Layer",
                lifecycle=PromptLifecycle.DRAFT,
                description=(
                    "SUPERSEDED by v1.1.0 — kept registered as a historical, "
                    "SHA-verified record only; do not consume this version. Defect: "
                    "asked the LLM for @REQ-PENDING/@AC-PENDING placeholders for ids "
                    "ADR-0043 D2 says Layer 1 already mints before Layer 2 runs; only "
                    "@SCN-* is genuinely deferred. See v1.1.0's description."
                ),
                sha256=loaded.sha256,
                compatibility=_GENERATE_FEATURE_COMPATIBILITY,
                release_introduced="1.0.0",
            ),
            content=loaded.content,
        )
    )

    # --- generate_feature v1.1.0 (current) -------------------------------
    loaded = loader.load(
        prompt_id="generate_feature",
        version="1.1.0",
        versions_dir=resolved_dir,
    )
    registry.register(
        PromptDefinition(
            metadata=PromptMetadata(
                prompt_id="generate_feature",
                name="Generate Feature File",
                version="1.1.0",
                owner="Feature Engineering Layer",
                lifecycle=PromptLifecycle.DRAFT,
                description=(
                    "Converts a structured TestableRequirement into Gherkin scenario "
                    "content for one .feature file (ADR-0043 D1/D4). Every ac_id is "
                    "already platform-minted (Layer 1) and is written verbatim, not "
                    "as a placeholder; req_id is never written by the model at all — "
                    "the platform attaches it directly to the Feature line it derives, "
                    "since a requirement-level tag has no per-scenario judgment to "
                    "make. Only @SCN-PENDING is a true placeholder, substituted with a "
                    "real, content-addressed @SCN-* id after generation (D2 — scenario "
                    "identity cannot exist before scenario content does). Does not "
                    "write the Feature: line itself. The version the generation core "
                    "consumes."
                ),
                sha256=loaded.sha256,
                compatibility=_GENERATE_FEATURE_COMPATIBILITY,
                release_introduced="1.1.0",
            ),
            content=loaded.content,
        )
    )

    # --- fix_gherkin_lint v1.0.0 -----------------------------------------
    loaded = loader.load(
        prompt_id="fix_gherkin_lint",
        version="1.0.0",
        versions_dir=resolved_dir,
    )
    registry.register(
        PromptDefinition(
            metadata=PromptMetadata(
                prompt_id="fix_gherkin_lint",
                name="Fix Gherkin Lint Issues",
                version="1.0.0",
                owner="Feature Engineering Layer",
                lifecycle=PromptLifecycle.DRAFT,
                description=(
                    "Fixes a specific list of the platform linter's own reported "
                    "violations against one feature file's exact current text "
                    "(ADR-0043 D5's bounded remediation loop — this is the prompt "
                    "only, not the loop orchestration, which is a later milestone). "
                    "Preserves every @REQ-*/@SCN-*/@AC-* tag verbatim. Layer 2 "
                    "remediation prompt."
                ),
                sha256=loaded.sha256,
                compatibility=_FIX_GHERKIN_LINT_COMPATIBILITY,
                release_introduced="1.0.0",
            ),
            content=loaded.content,
        )
    )

    # --- validate_generated_feature v1.0.0 -------------------------------
    loaded = loader.load(
        prompt_id="validate_generated_feature",
        version="1.0.0",
        versions_dir=resolved_dir,
    )
    registry.register(
        PromptDefinition(
            metadata=PromptMetadata(
                prompt_id="validate_generated_feature",
                name="Validate Generated Feature File",
                version="1.0.0",
                owner="Feature Engineering Layer",
                lifecycle=PromptLifecycle.DRAFT,
                description=(
                    "ADVISORY-ONLY. Judges exactly two dimensions a deterministic "
                    "rule cannot — business readability and step reusability — and "
                    "nothing else; every other check in the POC's original checklist "
                    "is already owned exactly by the platform's own linter and CP2's "
                    "deterministic gate. Per ADR-0040 Recommendation 1 and ADR-0043 "
                    "D5, this prompt's verdict never gates CP2 or any control point; "
                    "it feeds human-in-the-loop review only."
                ),
                sha256=loaded.sha256,
                compatibility=_VALIDATE_GENERATED_FEATURE_COMPATIBILITY,
                release_introduced="1.0.0",
            ),
            content=loaded.content,
        )
    )

    # Seal to prevent any future modification.
    registry.seal()
    return registry
