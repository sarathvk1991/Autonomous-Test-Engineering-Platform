"""Automation Engineering (Layer 3) Prompt Governance composition root.

This module is the **canonical composition root** for Layer 3's own governed
prompts, mirroring `feature_engineering.prompts.composition` (Layer 2's
composition root) and `requirement_intelligence.prompts.framework.composition`
(Layer 1's) exactly — same shared mechanism
(:class:`~shared.prompts.framework.prompt_loader.PromptLoader`,
:class:`~shared.prompts.framework.prompt_registry.PromptRegistry`), same
metadata-in-Python-not-in-the-template discipline, same OPEN→SEALED lifecycle.
Layer 3 is a third **consumer** of the shared mechanism (ADR-0044 D8); it owns
its own prompt *content* the same way Layer 1 owns `requirement_analysis`'s
and Layer 2 owns `generate_feature`'s — this package's `versions/` directory,
never theirs.

This registration is also the event ADR-0044 D8 records as the
`PromptCompatibility` generalization trigger (`architecture-baseline-v2.md`
§4 item 12(b)): registering `generate_step_definitions` below is Layer 3's
first real registrant against the shared registry, discharging the
deferral. See `shared/prompts/models/prompt_compatibility.py`'s own
docstring for the generalized model, and the additive note added to
ADR-0043 D4 alongside this change.

Responsibilities
-----------------
1. Define the canonical metadata for every governed Layer 3 prompt (hardcoded,
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
* It does not invoke any LLM — no generation logic lives here
  (:mod:`automation_engineering.generation.step_definition_generator` and
  :mod:`automation_engineering.generation.live_step_definition_generator`
  consume this registry's prompts; they are not built here).
* It does not build utilities, test-data classes, CP3, CP4, or promotion
  (each build's own scope boundary).
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

#: Layer 3's own compatibility dimensions -- neither Layer 1's five
#: subsystem-named fields nor Layer 2's single-dimension "n/a"-free pattern,
#: but its own, genuinely different pair (the generalized model's own
#: docstring, `shared/prompts/models/prompt_compatibility.py`):
#: `output_schema_version` (this prompt's own generated-Java step-definition
#: shape contract) and `customqa_profile_version` (the `customqa:*`
#: SonarQube quality-profile version its CONSTRAINTS section was authored
#: against, ADR-0044 D5's "constrain at generation" role for that profile).
_GENERATE_STEP_DEFINITIONS_COMPATIBILITY = PromptCompatibility(
    dimensions={
        "output_schema_version": "1.0.0",
        "customqa_profile_version": "1.0.0",
    }
)

#: Same two Layer-3 dimensions as `generate_step_definitions` -- the same
#: KIND of contract (a generated-Java shape, and the customqa:* profile
#: version its own CONSTRAINTS section was authored against), genuinely
#: reused rather than re-invented for a second Layer 3 prompt.
_GENERATE_PAGE_OBJECTS_COMPATIBILITY = PromptCompatibility(
    dimensions={
        "output_schema_version": "1.0.0",
        "customqa_profile_version": "1.0.0",
    }
)


# ---------------------------------------------------------------------------
# Canonical composition entry point
# ---------------------------------------------------------------------------


def build_prompt_registry(versions_dir: Path | None = None) -> PromptRegistry:
    """Build and return Layer 3's own sealed :class:`PromptRegistry`.

    Loads every governed Layer 3 prompt from this package's versioned
    storage directory, verifies SHA-256 integrity via the shared
    :class:`PromptLoader`, assembles :class:`PromptDefinition` objects,
    registers them, seals the registry, and returns it. Independent of
    Layer 1's and Layer 2's own registry instances — registries carry no
    shared state.

    Parameters
    ----------
    versions_dir:
        Override the default `automation_engineering/prompts/versions/`
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

    # --- generate_step_definitions v1.0.0 ---------------------------------
    loaded = loader.load(
        prompt_id="generate_step_definitions",
        version="1.0.0",
        versions_dir=resolved_dir,
    )
    registry.register(
        PromptDefinition(
            metadata=PromptMetadata(
                prompt_id="generate_step_definitions",
                name="Generate Step Definitions",
                version="1.0.0",
                owner="Automation Engineering Layer",
                lifecycle=PromptLifecycle.DRAFT,
                description=(
                    "Generates one Java step-definition method for a Gherkin step the "
                    "reuse engine (automation_engineering.reuse.engine.decide_reuse) "
                    "returned NO_MATCH for (ADR-0044 D3/D4). Born compliant with the "
                    "customqa:* quality profile (ADR-0044 D5) -- the constraints are "
                    "injected as both a static CONSTRAINTS section and structured "
                    "input, never left to the model to infer. Targets the tracked "
                    "test-suite-baseline's own package com.automation.steps convention. "
                    "Never generates page objects, utilities, test-data classes, or a "
                    "runner/test class (ADR-0044 D2)."
                ),
                sha256=loaded.sha256,
                compatibility=_GENERATE_STEP_DEFINITIONS_COMPATIBILITY,
                release_introduced="1.0.0",
            ),
            content=loaded.content,
        )
    )

    # --- generate_page_objects v1.0.0 --------------------------------------
    loaded = loader.load(
        prompt_id="generate_page_objects",
        version="1.0.0",
        versions_dir=resolved_dir,
    )
    registry.register(
        PromptDefinition(
            metadata=PromptMetadata(
                prompt_id="generate_page_objects",
                name="Generate Page Objects",
                version="1.0.0",
                owner="Automation Engineering Layer",
                lifecycle=PromptLifecycle.DRAFT,
                description=(
                    "Generates one Java page-object class for a page-object action the "
                    "reuse engine (automation_engineering.reuse.engine.decide_reuse) "
                    "returned NO_MATCH for (ADR-0044 D3/D4). Born compliant with the "
                    "customqa:* quality profile (ADR-0044 D5) -- unlike step definitions, "
                    "page objects are exactly where WebDriver calls legitimately live, so "
                    "the injected constraints constrain HOW WebDriver is used (long-method, "
                    "constructor-injected driver per ADR-0041 D5), not WHETHER it is used. "
                    "Targets the tracked test-suite-baseline's own package "
                    "com.automation.pages convention, extending BasePage. Never generates "
                    "utilities, test-data classes, or a runner/test class (ADR-0044 D2)."
                ),
                sha256=loaded.sha256,
                compatibility=_GENERATE_PAGE_OBJECTS_COMPATIBILITY,
                release_introduced="1.0.0",
            ),
            content=loaded.content,
        )
    )

    # Seal to prevent any future modification.
    registry.seal()
    return registry


__all__ = ["build_prompt_registry"]
