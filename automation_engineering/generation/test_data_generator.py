"""The test-data generation seam: one :class:`TestDataSpecification` in,
generated Java test-data source out -- everything else (the customqa:*
constraint list the context carries, the env/data boundary enforcement) is
orchestration-owned (:mod:`.test_data_orchestrator`), never this module's
concern. Mirrors :mod:`.utility_generator`/:mod:`.page_object_generator`
exactly in SHAPE -- same "stub now, live peer alongside it" split -- but its
input is fundamentally different: a
:class:`~contracts.test_data_specification.TestDataSpecification` (fields +
required positive/negative/boundary variants), never a
:class:`~automation_engineering.reuse.models.GherkinStepNeed` (there is no
Gherkin action text to semantically match against; see
:mod:`.test_data_orchestrator`'s own module docstring for the full
reasoning this asset kind breaks the triad's pattern).

``TestDataSpecification`` is the REAL Layer 2 -> Layer 3 boundary contract
(`contracts.test_data_specification`, emitted by
:mod:`feature_engineering.stage.test_data_spec`) -- it carries no Java-shape
fields (ADR-0043 D7: "not a dataset and not Java"), so
``TestDataGenerationContext`` carries ``class_name``/``target_package``
itself, computed by the orchestrator
(:func:`~.test_data_orchestrator.derive_test_data_class_name`), the same
way :class:`~.page_object_generator.PageObjectGenerationContext` already
carries its own orchestrator-derived ``class_name``.

:class:`TestDataGenerator` is the one interface the orchestration
(:mod:`.test_data_orchestrator`) depends on. Two implementations exist:

* :class:`StubTestDataGenerator` -- this task's deterministic,
  fixture-driven stand-in. Test/dev scaffolding only -- the same pattern as
  :class:`~automation_engineering.generation.utility_generator.StubUtilityGenerator`.
* ``LiveTestDataGenerator`` -- the live, ``llm_factory``-backed
  implementation (a peer behind this same seam, built in
  :mod:`.live_test_data_generator`, not this module).

The orchestrator never imports an LLM provider or ``llm_factory`` -- it
depends only on this Protocol.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from contracts.test_data_specification import TestDataSpecification


@dataclass(frozen=True, slots=True)
class TestDataGenerationContext:
    """Everything a :class:`TestDataGenerator` needs to generate one
    test-data class -- the seam's own input contract.

    ``specification`` is the caller-supplied, REAL Layer 2 emission
    (:class:`~contracts.test_data_specification.TestDataSpecification`,
    ADR-0043 D7's own handoff contract). ``class_name``/``target_package``
    are NOT read off the specification (it carries no Java-shape fields at
    all) -- they are the orchestrator's own derivation
    (:func:`~.test_data_orchestrator.derive_test_data_class_name`), the
    same split :class:`~.page_object_generator.PageObjectGenerationContext`
    already establishes for page objects.
    """

    #: Not a test class -- silences pytest's default `Test*` collection
    #: heuristic for a production dataclass that happens to share ADR-0043
    #: D7's own "test-data" naming.
    __test__ = False

    specification: TestDataSpecification
    class_name: str
    target_package: str
    customqa_constraints: tuple[str, ...]


class TestDataGenerator(Protocol):
    """Turns one :class:`TestDataGenerationContext` into generated Java
    test-data source.

    Not marked ``__test__ = False`` the way the other "Test"-prefixed
    classes in this module are: a ``Protocol`` has no concrete
    ``__init__`` for pytest's default collection heuristic to flag in the
    first place (verified directly -- this class was never among the
    classes pytest warned about), and adding a class attribute here would
    make it part of the STRUCTURAL interface every implementation
    (`StubTestDataGenerator`, `LiveTestDataGenerator`) would then need to
    satisfy too.
    """

    def generate(self, context: TestDataGenerationContext) -> str:
        """Return generated Java test-data source for ``context``.

        Per the registered ``generate_test_data`` v1.0.0 prompt's own
        OUTPUT CONTRACT (`automation_engineering/prompts/versions/
        generate_test_data_v1.0.0.txt`): a complete test-data class
        (package `com.automation.utils`, a class declaration, one field
        per ``context.specification.fields`` entry, values EITHER literal
        constants OR read via ``ConfigReader.data(...)`` -- NEVER
        ``ConfigReader.env(...)`` and never a fresh ``config.properties``
        `env.*` key), born compliant with every constraint in
        ``context.customqa_constraints``. The orchestrator
        (:mod:`.test_data_orchestrator`) trusts nothing about the result
        beyond that it is a string; CP3/CP4 (later, out-of-scope tasks)
        verify generated Java.
        """
        ...


class StubTestDataGenerator:
    """Deterministic, fixture-driven stand-in for the live LLM-backed
    generator.

    **Test/dev scaffolding only -- never the production path.** Returns
    pre-authored Java source keyed by
    ``context.specification.requirement_id``, so a test can script exactly
    what a given specification generates to, with no model call involved.
    Raises if asked to generate for a requirement id it has no canned
    answer for: a stub that silently invents Java on a cache miss is not
    deterministic, it is a worse-judgment fake LLM (same discipline as
    :class:`~automation_engineering.generation.utility_generator.StubUtilityGenerator`).

    Also a SPY: every context this stub is called with is recorded, in
    order, so a test can prove exactly what the orchestrator handed the
    seam -- in particular, that ``customqa_constraints`` actually reached
    the seam's own input, and that generation happens for EVERY
    specification handed in (there is no reuse-decision branch that could
    ever skip calling this seam -- see :mod:`.test_data_orchestrator`).
    """

    def __init__(self, java_source_by_requirement_id: Mapping[str, str]) -> None:
        self._canned = dict(java_source_by_requirement_id)
        self._received_contexts: list[TestDataGenerationContext] = []

    def generate(self, context: TestDataGenerationContext) -> str:
        self._received_contexts.append(context)
        try:
            return self._canned[context.specification.requirement_id]
        except KeyError:
            raise KeyError(
                f"StubTestDataGenerator has no canned Java source for "
                f"requirement_id={context.specification.requirement_id!r}. Register "
                "it via the constructor's java_source_by_requirement_id mapping."
            ) from None

    @property
    def call_count(self) -> int:
        return len(self._received_contexts)

    @property
    def received_contexts(self) -> tuple[TestDataGenerationContext, ...]:
        return tuple(self._received_contexts)


__all__ = [
    "StubTestDataGenerator",
    "TestDataGenerationContext",
    "TestDataGenerator",
]
