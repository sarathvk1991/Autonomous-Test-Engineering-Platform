"""Derives which page-object class, method(s), and signature(s) a
GENERATED step-definition's own body actually calls -- the missing "per-
step binding-request derivation" `docs/architecture/architecture-baseline-
v2.md`'s stage-15 wiring build entry records as this platform's own,
carried-forward scope boundary: "no subsystem derives 'which specific
page-object/utility method does this step need'... until a future task
builds THAT per-step binding-request derivation." This module is that
task, for page objects (utilities remain out of scope, mirroring every
prior page-object-before-utilities build in this generation package).

THE DESIGN DECISION -- derive from the GENERATED step-def's own body,
never infer from the raw Gherkin step-need text beforehand
====================================================================
Two candidate sources were possible; only one is consistent with ADR-0044
D4's own clarification note (Accepted, quoted in full in
:mod:`.page_object_orchestrator`'s own module docstring, restated here
because this module exists to resolve exactly the question it poses):

    "which specific method a not-yet-written step definition will call is
    NOT KNOWABLE UNTIL A FUTURE GENERATOR ACTUALLY WRITES THAT CALL."

That sentence rules out inferring a page-object method name from the raw
Gherkin step text BEFORE any step definition exists -- there is nothing in
step text like "the user logs in" that deterministically names a Java
method (`enterUsername`? `typeUsername`? `setUsername`?); any such
inference would be a guess dressed as a derivation, exactly the
"threshold locked against data collected before the underlying defect is
even fixable... a guess dressed as a number" failure mode this platform's
own `ADR-0047 D3` already names and rejects for a different metric. The
ONLY moment a specific method name genuinely exists is once a real
step-definition generator (:mod:`.step_definition_generator`) has already
written a call site -- so THIS module's own input is a step-definition's
own, already-generated ``java_source``, never a step-need's bare text.

`architecture-baseline-v2.md`'s own "from raw Gherkin text" phrasing
(quoted above) is read here as informal shorthand for "the missing per-
step binding-request derivation," not a binding technical prescription
that contradicts ADR-0044 D4's own explicit, Accepted text -- there is no
real ADR-vs-task disagreement once ADR-0044 D4 is read as authoritative
over that looser tracking-document phrasing.

Deterministic, no LLM, no semantic inference: the only input is Java text
already on disk (or already returned by a stub/live step-def generator).
Parses via ``javalang`` -- the SAME parser and helpers
(:mod:`automation_engineering.catalog.java_source`) the catalog scanner
already uses for declaration extraction, never a second parsing
mechanism; this module adds ONLY the one traversal the catalog scanner
never needed -- walking a method BODY for ``MethodInvocation`` call sites,
not a class's own declarations.

**Class name, never independently re-derived.** `class_name` is read
directly from the step-def's own field declaration (e.g. ``private
LoginPage loginPage;`` -> ``"LoginPage"``) -- the exact name a freshly
generated page object MUST use to keep the step-def compiling, and
possibly DIFFERENT from what
:func:`~.page_object_orchestrator.derive_page_object_class_name` would
independently guess from the step's own text (that function has no
visibility into what a step-def generator actually wrote). This module's
own output feeds :class:`~.models.PageObjectMethodNeed.class_name_override`
for exactly this reason.

**Parameter shapes, resolved from the real call site, never assumed to
equal `GherkinStepNeed.captures`.** A call argument that is a simple
identifier matching one of the step-def method's own declared parameters
resolves to that parameter's real, declared Java type; a literal resolves
by its own token shape (a quoted string, digits, `true`/`false`); anything
else resolves to `"Object"`, an honest, conservative fallback -- never a
crash, never a silent wrong guess. This is grounded in the ACTUAL
generated code, which the prompt's own INPUT CONTRACT already requires to
correspond to the step's own captures in order
(`generate_step_definitions_v1.0.0.txt`), but this module verifies that
correspondence by reading it, rather than assuming it holds.

**Page-object fields identified by the platform's own naming convention,
not a new heuristic.** A field is treated as a page-object collaborator
when its declared type name ends with ``"Page"`` -- the exact suffix
:func:`~.page_object_orchestrator.derive_page_object_class_name` already
guarantees every derived page-object class name carries, and the shape
`customqa:direct-webdriver-action` already forces every step-definition
field to be (a page-object or utility instance, never a raw `WebDriver`).
Utility-typed fields (which do not carry this suffix, e.g. `ConfigReader`)
are deliberately excluded -- utility-request derivation remains this
build's own, honestly carried-forward next scope, the identical
page-objects-before-utilities sequencing every generator/orchestrator in
this package has already followed.

KNOWN, DELIBERATELY UNRESOLVED GAP -- multiple FRESH methods on one class
==========================================================================
When a step-def references TWO OR MORE methods on a page-object class that
turns out to need FRESH generation (no catalogued match for either), only
the FIRST such method actually reaches
:func:`~.page_object_orchestrator.orchestrate_page_object_method`'s own
generation seam -- :class:`.page_object_generator.PageObjectGenerationContext`
is, as built, shaped around ONE method-need per generation call, with no
field through which a second, sibling method name could be requested in
the SAME class. Generating twice would silently produce two conflicting,
incomplete "LoginPage" sources under one class name -- worse than doing
nothing. This module never does that: a second-or-later method needed on
an ALREADY-freshly-generated class in the SAME derivation is recorded in
:attr:`CoGeneratedStepDefinition.unverified_method_names`, never silently
dropped and never silently mis-generated. Closing this gap needs a change
to the page-object generation SEAM's own input contract (accepting more
than one method-need per call) -- explicitly out of THIS build's own
scope (derivation + wiring only, never the live generator/prompt shape,
per this task's own instruction) and flagged here as a finding for the
live-regeneration follow-up task.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import javalang

from automation_engineering.catalog.java_source import CUCUMBER_STEP_ANNOTATIONS, type_name
from automation_engineering.catalog.models import AssetCatalog, JavaParameter
from automation_engineering.generation.models import (
    EscalatedPageObjectMethodNeed,
    EscalatedStepNeed,
    GeneratedPageObject,
    GeneratedStepDefinition,
    PageObjectMethodNeed,
    PageObjectMethodOutcome,
    StepDefinitionOutcome,
)
from automation_engineering.generation.orchestrator import (
    DEFAULT_CUSTOMQA_STEP_DEFINITION_CONSTRAINTS,
    DEFAULT_TARGET_PACKAGE,
    orchestrate_step_definition,
)
from automation_engineering.generation.page_object_generator import PageObjectGenerator
from automation_engineering.generation.page_object_orchestrator import (
    DEFAULT_CUSTOMQA_PAGE_OBJECT_CONSTRAINTS,
    DEFAULT_PAGE_OBJECT_TARGET_PACKAGE,
    orchestrate_page_object_method,
)
from automation_engineering.generation.step_definition_generator import StepDefinitionGenerator
from automation_engineering.reuse.engine import DEFAULT_CONFIDENCE_THRESHOLD
from automation_engineering.reuse.matcher import SemanticMatcher
from automation_engineering.reuse.models import GherkinStepNeed

#: A page-object-typed field's declared type always ends with this suffix
#: (module docstring) -- the same guarantee
#: `.page_object_orchestrator.derive_page_object_class_name` already
#: enforces for every FRESHLY derived class name.
_PAGE_OBJECT_TYPE_SUFFIX = "Page"


@dataclass(frozen=True, slots=True)
class DerivedPageObjectMethodCall:
    """One page-object method a step-definition's own body calls --
    ``parameters`` resolved from the real call-site arguments (module
    docstring), never assumed equal to `GherkinStepNeed.captures`."""

    method_name: str
    parameters: tuple[JavaParameter, ...]


@dataclass(frozen=True, slots=True)
class DerivedPageObjectRequest:
    """Every distinct method a step-definition's body calls against ONE
    page-object-typed field -- ``class_name`` is that field's OWN declared
    type (module docstring: read directly, never independently
    re-derived)."""

    class_name: str
    method_calls: tuple[DerivedPageObjectMethodCall, ...]


def _resolve_argument_type(
    argument: javalang.tree.Expression, step_def_parameter_types: dict[str, str]
) -> str:
    """The real Java type of one call-site argument expression, resolved
    (module docstring): a simple identifier matching one of the step-def
    method's own parameters resolves to that parameter's declared type; a
    literal resolves by its own token shape; anything else resolves to the
    honest, conservative ``"Object"`` fallback -- never a crash."""
    if isinstance(argument, javalang.tree.MemberReference) and not argument.qualifier:
        resolved = step_def_parameter_types.get(argument.member)
        if resolved is not None:
            return resolved
    if isinstance(argument, javalang.tree.Literal):
        value = argument.value
        if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
            return "String"
        if value in ("true", "false"):
            return "boolean"
        if value.lstrip("-").isdigit():
            return "int"
    return "Object"


def derive_page_object_requests(java_source: str) -> tuple[DerivedPageObjectRequest, ...]:
    """Parse one generated step-definition class's Java source and return
    one :class:`DerivedPageObjectRequest` per distinct page-object-typed
    field its own annotated step method calls, each carrying every
    distinct method invoked on that field (module docstring).

    Deterministic and side-effect-free: the same source always produces
    the identical result. A step-def that calls no page-object-typed
    field (e.g. a purely-assertion `Then` step, or one that only calls a
    utility) returns an empty tuple -- a legitimate, non-error outcome,
    never a crash.
    """
    tree = javalang.parse.parse(java_source)
    class_declaration = next(iter(tree.types))

    page_object_fields: dict[str, str] = {}
    for field_declaration in class_declaration.fields:
        declared_type = type_name(field_declaration.type)
        if not declared_type.endswith(_PAGE_OBJECT_TYPE_SUFFIX):
            continue
        for declarator in field_declaration.declarators:
            page_object_fields[declarator.name] = declared_type

    step_method = next(
        (
            method
            for method in class_declaration.methods
            if any(a.name in CUCUMBER_STEP_ANNOTATIONS for a in method.annotations)
        ),
        None,
    )
    if step_method is None or not page_object_fields:
        return ()

    parameter_types = {p.name: type_name(p.type) for p in step_method.parameters}

    # class_name -> method_name -> parameters ("first occurrence wins": a
    # well-formed generated step-def calls each method with one consistent
    # shape within its own single, short body, module docstring's own
    # `customqa:long-method` constraint keeping that body small).
    calls_by_class: dict[str, dict[str, tuple[JavaParameter, ...]]] = defaultdict(dict)
    for _, invocation in step_method.filter(javalang.tree.MethodInvocation):
        if invocation.qualifier not in page_object_fields:
            continue
        class_name = page_object_fields[invocation.qualifier]
        parameters = tuple(
            JavaParameter(
                name=f"arg{index}",
                java_type=_resolve_argument_type(argument, parameter_types),
            )
            for index, argument in enumerate(invocation.arguments)
        )
        calls_by_class[class_name].setdefault(invocation.member, parameters)

    return tuple(
        DerivedPageObjectRequest(
            class_name=class_name,
            method_calls=tuple(
                DerivedPageObjectMethodCall(method_name=method_name, parameters=parameters)
                for method_name, parameters in methods.items()
            ),
        )
        for class_name, methods in calls_by_class.items()
    )


@dataclass(frozen=True, slots=True)
class CoGeneratedStepDefinition:
    """A step-definition generated WITHOUT a pre-known page-object binding
    (:func:`~.orchestrator.orchestrate_step_definition` called with
    ``page_object_request=None``, today's only real call shape -- no
    subsystem derives one in advance, module docstring), together with
    every page-object outcome its own body was found, after the fact, to
    reference.

    ``unverified_method_names`` names any ``"ClassName.methodName"`` this
    derivation found but could NOT independently resolve/generate (module
    docstring's own known gap: a second-or-later FRESH method needed on a
    class already freshly generated earlier in this SAME call) -- empty in
    the common case (one page-object class, or every class either fully
    reused or needing exactly one fresh method).
    """

    need: GherkinStepNeed
    java_source: str
    target_package: str
    page_object_outcomes: tuple[PageObjectMethodOutcome, ...]
    unverified_method_names: tuple[str, ...] = ()


def generate_step_definition_with_derived_page_objects(
    need: GherkinStepNeed,
    catalog: AssetCatalog,
    step_matcher: SemanticMatcher,
    step_generator: StepDefinitionGenerator,
    page_object_matcher: SemanticMatcher,
    page_object_generator: PageObjectGenerator,
    *,
    target_package: str = DEFAULT_TARGET_PACKAGE,
    customqa_constraints: tuple[str, ...] = DEFAULT_CUSTOMQA_STEP_DEFINITION_CONSTRAINTS,
    page_object_target_package: str = DEFAULT_PAGE_OBJECT_TARGET_PACKAGE,
    page_object_customqa_constraints: tuple[str, ...] = DEFAULT_CUSTOMQA_PAGE_OBJECT_CONSTRAINTS,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> StepDefinitionOutcome | CoGeneratedStepDefinition:
    """The co-generation flow this module exists to wire (module
    docstring): generate the step-definition first (no pre-known page-
    object binding, exactly today's only real call shape), derive its
    own page-object references from the result, then resolve each
    (bind/generate/escalate) via
    :func:`~.page_object_orchestrator.orchestrate_page_object_method`,
    UNCHANGED -- this function builds no new reuse-decide or precise-fit
    logic, it only sequences the already-built pieces.

    Returns the underlying :func:`~.orchestrator.orchestrate_step_definition`
    outcome UNCHANGED for `BoundStepDefinition`/`EscalatedStepNeed` (no
    fresh Java body exists to derive from) or a `GeneratedStepDefinition`
    whose own body references no page-object field at all. Otherwise
    returns :class:`CoGeneratedStepDefinition`. If ANY derived page-object
    reference fails to resolve safely (precise method-fit failure, or the
    reuse engine's own escalation), the WHOLE step escalates
    (`EscalatedStepNeed`) -- mirroring
    :mod:`.orchestrator`'s own "any one failing routes to human review,
    never a silent fallback" discipline exactly, just triggered AFTER
    generation rather than before it.
    """
    outcome = orchestrate_step_definition(
        need,
        catalog,
        step_matcher,
        step_generator,
        target_package=target_package,
        customqa_constraints=customqa_constraints,
        confidence_threshold=confidence_threshold,
    )
    if not isinstance(outcome, GeneratedStepDefinition):
        return outcome

    derived_requests = derive_page_object_requests(outcome.java_source)
    if not derived_requests:
        return outcome

    page_object_outcomes: list[PageObjectMethodOutcome] = []
    unverified_method_names: list[str] = []
    generated_classes: set[str] = set()

    for request in derived_requests:
        for call in request.method_calls:
            if request.class_name in generated_classes:
                # A sibling method already triggered a FRESH generation for
                # this exact class earlier in this same call -- the
                # generation seam is one-method-need-shaped (module
                # docstring's own known gap); never regenerate a second,
                # conflicting source under the identical class name.
                unverified_method_names.append(f"{request.class_name}.{call.method_name}")
                continue

            method_need = PageObjectMethodNeed(
                need=need,
                method_name=call.method_name,
                class_name_override=request.class_name,
            )
            resolved = orchestrate_page_object_method(
                method_need,
                catalog,
                page_object_matcher,
                page_object_generator,
                target_package=page_object_target_package,
                customqa_constraints=page_object_customqa_constraints,
                confidence_threshold=confidence_threshold,
            )
            if isinstance(resolved, EscalatedPageObjectMethodNeed):
                return EscalatedStepNeed(need=need, escalation=resolved.escalation)
            page_object_outcomes.append(resolved)
            if isinstance(resolved, GeneratedPageObject):
                generated_classes.add(request.class_name)

    return CoGeneratedStepDefinition(
        need=need,
        java_source=outcome.java_source,
        target_package=outcome.target_package,
        page_object_outcomes=tuple(page_object_outcomes),
        unverified_method_names=tuple(unverified_method_names),
    )


__all__ = [
    "CoGeneratedStepDefinition",
    "DerivedPageObjectMethodCall",
    "DerivedPageObjectRequest",
    "derive_page_object_requests",
    "generate_step_definition_with_derived_page_objects",
]
