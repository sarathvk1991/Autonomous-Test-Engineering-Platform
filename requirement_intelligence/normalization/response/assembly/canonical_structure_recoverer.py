"""The canonical-structure recovery seam — how NORMALIZATION-0001 stays format-neutral.

``CanonicalStructureRecoverer`` is the **injected collaborator** through which
:class:`~requirement_intelligence.normalization.response.assembly.recover_canonical_structure.RecoverCanonicalStructure`
(NORMALIZATION-0001) turns the response's primary text into a **format-neutral**
structural representation — *without the stage ever knowing a serialization
format*.

Why this seam exists
--------------------
The Normalization Responsibility Catalog (§2.2, §3.4) places **parsers and
serialization formats** outside the architecture: a stage recovers *normalized*
structure, "not the structure of format X".  The stage's single concern is
therefore *orchestrating* recovery and recording the result — never parsing.  This
protocol is the minimal seam that keeps the stage:

* **provider-independent** — it operates on already-provider-independent text;
* **format-independent** — JSON, Markdown, XML, or any future representation is
  handled by a *recoverer*, never by the stage;
* **extensible** — new formats are new recoverer implementations (or a composite
  recoverer), added **without changing the stage** — exactly the additive-growth
  discipline every future ``NORMALIZATION-000N`` stage will follow.

Facts, not exceptions
---------------------
A recoverer returns the recovered **format-neutral structure**, or ``None`` when
the text expresses **no** recoverable well-formed structure.  ``None`` is a
**fact** (it becomes an absent normalized structure, which NORMALIZATION-0002
later reads to determine a ``MALFORMED`` outcome).  A recoverer raises **only** for
an infrastructure failure — never to signal "no structure".
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CanonicalStructureRecoverer(Protocol):
    """Recovers a format-neutral structural representation from response text.

    An implementation encapsulates one recovery *mechanism* (e.g. a specific
    serialization format, or a composite that tries several).  The mechanism is an
    **implementation detail** the stage never depends on; the stage depends only on
    this protocol.

    Conformance requirements (structural, not runtime-enforced):

    * **Deterministic** — the same text always yields the same result.
    * **Non-mutating / pure** — it never mutates its input and holds no state
      between calls.
    * **Format-neutral output** — the returned mapping represents *structure*
      (objects, arrays, scalars, identifiers), never a serialization format.
    * **Never judges** — it recovers what is present; it never assigns an outcome,
      severity, or verdict (that is NORMALIZATION-0002 and validation, respectively).
    """

    def recover(self, text: str) -> dict[str, Any] | None:
        """Recover the format-neutral structure *text* expresses.

        Parameters
        ----------
        text:
            The response's provider-independent primary text (``generated_text``),
            treated as **read-only**.

        Returns
        -------
        dict[str, Any] | None
            The recovered format-neutral structure, or ``None`` when the text
            expresses no recoverable well-formed structure.  ``None`` is a **fact**
            (an absent structure), not an error.

        Raises
        ------
        Exception
            Only for an unexpected **infrastructure** failure of the recovery
            mechanism itself — never to signal the ordinary absence of structure.
            The calling stage translates such a failure into a
            :class:`~requirement_intelligence.normalization.response.assembly.stage_exceptions.StructureRecoveryError`.
        """
        ...
