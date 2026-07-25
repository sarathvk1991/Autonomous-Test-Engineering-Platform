"""Deterministic, platform-owned id generation for the TestableRequirement contract.

ADR-0034 property 1 and ADR-0042 Decision 2: every ``REQ-*``, ``AC-*``, and ``RSK-*``
id is minted by the platform from already-computed inputs — never by the LLM, never
by a per-run counter. One shared normalization function (casefold, collapse
whitespace, strip punctuation) underlies every id type, so identical logical content
always yields an identical id across processes and runs, with no coordination.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable

_PUNCTUATION_RE = re.compile(r"[^\w\s]", re.UNICODE)
_WHITESPACE_RE = re.compile(r"\s+")

#: Length, in hex characters, of the short hash embedded in REQ-* and RSK-* ids.
SHORT_HASH_LENGTH = 8


def normalize(text: str) -> str:
    """Casefold, collapse whitespace, and strip punctuation.

    The single normalization function every id type (``REQ-*``, ``AC-*``,
    ``RSK-*``) is built from, per ADR-0042 Decision 2 — identical logical content
    always produces an identical id regardless of incidental formatting
    differences (extra whitespace, punctuation, case).
    """
    stripped = _PUNCTUATION_RE.sub("", text)
    collapsed = _WHITESPACE_RE.sub(" ", stripped).strip()
    return collapsed.casefold()


def _sha256_hex(normalized_text: str, sorted_keys: Iterable[str]) -> str:
    payload = "\x00".join([normalized_text, *sorted_keys])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def generate_requirement_id(title: str, source_external_ids: Iterable[str]) -> str:
    """``REQ-<first 8 hex of sha256(normalized title + sorted source external ids)>``."""
    digest = _sha256_hex(normalize(title), sorted(source_external_ids))
    return f"REQ-{digest[:SHORT_HASH_LENGTH]}"


def generate_risk_id(statement: str, source_external_ids: Iterable[str]) -> str:
    """``RSK-<first 8 hex of sha256(normalized statement + sorted source external ids)>``."""
    digest = _sha256_hex(normalize(statement), sorted(source_external_ids))
    return f"RSK-{digest[:SHORT_HASH_LENGTH]}"


def generate_acceptance_criterion_id(requirement_id: str, ordinal: int) -> str:
    """``AC-<REQ short>-<2-digit ordinal, stable within the requirement>``.

    ``requirement_id`` is expected in its full ``REQ-<8 hex>`` form; only the
    short hash suffix is embedded, per ADR-0042 Decision 2's ``AC-<REQ short>-NN``
    shape. ``ordinal`` is 1-based and must be stable within the requirement (the
    caller assigns it by the acceptance criterion's fixed position).
    """
    short = requirement_id.removeprefix("REQ-")
    return f"AC-{short}-{ordinal:02d}"


def compute_content_hash(canonical_json: str) -> str:
    """Full sha256 hex digest over a requirement's canonical JSON.

    Per ADR-0042 Decision 3: the caller is responsible for producing
    ``canonical_json`` from a JSON representation that already excludes
    ``requirement_id``, ``content_hash``, and ``supersedes`` — this function only
    hashes what it is given.
    """
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
