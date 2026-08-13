"""Unit tests for the pinning foundation (`GenerationIdentity`) --
the re-run/delta-scoped-regeneration cluster's own cache-key raw material
(`docs/architecture/mentor-feedback-scoping.md` item #1's re-run item).

Deterministic and provider-free throughout: every identity value is
constructed directly, per the module's own "purely additive persistence,
no cache built here" scope -- capture from a real generator is exercised by
each generator's own dedicated test module (e.g.
`tests/unit/test_automation_engineering_generation_step_definition_generator.py
::TestGenerationIdentityCapture`), not here.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from requirement_intelligence.llm.generation_identity import GenerationIdentity


def _identity(**overrides: str) -> GenerationIdentity:
    defaults: dict[str, str] = {
        "prompt_id": "generate_step_definitions",
        "prompt_version": "1.1.0",
        "prompt_sha256": "0" * 64,
        "provider": "gemini",
        "model": "gemini-2.5-flash",
    }
    defaults.update(overrides)
    return GenerationIdentity(**defaults)


class TestGenerationIdentity:
    def test_round_trips_through_json_by_alias(self) -> None:
        """The exact shape a `dataclass.to_json()`/`from_json()` caller
        (`AssetRecord`, `FeatureRecord`) round-trips through."""
        identity = _identity()
        dumped = identity.model_dump(mode="json", by_alias=True)
        assert dumped == {
            "promptId": "generate_step_definitions",
            "promptVersion": "1.1.0",
            "promptSha256": "0" * 64,
            "provider": "gemini",
            "model": "gemini-2.5-flash",
        }
        restored = GenerationIdentity.model_validate(dumped)
        assert restored == identity

    def test_equal_field_values_are_equal_regardless_of_construction_site(self) -> None:
        """Two independently constructed identities with the same field
        values compare equal -- needed so a cache key built from this shape
        is stable across independent constructions of the same real
        identity, not merely within one object's own lifetime."""
        assert _identity() == _identity()

    def test_different_prompt_version_is_a_different_identity(self) -> None:
        assert _identity(prompt_version="1.1.0") != _identity(prompt_version="1.2.0")

    def test_different_model_is_a_different_identity(self) -> None:
        assert _identity(model="gemini-2.5-flash") != _identity(model="gemini-3.5-flash")

    @pytest.mark.parametrize(
        "field", ["prompt_id", "prompt_version", "prompt_sha256", "provider", "model"]
    )
    def test_every_field_is_required_and_non_empty(self, field: str) -> None:
        with pytest.raises(ValidationError):
            _identity(**{field: ""})

    def test_carries_exactly_the_fields_a_future_cache_key_needs(self) -> None:
        """Nitin's own key: spec-slice + prompt-version + model-version +
        source-snapshot (`docs/architecture/mentor-feedback-scoping.md`
        item #1). This object supplies the prompt-version and model-version
        components (`prompt_id`/`prompt_version`/`prompt_sha256`, `model`) --
        spec-slice and source-snapshot are, deliberately, not this object's
        concern (they come from the requirement/artifact this identity is
        attached to, not from the identity itself)."""
        assert {"prompt_id", "prompt_version", "prompt_sha256", "provider", "model"} == set(
            GenerationIdentity.model_fields.keys()
        )
