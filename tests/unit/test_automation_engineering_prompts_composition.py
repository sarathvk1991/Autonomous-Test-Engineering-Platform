"""Registration + SHA-256 verification proof for Layer 3's governed prompts:
`generate_step_definitions` v1.0.0 (ADR-0044 D8), `generate_page_objects`
v1.0.0, `generate_utilities` v1.0.0, and `generate_test_data` v1.0.0 (this
build) -- the fourth and last generator, and the one whose "already-
registered" ADR-0044 D7 language turned out to describe the ORIGINAL POC's
own prompt catalog, never this platform's actual governed registry (see
`test_generate_test_data_was_not_actually_registered_before_this_build`).

Mirrors `tests/unit/test_feature_engineering_prompts_composition.py`'s shape
for Layer 2's registry, and `requirement_intelligence/tests/unit/
test_prompt_composition.py`'s shape for Layer 1's -- same shared mechanism,
same discipline, independent registry instance and independent content.

This module also proves the `PromptCompatibility` generalization
(`shared/prompts/models/prompt_compatibility.py`) `generate_step_definitions`'
registration triggered: Layer 3 declares its OWN dimensions here, and Layer
1's/Layer 2's own registrations still work unmodified under the generalized
model (cross-checked directly, not merely asserted independently in their
own test modules).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from automation_engineering.prompts.composition import build_prompt_registry
from shared.prompts.framework.prompt_loader import PromptLoader
from shared.prompts.framework.prompt_registry import PromptRegistryState
from shared.prompts.framework.prompt_template_contract import parse_governed_template
from shared.prompts.models.prompt_version import PromptLifecycle

_ALL_PROMPT_IDS = [
    "generate_step_definitions",
    "generate_page_objects",
    "generate_utilities",
    "generate_test_data",
]
_EXPECTED_PROMPT_IDS = set(_ALL_PROMPT_IDS)


def test_registry_seals_with_exactly_the_four_prompt_families() -> None:
    """Four distinct `prompt_id`s, nine total registered definitions --
    `generate_page_objects` carries five versions (v1.0.0, still
    single-method; v1.1.0, additive multi-method support; v1.2.0, additive
    real-BasePage-inventory support; v1.3.0, additive derived-return-type
    support; v1.4.0, additive DOM-grounding locator-catalog support) and
    `generate_step_definitions` carries two (v1.0.0; v1.1.0, additive
    real-WebDriver-lifecycle support)."""
    registry = build_prompt_registry()

    assert registry.state is PromptRegistryState.SEALED
    assert registry.count() == 9
    assert set(registry.list_prompt_ids()) == _EXPECTED_PROMPT_IDS
    for prompt_id in _ALL_PROMPT_IDS:
        assert registry.is_registered(prompt_id, "1.0.0")
    assert registry.is_registered("generate_page_objects", "1.1.0")
    assert registry.is_registered("generate_page_objects", "1.2.0")
    assert registry.is_registered("generate_page_objects", "1.3.0")
    assert registry.is_registered("generate_page_objects", "1.4.0")
    assert registry.is_registered("generate_step_definitions", "1.1.0")


def test_generate_test_data_was_not_actually_registered_before_this_build() -> None:
    """ADR-0044 D7 and ADR-0043 D7 both call `generate-test-data` "the
    already-registered `generate-test-data` prompt" -- true of the ORIGINAL
    POC's own prompt catalog (`docs/reference/automation-poc/prompts/
    generate-test-data.md`, which this test confirms still exists), but
    FALSE of this platform's actual governed registry: no
    `automation_engineering/prompts/composition.py` registration for it
    existed anywhere before this build. This test records that finding
    directly rather than silently accepting the ADR's own imprecise
    wording -- this build is the one that performs the registration."""
    poc_prompt = Path("docs/reference/automation-poc/prompts/generate-test-data.md")
    assert poc_prompt.exists()

    # Before this build, `generate_test_data` did not appear in the manifest
    # at all; verify the CURRENT manifest lists exactly one file for it,
    # confirming this build is where the registration actually happened.
    manifest_text = Path("automation_engineering/prompts/versions/manifest.json").read_text()
    assert manifest_text.count('"generate_test_data"') == 1


def test_registered_prompt_sha256_matches_the_manifest() -> None:
    """The registry's own load path already verifies this; recompute
    independently here so a tampered manifest or template fails this test
    too, not only the loader's internal check."""
    versions_dir = Path("automation_engineering/prompts/versions")
    registry = build_prompt_registry()

    for definition in registry.get_all():
        file_name = f"{definition.metadata.prompt_id}_v{definition.metadata.version}.txt"
        raw_bytes = (versions_dir / file_name).read_bytes()
        assert PromptLoader.compute_sha256(raw_bytes) == definition.metadata.sha256
        assert definition.content == raw_bytes.decode("utf-8")


def test_registered_as_draft() -> None:
    """Draft is the honest lifecycle for every registered version except
    `generate_page_objects` v1.0.0/v1.1.0/v1.2.0, retired (DEPRECATED) once
    each was superseded -- v1.0.0 by v1.1.0's methods-list template
    (cosmetic-tidy session, 2026-08-21), v1.1.0 by v1.2.0's real-BasePage-
    inventory template and v1.2.0 by v1.3.0's return-type contract (both
    cosmetic-tidy follow-up session, 2026-08-22) -- LivePageObjectGenerator
    loads only v1.3.0."""
    registry = build_prompt_registry()
    deprecated_versions = {"1.0.0", "1.1.0", "1.2.0"}

    for definition in registry.get_all():
        if (
            definition.metadata.prompt_id == "generate_page_objects"
            and definition.metadata.version in deprecated_versions
        ):
            assert definition.metadata.lifecycle == PromptLifecycle.DEPRECATED
        else:
            assert definition.metadata.lifecycle == PromptLifecycle.DRAFT


@pytest.mark.parametrize("prompt_id", _ALL_PROMPT_IDS)
def test_template_conforms_to_the_governed_system_user_contract(prompt_id: str) -> None:
    """All four Layer 3 prompts conform to the full governed template
    contract (unlike Layer 2's `generate_feature`, which carries no
    `{artifact_context}` placeholder at all) -- proven directly by parsing
    each, not merely by construction."""
    registry = build_prompt_registry()
    definition = registry.get(prompt_id, "1.0.0")

    template = parse_governed_template(definition.content)

    assert template.system_prompt.strip()
    assert "{artifact_context}" not in template.system_prompt
    assert template.user_template.count("{artifact_context}") == 1


@pytest.mark.parametrize("prompt_id", _ALL_PROMPT_IDS)
def test_template_embeds_customqa_long_method(prompt_id: str) -> None:
    """`customqa:long-method` is evidenced (`requirement_intelligence/input/
    sonar/sonar-issues.json`, the same fixture every Layer 3 constraint set
    cites) as applicable to all four generated-code shapes -- unconditionally
    present in every render, never optional at runtime."""
    registry = build_prompt_registry()
    definition = registry.get(prompt_id, "1.0.0")

    assert "customqa:long-method" in definition.content


@pytest.mark.parametrize("prompt_id", ["generate_step_definitions", "generate_page_objects"])
def test_only_step_defs_and_page_objects_embed_customqa_direct_webdriver_action(
    prompt_id: str,
) -> None:
    """`customqa:direct-webdriver-action`'s own evidenced target
    (`BadCheckoutPage.java`) and message ("route through the BasePage
    action helpers") are page-object-specific -- it applies to step
    definitions (prohibited there) and page objects (constrained, not
    prohibited, there), never fabricated for utilities or test data."""
    registry = build_prompt_registry()
    definition = registry.get(prompt_id, "1.0.0")

    assert "customqa:direct-webdriver-action" in definition.content


@pytest.mark.parametrize("prompt_id", ["generate_utilities", "generate_test_data"])
def test_utilities_and_test_data_do_not_fabricate_direct_webdriver_action(
    prompt_id: str,
) -> None:
    """The honest negative, for both non-page-object generators: neither
    claims `customqa:direct-webdriver-action` applies -- there is no
    evidence tying that rule to a non-page-object class. Both state the
    architectural boundary (no WebDriver at all) in plain English instead
    of dressing it up as a customqa:* rule this platform never evidenced
    against a utility or test-data file."""
    registry = build_prompt_registry()
    definition = registry.get(prompt_id, "1.0.0")

    assert "customqa:direct-webdriver-action" not in definition.content
    assert "webdriver" in definition.content.lower()  # the plain-English prohibition


def test_page_object_template_frames_webdriver_calls_as_legitimate_here() -> None:
    """The one deliberate asymmetry among the WebDriver-aware prompts: step
    definitions are told WebDriver calls never belong there; page objects
    are told the OPPOSITE -- this is exactly where those calls
    legitimately live."""
    registry = build_prompt_registry()
    definition = registry.get("generate_page_objects", "1.0.0")

    assert "legitimately" in definition.content.lower()
    assert "webdriver" in definition.content.lower()


def test_test_data_template_enforces_the_env_data_boundary() -> None:
    """ADR-0037 D3's SUT-binding boundary, restated where it matters most:
    the test-data prompt's own CONSTRAINTS section explicitly prohibits
    `ConfigReader.env(...)` and any `env.*` config key -- test-data classes
    are the DATA side only."""
    registry = build_prompt_registry()
    definition = registry.get("generate_test_data", "1.0.0")

    assert "configreader.env" in definition.content.lower()
    assert "data.*" in definition.content or "data(" in definition.content.lower()


def test_test_data_template_reconciles_the_stale_poc_configreader_get_call() -> None:
    """The POC's own `generate-test-data.md` calls a `ConfigReader.get(...)`
    method the tracked baseline's REAL `ConfigReader` never had (it only
    ever exposed `env(String)`/`data(String)`, per ADR-0037's own
    resolution note). The registered prompt must not carry that stale call
    forward."""
    registry = build_prompt_registry()
    definition = registry.get("generate_test_data", "1.0.0")

    assert "configreader.get" not in definition.content.lower()


@pytest.mark.parametrize("prompt_id", _ALL_PROMPT_IDS)
def test_compatibility_declares_layer3s_own_dimensions_not_layer1s(prompt_id: str) -> None:
    """Layer 3 declares dimensions genuinely its own -- neither Layer 1's
    five subsystem-named fields nor a fabricated "n/a" for any of them
    (ADR-0044 D8's own generalization; see
    `shared/prompts/models/prompt_compatibility.py`)."""
    registry = build_prompt_registry()
    definition = registry.get(prompt_id, "1.0.0")

    compat = definition.metadata.compatibility
    assert compat.dimensions == {
        "output_schema_version": "1.0.0",
        "customqa_profile_version": "1.0.0",
    }
    for layer1_dimension in (
        "normalization_version",
        "validation_version",
        "cp1_version",
        "golden_dataset_version",
    ):
        assert layer1_dimension not in compat.dimensions


def test_registry_instance_is_independent_of_layer_one_and_layer_two() -> None:
    """Layer 3's registry shares no state with Layer 1's or Layer 2's -- each
    `build_prompt_registry()` call returns its own sealed instance, and all
    three keep working simultaneously under the generalized
    `PromptCompatibility` model (the proof this test exists to make: the
    generalization did not break the other two consumers)."""
    from feature_engineering.prompts.composition import (
        build_prompt_registry as build_layer2_registry,
    )
    from requirement_intelligence.prompts.framework.composition import (
        build_prompt_registry as build_layer1_registry,
    )

    layer1 = build_layer1_registry()
    layer2 = build_layer2_registry()
    layer3 = build_prompt_registry()

    assert layer1 is not layer2 is not layer3
    assert set(layer1.list_prompt_ids()).isdisjoint(layer2.list_prompt_ids())
    assert set(layer1.list_prompt_ids()).isdisjoint(layer3.list_prompt_ids())
    assert set(layer2.list_prompt_ids()).isdisjoint(layer3.list_prompt_ids())

    # Each layer's own compatibility dimensions remain exactly its own.
    layer1_definition = layer1.get("requirement_analysis", "1.0.0")
    layer2_definition = layer2.get("generate_feature", "1.1.0")
    layer3_definition = layer3.get("generate_step_definitions", "1.0.0")

    assert "cp1_version" in layer1_definition.metadata.compatibility.dimensions
    assert layer2_definition.metadata.compatibility.dimensions == {
        "output_schema_version": "1.0.0"
    }
    assert "customqa_profile_version" in layer3_definition.metadata.compatibility.dimensions


# ===========================================================================
# generate_page_objects v1.1.0 -- multi-method extension (this build)
# ===========================================================================


class TestGeneratePageObjectsV110:
    """The multi-method-per-class prompt version -- additive alongside
    v1.0.0, never editing it (ADR-0014 invariant H.1: governed prompt
    wording is byte-for-byte frozen unless a governed version bump is
    performed). Retired (DEPRECATED, cosmetic-tidy follow-up session,
    2026-08-22) once superseded by v1.2.0's real-BasePage-inventory
    template -- LivePageObjectGenerator loads only v1.3.0."""

    def test_registered_alongside_v100_not_instead_of_it(self) -> None:
        registry = build_prompt_registry()

        assert registry.is_registered("generate_page_objects", "1.0.0")
        assert registry.is_registered("generate_page_objects", "1.1.0")

    def test_v100_content_is_byte_for_byte_unchanged(self) -> None:
        """The governed-frozen invariant, proven directly: v1.0.0's own
        file/sha256 are exactly what they were before this build."""
        registry = build_prompt_registry()
        v100 = registry.get("generate_page_objects", "1.0.0")

        assert v100.metadata.sha256 == (
            "7bf8cef207df8e0587239634753d55511a9e52192090b2992aa639895296a3ec"
        )
        assert "the single page action described below" in v100.content

    def test_lifecycle_is_deprecated(self) -> None:
        d = build_prompt_registry().get("generate_page_objects", "1.1.0")
        assert d.metadata.lifecycle == PromptLifecycle.DEPRECATED

    def test_release_introduced(self) -> None:
        d = build_prompt_registry().get("generate_page_objects", "1.1.0")
        assert d.metadata.release_introduced == "1.1.0"

    def test_sha256_matches_file_and_manifest(self) -> None:
        versions_dir = Path("automation_engineering/prompts/versions")
        d = build_prompt_registry().get("generate_page_objects", "1.1.0")
        file_bytes = (versions_dir / "generate_page_objects_v1.1.0.txt").read_bytes()

        assert d.metadata.sha256 == PromptLoader.compute_sha256(file_bytes)
        assert d.content == file_bytes.decode("utf-8")

    def test_conforms_to_the_governed_system_user_contract(self) -> None:
        d = build_prompt_registry().get("generate_page_objects", "1.1.0")

        template = parse_governed_template(d.content)

        assert template.system_prompt.strip()
        assert "{artifact_context}" not in template.system_prompt
        assert template.user_template.count("{artifact_context}") == 1

    def test_input_contract_describes_a_methods_list_not_a_single_action(self) -> None:
        d = build_prompt_registry().get("generate_page_objects", "1.1.0")

        assert "methods" in d.content
        assert "method_name" in d.content
        assert "action_text" in d.content

    def test_output_contract_requires_one_method_per_entry_verbatim_named(self) -> None:
        d = build_prompt_registry().get("generate_page_objects", "1.1.0")

        assert "VERBATIM" in d.content
        assert "no entry skipped" in d.content.lower()

    def test_still_embeds_both_customqa_rules(self) -> None:
        d = build_prompt_registry().get("generate_page_objects", "1.1.0")

        assert "customqa:direct-webdriver-action" in d.content
        assert "customqa:long-method" in d.content

    def test_compatibility_customqa_profile_preserved_output_schema_bumped(self) -> None:
        """`customqa_profile_version` is unchanged (the same rules); the
        MINOR bump's own real, additive difference (a `methods` list
        replacing a single `action_text`/`captures` pair) is reflected in
        `output_schema_version` instead -- compatibility is declared
        per-dimension, not all-or-nothing."""
        registry = build_prompt_registry()
        v100 = registry.get("generate_page_objects", "1.0.0")
        v110 = registry.get("generate_page_objects", "1.1.0")

        assert v110.metadata.compatibility.dimensions["customqa_profile_version"] == (
            v100.metadata.compatibility.dimensions["customqa_profile_version"]
        )
        assert v110.metadata.compatibility.dimensions["output_schema_version"] == "1.1.0"
        assert v100.metadata.compatibility.dimensions["output_schema_version"] == "1.0.0"


# ===========================================================================
# generate_page_objects v1.2.0 -- real BasePage inventory (defect-3 fix)
# ===========================================================================


class TestGeneratePageObjectsV120:
    """Fixes a live-measured defect: v1.1.0's own CONSTRAINTS section told
    the model to route WebDriver interactions "through the inherited
    BasePage helpers" without ever listing what they are, so the model fell
    back on Selenium-POM training conventions (`isElementDisplayed`,
    `sendKeys`, `click`, `findElement`, `getText`, ...) that this platform's
    real BasePage (`test-suite-baseline/src/test/java/com/automation/base/
    BasePage.java`) does not have -- 31 of 32 generated classes in a live
    regeneration run called at least one such fictional helper and failed to
    compile. v1.2.0 is additive alongside v1.0.0 and v1.1.0, never editing
    either (ADR-0014 invariant H.1: governed prompt wording is byte-for-byte
    frozen unless a governed version bump is performed). Retired
    (DEPRECATED, cosmetic-tidy follow-up session, 2026-08-22) once
    superseded by v1.3.0's return-type contract -- LivePageObjectGenerator
    loads only v1.3.0."""

    #: The real BasePage's complete inherited surface, read directly from
    #: the tracked baseline -- the source of truth this prompt version's own
    #: BASEPAGE'S REAL INHERITED API section must match exactly.
    _REAL_BASEPAGE_METHODS = ("open(String url)", "currentTitle()")
    _FICTIONAL_HELPERS_THE_LIVE_RUN_MEASURED = (
        "isElementDisplayed",
        "sendKeys",
        "click",
        "findElement",
        "getText",
    )

    def test_registered_alongside_v100_and_v110_not_instead_of_them(self) -> None:
        registry = build_prompt_registry()

        assert registry.is_registered("generate_page_objects", "1.0.0")
        assert registry.is_registered("generate_page_objects", "1.1.0")
        assert registry.is_registered("generate_page_objects", "1.2.0")

    def test_v110_content_is_byte_for_byte_unchanged(self) -> None:
        """The governed-frozen invariant, proven directly: v1.1.0's own
        file/sha256 are exactly what they were before this build."""
        registry = build_prompt_registry()
        v110 = registry.get("generate_page_objects", "1.1.0")

        assert v110.metadata.sha256 == (
            "c41ffbcf143c37e52d91dc870b9cb1ffa1570b645841a7cbf4f40aa64c6e79d9"
        )

    def test_lifecycle_is_deprecated(self) -> None:
        d = build_prompt_registry().get("generate_page_objects", "1.2.0")
        assert d.metadata.lifecycle == PromptLifecycle.DEPRECATED

    def test_release_introduced(self) -> None:
        d = build_prompt_registry().get("generate_page_objects", "1.2.0")
        assert d.metadata.release_introduced == "1.2.0"

    def test_sha256_matches_file_and_manifest(self) -> None:
        versions_dir = Path("automation_engineering/prompts/versions")
        d = build_prompt_registry().get("generate_page_objects", "1.2.0")
        file_bytes = (versions_dir / "generate_page_objects_v1.2.0.txt").read_bytes()

        assert d.metadata.sha256 == PromptLoader.compute_sha256(file_bytes)
        assert d.content == file_bytes.decode("utf-8")

    def test_conforms_to_the_governed_system_user_contract(self) -> None:
        d = build_prompt_registry().get("generate_page_objects", "1.2.0")

        template = parse_governed_template(d.content)

        assert template.system_prompt.strip()
        assert "{artifact_context}" not in template.system_prompt
        assert template.user_template.count("{artifact_context}") == 1

    def test_still_a_methods_list_input_contract_not_a_regression_to_v100(self) -> None:
        d = build_prompt_registry().get("generate_page_objects", "1.2.0")

        assert "methods" in d.content
        assert "method_name" in d.content
        assert "action_text" in d.content

    def test_still_embeds_both_customqa_rules(self) -> None:
        d = build_prompt_registry().get("generate_page_objects", "1.2.0")

        assert "customqa:direct-webdriver-action" in d.content
        assert "customqa:long-method" in d.content

    def test_supplies_the_real_basepage_method_inventory(self) -> None:
        """The core proof: the built prompt CONTAINS BasePage's real,
        complete method inventory -- read directly from the tracked
        baseline's own BasePage.java, not assumed."""
        d = build_prompt_registry().get("generate_page_objects", "1.2.0")

        for real_method in self._REAL_BASEPAGE_METHODS:
            assert real_method in d.content

    def test_names_the_specific_fictional_helpers_the_live_run_measured(self) -> None:
        """Names the exact fictional helpers as things NOT to call -- proven
        present (as a prohibition), not merely absent by omission."""
        d = build_prompt_registry().get("generate_page_objects", "1.2.0")
        content_lower = d.content.lower()

        for fictional_helper in self._FICTIONAL_HELPERS_THE_LIVE_RUN_MEASURED:
            assert fictional_helper.lower() in content_lower

    def test_constrains_to_the_real_api_not_merely_lists_it(self) -> None:
        """The prompt doesn't just list the real inventory -- it instructs
        the model to use ONLY it, never an invented helper."""
        d = build_prompt_registry().get("generate_page_objects", "1.2.0")
        content_lower = d.content.lower()

        assert "do not call a basepage method that is not in this list" in content_lower
        assert "never assume basepage exposes" in content_lower

    def test_real_inventory_matches_basepage_java_exactly(self) -> None:
        """Proves the prompt's own inventory is the REAL one -- reads the
        tracked baseline's BasePage.java directly and cross-checks every
        real public/protected member the prompt claims is present, with no
        additional invented BasePage method asserted as real."""
        basepage_source = Path(
            "test-suite-baseline/src/test/java/com/automation/base/BasePage.java"
        ).read_text()
        d = build_prompt_registry().get("generate_page_objects", "1.2.0")

        # Every real method signature the prompt claims is genuinely
        # declared in the real class.
        assert "public void open(String url)" in basepage_source
        assert "public String currentTitle()" in basepage_source
        assert "protected final WebDriver driver" in basepage_source
        assert "protected final WebDriverWait wait" in basepage_source
        for real_method in self._REAL_BASEPAGE_METHODS:
            assert real_method in d.content

        # BasePage has exactly two real methods -- confirm no third method
        # the prompt would need to (but doesn't) also list.
        import re

        method_declarations = re.findall(
            r"\bpublic\s+\S+\s+(\w+)\(", basepage_source
        )
        assert set(method_declarations) == {"open", "currentTitle"}

    def test_compatibility_identical_to_v110_purely_additive_content(self) -> None:
        """Both dimensions match v1.1.0's exactly -- this version adds
        prompt CONTENT (the real-inventory section), not a new request or
        response shape."""
        registry = build_prompt_registry()
        v110 = registry.get("generate_page_objects", "1.1.0")
        v120 = registry.get("generate_page_objects", "1.2.0")

        assert v120.metadata.compatibility.dimensions == v110.metadata.compatibility.dimensions


# ===========================================================================
# generate_page_objects v1.3.0 -- derived verification return type (defect-4 fix)
# ===========================================================================


class TestGeneratePageObjectsV130:
    """Fixes a live-measured defect found on the re-run after the
    defect-2/defect-3 fixes: the step-definition generator's own
    verification calls assume a boolean return
    (`Assertions.assertTrue(page.isDisplayed())`), while this prompt never
    told the model what the calling step definition expects back -- so the
    model was free to declare that same method void, which does not
    compile against the caller's own `assertTrue` usage. Measured on 5 of
    30 (17%) `is.../verify...` methods. No ADR and no working reference
    example specifies the contract, but it is cleanly DERIVABLE from the
    step-definition's own call-site usage
    (`automation_engineering.generation.page_object_reference_derivation`'s
    own "RETURN-TYPE DERIVATION" section, the same mechanism `method_name`
    derivation already uses). v1.3.0 is additive alongside v1.0.0/v1.1.0/
    v1.2.0, never editing any of them (ADR-0014 invariant H.1). Registered
    DRAFT, mirroring every other Layer 3 prompt's own current lifecycle."""

    def test_registered_alongside_v100_v110_and_v120_not_instead_of_them(self) -> None:
        registry = build_prompt_registry()

        assert registry.is_registered("generate_page_objects", "1.0.0")
        assert registry.is_registered("generate_page_objects", "1.1.0")
        assert registry.is_registered("generate_page_objects", "1.2.0")
        assert registry.is_registered("generate_page_objects", "1.3.0")

    def test_v120_content_is_byte_for_byte_unchanged(self) -> None:
        """The governed-frozen invariant, proven directly: v1.2.0's own
        file/sha256 are exactly what they were before this build."""
        registry = build_prompt_registry()
        v120 = registry.get("generate_page_objects", "1.2.0")

        assert v120.metadata.sha256 == (
            "101c6b4b131d4246aaa6da0d6fe730015962487f0879d8734f1b9924b21d4ab3"
        )

    def test_lifecycle_is_draft(self) -> None:
        d = build_prompt_registry().get("generate_page_objects", "1.3.0")
        assert d.metadata.lifecycle == PromptLifecycle.DRAFT

    def test_release_introduced(self) -> None:
        d = build_prompt_registry().get("generate_page_objects", "1.3.0")
        assert d.metadata.release_introduced == "1.3.0"

    def test_sha256_matches_file_and_manifest(self) -> None:
        versions_dir = Path("automation_engineering/prompts/versions")
        d = build_prompt_registry().get("generate_page_objects", "1.3.0")
        file_bytes = (versions_dir / "generate_page_objects_v1.3.0.txt").read_bytes()

        assert d.metadata.sha256 == PromptLoader.compute_sha256(file_bytes)
        assert d.content == file_bytes.decode("utf-8")

    def test_conforms_to_the_governed_system_user_contract(self) -> None:
        d = build_prompt_registry().get("generate_page_objects", "1.3.0")

        template = parse_governed_template(d.content)

        assert template.system_prompt.strip()
        assert "{artifact_context}" not in template.system_prompt
        assert template.user_template.count("{artifact_context}") == 1

    def test_still_a_methods_list_input_contract_not_a_regression(self) -> None:
        d = build_prompt_registry().get("generate_page_objects", "1.3.0")

        assert "methods" in d.content
        assert "method_name" in d.content
        assert "action_text" in d.content

    def test_still_embeds_both_customqa_rules_and_the_basepage_inventory(self) -> None:
        d = build_prompt_registry().get("generate_page_objects", "1.3.0")

        assert "customqa:direct-webdriver-action" in d.content
        assert "customqa:long-method" in d.content
        assert "open(String url)" in d.content
        assert "currentTitle()" in d.content

    def test_adds_an_optional_return_type_field_to_each_methods_entry(self) -> None:
        d = build_prompt_registry().get("generate_page_objects", "1.3.0")

        assert "return_type" in d.content

    def test_conveys_the_three_derivable_shapes_and_the_null_fallback(self) -> None:
        d = build_prompt_registry().get("generate_page_objects", "1.3.0")
        content_lower = d.content.lower()

        assert "boolean" in content_lower
        assert "void" in content_lower
        assert "null" in content_lower

    def test_instructs_against_substituting_an_assertion_for_returning_a_value(self) -> None:
        """The exact defect-4 failure mode -- a boolean-declared method that
        throws/self-asserts instead of returning -- named as prohibited."""
        d = build_prompt_registry().get("generate_page_objects", "1.3.0")
        content_lower = d.content.lower()

        assert "must not throw" in content_lower or "never throw" in content_lower

    def test_compatibility_identical_to_v120_purely_additive_content(self) -> None:
        """Both dimensions match v1.2.0's exactly -- this version adds
        prompt CONTENT (the optional return_type field and its own
        RETURN-TYPE CONTRACT section), not a new request or response
        shape."""
        registry = build_prompt_registry()
        v120 = registry.get("generate_page_objects", "1.2.0")
        v130 = registry.get("generate_page_objects", "1.3.0")

        assert v130.metadata.compatibility.dimensions == v120.metadata.compatibility.dimensions


# ===========================================================================
# generate_step_definitions v1.1.0 -- real WebDriver lifecycle (defect-2 fix)
# ===========================================================================


class TestGenerateStepDefinitionsV110:
    """Fixes a live-measured defect: v1.0.0's own prompt never conveyed HOW
    a step definition obtains a `WebDriver` to hand to a page object's
    constructor-injected constructor (ADR-0041 D5) -- so the platform's
    pre-existing step-defs construct page objects with `new XPage()`
    (no-arg), which does not compile against a page object whose only real
    constructor takes a `WebDriver`. ADR-0041 D5 already specifies the
    mechanism (a `ThreadLocal`-owning factory in the tracked baseline
    module), and the tracked baseline already implements + proves it
    (`DriverFactory`, `Hooks`, `SmokeSteps.java`/`SmokePage.java`). v1.1.0 is
    additive alongside v1.0.0, never editing it (ADR-0014 invariant H.1).
    Registered DRAFT, mirroring every other Layer 3 prompt's own current
    lifecycle."""

    def test_registered_alongside_v100_not_instead_of_it(self) -> None:
        registry = build_prompt_registry()

        assert registry.is_registered("generate_step_definitions", "1.0.0")
        assert registry.is_registered("generate_step_definitions", "1.1.0")

    def test_v100_content_is_byte_for_byte_unchanged(self) -> None:
        """The governed-frozen invariant, proven directly: v1.0.0's own
        file/sha256 are exactly what they were before this build."""
        registry = build_prompt_registry()
        v100 = registry.get("generate_step_definitions", "1.0.0")

        assert v100.metadata.sha256 == (
            "06c6207b7f9e87850e92a8708e277be9c26f8f111244fd2e251c70f4bb148d35"
        )

    def test_lifecycle_is_draft(self) -> None:
        d = build_prompt_registry().get("generate_step_definitions", "1.1.0")
        assert d.metadata.lifecycle == PromptLifecycle.DRAFT

    def test_release_introduced(self) -> None:
        d = build_prompt_registry().get("generate_step_definitions", "1.1.0")
        assert d.metadata.release_introduced == "1.1.0"

    def test_sha256_matches_file_and_manifest(self) -> None:
        versions_dir = Path("automation_engineering/prompts/versions")
        d = build_prompt_registry().get("generate_step_definitions", "1.1.0")
        file_bytes = (versions_dir / "generate_step_definitions_v1.1.0.txt").read_bytes()

        assert d.metadata.sha256 == PromptLoader.compute_sha256(file_bytes)
        assert d.content == file_bytes.decode("utf-8")

    def test_conforms_to_the_governed_system_user_contract(self) -> None:
        d = build_prompt_registry().get("generate_step_definitions", "1.1.0")

        template = parse_governed_template(d.content)

        assert template.system_prompt.strip()
        assert "{artifact_context}" not in template.system_prompt
        assert template.user_template.count("{artifact_context}") == 1

    def test_still_embeds_both_customqa_rules_referenced_by_v100(self) -> None:
        d = build_prompt_registry().get("generate_step_definitions", "1.1.0")

        assert "customqa:direct-webdriver-action" in d.content
        assert "customqa:long-method" in d.content

    def test_conveys_the_real_driverfactory_and_hooks_mechanism(self) -> None:
        """The core proof: the built prompt cites the REAL, already-
        implemented classes -- not an invented mechanism."""
        d = build_prompt_registry().get("generate_step_definitions", "1.1.0")

        assert "com.automation.base.DriverFactory" in d.content
        assert "com.automation.base.Hooks" in d.content
        assert "DriverFactory.get()" in d.content

    def test_cites_the_real_smokesteps_precedent(self) -> None:
        d = build_prompt_registry().get("generate_step_definitions", "1.1.0")

        assert "SmokeSteps" in d.content
        assert "SmokePage" in d.content

    def test_instructs_lazy_construction_not_a_no_arg_constructor(self) -> None:
        """The prompt doesn't just cite the mechanism -- it instructs AWAY
        from the exact defect measured (`new XPage()`, an inline field
        initializer) and TOWARD the lazy, null-guarded construction the
        real WebDriver lifecycle requires."""
        d = build_prompt_registry().get("generate_step_definitions", "1.1.0")

        assert "new XPage()" in d.content  # named as the thing that never compiles
        assert "without an inline initializer" in d.content
        assert "null check" in d.content.lower()

    def test_prevents_calling_driverfactory_create_directly(self) -> None:
        """Only `Hooks` may call `DriverFactory.create()` -- a generated
        step-def must only ever call `DriverFactory.get()`."""
        d = build_prompt_registry().get("generate_step_definitions", "1.1.0")

        assert "never `DriverFactory.create()`" in d.content or (
            "never" in d.content.lower() and "DriverFactory.create()" in d.content
        )

    def test_real_mechanism_matches_the_tracked_baselines_own_classes(self) -> None:
        """Proves the prompt's own citation is the REAL mechanism -- reads
        DriverFactory.java, Hooks.java, and SmokeSteps.java directly and
        cross-checks the exact call shape the prompt instructs against what
        the tracked baseline actually implements."""
        base_dir = Path("test-suite-baseline/src/test/java/com/automation/base")
        driver_factory_source = (base_dir / "DriverFactory.java").read_text()
        hooks_source = (base_dir / "Hooks.java").read_text()
        smoke_steps_source = Path(
            "test-suite-baseline/src/test/java/com/automation/steps/SmokeSteps.java"
        ).read_text()

        assert "public static WebDriver get()" in driver_factory_source
        assert "public static WebDriver create()" in driver_factory_source
        assert "DriverFactory.create()" in hooks_source
        assert "DriverFactory.quit()" in hooks_source
        assert "new SmokePage(DriverFactory.get())" in smoke_steps_source

    def test_compatibility_identical_to_v100_purely_additive_content(self) -> None:
        """Both dimensions match v1.0.0's exactly -- this version adds
        prompt CONTENT (the PAGE-OBJECT CONSTRUCTION section), not a new
        request or response shape."""
        registry = build_prompt_registry()
        v100 = registry.get("generate_step_definitions", "1.0.0")
        v110 = registry.get("generate_step_definitions", "1.1.0")

        assert v110.metadata.compatibility.dimensions == v100.metadata.compatibility.dimensions
