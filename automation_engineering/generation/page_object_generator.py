"""The page-object generation seam: one NO_MATCH page-object need plus its
generation context in, generated Java page-object source out -- everything
else (the reuse-first decision that routes here, the customqa:* constraint
list that context carries, the precise method-fit discharge on a TRUSTED
reuse) is orchestration-owned (:mod:`.page_object_orchestrator`), never this
module's concern. Mirrors :mod:`.step_definition_generator` exactly -- same
seam shape, same "stub now, live peer alongside it" split, same reasoning.

:class:`PageObjectGenerator` is the one interface the orchestration
(:mod:`.page_object_orchestrator`) depends on. Two implementations exist:

* :class:`StubPageObjectGenerator` -- this task's deterministic,
  fixture-driven stand-in. Test/dev scaffolding only -- the same pattern as
  :class:`~automation_engineering.generation.step_definition_generator.StubStepDefinitionGenerator`.
* ``LivePageObjectGenerator`` -- the live, ``llm_factory``-backed
  implementation (a peer behind this same seam, built in
  :mod:`.live_page_object_generator`, not this module).

The orchestrator (:mod:`.page_object_orchestrator`) never imports an LLM
provider or ``llm_factory`` -- it depends only on this Protocol, so the
reuse-first decision of whether to generate at all stays provably
deterministic regardless of which implementation is wired in.

**Multi-method-per-class (additive, this build).**
:class:`PageObjectGenerationContext` gained ``additional_method_needs``
(default ``()``): when a page-object class needs MULTIPLE fresh methods at
once
(:func:`~.page_object_orchestrator.orchestrate_page_object_class` batches
every NO_MATCH method-need destined for the same class into ONE seam
call), the primary method rides ``need`` exactly as before and every
sibling method rides this new field -- so the seam is called ONCE per
class, not once per method, and the class it returns carries every method
a step-def actually calls. Closes the gap
`page_object_reference_derivation.py`'s own derivation build flagged and
deliberately left open (``unverified_method_names``).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from automation_engineering.generation.models import PageObjectMethodNeed
from automation_engineering.reuse.models import GherkinStepNeed


@dataclass(frozen=True, slots=True)
class PageObjectGenerationContext:
    """Everything a :class:`PageObjectGenerator` needs to generate one page
    object -- the seam's own input contract.

    ``need`` describes the page-object action driving this generation (a
    :class:`~automation_engineering.reuse.models.GherkinStepNeed`-shaped
    value: the action's own text plus its required parameter shape --
    mirrors :class:`~.step_definition_generator.StepDefinitionGenerationContext`'s
    own use of the same shape). ``class_name`` is the deterministically
    derived class name (:func:`~.page_object_orchestrator.derive_page_object_class_name`)
    the orchestrator has already computed for this brand-new page object --
    an informational instruction the generated code must honor, not
    something this seam derives itself.

    ``additional_method_needs`` (additive, default ``()`` -- every
    pre-existing context/call site is unchanged) carries every OTHER
    method-need the SAME fresh ``class_name`` must ALSO satisfy, when the
    orchestrator (:func:`~.page_object_orchestrator.orchestrate_page_object_class`)
    has batched two-or-more NO_MATCH method-needs for one class into this
    ONE generation call -- the multi-method seam extension this platform's
    own page-object-request-derivation build (`page_object_reference_
    derivation.py`) flagged as a precondition: a step-def calling several
    methods on one brand-new page-object class must generate ONE class with
    ALL of them, never silently drop the second-or-later method. ``need``
    remains the PRIMARY method's own need (unchanged shape, unchanged
    meaning); each entry in ``additional_method_needs`` carries its OWN
    ``need``/``method_name`` for a sibling method the same class must also
    expose. Empty for the ordinary, still-most-common one-method-per-class
    case -- every existing caller that never sets this field is unaffected.

    ``method_name`` (additive, default ``None``) is the PRIMARY method's own
    caller-chosen Java method name -- the ``additional_method_needs`` sibling
    to :class:`~.models.PageObjectMethodNeed.method_name`, threaded through
    so a multi-method generation request can name EVERY method it asks for,
    not just the additional ones. ``None`` for the ordinary single-method
    case (v1.0.0's own INPUT CONTRACT never carried a method name at all --
    the model chooses it, exactly as before; this field is simply unused
    then). Required (never ``None``) whenever ``additional_method_needs`` is
    non-empty -- a multi-method generation request must name every method,
    including the first, never leave exactly one of several entries for the
    model to invent while the rest are caller-named.
    """

    need: GherkinStepNeed
    class_name: str
    target_package: str
    customqa_constraints: tuple[str, ...]
    additional_method_needs: tuple[PageObjectMethodNeed, ...] = ()
    method_name: str | None = None


class PageObjectGenerator(Protocol):
    """Turns one NO_MATCH page-object need plus its generation context into
    generated Java page-object source."""

    def generate(self, context: PageObjectGenerationContext) -> str:
        """Return generated Java page-object source for ``context``.

        Per the registered ``generate_page_objects`` v1.0.0 prompt's own
        OUTPUT CONTRACT (`automation_engineering/prompts/versions/
        generate_page_objects_v1.0.0.txt`): a complete page-object class
        (package, imports, class extending ``BasePage``, a
        constructor-injected ``WebDriver`` per ADR-0041 D5, locator fields,
        and at least one action method) in ``context.target_package``, born
        compliant with every constraint in ``context.customqa_constraints``.
        When ``context.additional_method_needs`` is non-empty, the returned
        class must additionally expose one action method per entry there,
        alongside ``context.need``'s own -- still exactly ONE class, now
        with multiple methods. The orchestrator (:mod:`.page_object_orchestrator`)
        trusts nothing about the result beyond that it is a string -- it
        performs no parsing, no compilation, no lint of its own; CP3/CP4
        (later, out-of-scope tasks) are where generated Java is actually
        verified. An implementation that cannot yet honor
        ``additional_method_needs`` (e.g. because its own backing prompt is
        still single-action-shaped) must raise rather than silently drop
        the extra methods -- see ``LivePageObjectGenerator`` for the
        current honest example of exactly that.
        """
        ...


class StubPageObjectGenerator:
    """Deterministic, fixture-driven stand-in for the live LLM-backed
    generator.

    **Test/dev scaffolding only -- never the production path.** Returns
    pre-authored Java source keyed by ``context.need.text``, so a test can
    script exactly what a given page-object need generates to, with no
    model call involved. Raises if asked to generate for a need text it has
    no canned answer for: a stub that silently invents Java on a cache miss
    is not deterministic, it is a worse-judgment fake LLM (same discipline
    as :class:`~.step_definition_generator.StubStepDefinitionGenerator`).

    Also a SPY: every context this stub is called with is recorded, in
    order, so a test can prove exactly what the orchestrator handed the
    seam -- in particular, that ``customqa_constraints`` actually reached
    the seam's own input (ADR-0044 D5's "constrain at generation"), and --
    the Part 1 proof this build's verification section requires -- that a
    TRUSTED_REUSE page-object binding never calls this seam at all.
    """

    def __init__(self, java_source_by_need_text: Mapping[str, str]) -> None:
        self._canned = dict(java_source_by_need_text)
        self._received_contexts: list[PageObjectGenerationContext] = []

    def generate(self, context: PageObjectGenerationContext) -> str:
        self._received_contexts.append(context)
        try:
            return self._canned[context.need.text]
        except KeyError:
            raise KeyError(
                f"StubPageObjectGenerator has no canned Java source for "
                f"need.text={context.need.text!r}. Register it via the "
                "constructor's java_source_by_need_text mapping."
            ) from None

    @property
    def call_count(self) -> int:
        return len(self._received_contexts)

    @property
    def received_contexts(self) -> tuple[PageObjectGenerationContext, ...]:
        return tuple(self._received_contexts)


__all__ = [
    "PageObjectGenerationContext",
    "PageObjectGenerator",
    "StubPageObjectGenerator",
]
