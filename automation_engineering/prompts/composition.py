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
* It does not build CP3, CP4, or promotion (each build's own scope
  boundary).
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

#: v1.1.0's own compatibility -- deliberately NOT identical to v1.0.0's.
#: `customqa_profile_version` is unchanged (the SAME customqa:* rules are
#: referenced, verbatim, by both versions' own CONSTRAINTS sections); but
#: `output_schema_version` is bumped to "1.1.0" because the INPUT contract
#: this version's own shape depends on genuinely changed (a `methods` list
#: of caller-named method specs, replacing the single top-level
#: `action_text`/`captures` pair) -- a real, load-bearing difference a
#: downstream consumer checking compatibility should be able to see, even
#: though the class-level OUTPUT shape (one class extending BasePage, with
#: locator fields and action methods) is the same FAMILY of contract v1.0.0
#: already declared (this is what makes the change MINOR, per ADR-0014's
#: own versioning table, not MAJOR).
_GENERATE_PAGE_OBJECTS_V1_1_0_COMPATIBILITY = PromptCompatibility(
    dimensions={
        "output_schema_version": "1.1.0",
        "customqa_profile_version": "1.0.0",
    }
)

#: Same two Layer-3 dimensions as the other two prompts -- the third
#: registrant, still the same genuine reuse, not re-invention.
_GENERATE_UTILITIES_COMPATIBILITY = PromptCompatibility(
    dimensions={
        "output_schema_version": "1.0.0",
        "customqa_profile_version": "1.0.0",
    }
)

