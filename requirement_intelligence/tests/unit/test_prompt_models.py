"""Unit tests for the Prompt Governance Canonical Models.

Covers:
- PromptVersion: parse, str, comparison, bumping, invalid format, compatibility
- PromptLifecycle: values, ordering
- PromptCompatibility: construction, immutability, fields
- PromptMetadata: construction, all fields, immutability, optional field
- PromptDefinition: construction, fields, immutability

No I/O.  No LLM calls.  No provider references.
"""

from __future__ import annotations

import dataclasses

import pytest
from pydantic import ValidationError

from requirement_intelligence.prompts.models.prompt_compatibility import PromptCompatibility
from requirement_intelligence.prompts.models.prompt_definition import (
    PROMPT_DEFINITION_VERSION,
    PromptDefinition,
)
from requirement_intelligence.prompts.models.prompt_metadata import (
    PROMPT_METADATA_VERSION,
    PromptMetadata,
)
from requirement_intelligence.prompts.models.prompt_version import PromptLifecycle, PromptVersion

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


def _metadata(
    version: str = "1.0.0",
    lifecycle: PromptLifecycle = PromptLifecycle.PRODUCTION,
    sha256: str = "a" * 64,
) -> PromptMetadata:
    return PromptMetadata(
        prompt_id="test_prompt",
        name="Test Prompt",
        version=version,
        owner="Test Owner",
        lifecycle=lifecycle,
        description="A test prompt.",
        sha256=sha256,
        compatibility=_compat(),
        release_introduced="1.0.0",
    )


def _definition(content: str = "Hello {artifact_context}") -> PromptDefinition:
    return PromptDefinition(metadata=_metadata(), content=content)


# ===========================================================================
# PromptVersion
# ===========================================================================


