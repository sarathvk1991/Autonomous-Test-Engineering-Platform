"""THE PRECISE HALF of ADR-0044 D4(c)'s method-fit check for page objects --
the obligation the reuse engine's own coarse screen
(`automation_engineering.reuse.engine._check_method_fit`) and its
`TrustedReuse` docstring recorded as belonging here, not there. Discharged
by this module.

ADR-0044 D4's own clarification note (2026-07-30), quoted in full because
this module exists to be exactly what it describes:

    "At reuse-decision time, the engine can only run a COARSE
    class-compatibility screen: does the catalogued class provide *some*
    method whose parameter shape (arity, per-position type) could accept
    the call -- escalating only on gross incompatibility [...]. This screen
    structurally CANNOT detect a class that has some shape-compatible
    method but not the SPECIFIC one the binding actually needs (e.g. a
    LoginPage reused for a step needing clickForgotPasswordLink(), where
    LoginPage merely happens to have some other zero-arg method) -- which
    specific method a not-yet-written step definition will call is not
    knowable until a future generator actually writes that call. THE
    PRECISE CHECK IS THEREFORE THE GENERATOR'S OWN OBLIGATION, NOT THIS
    ENGINE'S: before binding a step to a reused page-object/utility method,
    the generator that eventually implements Layer 3's generation step must
    verify the specific method it is about to call is actually present, and
    escalate/regenerate if it is not. The reuse engine's TrustedReuse
    outcome carries the full method inventory (names included) precisely so
    that future check has what it needs; it does not perform that check
    itself."

What this module has, per that note's own accounting
------------------------------------------------------
Exactly the two things the note says the future generator would have:
the reused page object's full method inventory
(`TrustedReuse.asset.methods`, unedited, handed straight through by
:mod:`automation_engineering.generation.page_object_orchestrator`) and the
SPECIFIC method name a step-def call site is about to use
(:class:`~automation_engineering.generation.models.PageObjectMethodNeed.method_name`,
caller-supplied -- see that class's own docstring for why it is never
derived here).

Scope, stated precisely
-------------------------
This module discharges the obligation for **page objects only** -- the
scope this build's own task explicitly names. The note itself phrases the
obligation as "page-object/utility method," since the reuse engine's own
coarse screen (`_check_method_fit`) is asset-type-agnostic and already
treats `UtilityAsset` identically to `PageObjectAsset`
(`automation_engineering/reuse/engine.py`'s own docstring: "Utilities get
the SAME coarse screen as page objects, not a weaker one"). This module's
own :func:`verify_specific_method_fit` is written against that SAME
type union (`PageObjectAsset | UtilityAsset`) for exactly that reason --
so it is not accidentally page-object-shaped in a way a future utilities
task would have to rewrite -- but no orchestration in this build ever
calls it with a `UtilityAsset`: utilities remain the next task's own scope
boundary (`automation_engineering.generation.page_object_orchestrator`'s
own module docstring), carried forward the same honest way the step-def
task carried this exact obligation forward before this build discharged it.
"""

from __future__ import annotations

from automation_engineering.catalog.models import JavaParameter, PageObjectAsset, UtilityAsset
from automation_engineering.reuse.engine import method_shape_fits
from automation_engineering.reuse.models import (
    Escalation,
    EscalationCheck,
    GherkinStepNeed,
    MatchCandidate,
)


def verify_specific_method_fit(
    need: GherkinStepNeed,
    asset: PageObjectAsset | UtilityAsset,
    candidate: MatchCandidate,
    method_name: str,
    *,
    parameters: tuple[JavaParameter, ...] | None = None,
) -> Escalation | None:
    """The PRECISE check ADR-0044 D4's clarification note assigns to "the
    generator that eventually implements Layer 3's generation step" --
    this module, called from
    :func:`automation_engineering.generation.page_object_orchestrator.orchestrate_page_object_method`
    immediately after the reuse engine returns a `TrustedReuse` (i.e. the
    COARSE screen already passed).

    ``parameters`` (additive, the captures-arity fix's BIND-side mirror of
    the GENERATE-side fix already shipped in
    :class:`~automation_engineering.generation.models.PageObjectMethodNeed`)
    is the EXACT argument count the step-def call site actually passes to
    this method -- derived, when available, by
    :mod:`.page_object_reference_derivation` from an ALREADY-GENERATED
    step-definition's own call-site arguments, the SAME value the GENERATE
    path already uses in preference to ``need.captures`` (see that model's
    own docstring for the live, compile-breaking counterexample this
    exists to prevent: a captured value routed into an assertion rather
    than passed to the page-object call, so the call site takes FEWER
    arguments than the step's own text captures). When supplied (not
    ``None``), the fit check compares the candidate method's own arity
    against ``len(parameters)`` -- the call site's real requirement --
    instead of ``len(need.captures)``. ``None`` (the default) preserves
    the PRIOR, sole behavior exactly: fall back to
    :func:`~automation_engineering.reuse.engine.method_shape_fits` against
    ``need.captures`` (arity plus per-position type compatibility) --
    unconstrained by call-site arity, exactly as before this parameter
    existed. This is an ARITY-only upgrade when ``parameters`` is supplied
    (a straight ``len(...)`` comparison, not a second type-shape check
    against ``JavaParameter`` values) -- the same scope the GENERATE-side
    fix shipped, deliberately not broadened here.

    Returns ``None`` when ``method_name`` is present on ``asset.methods``
    AND that method fits (per the rule above) -- the binding is now fully
    verified (coarse + precise, D4(c) complete). Returns an
    :class:`Escalation` (``check=EscalationCheck.METHOD_FIT``, reusing the
    SAME check identity the coarse screen itself uses -- this is check (c)
    closing its own remaining gap, not a new, fourth check) when
    ``method_name`` is absent from ``asset.methods`` entirely, or present
    with an incompatible shape.

    ``candidate`` is threaded through unedited from the `TrustedReuse` this
    check follows -- the same discipline every other escalation in
    :mod:`automation_engineering.reuse.engine` already uses: the failing
    candidate travels with its own escalation so a human reviewer never has
    to re-run the match to see what was actually considered.
    """
    matching_methods = tuple(method for method in asset.methods if method.name == method_name)

    if not matching_methods:
        return Escalation(
            need=need,
            check=EscalationCheck.METHOD_FIT,
            candidate=candidate,
            detail=(
                f"asset_id={candidate.asset_id!r} ({type(asset).__name__}) coarse "
                f"class-compatibility screen passed, but the class has no method "
                f"named {method_name!r} at all -- the SPECIFIC method this binding "
                f"needs is absent; available method(s): "
                f"{tuple(m.name for m in asset.methods)!r}"
            ),
        )

    if parameters is not None:
        required_count = len(parameters)
        fits = any(len(method.parameters) == required_count for method in matching_methods)
        requirement_description = f"{required_count} call-site argument(s)"
    else:
        fits = any(method_shape_fits(method, need.captures) for method in matching_methods)
        requirement_description = f"{len(need.captures)} required capture(s)"

    if not fits:
        return Escalation(
            need=need,
            check=EscalationCheck.METHOD_FIT,
            candidate=candidate,
            detail=(
                f"asset_id={candidate.asset_id!r} ({type(asset).__name__}) has a "
                f"method named {method_name!r}, but its parameter shape does not "
                f"fit the {requirement_description}"
            ),
        )

    return None


__all__ = ["verify_specific_method_fit"]
