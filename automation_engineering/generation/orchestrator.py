"""Reuse-first step-definition orchestration (ADR-0044 D3/D4, this build's
own BUILD section).

For each Gherkin step-need a feature requires a binding for, this module
consults the reuse engine's own decision
(:func:`automation_engineering.reuse.engine.decide_reuse`) and acts on
exactly it -- never re-judging reuse itself, never silently reinterpreting
an escalation as either a bind or a generate:

* ``NoMatch`` -> GENERATE. The step-definition generation seam
  (:mod:`.step_definition_generator`) is called, with the platform's own
  ``customqa:*`` constraints (ADR-0044 D5) injected into the seam's own
  input -- born compliant, not verified compliant after the fact (CP3's
  Sonar scan, a later, out-of-scope task, is the verification half).
* ``TrustedReuse`` -> BIND. The existing catalog asset is bound as-is; the
  generation seam is never called -- proven, not merely claimed, by the
  spy contract :class:`~.step_definition_generator.StubStepDefinitionGenerator`
  exposes (`tests/unit/test_automation_engineering_generation_orchestrator.py`).
* ``Escalation`` -> SURFACE. Neither generated nor bound -- the reuse
  engine's own :class:`~automation_engineering.reuse.models.Escalation`
  record is carried through unedited, for the same human-in-the-loop
  surface every other layer's escalation already uses.

This module never imports ``llm_factory`` or any LLM provider -- it depends
only on the :class:`~.step_definition_generator.StepDefinitionGenerator`
Protocol, so the reuse-first routing decision (generate vs. bind vs.
escalate) stays provably deterministic regardless of which generator
implementation is wired in. It also never imports a live embedding provider
-- it depends only on
:class:`~automation_engineering.reuse.matcher.SemanticMatcher`, for the same
reason.

THE INHERITED PRECISE METHOD-FIT OBLIGATION -- carried forward, not discharged
--------------------------------------------------------------------------------
ADR-0044 D4's own clarification note (and this platform's reuse-engine build,
``automation_engineering/reuse/engine.py``) records that binding a step
definition to a REUSED PAGE OBJECT requires a PRECISE check -- does the
specific method the generated call is about to invoke actually exist on that
page object -- which only the generator that WRITES that call can perform,
because only it knows which method it is about to name. This module is that
generator's step-definition half, but it does **not** discharge that
obligation, because it never reaches the situation the obligation describes:
page-object reuse or generation does not exist yet (the next task, per this
build's own scope boundary). Concretely:

* ``StepDefinitionGenerationContext.page_object_interface`` is a bare,
  optional hint field on the seam's own input contract (see
  :mod:`.step_definition_generator`) -- this orchestrator never populates
  it. Every context this module constructs carries
  ``page_object_interface=None``; there is no catalog lookup against
  ``catalog.page_objects``/``catalog.utilities`` anywhere in this file. A
  test proves this directly (`test_generation_context_never_carries_a_page_object_hint`).
* The reuse engine's own ``TrustedReuse.asset`` -- when this task's
  orchestration binds a step (the ``BoundStepDefinition`` branch) -- is
  always a :class:`~automation_engineering.catalog.models.StepDefinitionAsset`
  in practice, never a page object or utility, because the only matcher this
  build wires in (:class:`~automation_engineering.reuse.matcher.SemanticMatcher`'s
  live realization, :class:`~automation_engineering.reuse.live_matcher.LiveSemanticMatcher`)
  only ever searches ``catalog.step_definitions`` (that module's own
  docstring: "Only step definitions are matched"). A step-definition-to-
  reused-PAGE-OBJECT binding therefore cannot even occur inside this
  orchestration as built -- it becomes possible only once a page-object-aware
  generator exists to make that binding decision, at which point the
  reuse engine's own coarse method-fit screen (already built,
  ``_check_method_fit``) and the full ``asset.methods`` inventory
  (`TrustedReuse`'s own docstring) are exactly what that future generator
  needs, and were built precisely so this obligation is discharge-*able*
  then, not now.

This module does not fake discharging that obligation by, say, silently
approving every generated step's page-object call as "fine" -- it simply
never generates a call against a *reused* page object at all, because no
reused page object is ever in scope here.
"""

from __future__ import annotations

from collections.abc import Sequence