class TestPromptVersion:
    """Semantic version value object."""

    # --- Parse ---

    @pytest.mark.unit
    def test_parse_valid_version(self) -> None:
        v = PromptVersion.parse("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3

    @pytest.mark.unit
    def test_parse_zero_patch(self) -> None:
        v = PromptVersion.parse("2.0.0")
        assert v.major == 2
        assert v.minor == 0
        assert v.patch == 0

    @pytest.mark.unit
    def test_parse_strips_whitespace(self) -> None:
        v = PromptVersion.parse("  1.0.0  ")
        assert v.major == 1

    @pytest.mark.unit
    def test_parse_invalid_missing_patch(self) -> None:
        with pytest.raises(ValueError, match="Invalid prompt version"):
            PromptVersion.parse("1.0")

    @pytest.mark.unit
    def test_parse_invalid_alpha(self) -> None:
        with pytest.raises(ValueError, match="Invalid prompt version"):
            PromptVersion.parse("1.0.x")

    @pytest.mark.unit
    def test_parse_invalid_empty(self) -> None:
        with pytest.raises(ValueError, match="Invalid prompt version"):
            PromptVersion.parse("")

    @pytest.mark.unit
    def test_parse_invalid_four_components(self) -> None:
        with pytest.raises(ValueError, match="Invalid prompt version"):
            PromptVersion.parse("1.0.0.0")

    # --- str representation ---

    @pytest.mark.unit
    def test_str_round_trip(self) -> None:
        v = PromptVersion.parse("3.4.5")
        assert str(v) == "3.4.5"

    @pytest.mark.unit
    def test_str_zero_components(self) -> None:
        v = PromptVersion(0, 0, 0)
        assert str(v) == "0.0.0"

    # --- Comparison ---

    @pytest.mark.unit
    def test_equality(self) -> None:
        assert PromptVersion.parse("1.0.0") == PromptVersion.parse("1.0.0")

    @pytest.mark.unit
    def test_inequality_minor(self) -> None:
        assert PromptVersion.parse("1.1.0") != PromptVersion.parse("1.0.0")

    @pytest.mark.unit
    def test_ordering_major(self) -> None:
        assert PromptVersion.parse("2.0.0") > PromptVersion.parse("1.9.9")

    @pytest.mark.unit
    def test_ordering_minor(self) -> None:
        assert PromptVersion.parse("1.2.0") > PromptVersion.parse("1.1.9")

    @pytest.mark.unit
    def test_ordering_patch(self) -> None:
        assert PromptVersion.parse("1.0.1") > PromptVersion.parse("1.0.0")

    @pytest.mark.unit
    def test_sorting(self) -> None:
        versions = [
            PromptVersion.parse("2.0.0"),
            PromptVersion.parse("1.0.1"),
            PromptVersion.parse("1.1.0"),
        ]
        assert sorted(versions) == [
            PromptVersion.parse("1.0.1"),
            PromptVersion.parse("1.1.0"),
            PromptVersion.parse("2.0.0"),
        ]

    # --- Bumping ---

    @pytest.mark.unit
    def test_bump_patch(self) -> None:
        v = PromptVersion.parse("1.0.0")
        assert v.bump_patch() == PromptVersion.parse("1.0.1")

    @pytest.mark.unit
    def test_bump_patch_carries(self) -> None:
        v = PromptVersion.parse("1.0.9")
        assert v.bump_patch() == PromptVersion.parse("1.0.10")

    @pytest.mark.unit
    def test_bump_minor_resets_patch(self) -> None:
        v = PromptVersion.parse("1.0.5")
        bumped = v.bump_minor()
        assert bumped == PromptVersion.parse("1.1.0")

    @pytest.mark.unit
    def test_bump_major_resets_minor_and_patch(self) -> None:
        v = PromptVersion.parse("1.3.7")
        bumped = v.bump_major()
        assert bumped == PromptVersion.parse("2.0.0")

    @pytest.mark.unit
    def test_bumping_returns_new_instance(self) -> None:
        v = PromptVersion.parse("1.0.0")
        patched = v.bump_patch()
        assert patched is not v
        assert v == PromptVersion.parse("1.0.0")  # original unchanged

    # --- Compatibility ---

    @pytest.mark.unit
    def test_is_compatible_same_major(self) -> None:
        v1 = PromptVersion.parse("1.0.0")
        v2 = PromptVersion.parse("1.2.3")
        assert v1.is_compatible_with(v2)
        assert v2.is_compatible_with(v1)

    @pytest.mark.unit
    def test_is_not_compatible_different_major(self) -> None:
        v1 = PromptVersion.parse("2.0.0")
        v2 = PromptVersion.parse("1.9.9")
        assert not v1.is_compatible_with(v2)

    # --- Immutability ---

    @pytest.mark.unit
    def test_version_is_frozen(self) -> None:
        v = PromptVersion.parse("1.0.0")
        with pytest.raises(dataclasses.FrozenInstanceError):
            v.major = 2  # type: ignore[misc]


# ===========================================================================
# PromptLifecycle
# ===========================================================================


class TestPromptLifecycle:
    """Governed lifecycle enumeration."""

    @pytest.mark.unit
    def test_all_states_present(self) -> None:
        states = {lc.value for lc in PromptLifecycle}
        assert states == {
            "draft", "experimental", "approved", "production",
            "deprecated", "archived",
        }

    @pytest.mark.unit
    def test_string_comparison(self) -> None:
        assert PromptLifecycle.PRODUCTION == "production"

    @pytest.mark.unit
    def test_production_is_distinct_from_draft(self) -> None:
        assert PromptLifecycle.PRODUCTION != PromptLifecycle.DRAFT


# ===========================================================================
# PromptCompatibility
# ===========================================================================


class TestPromptCompatibility:
    """Compatibility declarations model."""

    @pytest.mark.unit
    def test_construction(self) -> None:
        c = _compat()
        assert c.normalization_version == "1.0"
        assert c.validation_version == "1.0"
        assert c.cp1_version == "1.0"
        assert c.golden_dataset_version == "1.0.0"
        assert c.output_schema_version == "1.0.0"

    @pytest.mark.unit
    def test_immutable(self) -> None:
        c = _compat()
        with pytest.raises(ValidationError):
            c.normalization_version = "2.0"  # type: ignore[misc]

    @pytest.mark.unit
    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PromptCompatibility(  # type: ignore[call-arg]
                normalization_version="1.0",
                validation_version="1.0",
                cp1_version="1.0",
                golden_dataset_version="1.0.0",
                output_schema_version="1.0.0",
                extra_field="oops",
            )


# ===========================================================================
# PromptMetadata
# ===========================================================================


class TestPromptMetadata:
    """Descriptive identity model."""

    @pytest.mark.unit
    def test_all_required_fields(self) -> None:
        m = _metadata()
        assert m.prompt_id == "test_prompt"
        assert m.name == "Test Prompt"
        assert m.version == "1.0.0"
        assert m.owner == "Test Owner"
        # Schema base uses use_enum_values=True; lifecycle stores as string value
        assert m.lifecycle == PromptLifecycle.PRODUCTION
        assert m.description == "A test prompt."
        assert m.sha256 == "a" * 64
        assert m.release_introduced == "1.0.0"
        assert m.release_deprecated is None

    @pytest.mark.unit
    def test_optional_release_deprecated(self) -> None:
        m = PromptMetadata(
            prompt_id="p",
            name="P",
            version="1.0.0",
            owner="O",
            lifecycle=PromptLifecycle.DEPRECATED,
            description="deprecated",
            sha256="b" * 64,
            compatibility=_compat(),
            release_introduced="1.0.0",
            release_deprecated="1.1.0",
        )
        assert m.release_deprecated == "1.1.0"

    @pytest.mark.unit
    def test_lifecycle_stored_as_value(self) -> None:
        m = _metadata(lifecycle=PromptLifecycle.APPROVED)
        assert m.lifecycle == "approved"

    @pytest.mark.unit
    def test_immutable(self) -> None:
        m = _metadata()
        with pytest.raises(ValidationError):
            m.version = "2.0.0"  # type: ignore[misc]

    @pytest.mark.unit
    def test_metadata_version_constant(self) -> None:
        assert PROMPT_METADATA_VERSION == "1.0"


# ===========================================================================
# PromptDefinition
# ===========================================================================


class TestPromptDefinition:
    """Aggregate root canonical model."""

    @pytest.mark.unit
    def test_construction(self) -> None:
        d = _definition("template content {artifact_context} end")
        assert d.metadata.prompt_id == "test_prompt"
        assert d.content == "template content {artifact_context} end"

    @pytest.mark.unit
    def test_immutable(self) -> None:
        d = _definition()
        with pytest.raises(ValidationError):
            d.content = "changed"  # type: ignore[misc]

    @pytest.mark.unit
    def test_definition_version_constant(self) -> None:
        assert PROMPT_DEFINITION_VERSION == "1.0"

    @pytest.mark.unit
    def test_metadata_nested(self) -> None:
        d = _definition()
        assert isinstance(d.metadata, PromptMetadata)
        assert isinstance(d.metadata.compatibility, PromptCompatibility)

    @pytest.mark.unit
    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PromptDefinition(  # type: ignore[call-arg]
                metadata=_metadata(),
                content="ok",
                extra="bad",
            )
