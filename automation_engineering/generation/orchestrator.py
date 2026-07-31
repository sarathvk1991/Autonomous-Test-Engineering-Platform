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

THE INHERITED PRECISE METHOD-FIT OBLIGATION -- now DISCHARGED
------------------------------------------------------------------
ADR-0044 D4's own clarification note recorded that binding a step
definition to a REUSED PAGE OBJECT requires a PRECISE check -- does the
specific method the generated call is about to invoke actually exist on
that page object -- and named it "the generator's own obligation, not this
engine's." The step-definition build that first wrote this module carried
that obligation forward, undischarged, because it never reached the
situation the obligation describes: no page-object generator existed yet.

**That generator now exists** (:mod:`.page_object_orchestrator`,
:mod:`.method_fit`, this build), and this module is where its result is
consumed -- the ACTUAL binding point the obligation names. Concretely:

* ``page_object_request: PageObjectBindingRequest | None`` is a new,
  OPTIONAL parameter on :func:`orchestrate_step_definition`/
  :func:`generate_step_definitions`. Omitted (the default), behavior is
  UNCHANGED from before this build: ``page_object_interface`` stays
  ``None``, exactly as the prior obligation-carried-forward note described.
* SUPPLIED, and the step needs to be GENERATED (NO_MATCH): this module
  calls :func:`~.page_object_orchestrator.orchestrate_page_object_method`
  BEFORE calling the step-definition generation seam. That call runs the
  SAME reuse engine (:func:`automation_engineering.reuse.engine.decide_reuse`,
  unmodified) against ``catalog.page_objects``, and -- when it returns a
  ``TrustedReuse`` -- the PRECISE check
  (:func:`automation_engineering.generation.method_fit.verify_specific_method_fit`)
  verifies the SPECIFIC method (``page_object_request.method_need.method_name``)
  is actually present on the reused class's real inventory
  (``TrustedReuse.asset.methods``), not merely that SOME method has a
  compatible shape (the coarse screen's own, narrower guarantee).
  - Verified -> ``page_object_interface`` is populated with the reused
    class's own ``class_name``, and the step definition is generated
    against a page-object binding that is now FULLY verified (coarse +
    precise, D4(c) complete for page objects).
  - NOT verified (absent, or present with the wrong shape) -> the WHOLE
    step escalates (``EscalatedStepNeed``, carrying the precise check's own
    ``Escalation``) -- the step is not generated against a page-object call
    this platform cannot trust, mirroring D4's own "any one failing routes
    to human review, never a silent fallback."
  - No catalogued page object even coarsely matches -> a brand-new page
    object is generated (:mod:`.page_object_generator`'s own seam), and
    ``page_object_interface`` is populated with the freshly derived class
    name.

This closes the gap D4 exists to close for page objects: check (c) is now
COARSE (decision-time, `_check_method_fit`) **and** PRECISE (generation-time,
this module wired to :mod:`.method_fit`), both realized, neither one alone
mistaken for the whole of (c).

**Utilities remain out of this build's scope**, the same honest deferral
this module itself used for page objects before this build existed:
nothing in this module, :mod:`.page_object_orchestrator`, or
:mod:`.method_fit` ever looks up ``catalog.utilities`` -- a structural
guard test proves it directly
(`test_orchestrator_still_never_looks_up_utilities`).
"""

from __future__ import annotations

from collections.abc import Sequence

from automation_engineering.catalog.models import AssetCatalog
from automation_engineering.generation.models import (
    BoundPageObjectMethod,
    BoundStepDefinition,
    EscalatedStepNeed,
    GeneratedPageObject,
    GeneratedStepDefinition,
    StepDefinitionOutcome,
)
from automation_engineering.generation.page_object_orchestrator import (
    PageObjectBindingRequest,
    orchestrate_page_object_method,
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
    page_object_request: PageObjectBindingRequest | None = None,
) -> StepDefinitionOutcome:
    """Reuse-first orchestration for exactly one Gherkin step-need.

    Consults :func:`~automation_engineering.reuse.engine.decide_reuse` once,
    and acts on exactly its outcome -- see module docstring for the three
    branches. Deterministic given deterministic ``matcher``/``generator``
    implementations (:class:`~automation_engineering.reuse.matcher.StubSemanticMatcher`/
    :class:`~.step_definition_generator.StubStepDefinitionGenerator`); the
    only nondeterministic calls (a live semantic match, a live generation)
    live entirely behind those two seams, never in this function.

    ``page_object_request``, when supplied, resolves the page object the
    generated step will call BEFORE generation happens -- the precise
    method-fit discharge (module docstring, "THE INHERITED PRECISE
    METHOD-FIT OBLIGATION"). Omitted, behavior is unchanged from before this
    build: ``page_object_interface`` stays ``None``.
    """
    decision = decide_reuse(need, catalog, matcher, confidence_threshold=confidence_threshold)

    if isinstance(decision, TrustedReuse):
        return BoundStepDefinition(need=need, asset=decision.asset)

    if isinstance(decision, Escalation):
        return EscalatedStepNeed(need=need, escalation=decision)

    if isinstance(decision, NoMatch):
        page_object_interface = None
        page_object_outcome: GeneratedPageObject | BoundPageObjectMethod | None = None

        if page_object_request is not None:
            resolved = orchestrate_page_object_method(
                page_object_request.method_need,
                catalog,
                page_object_request.matcher,
                page_object_request.generator,
                target_package=page_object_request.target_package,
                customqa_constraints=page_object_request.customqa_constraints,
                confidence_threshold=confidence_threshold,
            )
            if not isinstance(resolved, (GeneratedPageObject, BoundPageObjectMethod)):
                # EscalatedPageObjectMethodNeed -- the step cannot be safely
                # generated against a page-object binding this platform does
                # not trust; the WHOLE step escalates, carrying the
                # page-object side's own Escalation (module docstring).
                return EscalatedStepNeed(need=need, escalation=resolved.escalation)
            page_object_outcome = resolved
            page_object_interface = (
                resolved.asset.class_name
                if isinstance(resolved, BoundPageObjectMethod)
                else resolved.class_name
            )

        context = StepDefinitionGenerationContext(
            need=need,
            target_package=target_package,
            customqa_constraints=customqa_constraints,
            page_object_interface=page_object_interface,
        )
        java_source = generator.generate(context)
        return GeneratedStepDefinition(
            need=need,
            java_source=java_source,
            target_package=target_package,
            page_object_outcome=page_object_outcome,
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
    page_object_request: PageObjectBindingRequest | None = None,
) -> tuple[StepDefinitionOutcome, ...]:
    """Reuse-first orchestration for a feature's full set of step-needs --
    one :func:`orchestrate_step_definition` call per need, in order. When
    supplied, the SAME ``page_object_request`` is used for every need in the
    batch -- a caller needing per-step page-object requests calls
    :func:`orchestrate_step_definition` directly, per step."""
    return tuple(
        orchestrate_step_definition(
            need,
            catalog,
            matcher,
            generator,
            target_package=target_package,
            customqa_constraints=customqa_constraints,
            confidence_threshold=confidence_threshold,
            page_object_request=page_object_request,
        )
        for need in needs
    )


__all__ = [
    "DEFAULT_CUSTOMQA_STEP_DEFINITION_CONSTRAINTS",
    "DEFAULT_TARGET_PACKAGE",
    "generate_step_definitions",
    "orchestrate_step_definition",
]
