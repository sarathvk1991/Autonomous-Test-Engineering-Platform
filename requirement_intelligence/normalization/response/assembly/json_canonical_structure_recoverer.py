"""JsonCanonicalStructureRecoverer — the JSON recovery mechanism for NORMALIZATION-0001.

This is a concrete
:class:`~requirement_intelligence.normalization.response.assembly.canonical_structure_recoverer.CanonicalStructureRecoverer`
— the injected collaborator through which
:class:`~requirement_intelligence.normalization.response.assembly.recover_canonical_structure.RecoverCanonicalStructure`
(NORMALIZATION-0001) turns a response's ``generated_text`` into a **format-neutral**
structural representation.  The platform's AI responses express structured
documents as JSON, so this recoverer reads that format; a future format would be a
*different* recoverer, added without changing the stage or the Protocol.

Why it lives here, not in the orchestrator
------------------------------------------
The recoverer is an **implementation detail of NORMALIZATION-0001**, not of the
``ResponseNormalizer``.  It is the one place the *serialization format* is known
(Normalization Responsibility Catalog §2.2, §3.4); keeping it beside the stage — and
out of the orchestrator — is what keeps the orchestrator format-independent.

Observe, never repair (Response Normalization Contract §3.2)
------------------------------------------------------------
Recovery is **strict**.  The recoverer performs a single strict ``json.loads`` and
**never** repairs, strips fences, retries, or coerces:

* a JSON **object** (the only shape that expresses a structural document) → the
  recovered format-neutral mapping;
* any **other** valid JSON value (array, string, number, boolean, ``null``) → the
  recorded **absence** of structure (``None``);
* **malformed** input (invalid JSON) → the recorded **absence** of structure
  (``None``).

``None`` is a **fact** (an absent structure), which NORMALIZATION-0002 later reads
to determine a ``MALFORMED`` outcome — it is **never** an exception (Assembly
Contract §8).

Determinism & purity (Stage Implementation Contract §4; Protocol contract)
--------------------------------------------------------------------------
The recoverer is deterministic, pure, and non-mutating: the same text always
yields the same result, it holds no state between calls, and it never mutates its
input.  It references no provider, model, or endpoint.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

#: The Unicode replacement character.  Its presence in already-decoded text is the
#: standard signal of a lossy or corrupt decode (an encoding-integrity problem).
_REPLACEMENT_CHARACTER = "�"


def _detect_encoding_issues(text: str) -> tuple[str, ...]:
    """Report character-encoding integrity facts in *text* (format-independent, pure).

    ``text`` is already a decoded ``str`` (decoding happens at the provider adapter);
    the standard, deterministic signal of a lossy/corrupt decode is the Unicode
    replacement character (U+FFFD).  Returns a single descriptive fact when one or
    more are present, or an empty tuple when the encoding is intact.  This is a pure
    function of the text — no serialization format is involved, so it is reused
    unchanged by any future format recoverer.
    """
    replacement_count = text.count(_REPLACEMENT_CHARACTER)
    if replacement_count == 0:
        return ()
    return (
        f"{replacement_count} Unicode replacement character(s) (U+FFFD) indicate a "
        f"lossy or corrupt character decode.",
    )


class JsonCanonicalStructureRecoverer:
    """Recovers a format-neutral structure from a JSON response, or records its absence.

    Implements the
    :class:`~requirement_intelligence.normalization.response.assembly.canonical_structure_recoverer.CanonicalStructureRecoverer`
    Protocol structurally (the Protocol is ``runtime_checkable``; no inheritance is
    required).  A JSON **object** is the only value that expresses a canonical
    structural document; every other valid JSON value and all malformed input record
    an **absent** structure (``None``).

    Duplicate-key detection (optional capability)
    ---------------------------------------------
    It **additionally** implements
    :class:`~requirement_intelligence.normalization.response.assembly.canonical_structure_recoverer.DuplicateIdentifierReporter`:
    :meth:`duplicate_identifiers` reports the field identifiers duplicated within a
    JSON object (at any nesting depth) — a **format-level fact** the recoverer, as
    the one place JSON is understood, is uniquely able to observe.  Detection is a
    pure implementation detail: it creates **no** observation, performs **no**
    validation, and never repairs or mutates anything.  ``recover`` is unchanged and
    still yields the last-value-wins structure standard JSON parsing produces.

    Encoding-integrity detection (optional capability)
    --------------------------------------------------
    It **also** implements
    :class:`~requirement_intelligence.normalization.response.assembly.canonical_structure_recoverer.EncodingIntegrityReporter`:
    :meth:`encoding_observations` reports character-encoding integrity facts (Unicode
    replacement characters, U+FFFD) found in the decoded text.  Unlike structure
    recovery and duplicate detection, this is **format-independent** — it inspects the
    text alone — so the logic lives in a pure module-level helper the recoverer merely
    exposes as a capability.  Like the others it creates **no** observation, performs
    **no** validation, and never repairs or mutates anything.
    """

    def recover(self, text: str) -> dict[str, Any] | None:
        """Recover the format-neutral structure *text* expresses, or ``None``.

        Parameters
        ----------
        text:
            The response's provider-independent primary text (``generated_text``),
            treated as **read-only**.

        Returns
        -------
        dict[str, Any] | None
            The recovered mapping when *text* is a JSON **object**; ``None`` for any
            other valid JSON value or for malformed input.  ``None`` is a **fact**
            (an absent structure), not an error.
        """
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            # Malformed JSON is a recorded absence of structure — a fact, never an
            # exception (Response Normalization Contract §3.2; Assembly Contract §8).
            return None

        # Only a JSON object expresses a canonical structural document.  An array,
        # scalar, or null is valid JSON but not a structure → recorded absence.
        if isinstance(value, dict):
            return value
        return None

    def duplicate_identifiers(self, text: str) -> tuple[str, ...]:
        """Report field identifiers duplicated within a JSON object in *text*.

        Detection is performed in a **single, standards-compliant parse** using
        ``json``'s ``object_pairs_hook``, which receives every object's raw
        ``(key, value)`` pairs *before* de-duplication.  For each object (at any
        nesting depth) each identifier that appears more than once contributes one
        entry; the returned order is deterministic.  The recovered structure is
        **unaffected** — the hook returns ``dict(pairs)``, the identical
        last-value-wins mapping standard parsing produces.

        Malformed input yields an **empty** tuple: an absent structure is a fact
        reported by :meth:`recover`, and a document that cannot be parsed has no
        object in which an identifier could be duplicated.  This never raises for
        ordinary absence.

        Parameters
        ----------
        text:
            The response's provider-independent primary text, treated as read-only.

        Returns
        -------
        tuple[str, ...]
            One entry per (object, duplicated-identifier) occurrence; empty when no
            identifier is duplicated or the text is malformed.
        """
        duplicates: list[str] = []

        def _record_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            # Counter preserves first-seen order (Python 3.7+), so the reported
            # duplicates are deterministic for a given text.
            counts = Counter(key for key, _ in pairs)
            duplicates.extend(key for key, count in counts.items() if count > 1)
            # Return the identical last-value-wins mapping standard parsing yields.
            return dict(pairs)

        try:
            json.loads(text, object_pairs_hook=_record_duplicates)
        except json.JSONDecodeError:
            # Malformed input has no recoverable object; duplicates are moot here.
            return ()

        return tuple(duplicates)

    def encoding_observations(self, text: str) -> tuple[str, ...]:
        """Report character-encoding integrity facts found in *text*.

        Format-independent: it inspects the decoded text for the Unicode replacement
        character (U+FFFD), the standard signal of a lossy/corrupt decode, and
        reports a fact when any are present.  Independent of JSON well-formedness — a
        malformed response can still carry encoding corruption — so it never parses
        and never depends on structure recovery.  Pure and deterministic.

        Parameters
        ----------
        text:
            The response's provider-independent primary text, treated as read-only.

        Returns
        -------
        tuple[str, ...]
            One entry describing the encoding-integrity problem when present; empty
            when the encoding is intact.
        """
        return _detect_encoding_issues(text)
