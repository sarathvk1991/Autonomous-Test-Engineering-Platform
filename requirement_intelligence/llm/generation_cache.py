"""ADR-0050's artifact-level generation cache -- the key (D1) and the store
(D2), the first build increment (D5): store + key + one decorator, wrapping
:class:`~automation_engineering.generation.live_step_definition_generator.
LiveStepDefinitionGenerator` only (:mod:`automation_engineering.generation.
caching_step_definition_generator`, a sibling module, owns the decorator
itself -- this module owns only the key function and the store).

THE KEY (D1, the centerpiece decision): hashes the *exact* deterministic
payload a generator already serializes immediately before its LLM call,
combined with its :class:`~requirement_intelligence.llm.generation_identity.
GenerationIdentity` -- never a ``REQ-*`` or any other id-based proxy. The
payload is not an approximation of what determines a generator's output; it
*is* what determines it (ADR-0050 D1's own correctness argument, restated
here at the point it is implemented, not re-argued).

THE STORE (D2): on-disk, content-addressed, keyed by the hash above,
surviving across process invocations -- cross-run reuse is the entire point.
Reuses :mod:`~requirement_intelligence.run_state.atomic_write` verbatim (the
same durable-write primitive :class:`~requirement_intelligence.run_state.
run_state_manager.RunStateManager` already uses) rather than reimplementing
atomic writes a second time. Does **not** reuse ``RunStateManager`` itself --
confirmed, again, architecturally closed to the fixed 19-entry
``STAGE_DEFINITIONS`` catalogue (ADR-0050 D2).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.llm.generation_identity import GenerationIdentity
from requirement_intelligence.run_state.atomic_write import atomic_write_json, read_json_if_valid
from shared.contracts.base import Schema

#: The canonical, deterministic JSON serialization the key is hashed over --
#: sort_keys so key order never affects the hash, compact separators so the
#: hash is stable regardless of incidental whitespace choices elsewhere
#: (mirrors ``_hash_artifacts``'s own ``json.dumps(..., sort_keys=True,
#: separators=(",", ":"))`` convention, `run_state_manager.py`). This is the
#: ONLY place a payload is serialized for hashing -- a generator's own
#: prompt-rendering serialization (pretty-printed, ``indent=2``) is a
#: separate, presentation-only concern that must produce the identical
#: logical payload, never the identical byte string.
_JSON_SEPARATORS = (",", ":")


def compute_cache_key(identity: GenerationIdentity, payload: Mapping[str, Any]) -> str:
    """The artifact-generation cache key (ADR-0050 D1): ``sha256`` over
    ``identity``'s five fields plus ``payload``'s own canonical JSON
    serialization.

    ``payload`` must be the *exact* dict a generator's own prompt-building
    code serializes into its LLM call -- not a derived id, not a subset, not
    an approximation. Passing anything else silently reopens the exact
    correctness gap ADR-0050 D1 found in the naive ``REQ-*``-keyed design.
    """
    payload_json = json.dumps(payload, sort_keys=True, separators=_JSON_SEPARATORS)
    parts = "\x00".join(
        [
            identity.prompt_id,
            identity.prompt_version,
            identity.prompt_sha256,
            identity.provider,
            identity.model,
            payload_json,
        ]
    )
    return hashlib.sha256(parts.encode("utf-8")).hexdigest()


class GenerationCacheEntry(Schema):
    """One stored cache entry: the generated artifact text, the
    :class:`GenerationIdentity` that produced it (replayed verbatim on a hit
    -- ADR-0050 D3's hit-consumption contract), and an optional
    human-readable label (e.g. the step text) for diagnosis only, never
    part of the key (ADR-0050 D1: id-based fields are decided *out* of the
    correctness-bearing hash)."""

    model_config = ConfigDict(alias_generator=to_camel)

    generated_text: str = Field(..., min_length=1)
    identity: GenerationIdentity
    label: dict[str, str] = Field(default_factory=dict)


class GenerationCacheStore:
    """On-disk, content-addressed store for :class:`GenerationCacheEntry`,
    keyed by :func:`compute_cache_key`'s own hash.

    One file per entry, under ``<cache_dir>/<hash[:2]>/<hash>.json`` (avoids
    one flat directory of unbounded size, ADR-0050 D2's own entry-shape
    decision). A present-but-corrupt or present-but-truncated entry is
    treated exactly like a missing one -- :meth:`get` returns ``None``,
    never raises -- mirroring ``RunStateManager.should_skip``'s own
    invariant (b) discipline: a cache must never crash a caller merely
    because a previously-written entry was damaged; it degrades to a MISS.
    """

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = cache_dir

    def _path_for(self, key: str) -> Path:
        return self._cache_dir / key[:2] / f"{key}.json"

    def get(self, key: str) -> GenerationCacheEntry | None:
        raw = read_json_if_valid(self._path_for(key))
        if raw is None:
            return None
        return GenerationCacheEntry.model_validate(raw)

    def put(self, key: str, entry: GenerationCacheEntry) -> None:
        atomic_write_json(self._path_for(key), entry.model_dump(mode="json", by_alias=True))


__all__ = ["GenerationCacheEntry", "GenerationCacheStore", "compute_cache_key"]
