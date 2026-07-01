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
from typing import Any


class JsonCanonicalStructureRecoverer:
    """Recovers a format-neutral structure from a JSON response, or records its absence.

    Implements the
    :class:`~requirement_intelligence.normalization.response.assembly.canonical_structure_recoverer.CanonicalStructureRecoverer`
    Protocol structurally (the Protocol is ``runtime_checkable``; no inheritance is
    required).  A JSON **object** is the only value that expresses a canonical
    structural document; every other valid JSON value and all malformed input record
    an **absent** structure (``None``).
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
