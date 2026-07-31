"""Registration + SHA-256 verification proof for Layer 3's first governed
prompt, `generate_step_definitions` v1.0.0 (ADR-0044 D8).

Mirrors `tests/unit/test_feature_engineering_prompts_composition.py`'s shape
for Layer 2's registry, and `requirement_intelligence/tests/unit/
test_prompt_composition.py`'s shape for Layer 1's -- same shared mechanism,
same discipline, independent registry instance and independent content
(ADR-0044 D8).

This module also proves the `PromptCompatibility` generalization
(`shared/prompts/models/prompt_compatibility.py`) this registration
triggered: Layer 3 declares its OWN dimensions here, and Layer 1's/Layer 2's
own registrations still work unmodified under the generalized model
(cross-checked directly, not merely asserted independently in their own
test modules).
"""

from __future__ import annotations

from pathlib import Path

from automation_engineering.prompts.composition import build_prompt_registry
from shared.prompts.framework.prompt_loader import PromptLoader
from shared.prompts.framework.prompt_registry import PromptRegistryState
from shared.prompts.framework.prompt_template_contract import parse_governed_template
from shared.prompts.models.prompt_version import PromptLifecycle

_EXPECTED_PROMPT_IDS = {"generate_step_definitions"}


def test_registry_seals_with_exactly_the_one_registered_prompt() -> None:
    registry = build_prompt_registry()

    assert registry.state is PromptRegistryState.SEALED
    assert registry.count() == 1
    assert set(registry.list_prompt_ids()) == _EXPECTED_PROMPT_IDS
    assert registry.is_registered("generate_step_definitions", "1.0.0")


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
    CLI, no CP3) -- Draft is the honest lifecycle."""
    registry = build_prompt_registry()

    for definition in registry.get_all():
        assert definition.metadata.lifecycle == PromptLifecycle.DRAFT


def test_template_conforms_to_the_governed_system_user_contract() -> None:
    """Unlike Layer 2's `generate_feature` (which does not carry an
    `{artifact_context}` placeholder at all), `generate_step_definitions`
    v1.0.0 DOES conform to the full governed template contract -- proven
    directly by parsing it, not merely by construction."""
    registry = build_prompt_registry()
    definition = registry.get("generate_step_definitions", "1.0.0")

    template = parse_governed_template(definition.content)

    assert template.system_prompt.strip()
    assert "{artifact_context}" not in template.system_prompt
    assert template.user_template.count("{artifact_context}") == 1


def test_template_embeds_the_evidenced_customqa_constraints() -> None:
    """Born-compliant generation (ADR-0044 D5): the customqa:* rules this
    task evidenced against this repo's own real SonarQube fixture data
    (`requirement_intelligence/input/sonar/sonar-issues.json`) are baked
    into the static, versioned CONSTRAINTS section -- unconditionally
    present in every render, never optional at runtime."""
    registry = build_prompt_registry()
    definition = registry.get("generate_step_definitions", "1.0.0")

    assert "customqa:direct-webdriver-action" in definition.content
    assert "customqa:long-method" in definition.content


def test_compatibility_declares_layer3s_own_dimensions_not_layer1s() -> None:
    """Layer 3 declares dimensions genuinely its own -- neither Layer 1's
    five subsystem-named fields nor a fabricated "n/a" for any of them
    (ADR-0044 D8's own generalization; see
    `shared/prompts/models/prompt_compatibility.py`)."""
    registry = build_prompt_registry()
    definition = registry.get("generate_step_definitions", "1.0.0")

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
