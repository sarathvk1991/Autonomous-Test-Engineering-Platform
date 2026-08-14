"""ADR-0050's artifact-generation cache key (D1) and store (D2).

Deterministic throughout -- no LLM call anywhere in this module. The
decorator that actually wraps a live generator with this store/key is
proven separately (`tests/unit/test_automation_engineering_generation_
caching_step_definition_generator.py`); this module proves the key and the
store on their own, independent of any generator.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from requirement_intelligence.llm.generation_cache import (
    GenerationCacheEntry,
    GenerationCacheStore,
    compute_cache_key,
)
from requirement_intelligence.llm.generation_identity import GenerationIdentity

pytestmark = pytest.mark.unit


def _identity(**overrides: str) -> GenerationIdentity:
    defaults: dict[str, str] = {
        "prompt_id": "generate_step_definitions",
        "prompt_version": "1.1.0",
        "prompt_sha256": "a" * 64,
        "provider": "gemini",
        "model": "gemini-3.5-flash",
    }
    defaults.update(overrides)
    return GenerationIdentity(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# compute_cache_key -- D1, the correctness centerpiece
# ---------------------------------------------------------------------------


class TestComputeCacheKey:
    def test_identical_identity_and_payload_yield_identical_key(self) -> None:
        identity = _identity()
        payload = {"step_text": "I log in", "target_package": "com.automation.steps"}

        first = compute_cache_key(identity, payload)
        second = compute_cache_key(_identity(), dict(payload))

        assert first == second

    def test_key_is_a_64_character_hex_sha256_digest(self) -> None:
        key = compute_cache_key(_identity(), {"a": 1})
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)

    def test_a_payload_field_the_naive_requirement_id_key_would_have_missed_changes_the_key(
        self,
    ) -> None:
        """The centerpiece correctness proof (ADR-0050 D1): a naive key built
        around only an id-like field (e.g. the step's own `need.text`, the
        L3 analogue of the L2 `REQ-*`-title-only defect the surfacing found)
        would be blind to a change in `page_object_interface` or
        `customqa_constraints` -- fields that genuinely change the rendered
        prompt (`build_step_definition_payload` includes them) but carry no
        id of their own. This test holds `step_text` FIXED (what a naive key
        would have hashed) and changes only `page_object_interface` -- the
        corrected, full-payload key must still produce a different key,
        proving it does not share the naive key's blind spot.
        """
        identity = _identity()
        base_payload = {
            "step_text": "I log in as {string}",
            "step_type": "When",
            "captures": [],
            "target_package": "com.automation.steps",
            "page_object_interface": None,
            "customqa_constraints": ["c1"],
        }
        changed_payload = dict(base_payload, page_object_interface="com.automation.pages.LoginPage")

        key_before = compute_cache_key(identity, base_payload)
        key_after = compute_cache_key(identity, changed_payload)

        assert key_before != key_after

    def test_a_customqa_constraints_change_with_step_text_fixed_changes_the_key(self) -> None:
        identity = _identity()
        base_payload = {"step_text": "I log in", "customqa_constraints": ["c1"]}
        changed_payload = {"step_text": "I log in", "customqa_constraints": ["c1", "c2"]}

        assert compute_cache_key(identity, base_payload) != compute_cache_key(
            identity, changed_payload
        )

    def test_key_order_in_the_payload_dict_does_not_affect_the_key(self) -> None:
        identity = _identity()
        payload_a = {"step_text": "x", "target_package": "y"}
        payload_b = {"target_package": "y", "step_text": "x"}

        assert compute_cache_key(identity, payload_a) == compute_cache_key(identity, payload_b)

    @pytest.mark.parametrize(
        "field", ["prompt_id", "prompt_version", "prompt_sha256", "provider", "model"]
    )
    def test_every_identity_field_change_changes_the_key(self, field: str) -> None:
        payload = {"step_text": "I log in"}
        base_key = compute_cache_key(_identity(), payload)
        changed_key = compute_cache_key(_identity(**{field: "different-value"}), payload)

        assert base_key != changed_key


# ---------------------------------------------------------------------------
# GenerationCacheStore -- D2, on-disk content-addressed
# ---------------------------------------------------------------------------


class TestGenerationCacheStore:
    def test_get_on_empty_store_is_none(self, tmp_path: Path) -> None:
        store = GenerationCacheStore(tmp_path)
        assert store.get("a" * 64) is None

    def test_put_then_get_round_trips_the_entry(self, tmp_path: Path) -> None:
        store = GenerationCacheStore(tmp_path)
        key = "b" * 64
        entry = GenerationCacheEntry(
            generated_text="package com.automation.steps;\n",
            identity=_identity(),
            label={"step_text": "I log in"},
        )

        store.put(key, entry)
        result = store.get(key)

        assert result is not None
        assert result.generated_text == entry.generated_text
        assert result.identity == entry.identity
        assert result.label == entry.label

    def test_entries_persist_across_independent_store_instances(self, tmp_path: Path) -> None:
        """Proves genuine on-disk persistence, not an in-memory dict
        masquerading as a store -- the cross-run reuse D2 exists for."""
        key = "c" * 64
        entry = GenerationCacheEntry(generated_text="text", identity=_identity())

        GenerationCacheStore(tmp_path).put(key, entry)
        reloaded = GenerationCacheStore(tmp_path).get(key)

        assert reloaded is not None
        assert reloaded.generated_text == "text"

    def test_entry_is_stored_under_a_content_addressed_path(self, tmp_path: Path) -> None:
        store = GenerationCacheStore(tmp_path)
        key = "d" * 64
        store.put(key, GenerationCacheEntry(generated_text="text", identity=_identity()))

        expected_path = tmp_path / key[:2] / f"{key}.json"
        assert expected_path.exists()

    def test_a_corrupt_entry_file_is_treated_as_a_miss_not_a_crash(self, tmp_path: Path) -> None:
        store = GenerationCacheStore(tmp_path)
        key = "e" * 64
        path = tmp_path / key[:2] / f"{key}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not valid json {{{", encoding="utf-8")

        assert store.get(key) is None

    def test_different_keys_do_not_collide(self, tmp_path: Path) -> None:
        store = GenerationCacheStore(tmp_path)
        store.put("f" * 64, GenerationCacheEntry(generated_text="one", identity=_identity()))
        store.put("1" * 64, GenerationCacheEntry(generated_text="two", identity=_identity()))

        assert store.get("f" * 64).generated_text == "one"  # type: ignore[union-attr]
        assert store.get("1" * 64).generated_text == "two"  # type: ignore[union-attr]
