"""Unit tests for the PromptRegistry.

Covers:
- Initial state (OPEN)
- Explicit registration
- Duplicate registration detection (same prompt_id + version)
- Sealing (OPEN → SEALED, idempotent)
- Registration after sealing raises error
- Retrieval by prompt_id
- Retrieval by prompt_id + version
- Ambiguous lookup (multiple versions, no version specified)
- Not-found lookup
- Deterministic ordering (registration order preserved)
- list_prompt_ids / count / is_registered introspection

No I/O.  No LLM calls.  No filesystem access.
"""

from __future__ import annotations

import pytest

from requirement_intelligence.prompts.framework.prompt_exceptions import (
    PromptNotFoundError,
    PromptRegistryError,
)
from requirement_intelligence.prompts.framework.prompt_registry import (
    PromptRegistry,
    PromptRegistryState,
)
from requirement_intelligence.prompts.models.prompt_compatibility import PromptCompatibility
from requirement_intelligence.prompts.models.prompt_definition import PromptDefinition
from requirement_intelligence.prompts.models.prompt_metadata import PromptMetadata
from requirement_intelligence.prompts.models.prompt_version import PromptLifecycle

# ===========================================================================
# Helpers
# ===========================================================================


def _compat() -> PromptCompatibility:
    return PromptCompatibility(
        normalization_version="1.0",
        validation_version="1.0",
        cp1_version="1.0",
        golden_dataset_version="1.0.0",
        output_schema_version="1.0.0",
    )


def _make_definition(
    prompt_id: str = "test_prompt",
    version: str = "1.0.0",
    content: str = "template {artifact_context}",
) -> PromptDefinition:
    metadata = PromptMetadata(
        prompt_id=prompt_id,
        name=f"Prompt {prompt_id}",
        version=version,
        owner="Test",
        lifecycle=PromptLifecycle.PRODUCTION,
        description="Test prompt.",
        sha256="a" * 64,
        compatibility=_compat(),
        release_introduced="1.0.0",
    )
    return PromptDefinition(metadata=metadata, content=content)


# ===========================================================================
# Initial state
# ===========================================================================


class TestPromptRegistryInitialState:
    @pytest.mark.unit
    def test_starts_open(self) -> None:
        r = PromptRegistry()
        assert r.state is PromptRegistryState.OPEN

    @pytest.mark.unit
    def test_not_sealed_initially(self) -> None:
        r = PromptRegistry()
        assert not r.is_sealed

    @pytest.mark.unit
    def test_empty_initially(self) -> None:
        r = PromptRegistry()
        assert r.count() == 0
        assert r.get_all() == []
        assert r.list_prompt_ids() == []


# ===========================================================================
# Registration
# ===========================================================================


class TestPromptRegistryRegistration:
    @pytest.mark.unit
    def test_register_single(self) -> None:
        r = PromptRegistry()
        r.register(_make_definition())
        assert r.count() == 1

    @pytest.mark.unit
    def test_register_multiple_different_ids(self) -> None:
        r = PromptRegistry()
        r.register(_make_definition(prompt_id="a"))
        r.register(_make_definition(prompt_id="b"))
        assert r.count() == 2

    @pytest.mark.unit
    def test_register_multiple_versions_same_id(self) -> None:
        r = PromptRegistry()
        r.register(_make_definition(prompt_id="p", version="1.0.0"))
        r.register(_make_definition(prompt_id="p", version="2.0.0"))
        assert r.count() == 2

    @pytest.mark.unit
    def test_duplicate_same_id_version_raises(self) -> None:
        r = PromptRegistry()
        r.register(_make_definition(prompt_id="p", version="1.0.0"))
        with pytest.raises(PromptRegistryError, match="already registered"):
            r.register(_make_definition(prompt_id="p", version="1.0.0"))

    @pytest.mark.unit
    def test_register_after_seal_raises(self) -> None:
        r = PromptRegistry()
        r.seal()
        with pytest.raises(PromptRegistryError, match="sealed"):
            r.register(_make_definition())

    @pytest.mark.unit
    def test_register_after_seal_error_message_includes_id(self) -> None:
        r = PromptRegistry()
        r.seal()
        with pytest.raises(PromptRegistryError, match="my_prompt"):
            r.register(_make_definition(prompt_id="my_prompt"))


# ===========================================================================
# Sealing
# ===========================================================================


class TestPromptRegistrySealing:
    @pytest.mark.unit
    def test_seal_transitions_to_sealed(self) -> None:
        r = PromptRegistry()
        r.seal()
        assert r.is_sealed
        assert r.state is PromptRegistryState.SEALED

    @pytest.mark.unit
    def test_seal_is_idempotent(self) -> None:
        r = PromptRegistry()
        r.seal()
        r.seal()  # Should not raise
        assert r.is_sealed

    @pytest.mark.unit
    def test_retrieval_works_after_sealing(self) -> None:
        r = PromptRegistry()
        r.register(_make_definition(prompt_id="p"))
        r.seal()
        d = r.get("p")
        assert d.metadata.prompt_id == "p"

    @pytest.mark.unit
    def test_get_all_works_after_sealing(self) -> None:
        r = PromptRegistry()
        r.register(_make_definition())
        r.seal()
        assert len(r.get_all()) == 1


