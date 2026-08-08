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

#: v1.1.0's own compatibility -- deliberately IDENTICAL to v1.0.0's, on both
#: dimensions. Purely additive content within the same request/response
#: shape (still "one step-definition class, one caller-named method"): a new
#: PAGE-OBJECT CONSTRUCTION section conveys this platform's REAL WebDriver
#: lifecycle (`com.automation.base.DriverFactory`/`Hooks`, ADR-0041 D5) and
#: instructs the model to construct the page-object field lazily via
#: `DriverFactory.get()` rather than a no-argument constructor -- fixing a
#: live-measured defect where the pre-existing step-defs' own `new XPage()`
#: is incompatible with the constructor-injected page objects ADR-0041 D5
#: requires. MINOR per ADR-0014's own versioning table ("Additive section --
#: output schema compatibility preserved"), not a new schema version;
#: `customqa_profile_version` is unchanged -- the same customqa:* rules are
#: referenced, verbatim, by this version's own CONSTRAINTS section too.
_GENERATE_STEP_DEFINITIONS_V1_1_0_COMPATIBILITY = PromptCompatibility(
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

#: v1.2.0's own compatibility -- deliberately IDENTICAL to v1.1.0's, on both
#: dimensions. `output_schema_version` stays "1.1.0": the INPUT contract (a
#: `methods` list of caller-named method specs) and the class-level OUTPUT
#: shape (one class extending BasePage, locator fields, action methods) are
#: both unchanged -- this version adds a BASEPAGE'S REAL INHERITED API
#: section supplying BasePage's actual method inventory (`open(String)`,
#: `currentTitle()`, and the inherited `driver`/`wait` fields) so the model
#: stops inventing fictional Selenium-POM helpers (`isElementDisplayed`,
#: `sendKeys`, `click`, `findElement`, `getText`, ...) that don't exist on
#: this platform's real BasePage -- a live-measured defect (31 of 32
#: generated classes called at least one such helper). Purely additive
#: content within the same request/response shape: MINOR per ADR-0014's own
#: versioning table ("Additive section -- output schema compatibility
#: preserved"), not a new schema version. `customqa_profile_version` is
#: unchanged for the same reason v1.1.0's was: the same customqa:* rules are
#: referenced, verbatim, by this version's own CONSTRAINTS section too.
_GENERATE_PAGE_OBJECTS_V1_2_0_COMPATIBILITY = PromptCompatibility(
    dimensions={
        "output_schema_version": "1.1.0",
        "customqa_profile_version": "1.0.0",
    }
)

#: v1.3.0's own compatibility -- deliberately IDENTICAL to v1.2.0's, on both
#: dimensions. `output_schema_version` stays "1.1.0": the INPUT contract (a
#: `methods` list of caller-named method specs) and the class-level OUTPUT
#: shape (one class extending BasePage, locator fields, action methods) are
#: both unchanged -- this version adds an OPTIONAL `return_type` field to
#: each `methods` entry (defect-4 fix: a live regeneration run found the
#: step-definition generator's own verification calls assume a boolean
#: return while the page-object generator, never told what the call site
#: expects, is free to declare the same method void -- neither prompt
#: conveyed its own assumption to the other). A request that omits
#: `return_type` (or supplies `null`) behaves exactly as v1.2.0 did --
#: unconstrained, model's own choice -- so this is purely additive content
#: within the same request/response shape: MINOR per ADR-0014's own
#: versioning table ("Additive section -- output schema compatibility
#: preserved"), not a new schema version. `customqa_profile_version` is
#: unchanged for the same reason v1.1.0's/v1.2.0's were: the same
#: customqa:* rules are referenced, verbatim, by this version's own
#: CONSTRAINTS section too.
_GENERATE_PAGE_OBJECTS_V1_3_0_COMPATIBILITY = PromptCompatibility(
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

    # --- generate_step_definitions v1.1.0 -----------------------------------
    # Additive: conveys this platform's REAL WebDriver lifecycle
    # (com.automation.base.DriverFactory + Hooks, ADR-0041 D5) via a new
    # PAGE-OBJECT CONSTRUCTION section, and instructs the model to construct
    # the page-object field lazily -- `if (xPage == null) { xPage = new
    # XPage(DriverFactory.get()); }` inside the generated method's own body
    # -- rather than a no-argument constructor. Fixes a live-measured
    # defect: the platform's pre-existing step-defs (test-suite-baseline's
    # own LoginSteps.java, CheckoutSteps.java, ...) construct page objects
    # with `new XPage()` (no-arg), which is incompatible with the
    # constructor-injected page objects ADR-0041 D5 (and every generated
    # page-object prompt) requires -- `new XPage()` does not compile against
    # a class whose only constructor takes a WebDriver. MINOR per
    # ADR-0014's own versioning table ("Additive section -- output schema
    # compatibility preserved"): still one step-definition class, one
    # caller-matched method. v1.0.0's own file/metadata are UNCHANGED
    # (ADR-0014 invariant H.1: governed prompt wording is byte-for-byte
    # frozen unless a governed version bump is performed -- this is that
    # bump, added alongside, never edited in place). Registered DRAFT,
    # mirroring every other Layer 3 prompt's own current lifecycle. This is
    # the INPUT-side fix only -- the tracked baseline's own DriverFactory/
    # Hooks mechanism and its proven `SmokeSteps.java`/`SmokePage.java`
    # pattern already exist and are cited directly, not invented here;
    # whether the model actually follows the lazy-construction instruction
    # is proven by the (separate, later) live regeneration re-run.
    loaded_v1_1_0 = loader.load(
        prompt_id="generate_step_definitions",
        version="1.1.0",
        versions_dir=resolved_dir,
    )
    registry.register(
        PromptDefinition(
            metadata=PromptMetadata(
                prompt_id="generate_step_definitions",
                name="Generate Step Definitions",
                version="1.1.0",
                owner="Automation Engineering Layer",
                lifecycle=PromptLifecycle.DRAFT,
                description=(
                    "Generates one Java step-definition method for a Gherkin step the "
                    "reuse engine (automation_engineering.reuse.engine.decide_reuse) "
                    "returned NO_MATCH for (ADR-0044 D3/D4) -- identical request/response "
                    "shape to v1.0.0, now conveying this platform's REAL WebDriver "
                    "lifecycle (com.automation.base.DriverFactory + Hooks, ADR-0041 D5) "
                    "so the model constructs page-object fields lazily via "
                    "DriverFactory.get() -- exactly the tracked baseline's own "
                    "SmokeSteps.java/SmokePage.java pattern -- instead of a no-argument "
                    "constructor. Fixes a live-measured defect: the platform's "
                    "pre-existing step-defs construct page objects with new XPage() "
                    "(no-arg), incompatible with the constructor-injected page objects "
                    "ADR-0041 D5 requires. Targets the tracked test-suite-baseline's own "
                    "package com.automation.steps convention. v1.0.0 remains registered, "
                    "unedited."
                ),
                sha256=loaded_v1_1_0.sha256,
                compatibility=_GENERATE_STEP_DEFINITIONS_V1_1_0_COMPATIBILITY,
                release_introduced="1.1.0",
            ),
            content=loaded_v1_1_0.content,
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

    # --- generate_page_objects v1.2.0 --------------------------------------
    # Additive: supplies BasePage's REAL inherited method inventory (a new
    # BASEPAGE'S REAL INHERITED API section listing `open(String)`,
    # `currentTitle()`, and the inherited `driver`/`wait` fields -- the
    # COMPLETE real surface, read directly from the tracked baseline's own
    # test-suite-baseline/src/test/java/com/automation/base/BasePage.java)
    # and constrains generation to it -- MINOR per ADR-0014's own versioning
    # table ("Additive section -- output schema compatibility preserved"):
    # the `methods`-list request shape and the one-class-extending-BasePage
    # response shape are both unchanged from v1.1.0. Fixes a live-measured
    # defect: v1.1.0's own CONSTRAINTS section told the model to "route
    # through the inherited BasePage helpers" WITHOUT ever listing what they
    # are, so the model fell back on Selenium-POM training conventions
    # (isElementDisplayed, sendKeys, click, findElement, getText, ...) that
    # this platform's real BasePage does not have -- 31 of 32 generated
    # classes in a live regeneration run called at least one such fictional
    # helper and failed to compile. v1.1.0's own file/metadata are UNCHANGED
    # (ADR-0014 invariant H.1: governed prompt wording is byte-for-byte
    # frozen unless a governed version bump is performed -- this is that
    # bump, added alongside, never edited in place). Registered DRAFT,
    # mirroring every other Layer 3 prompt's own current lifecycle. The real
    # inventory is HARDCODED directly in this version's own prompt text
    # (not parsed from BasePage.java at render time) -- BasePage is a
    # stable platform class, this prompt is itself a governed, versioned
    # asset, and the platform already hardcodes another real class's
    # surface the same way (generate_test_data_v1.0.0.txt's own
    # ConfigReader.env(...)/ConfigReader.data(...) references); if BasePage
    # ever changes, the prompt version bumps, exactly as governance
    # intends. This is the INPUT-side fix only -- it proves the real
    # inventory reaches the prompt; whether the model actually stops
    # inventing helpers is proven by the (separate, later) live
    # regeneration re-run, not by this registration.
    loaded_v1_2_0 = loader.load(
        prompt_id="generate_page_objects",
        version="1.2.0",
        versions_dir=resolved_dir,
    )
    registry.register(
        PromptDefinition(
            metadata=PromptMetadata(
                prompt_id="generate_page_objects",
                name="Generate Page Objects",
                version="1.2.0",
                owner="Automation Engineering Layer",
                lifecycle=PromptLifecycle.DRAFT,
                description=(
                    "Generates one Java page-object class for MULTIPLE page-object "
                    "actions at once -- identical request/response shape to v1.1.0, now "
                    "supplying BasePage's REAL inherited method inventory (open(String), "
                    "currentTitle(), and the inherited driver/wait fields -- the COMPLETE "
                    "real surface of test-suite-baseline's own BasePage.java) and "
                    "constraining generation to it, so the model uses ONLY real inherited "
                    "helpers (or this class's own driver/wait fields directly) instead of "
                    "inventing fictional Selenium-POM helpers from training data "
                    "(isElementDisplayed, sendKeys, click, findElement, getText, ...) that "
                    "don't exist on this platform's real BasePage -- a live-measured "
                    "defect (31 of 32 generated classes called at least one such "
                    "nonexistent helper, failing to compile). v1.1.0 and v1.0.0 both "
                    "remain registered, unedited."
                ),
                sha256=loaded_v1_2_0.sha256,
                compatibility=_GENERATE_PAGE_OBJECTS_V1_2_0_COMPATIBILITY,
                release_introduced="1.2.0",
            ),
            content=loaded_v1_2_0.content,
        )
    )

    # --- generate_page_objects v1.3.0 --------------------------------------
    # Additive: adds an OPTIONAL `return_type` field to each `methods` entry
    # (a new RETURN-TYPE CONTRACT section instructs the model how to honor
    # it) -- identical request/response shape to v1.2.0 otherwise. Fixes a
    # live-measured defect found on the re-run after the defect-2/defect-3
    # fixes: the step-definition generator's own verification calls assume
    # a boolean return (`Assertions.assertTrue(page.isDisplayed())`), while
    # the page-object generator -- never told what the call site expects
    # back -- was free to declare that same method void (waiting/throwing
    # internally instead of returning); measured on 5 of 30 (17%)
    # is.../verify... methods. Investigated first: no ADR and no working
    # reference example (SmokePage.java/SmokeSteps.java, the same reference
    # that anchored the defect-2 fix) specifies this contract -- but it is
    # cleanly DERIVABLE from the step-definition's own call-site usage, the
    # exact mechanism `method_name` derivation already uses
    # (`automation_engineering.generation.page_object_reference_derivation`,
    # its own "RETURN-TYPE DERIVATION" section), extended to also derive the
    # return type implied by how the call's result is used (a sole
    # assertTrue/assertFalse argument implies boolean; an assignment implies
    # its declared type; a bare statement implies void). `return_type` is
    # `null` whenever that derivation is not clean -- the model chooses
    # freely for that one method, identical to v1.2.0's own behavior, never
    # a guessed constraint. MINOR per ADR-0014's own versioning table
    # ("Additive section -- output schema compatibility preserved").
    # v1.0.0/v1.1.0/v1.2.0's own files/metadata are UNCHANGED (ADR-0014
    # invariant H.1: governed prompt wording is byte-for-byte frozen unless
    # a governed version bump is performed -- this is that bump, added
    # alongside, never edited in place). Registered DRAFT, mirroring every
    # other Layer 3 prompt's own current lifecycle. This is the INPUT-side
    # fix only -- it proves the derived return type reaches the prompt and
    # the prompt instructs the model to honor it; whether the model actually
    # complies is proven by the (separate, later) live regeneration re-run,
    # not by this registration.
    loaded_v1_3_0 = loader.load(
        prompt_id="generate_page_objects",
        version="1.3.0",
        versions_dir=resolved_dir,
    )
    registry.register(
        PromptDefinition(
            metadata=PromptMetadata(
                prompt_id="generate_page_objects",
                name="Generate Page Objects",
                version="1.3.0",
                owner="Automation Engineering Layer",
                lifecycle=PromptLifecycle.DRAFT,
                description=(
                    "Generates one Java page-object class for MULTIPLE page-object "
                    "actions at once -- identical request/response shape to v1.2.0, now "
                    "accepting an OPTIONAL return_type per method entry (already derived "
                    "by the platform from the calling step definition's own real usage: "
                    "assertTrue(page.isX()) implies boolean, a bare call implies void, an "
                    "assignment implies its declared type) and instructing the model to "
                    "declare that EXACT return type -- so a verification method's return "
                    "type agrees with what the already-generated step definition actually "
                    "does with the result, fixing a live-measured defect (5 of 30, 17%, "
                    "is.../verify... methods where the step-def assumed boolean and the "
                    "page object declared void, which does not compile). return_type: "
                    "null leaves the method unconstrained, identical to v1.2.0's own "
                    "behavior. v1.2.0, v1.1.0, and v1.0.0 all remain registered, unedited."
                ),
                sha256=loaded_v1_3_0.sha256,
                compatibility=_GENERATE_PAGE_OBJECTS_V1_3_0_COMPATIBILITY,
                release_introduced="1.3.0",
            ),
            content=loaded_v1_3_0.content,
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