from automation_engineering.catalog.models import AssetCatalog
from automation_engineering.generation.models import (
    BoundStepDefinition,
    EscalatedStepNeed,
    GeneratedStepDefinition,
    StepDefinitionOutcome,
)
from automation_engineering.generation.step_definition_generator import (
    StepDefinitionGenerationContext,
    StepDefinitionGenerator,
)
from automation_engineering.reuse.engine import DEFAULT_CONFIDENCE_THRESHOLD, decide_reuse
from automation_engineering.reuse.matcher import SemanticMatcher
from automation_engineering.reuse.models import Escalation, GherkinStepNeed, NoMatch, TrustedReuse

#: The tracked test-suite-baseline's own step-definition package
#: (`test-suite-baseline/src/test/java/com/automation/steps/SmokeSteps.java`).
DEFAULT_TARGET_PACKAGE = "com.automation.steps"

#: ADR-0044 D5's "constrain at generation" -- the `customqa:*` SonarQube
#: quality-profile rules that are STEP-DEFINITION constraints specifically,
#: evidenced directly in this platform's own real SonarQube fixture data
#: (`requirement_intelligence/input/sonar/sonar-issues.json`, the same
#: evidence ADR-0037 D1 cites): `customqa:direct-webdriver-action` and
#: `customqa:long-method`. Injected into every generation context below so a
#: live call would be constrained by them, not merely informed of them
#: (proven deterministically via the stub seam's own spy, never requiring a
#: live SonarQube scan -- that verification half is CP3's, a later,
#: out-of-scope task).
DEFAULT_CUSTOMQA_STEP_DEFINITION_CONSTRAINTS: tuple[str, ...] = (
    "customqa:direct-webdriver-action -- never call a WebDriver method or "
    "import org.openqa.selenium.WebDriver directly in a step definition; "
    "every UI interaction must go through a page-object method.",
    "customqa:long-method -- keep the generated method under 40 lines; "
    "delegate multi-step logic to a page-object helper instead of inlining it.",
)


def orchestrate_step_definition(
    need: GherkinStepNeed,
    catalog: AssetCatalog,
    matcher: SemanticMatcher,
    generator: StepDefinitionGenerator,
    *,
    target_package: str = DEFAULT_TARGET_PACKAGE,
    customqa_constraints: tuple[str, ...] = DEFAULT_CUSTOMQA_STEP_DEFINITION_CONSTRAINTS,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> StepDefinitionOutcome:
    """Reuse-first orchestration for exactly one Gherkin step-need.

    Consults :func:`~automation_engineering.reuse.engine.decide_reuse` once,
    and acts on exactly its outcome -- see module docstring for the three
    branches. Deterministic given deterministic ``matcher``/``generator``
    implementations (:class:`~automation_engineering.reuse.matcher.StubSemanticMatcher`/
    :class:`~.step_definition_generator.StubStepDefinitionGenerator`); the
    only nondeterministic calls (a live semantic match, a live generation)
    live entirely behind those two seams, never in this function.
    """
    decision = decide_reuse(need, catalog, matcher, confidence_threshold=confidence_threshold)

    if isinstance(decision, TrustedReuse):
        return BoundStepDefinition(need=need, asset=decision.asset)

    if isinstance(decision, Escalation):
        return EscalatedStepNeed(need=need, escalation=decision)

    if isinstance(decision, NoMatch):
        context = StepDefinitionGenerationContext(
            need=need,
            target_package=target_package,
            customqa_constraints=customqa_constraints,
        )
        java_source = generator.generate(context)
        return GeneratedStepDefinition(
            need=need, java_source=java_source, target_package=target_package
        )

    raise AssertionError(f"unreachable: unknown ReuseDecision variant {decision!r}")


def generate_step_definitions(
    needs: Sequence[GherkinStepNeed],
    catalog: AssetCatalog,
    matcher: SemanticMatcher,
    generator: StepDefinitionGenerator,
    *,
    target_package: str = DEFAULT_TARGET_PACKAGE,
    customqa_constraints: tuple[str, ...] = DEFAULT_CUSTOMQA_STEP_DEFINITION_CONSTRAINTS,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> tuple[StepDefinitionOutcome, ...]:
    """Reuse-first orchestration for a feature's full set of step-needs --
    one :func:`orchestrate_step_definition` call per need, in order."""
    return tuple(
        orchestrate_step_definition(
            need,
            catalog,
            matcher,
            generator,
            target_package=target_package,
            customqa_constraints=customqa_constraints,
            confidence_threshold=confidence_threshold,
        )
        for need in needs
    )


__all__ = [
    "DEFAULT_CUSTOMQA_STEP_DEFINITION_CONSTRAINTS",
    "DEFAULT_TARGET_PACKAGE",
    "generate_step_definitions",
    "orchestrate_step_definition",
]
