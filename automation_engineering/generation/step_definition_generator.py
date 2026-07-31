"""The step-definition generation seam: one NO_MATCH step-need plus its
generation context in, generated Java step-definition source out --
everything else (the reuse-first decision that routes here, the customqa:*
constraint list that context carries) is orchestration-owned
(:mod:`.orchestrator`), never this module's concern. Mirrors
:mod:`automation_engineering.reuse.matcher` exactly -- same seam shape, same
"stub now, live peer alongside it" split, same reasoning.

:class:`StepDefinitionGenerator` is the one interface the orchestration
(:mod:`.orchestrator`) depends on. Two implementations exist:

* :class:`StubStepDefinitionGenerator` -- this task's deterministic,
  fixture-driven stand-in. Test/dev scaffolding only -- the same pattern as
  :class:`~automation_engineering.reuse.matcher.StubSemanticMatcher`/
  :class:`~feature_engineering.generation.content_generator.StubFeatureContentGenerator`.
* ``LiveStepDefinitionGenerator`` -- the live, ``llm_factory``-backed
  implementation (a peer behind this same seam, built in
  :mod:`.live_step_definition_generator`, not this module).

The orchestrator (:mod:`.orchestrator`) never imports an LLM provider or
``llm_factory`` -- it depends only on this Protocol, so the reuse-first
decision of whether to generate at all stays provably deterministic
regardless of which implementation is wired in.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from automation_engineering.reuse.models import GherkinStepNeed


@dataclass(frozen=True, slots=True)
class StepDefinitionGenerationContext:
    """Everything a :class:`StepDefinitionGenerator` needs to generate one
    step-definition method -- the seam's own input contract.

    ``page_object_interface``/``utility_interface`` are bare hint fields (a
    fully-qualified class name the generated code MAY reference). Both stay
    ``None`` unless the step-def orchestrator (:mod:`.orchestrator`) was
    supplied a ``page_object_request``/``utility_request`` for this need and
    that resolution VERIFIED the binding (coarse + precise method-fit,
    ADR-0044 D4(c)) -- see :mod:`.orchestrator`'s own module docstring.
    """

    need: GherkinStepNeed
    target_package: str
    customqa_constraints: tuple[str, ...]
    page_object_interface: str | None = None
    utility_interface: str | None = None


class StepDefinitionGenerator(Protocol):
    """Turns one NO_MATCH step-need plus its generation context into
    generated Java step-definition source."""

    def generate(self, context: StepDefinitionGenerationContext) -> str:
        """Return generated Java step-definition source for ``context``.

        Per the registered ``generate_step_definitions`` v1.0.0 prompt's own
        OUTPUT CONTRACT (`automation_engineering/prompts/versions/
        generate_step_definitions_v1.0.0.txt`): a complete step-definition
        class (package, imports, class, exactly one annotated method) in
        ``context.target_package``, born compliant with every constraint in
        ``context.customqa_constraints``. The orchestrator (:mod:`.orchestrator`)
        trusts nothing about the result beyond that it is a string -- it
        performs no parsing, no compilation, no lint of its own; CP3 (a
        later, out-of-scope task) is where generated Java is actually
        verified.
        """
        ...


class StubStepDefinitionGenerator:
    """Deterministic, fixture-driven stand-in for the live LLM-backed
    generator.

    **Test/dev scaffolding only -- never the production path.** Returns
    pre-authored Java source keyed by ``context.need.text``, so a test can
    script exactly what a given step need generates to, with no model call
    involved. Raises if asked to generate for a step text it has no canned
    answer for: a stub that silently invents Java on a cache miss is not
    deterministic, it is a worse-judgment fake LLM (same discipline as
    :class:`~automation_engineering.reuse.matcher.StubSemanticMatcher`).

    Also a SPY: every context this stub is called with is recorded, in
    order, so a test can prove exactly what the orchestrator handed the
    seam -- in particular, that ``customqa_constraints`` actually reached
    the seam's own input (ADR-0044 D5's "constrain at generation").
    """

    def __init__(self, java_source_by_step_text: Mapping[str, str]) -> None:
        self._canned = dict(java_source_by_step_text)
        self._received_contexts: list[StepDefinitionGenerationContext] = []

    def generate(self, context: StepDefinitionGenerationContext) -> str:
        self._received_contexts.append(context)
        try:
            return self._canned[context.need.text]
        except KeyError:
            raise KeyError(
                f"StubStepDefinitionGenerator has no canned Java source for "
                f"need.text={context.need.text!r}. Register it via the "
                "constructor's java_source_by_step_text mapping."
            ) from None

    @property
    def call_count(self) -> int:
        return len(self._received_contexts)

    @property
    def received_contexts(self) -> tuple[StepDefinitionGenerationContext, ...]:
        return tuple(self._received_contexts)


__all__ = [
    "StepDefinitionGenerationContext",
    "StepDefinitionGenerator",
    "StubStepDefinitionGenerator",
]