# ===========================================================================
# Retrieval
# ===========================================================================


class TestPromptRegistryRetrieval:
    @pytest.mark.unit
    def test_get_by_id_single_version(self) -> None:
        r = PromptRegistry()
        r.register(_make_definition(prompt_id="req", version="1.0.0"))
        d = r.get("req")
        assert d.metadata.version == "1.0.0"

    @pytest.mark.unit
    def test_get_by_id_and_version(self) -> None:
        r = PromptRegistry()
        r.register(_make_definition(prompt_id="req", version="1.0.0"))
        r.register(_make_definition(prompt_id="req", version="2.0.0"))
        d = r.get("req", "2.0.0")
        assert d.metadata.version == "2.0.0"

    @pytest.mark.unit
    def test_get_ambiguous_raises_when_no_version(self) -> None:
        r = PromptRegistry()
        r.register(_make_definition(prompt_id="p", version="1.0.0"))
        r.register(_make_definition(prompt_id="p", version="2.0.0"))
        with pytest.raises(PromptRegistryError, match="Ambiguous"):
            r.get("p")

    @pytest.mark.unit
    def test_get_not_found_raises(self) -> None:
        r = PromptRegistry()
        with pytest.raises(PromptNotFoundError):
            r.get("unknown")

    @pytest.mark.unit
    def test_get_not_found_with_version_raises(self) -> None:
        r = PromptRegistry()
        r.register(_make_definition(prompt_id="p", version="1.0.0"))
        with pytest.raises(PromptNotFoundError):
            r.get("p", "9.9.9")

    @pytest.mark.unit
    def test_get_all_empty(self) -> None:
        r = PromptRegistry()
        assert r.get_all() == []

    @pytest.mark.unit
    def test_get_all_returns_copy(self) -> None:
        r = PromptRegistry()
        r.register(_make_definition())
        result = r.get_all()
        result.clear()
        # Original should be unaffected
        assert r.count() == 1


# ===========================================================================
# Deterministic ordering
# ===========================================================================


class TestPromptRegistryOrdering:
    @pytest.mark.unit
    def test_registration_order_preserved_get_all(self) -> None:
        r = PromptRegistry()
        r.register(_make_definition(prompt_id="c"))
        r.register(_make_definition(prompt_id="a"))
        r.register(_make_definition(prompt_id="b"))
        ids = [d.metadata.prompt_id for d in r.get_all()]
        assert ids == ["c", "a", "b"]

    @pytest.mark.unit
    def test_list_prompt_ids_order(self) -> None:
        r = PromptRegistry()
        r.register(_make_definition(prompt_id="z"))
        r.register(_make_definition(prompt_id="y"))
        assert r.list_prompt_ids() == ["z", "y"]

    @pytest.mark.unit
    def test_list_prompt_ids_deduplicates(self) -> None:
        r = PromptRegistry()
        r.register(_make_definition(prompt_id="p", version="1.0.0"))
        r.register(_make_definition(prompt_id="p", version="2.0.0"))
        assert r.list_prompt_ids() == ["p"]


# ===========================================================================
# Introspection
# ===========================================================================


class TestPromptRegistryIntrospection:
    @pytest.mark.unit
    def test_count_empty(self) -> None:
        r = PromptRegistry()
        assert r.count() == 0

    @pytest.mark.unit
    def test_count_after_registration(self) -> None:
        r = PromptRegistry()
        r.register(_make_definition(prompt_id="a"))
        r.register(_make_definition(prompt_id="b"))
        assert r.count() == 2

    @pytest.mark.unit
    def test_is_registered_by_id_true(self) -> None:
        r = PromptRegistry()
        r.register(_make_definition(prompt_id="p"))
        assert r.is_registered("p")

    @pytest.mark.unit
    def test_is_registered_by_id_false(self) -> None:
        r = PromptRegistry()
        assert not r.is_registered("missing")

    @pytest.mark.unit
    def test_is_registered_by_id_and_version_true(self) -> None:
        r = PromptRegistry()
        r.register(_make_definition(prompt_id="p", version="1.0.0"))
        assert r.is_registered("p", "1.0.0")

    @pytest.mark.unit
    def test_is_registered_by_id_and_version_false(self) -> None:
        r = PromptRegistry()
        r.register(_make_definition(prompt_id="p", version="1.0.0"))
        assert not r.is_registered("p", "2.0.0")

    @pytest.mark.unit
    def test_each_registry_instance_independent(self) -> None:
        r1 = PromptRegistry()
        r2 = PromptRegistry()
        r1.register(_make_definition(prompt_id="shared"))
        assert r2.count() == 0