#: Same two Layer-3 dimensions as the other three prompts -- the fourth
#: registrant, and the one whose OWN output_schema_version tracks a
#: different contract (ADR-0043 D7's test-data specification shape) than
#: the other three's Gherkin-step-need-derived contracts, even though the
#: dimension NAME is shared.
_GENERATE_TEST_DATA_COMPATIBILITY = PromptCompatibility(
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

    # --- generate_page_objects v1.1.0 --------------------------------------
    # Additive: adds MULTI-METHOD support (a `methods` list of caller-named
    # method specs) alongside v1.0.0's own single-action shape -- MINOR per
    # ADR-0014's own versioning table ("Additive section -- output schema
    # compatibility preserved"): the class-level OUTPUT shape (one class
    # extending BasePage, locator fields, action methods) is the same
    # FAMILY of contract v1.0.0 already declared, just now able to carry
    # more than one method per class. v1.0.0's own file/metadata are
    # UNCHANGED (ADR-0014 invariant H.1: governed prompt wording is
    # byte-for-byte frozen unless a governed version bump is performed --
    # this is that bump, added alongside, never edited in place). Registered
    # DRAFT, mirroring the other three Layer 3 prompts' own current
    # lifecycle (Layer 3 has not reached production maturity) -- unlike
    # Layer 1's `requirement_analysis` v1.1.0 precedent (registered
    # APPROVED, since that family is already PRODUCTION).
    loaded_v1_1_0 = loader.load(
        prompt_id="generate_page_objects",
        version="1.1.0",
        versions_dir=resolved_dir,
    )
    registry.register(
        PromptDefinition(
            metadata=PromptMetadata(
                prompt_id="generate_page_objects",
                name="Generate Page Objects",
                version="1.1.0",
                owner="Automation Engineering Layer",
                lifecycle=PromptLifecycle.DRAFT,
                description=(
                    "Generates one Java page-object class for MULTIPLE page-object "
                    "actions at once -- the multi-method extension of v1.0.0. Takes an "
                    "ordered, non-empty list of method specs (each with a caller-chosen "
                    "method_name, an action_text, and its own captures) and produces ONE "
                    "class exposing exactly one action method per spec, every method_name "
                    "used verbatim. Used when the generation seam "
                    "(automation_engineering.generation.page_object_orchestrator"
                    ".orchestrate_page_object_class) batches two-or-more NO_MATCH "
                    "method-needs for the SAME fresh class into one generation call, "
                    "closing the gap where only the first of several methods on one "
                    "brand-new class ever reached the seam. Born compliant with the "
                    "customqa:* quality profile (ADR-0044 D5) exactly as v1.0.0 is, "
                    "including customqa:long-method applied to EVERY generated method, "
                    "not just one. Targets the same tracked test-suite-baseline's own "
                    "package com.automation.pages convention, extending BasePage. v1.0.0 "
                    "remains registered, unedited, for the ordinary single-method case."
                ),
                sha256=loaded_v1_1_0.sha256,
                compatibility=_GENERATE_PAGE_OBJECTS_V1_1_0_COMPATIBILITY,
                release_introduced="1.1.0",
            ),
            content=loaded_v1_1_0.content,
        )
    )

    # --- generate_utilities v1.0.0 -----------------------------------------
    loaded = loader.load(
        prompt_id="generate_utilities",
        version="1.0.0",
        versions_dir=resolved_dir,
    )
    registry.register(
        PromptDefinition(
            metadata=PromptMetadata(
                prompt_id="generate_utilities",
                name="Generate Utilities",
                version="1.0.0",
                owner="Automation Engineering Layer",
                lifecycle=PromptLifecycle.DRAFT,
                description=(
                    "Generates one Java utility class for a utility action the reuse "
                    "engine (automation_engineering.reuse.engine.decide_reuse) returned "
                    "NO_MATCH for (ADR-0044 D3/D4). Born compliant with the customqa:* "
                    "quality profile (ADR-0044 D5) -- only customqa:long-method is "
                    "evidenced as applicable (customqa:direct-webdriver-action's own "
                    "evidenced target is a page-object file specifically; a utility that "
                    "needs WebDriver is architecturally a page object, not a utility, so "
                    "the constraint here is structural -- no WebDriver import at all -- "
                    "not a customqa:* rule restated). Targets the tracked baseline's own "
                    "package com.automation.utils convention, mirroring the real "
                    "ConfigReader shape (final class, private constructor, static methods "
                    "only). Never generates page objects, test-data classes, or a "
                    "runner/test class (ADR-0044 D2)."
                ),
                sha256=loaded.sha256,
                compatibility=_GENERATE_UTILITIES_COMPATIBILITY,
                release_introduced="1.0.0",
            ),
            content=loaded.content,
        )
    )

    # --- generate_test_data v1.0.0 ------------------------------------------
    loaded = loader.load(
        prompt_id="generate_test_data",
        version="1.0.0",
        versions_dir=resolved_dir,
    )
    registry.register(
        PromptDefinition(
            metadata=PromptMetadata(
                prompt_id="generate_test_data",
                name="Generate Test Data",
                version="1.0.0",
                owner="Automation Engineering Layer",
                lifecycle=PromptLifecycle.DRAFT,
                description=(
                    "Generates one Java test-data class from Layer 2's own test-data "
                    "specification (ADR-0043 D7 -- 'which fields are needed, and for each, "
                    "whether positive/negative/boundary variants are required, seeded by "
                    "AcceptanceCriterion.polarity_hints[]'). BREAKS the reuse-first triad "
                    "pattern deliberately (ADR-0044 D3): this generator's input is never a "
                    "Gherkin step need, and generation never consults the reuse engine -- a "
                    "test-data class's own field set is intrinsically specific to the one "
                    "requirement/AC that seeded it, unlike a step-def/page-object/utility's "
                    "generic, requirement-independent capability. Reconciles the converted "
                    "POC prompt (docs/reference/automation-poc/prompts/generate-test-data.md, "
                    "which called a ConfigReader.get(...) method the tracked baseline's real "
                    "ConfigReader never had) against the walking-skeleton's actual env()/data() "
                    "split (ADR-0037 D3): every generated value is ConfigReader.data(...)- "
                    "mediated or a literal constant, never ConfigReader.env(...) and never a "
                    "new env.* config.properties key. Targets the tracked baseline's own "
                    "package com.automation.utils convention (ADR-0044 D7's own lock -- the "
                    "SAME package generic utilities target). Never generates page objects, "
                    "generic utilities, or a runner/test class (ADR-0044 D2)."
                ),
                sha256=loaded.sha256,
                compatibility=_GENERATE_TEST_DATA_COMPATIBILITY,
                release_introduced="1.0.0",
            ),
            content=loaded.content,
        )
    )

    # Seal to prevent any future modification.
    registry.seal()
    return registry


__all__ = ["build_prompt_registry"]
