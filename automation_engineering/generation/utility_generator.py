"""The utility generation seam: one NO_MATCH utility need plus its
generation context in, generated Java utility source out -- everything else
(the reuse-first decision that routes here, the customqa:* constraint list
that context carries, the precise method-fit discharge on a TRUSTED reuse)
is orchestration-owned (:mod:`.utility_orchestrator`), never this module's
concern. Mirrors :mod:`.page_object_generator` exactly -- same seam shape,
same "stub now, live peer alongside it" split, same reasoning.

:class:`UtilityGenerator` is the one interface the orchestration
(:mod:`.utility_orchestrator`) depends on. Two implementations exist:

* :class:`StubUtilityGenerator` -- this task's deterministic, fixture-driven
  stand-in. Test/dev scaffolding only -- the same pattern as
  :class:`~automation_engineering.generation.page_object_generator.StubPageObjectGenerator`.
* ``LiveUtilityGenerator`` -- the live, ``llm_factory``-backed implementation
  (a peer behind this same seam, built in :mod:`.live_utility_generator`, not
  this module).

The orchestrator (:mod:`.utility_orchestrator`) never imports an LLM
provider or ``llm_factory`` -- it depends only on this Protocol, so the
reuse-first decision of whether to generate at all stays provably
deterministic regardless of which implementation is wired in.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from automation_engineering.reuse.models import GherkinStepNeed


@dataclass(frozen=True, slots=True)
class UtilityGenerationContext:
    """Everything a :class:`UtilityGenerator` needs to generate one utility
    class -- the seam's own input contract.

    ``need`` describes the utility action driving this generation (a
    :class:`~automation_engineering.reuse.models.GherkinStepNeed`-shaped
    value: the action's own text plus its required parameter shape --
    mirrors :class:`~.page_object_generator.PageObjectGenerationContext`'s
    own use of the same shape). ``class_name`` is the deterministically
    derived class name
    (:func:`~.utility_orchestrator.derive_utility_class_name`) the
    orchestrator has already computed for this brand-new utility --
    informational, not something this seam derives itself.
    """

    need: GherkinStepNeed
    class_name: str
    target_package: str
    customqa_constraints: tuple[str, ...]


class UtilityGenerator(Protocol):
    """Turns one NO_MATCH utility need plus its generation context into
    generated Java utility source."""

    def generate(self, context: UtilityGenerationContext) -> str:
        """Return generated Java utility source for ``context``.

        Per the registered ``generate_utilities`` v1.0.0 prompt's own
        OUTPUT CONTRACT (`automation_engineering/prompts/versions/
        generate_utilities_v1.0.0.txt`): a complete, stateless utility class
        (package, imports, a `final` class with a private constructor,
        static methods only -- mirroring the tracked baseline's own real
        `ConfigReader` shape, `test-suite-baseline/src/test/java/com/
        automation/base/ConfigReader.java`) in ``context.target_package``,
        born compliant with every constraint in
        ``context.customqa_constraints``. The orchestrator
        (:mod:`.utility_orchestrator`) trusts nothing about the result
        beyond that it is a string -- it performs no parsing, no
        compilation, no lint of its own; CP3/CP4 (later, out-of-scope
        tasks) are where generated Java is actually verified.
        """
        ...


class StubUtilityGenerator:
    """Deterministic, fixture-driven stand-in for the live LLM-backed
    generator.

    **Test/dev scaffolding only -- never the production path.** Returns
    pre-authored Java source keyed by ``context.need.text``, so a test can
    script exactly what a given utility need generates to, with no model
    call involved. Raises if asked to generate for a need text it has no
    canned answer for: a stub that silently invents Java on a cache miss is
    not deterministic, it is a worse-judgment fake LLM (same discipline as
    :class:`~automation_engineering.generation.page_object_generator.StubPageObjectGenerator`).

    Also a SPY: every context this stub is called with is recorded, in
    order, so a test can prove exactly what the orchestrator handed the
    seam -- in particular, that ``customqa_constraints`` actually reached
    the seam's own input, and that a TRUSTED_REUSE utility binding never
    calls this seam at all.
    """

    def __init__(self, java_source_by_need_text: Mapping[str, str]) -> None:
        self._canned = dict(java_source_by_need_text)
        self._received_contexts: list[UtilityGenerationContext] = []

    def generate(self, context: UtilityGenerationContext) -> str:
        self._received_contexts.append(context)
        try:
            return self._canned[context.need.text]
        except KeyError:
            raise KeyError(
                f"StubUtilityGenerator has no canned Java source for "
                f"need.text={context.need.text!r}. Register it via the "
                "constructor's java_source_by_need_text mapping."
            ) from None

    @property
    def call_count(self) -> int:
        return len(self._received_contexts)

    @property
    def received_contexts(self) -> tuple[UtilityGenerationContext, ...]:
        return tuple(self._received_contexts)


__all__ = [
    "StubUtilityGenerator",
    "UtilityGenerationContext",
    "UtilityGenerator",
]
