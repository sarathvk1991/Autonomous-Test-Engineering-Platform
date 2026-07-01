"""Abstract base class for all normalization responsibilities.

This module defines :class:`NormalizationResponsibility` — the stable contract
that the
:class:`~requirement_intelligence.normalization.framework.normalization_registry.NormalizationRegistry`
and
:class:`~requirement_intelligence.normalization.framework.normalization_pipeline.NormalizationPipeline`
depend on.  Concrete responsibilities are registered, never imported directly.

It is the normalization sibling of the validation framework's ``ValidationRule``
and is held to the same maturity bar — but it is **not a validation rule** and
carries no validation semantics.

What a responsibility is
------------------------
A NormalizationResponsibility is a **generic** framework execution unit that owns
exactly one observation-producing concern.  It reads the normalization *source* and
records **facts** (Normalization Observations); it never judges them.  Per
**ADR-0002** it is **not** one of the ``NORMALIZATION-0001…0005`` catalog stages —
those are internal stages of the ``ResponseNormalizer`` component, not framework
responsibilities (see "Scope (ADR-0002)" below).

No layers
---------
Unlike a validation rule, a responsibility has **no layer**.  Normalization is a
single-stage subsystem; responsibilities execute in registration order.  Identity
is the ``NORMALIZATION-NNNN`` id alone.

Responsibility Independence
---------------------------
Mirroring Rule Independence, every NormalizationResponsibility must be:

1. **Deterministic** — given the same source it always records the same
   observations.  It depends only on the source, never on the outcome of any
   other responsibility.
2. **Stateless / non-mutating** — it never mutates the source, accumulates state
   between invocations, or writes to shared mutable structure (Observe, Never
   Repair — contract §3.2).
3. **Idempotent / order-independent** — because responsibilities share no state
   and never observe each other, any permutation yields the same observations.
4. **Pure / side-effect free** — it performs no I/O, no provider interaction, and
   no parsing of provider-specific or format-specific payloads here.

These are structural requirements of the contract, not runtime-enforced.

Facts, not judgments
--------------------
``normalize`` returns
:class:`~requirement_intelligence.normalization.models.normalization_observation.NormalizationObservation`
objects — **un-judged facts**.  A responsibility never assigns severity, never
assigns a verdict, and never produces a ``ValidationIssue`` (Response
Normalization Contract §10).

Scope (ADR-0002)
----------------
This base class is **generic** framework infrastructure — the reusable contract a
framework ``NormalizationResponsibility`` implements.  It performs no parsing, no
structure recovery, and no ``ParsedResponse`` creation.  Per **ADR-0002**, the
platform's five normalization stages (``NORMALIZATION-0001…0005``) are **internal
stages of the ``ResponseNormalizer`` component**, coordinated through its Assembly
State — they are **not** framework ``NormalizationResponsibility`` instances and are
not registered here.  The platform therefore registers no framework responsibilities
of its own today; this remains the generic execution seat any observation-producing
responsibility (e.g. a generic ``EXAMPLE-0001``) can build on.

Responsibility Documentation Contract
-------------------------------------
Every concrete :class:`NormalizationResponsibility` implementation must document
the following in its class docstring (a documentation standard, not enforced):

1. **Purpose** — the single responsibility it owns.
2. **Catalog ID** — its ``NORMALIZATION-NNNN`` id (contract §13).
3. **Inputs** — what part of the source it reads.
4. **Outputs** — what observations it can record (never judgments).
5. **Worked Example** — a concrete illustration.
6. **Architecture Reference** — the governing section of
   ``docs/architecture/response-normalization-contract.md``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from requirement_intelligence.normalization.framework.normalization_metadata import (
    NormalizationResponsibilityMetadata,
)
from requirement_intelligence.normalization.models.normalization_observation import (
    NormalizationObservation,
)

__all__ = [
    "NormalizationResponsibility",
    "NormalizationResponsibilityMetadata",
]


class NormalizationResponsibility(ABC):
    """Abstract contract every normalization responsibility must satisfy.

    A NormalizationResponsibility encapsulates **exactly one** normalization
    responsibility and records facts about a single normalization source.  It is
    the fundamental building block of the Response Normalization Layer.

    Design philosophy
    -----------------
    Like the platform's other extensible framework contracts (``SourceConnector``,
    ``LLMProvider``, ``BaseMapper``, ``ValidationRule``), this is the stable
    abstraction that the registry and pipeline depend on.  New responsibilities
    are added by implementing this class and registering the instance; no
    framework code changes.

    Identity comes from metadata
    ----------------------------
    A responsibility's descriptive identity lives in a single immutable
    :class:`~requirement_intelligence.normalization.framework.normalization_metadata.NormalizationResponsibilityMetadata`
    value, exposed through :attr:`metadata`.  Convenience wrappers
    (:attr:`responsibility_id`, :attr:`responsibility_name`,
    :attr:`responsibility_version`, :attr:`order`, :attr:`enabled`) read from it.
    This is **runtime identity**; the Normalization Responsibility Catalog remains
    the governing architecture (see the metadata module docstring).

    Adding a new responsibility
    ---------------------------
    1. Subclass :class:`NormalizationResponsibility`.
    2. Implement :attr:`metadata` (returning an immutable
       :class:`NormalizationResponsibilityMetadata`) and :meth:`normalize`.
    3. Document the Responsibility Documentation Contract sections (see module
       docstring).
    4. Register the instance with the
       :class:`~requirement_intelligence.normalization.framework.normalization_registry.NormalizationRegistry`.

    No other change is required anywhere in the framework.
    """

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def metadata(self) -> NormalizationResponsibilityMetadata:
        """Immutable descriptive identity of this responsibility.

        The single source of truth for ``responsibility_id``,
        ``responsibility_name``, ``responsibility_version``, ``order``,
        ``enabled``, and the reserved extension points.  Must be an immutable
        :class:`NormalizationResponsibilityMetadata`.

        Returns
        -------
        NormalizationResponsibilityMetadata
            The frozen metadata value describing this responsibility.
        """

    # ------------------------------------------------------------------
    # Identity — convenience wrappers
    # ------------------------------------------------------------------

    @property
    def responsibility_id(self) -> str:
        """Stable, unique identifier (reads :attr:`metadata`).

        Convention: ``<NAME>-NNNN`` (e.g. a generic ``EXAMPLE-0001``).  Must
        not change once published, because it appears in result records.  It is
        **not** a validation rule id, and it is **not** one of the
        ``NORMALIZATION-0001…0005`` internal ``ResponseNormalizer`` stages (ADR-0002).
        """
        return self.metadata.responsibility_id

    @property
    def responsibility_name(self) -> str:
        """Human-readable name (reads :attr:`metadata`)."""
        return self.metadata.responsibility_name

    @property
    def responsibility_version(self) -> str:
        """The version of this responsibility's logic (reads :attr:`metadata`)."""
        return self.metadata.responsibility_version

    @property
    def order(self) -> int:
        """The responsibility's declared catalog position (reads :attr:`metadata`).

        **Descriptive identity only.**  The registry and pipeline never read this
        to sequence execution — registration order is the sole execution order
        (Normalization Responsibility Catalog §8: there is no separate ordering
        dimension).  It mirrors the frozen ``0001 → … → 0005`` catalog chain
        (Catalog §4) as runtime provenance.
        """
        return self.metadata.order

    @property
    def enabled(self) -> bool:
        """Whether this responsibility participates in execution (reads :attr:`metadata`).

        Disabled responsibilities are registered but skipped by the pipeline.
        """
        return self.metadata.enabled

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------

    @abstractmethod
    def normalize(self, source: Any) -> list[NormalizationObservation]:
        """Read *source* and return the facts this responsibility recorded.

        This method is the sole place where normalization behaviour lives.  It
        must satisfy all four Responsibility Independence constraints (see module
        docstring): deterministic, non-mutating, idempotent/order-independent, and
        pure.

        Parameters
        ----------
        source:
            The normalization input, treated as **read-only**.  In production this
            is the provider-independent ``LLMResponse`` the Response Normalization
            Layer receives (Response Normalization Contract §4.1).  It is typed
            ``Any`` here so the framework contract does not couple to any concrete
            input shape, provider, or serialization format — the typed entry point
            will be the future ``ResponseNormalizer``.

        Returns
        -------
        list[NormalizationObservation]
            An ordered list of recorded
            :class:`~requirement_intelligence.normalization.models.normalization_observation.NormalizationObservation`
            facts.  An empty list means this responsibility recorded no fact worth
            keeping.

        Notes
        -----
        * **Never mutate** *source* — normalization observes, it does not repair
          (Observe, Never Repair, contract §3.2).
        * **Never judge** — return facts, never severities, verdicts, or
          ``ValidationIssue`` objects (contract §10).
        * **Raise**
          :class:`~requirement_intelligence.normalization.framework.normalization_exceptions.NormalizationResponsibilityError`
          only for unexpected internal failures; do not raise for normal recorded
          facts (those are returned, not raised).
        """
