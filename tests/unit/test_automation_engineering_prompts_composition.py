"""Registration + SHA-256 verification proof for Layer 3's governed prompts:
`generate_step_definitions` v1.0.0 (ADR-0044 D8), `generate_page_objects`
v1.0.0, and `generate_utilities` v1.0.0 (this build) -- the last of the
three Gherkin-derived generators.

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

_ALL_PROMPT_IDS = ["generate_step_definitions", "generate_page_objects", "generate_utilities"]
_EXPECTED_PROMPT_IDS = set(_ALL_PROMPT_IDS)


def test_registry_seals_with_exactly_the_three_registered_prompts() -> None:
    registry = build_prompt_registry()

    assert registry.state is PromptRegistryState.SEALED
    assert registry.count() == 3
    assert set(registry.list_prompt_ids()) == _EXPECTED_PROMPT_IDS
    for prompt_id in _ALL_PROMPT_IDS:
        assert registry.is_registered(prompt_id, "1.0.0")


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
    """Not yet exercised by any live pipeline (no orchestration wired into a
    CLI, no CP3/CP4) -- Draft is the honest lifecycle."""
    registry = build_prompt_registry()

    for definition in registry.get_all():
        assert definition.metadata.lifecycle == PromptLifecycle.DRAFT


@pytest.mark.parametrize("prompt_id", _ALL_PROMPT_IDS)
def test_template_conforms_to_the_governed_system_user_contract(prompt_id: str) -> None:
    """All three Layer 3 prompts conform to the full governed template
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
    cites) as applicable to all three generated-code shapes -- unconditionally
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
    prohibited, there), never fabricated for utilities."""
    registry = build_prompt_registry()
    definition = registry.get(prompt_id, "1.0.0")

    assert "customqa:direct-webdriver-action" in definition.content


def test_utility_template_does_not_fabricate_direct_webdriver_action() -> None:
    """The honest negative: `generate_utilities` never claims
    `customqa:direct-webdriver-action` applies -- there is no evidence tying
    that rule to a non-page-object class. It states the architectural
    boundary (no WebDriver at all) in plain English instead of dressing it
    up as a customqa:* rule this platform never evidenced against a
    utility file."""
    registry = build_prompt_registry()
    definition = registry.get("generate_utilities", "1.0.0")

    assert "customqa:direct-webdriver-action" not in definition.content
    assert "webdriver" in definition.content.lower()  # the plain-English prohibition


def test_page_object_template_frames_webdriver_calls_as_legitimate_here() -> None:
    """The one deliberate asymmetry between step defs and page objects:
    step definitions are told WebDriver calls never belong there; page
    objects are told the OPPOSITE -- this is exactly where those calls
    legitimately live."""
    registry = build_prompt_registry()
    definition = registry.get("generate_page_objects", "1.0.0")

    assert "legitimately" in definition.content.lower()
    assert "webdriver" in definition.content.lower()


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
