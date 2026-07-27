"""Registration + SHA-256 verification proof for Layer 2's converted prompts.

Mirrors `requirement_intelligence/tests/unit/test_prompt_composition.py`'s
shape for Layer 1's registry — same shared mechanism, same discipline,
independent registry instance and independent content (ADR-0043 D4).
"""

from __future__ import annotations

from pathlib import Path

from feature_engineering.prompts.composition import build_prompt_registry
from shared.prompts.framework.prompt_loader import PromptLoader
from shared.prompts.framework.prompt_registry import PromptRegistryState
from shared.prompts.models.prompt_version import PromptLifecycle

_EXPECTED_PROMPT_IDS = {"generate_feature", "fix_gherkin_lint", "validate_generated_feature"}


def test_registry_seals_with_exactly_the_three_converted_prompts() -> None:
    """4 registered *definitions* (generate_feature carries two versions: the
    superseded v1.0.0, kept as a historical record, and the current v1.1.0),
    but exactly the 3 converted prompt_ids."""
    registry = build_prompt_registry()

    assert registry.state is PromptRegistryState.SEALED
    assert registry.count() == 4
    assert set(registry.list_prompt_ids()) == _EXPECTED_PROMPT_IDS
    assert registry.is_registered("generate_feature", "1.0.0")
    assert registry.is_registered("generate_feature", "1.1.0")


def test_every_registered_prompt_sha256_matches_the_manifest() -> None:
    """The registry's own load path already verifies this; recompute
    independently here so a tampered manifest or template fails this test
    too, not only the loader's internal check."""
    versions_dir = Path("feature_engineering/prompts/versions")
    registry = build_prompt_registry()

    for definition in registry.get_all():
        file_name = f"{definition.metadata.prompt_id}_v{definition.metadata.version}.txt"
        raw_bytes = (versions_dir / file_name).read_bytes()
        assert PromptLoader.compute_sha256(raw_bytes) == definition.metadata.sha256
        assert definition.content == raw_bytes.decode("utf-8")


def test_all_three_are_registered_as_draft() -> None:
    """None has yet been exercised by any live pipeline (no generation logic,
    no CP2, no remediation loop exist yet) — Draft is the honest lifecycle."""
    registry = build_prompt_registry()

    for definition in registry.get_all():
        # Schema uses `use_enum_values=True`, so the stored value is the
        # plain string, not the enum member -- compare by value, not identity.
        assert definition.metadata.lifecycle == PromptLifecycle.DRAFT


def test_compatibility_declares_layer1_dimensions_as_not_applicable() -> None:
    """None of these prompts was ever validated against Layer 1's
    Normalization/Validation/CP1/golden-dataset contracts -- claiming a
    version there would be a fabricated signal, so each declares "n/a"."""
    registry = build_prompt_registry()

    for definition in registry.get_all():
        compat = definition.metadata.compatibility
        assert compat.normalization_version == "n/a"
        assert compat.validation_version == "n/a"
        assert compat.cp1_version == "n/a"
        assert compat.golden_dataset_version == "n/a"
        assert compat.output_schema_version == "1.0.0"


def test_registry_instance_is_independent_of_layer_ones() -> None:
    """Layer 2's registry and Layer 1's registry share no state -- each
    build_prompt_registry() call returns its own sealed instance."""
    from requirement_intelligence.prompts.framework.composition import (
        build_prompt_registry as build_layer1_registry,
    )

    layer1 = build_layer1_registry()
    layer2 = build_prompt_registry()

    assert set(layer1.list_prompt_ids()).isdisjoint(layer2.list_prompt_ids())
    assert layer1 is not layer2
