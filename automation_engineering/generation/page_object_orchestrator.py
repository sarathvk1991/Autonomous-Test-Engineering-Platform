"""Reuse-first page-object orchestration (ADR-0044 D3/D5, this build's own
Part 1) PLUS the precise method-fit discharge (ADR-0044 D4's clarification
note, this build's own Part 2).

For each page-object need a step definition requires a binding for, this
module consults the reuse engine's own decision
(:func:`automation_engineering.reuse.engine.decide_reuse`) and acts on
exactly it, mirroring :mod:`.orchestrator`'s own step-definition discipline:

* ``NoMatch`` -> GENERATE. The page-object generation seam
  (:mod:`.page_object_generator`) is called, with the platform's own
  ``customqa:*`` constraints (ADR-0044 D5) injected into the seam's own
  input -- born compliant. Note the constraints CONSTRAIN HOW WebDriver is
  used here, not WHETHER: unlike step definitions, page objects are exactly
  where ``customqa:direct-webdriver-action`` says WebDriver calls belong.
* ``TrustedReuse`` -> the COARSE class-compatibility screen already passed
  (`automation_engineering.reuse.engine._check_method_fit`). This is where
  Part 2 fires: :func:`~automation_engineering.generation.method_fit.verify_specific_method_fit`
  checks the SPECIFIC method the need names (:class:`~.models.PageObjectMethodNeed.method_name`)
  against the reused class's real inventory (`TrustedReuse.asset.methods`).
  Present with a fitting shape -> BIND (never regenerate; proven by the
  same spy discipline :class:`~.page_object_generator.StubPageObjectGenerator`
  exposes). Absent, or present with the wrong shape -> ESCALATE -- the exact
  gap ADR-0044 D4's clarification note recorded as this build's own
  obligation, now closed.
* ``Escalation`` -> SURFACE. Neither generated nor bound -- the reuse
  engine's own :class:`~automation_engineering.reuse.models.Escalation`
  record is carried through unedited.

This module never imports ``llm_factory`` or any LLM provider -- it depends
only on the :class:`~.page_object_generator.PageObjectGenerator` Protocol.
It also never imports a live embedding provider -- it depends only on
:class:`~automation_engineering.reuse.matcher.SemanticMatcher`.

**Multi-method-per-class (additive, this build).** :func:`orchestrate_page_object_method`
above stays exactly as it always was -- one method-need in, one seam call
(at most) out. :func:`orchestrate_page_object_class`, added by this build,
resolves every method-need destined for the SAME class together: each is
still reuse-decided independently (so a class can end up with some methods
bound and others generated), but every NO_MATCH method-need is batched into
ONE generation call, closing the gap
:mod:`.page_object_reference_derivation` flagged (a second-or-later fresh
method on the same class silently going unresolved,
``CoGeneratedStepDefinition.unverified_method_names``).

Scope: page objects only, not utilities
------------------------------------------
:mod:`.method_fit`'s own :func:`~.method_fit.verify_specific_method_fit` is
written generically against ``PageObjectAsset | UtilityAsset`` (mirroring
the reuse engine's own asset-type-agnostic coarse screen), but every
orchestration function in THIS module only ever resolves a need against
``catalog.page_objects`` -- never ``catalog.utilities``. Utilities remain
this build's own carried-forward obligation, the same honest deferral
pattern the step-definition task used for page objects before this build
existed to discharge it: not faked, not silently approved, simply not
reached.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from automation_engineering.catalog.models import AssetCatalog, PageObjectAsset, UtilityAsset
from automation_engineering.generation.method_fit import verify_specific_method_fit
from automation_engineering.generation.models import (
    BoundPageObjectMethod,
    EscalatedPageObjectMethodNeed,
    GeneratedPageObject,
    PageObjectMethodNeed,
    PageObjectMethodOutcome,
)
from automation_engineering.generation.page_object_generator import (
    PageObjectGenerationContext,
    PageObjectGenerator,
)
from automation_engineering.reuse.engine import DEFAULT_CONFIDENCE_THRESHOLD, decide_reuse
from automation_engineering.reuse.matcher import SemanticMatcher
from automation_engineering.reuse.models import Escalation, NoMatch, TrustedReuse

#: The tracked test-suite-baseline's own page-object package
#: (`test-suite-baseline/src/test/java/com/automation/pages/SmokePage.java`).
DEFAULT_PAGE_OBJECT_TARGET_PACKAGE = "com.automation.pages"

#: ADR-0044 D5's "constrain at generation" -- the `customqa:*` SonarQube
#: quality-profile rules that are PAGE-OBJECT constraints specifically,
#: evidenced directly in this platform's own real SonarQube fixture data
#: (`requirement_intelligence/input/sonar/sonar-issues.json`, the same
#: evidence ADR-0037 D1 and the step-def orchestrator's own constraints
#: cite): `customqa:direct-webdriver-action` and `customqa:long-method` --
#: the SAME two rules the step-def orchestrator injects, but constraining
#: the OPPOSITE thing: for a step definition the rule prohibits WebDriver
#: calls outright; for a page object it constrains how those calls are
#: made (through this class, constructor-injected driver, no static/self-
#: constructed WebDriver -- ADR-0041 D5), since this is exactly where they
#: legitimately belong.
DEFAULT_CUSTOMQA_PAGE_OBJECT_CONSTRAINTS: tuple[str, ...] = (
    "customqa:direct-webdriver-action -- page objects are where WebDriver "
    "calls legitimately live; every locator interaction must be made from "
    "inside this class (via the inherited BasePage helpers or a direct "
    "WebDriver call here), never delegated back out to a step definition.",
    "customqa:long-method -- keep every generated method under 40 lines; "
    "split a multi-step page flow into smaller, composable methods.",
)

_STOPWORDS = frozenset({"a", "an", "the", "to", "on", "in", "of", "with", "for"})
_LEADING_VERBS = frozenset(
    {"click", "enter", "select", "open", "navigate", "verify", "check", "type", "submit"}
)
_WORD_RE = re.compile(r"[A-Za-z0-9']+")


def derive_page_object_class_name(action_text: str) -> str:
    """Deterministic UpperCamelCase + ``Page`` derivation from a page-object
    action's own description -- mirrors the tracked baseline's own naming
    convention (``LoginPage``, ``SmokePage``) and the ``generate_page_objects``
    prompt's own OUTPUT CONTRACT instruction to use the name verbatim.

    INFORMATIONAL only for a freshly generated page object: this name is
    handed to the generation seam as an instruction, never re-parsed out of
    the generated Java to confirm the model actually used it -- the same
    trust level the step-definition generator already places in its own
    method-naming convention (ADR-0044 D2's own scope: this build performs
    no parsing or compilation of generated code; CP3/CP4 verify it, a
    later, out-of-scope task).
    """
    words = [w for w in _WORD_RE.findall(action_text) if w.lower() not in _STOPWORDS]
    if words and words[0].lower() in _LEADING_VERBS:
        stripped = words[1:]
        words = stripped if stripped else words
    class_name = "".join(word.capitalize() for word in words)
    if not class_name.endswith("Page"):
        class_name += "Page"
    return class_name


@dataclass(frozen=True, slots=True)
class PageObjectBindingRequest:
    """Everything the step-def orchestrator (:mod:`.orchestrator`) needs to
    resolve ONE step's required page-object call: reuse-decide it,
    precisely verify a trusted reuse's specific method, or generate a
    brand-new page object if none reuses. A single optional parameter on
    that orchestrator's own functions, carrying the page-object-side seam
    and matcher so the step-def orchestrator's own signature stays a single
    new parameter rather than four.
    """

    method_need: PageObjectMethodNeed
    matcher: SemanticMatcher
    generator: PageObjectGenerator
    target_package: str = DEFAULT_PAGE_OBJECT_TARGET_PACKAGE
    customqa_constraints: tuple[str, ...] = DEFAULT_CUSTOMQA_PAGE_OBJECT_CONSTRAINTS


def orchestrate_page_object_method(
    method_need: PageObjectMethodNeed,
    catalog: AssetCatalog,
    matcher: SemanticMatcher,
    generator: PageObjectGenerator,
    *,
    target_package: str = DEFAULT_PAGE_OBJECT_TARGET_PACKAGE,
    customqa_constraints: tuple[str, ...] = DEFAULT_CUSTOMQA_PAGE_OBJECT_CONSTRAINTS,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> PageObjectMethodOutcome:
    """Reuse-first orchestration for exactly one page-object method-need,
    with the precise method-fit discharge (Part 2) wired directly into the
    TRUSTED_REUSE branch.

    Consults :func:`~automation_engineering.reuse.engine.decide_reuse` once
    -- the SAME engine the step-def orchestrator uses, unmodified, proving
    D3's own catalog and reuse-first discipline really is asset-type-
    agnostic exactly as ADR-0044 D4's clarification note says. Deterministic
    given deterministic ``matcher``/``generator`` implementations; the only
    nondeterministic calls (a live semantic match, a live generation) live
    entirely behind those two seams, never in this function.

    A fresh (NO_MATCH) generation uses ``method_need.class_name_override``
    when supplied, in preference to :func:`derive_page_object_class_name`'s
    own independent guess (:class:`~.models.PageObjectMethodNeed`'s own
    docstring) -- the seam
    :mod:`.page_object_reference_derivation` uses to keep a freshly
    generated page object's class name consistent with whatever an
    already-generated step-definition's own body already references.

    The generation context's own ``method_name`` is set from
    ``method_need.method_name`` (additive, this fix) -- the derived,
    caller-supplied name the seam must convey to the generator so the
    generated method is declared under the SAME name a step-def's own call
    site actually uses, never a name the generator invents independently
    from ``need.text`` (the live defect this closes:
    :class:`~automation_engineering.generation.live_page_object_generator.LivePageObjectGenerator`
    requires ``context.method_name``, exactly because a name the model
    invents from prose almost never matches the name a real call site
    needs).
    """
    decision = decide_reuse(
        method_need.need, catalog, matcher, confidence_threshold=confidence_threshold
    )

    if isinstance(decision, TrustedReuse):
        if not isinstance(decision.asset, (PageObjectAsset, UtilityAsset)):
            # Cannot happen given this function's own matcher contract (it
            # only ever resolves a page-object need against
            # `catalog.page_objects`, the same guarantee the step-def
            # orchestrator's own module docstring documents for its own
            # matcher/`catalog.step_definitions` pairing) -- narrows the
            # type for `verify_specific_method_fit`'s own signature and
            # fails loudly, not silently, if that invariant is ever broken.
            raise TypeError(
                f"orchestrate_page_object_method resolved a TrustedReuse against "
                f"a {type(decision.asset).__name__}, not a page object/utility -- "
                "the matcher passed in must only ever search catalog.page_objects."
            )
        method_fit_escalation = verify_specific_method_fit(
            method_need.need, decision.asset, decision.candidate, method_need.method_name
        )
        if method_fit_escalation is not None:
            return EscalatedPageObjectMethodNeed(
                method_need=method_need, escalation=method_fit_escalation
            )
        return BoundPageObjectMethod(method_need=method_need, asset=decision.asset)

    if isinstance(decision, Escalation):
        return EscalatedPageObjectMethodNeed(method_need=method_need, escalation=decision)

    if isinstance(decision, NoMatch):
        class_name = method_need.class_name_override or derive_page_object_class_name(
            method_need.need.text
        )
        context = PageObjectGenerationContext(
            need=method_need.need,
            class_name=class_name,
            target_package=target_package,
            customqa_constraints=customqa_constraints,
            method_name=method_need.method_name,
        )
        java_source = generator.generate(context)
        return GeneratedPageObject(
            method_need=method_need,
            java_source=java_source,
            target_package=target_package,
            class_name=class_name,
        )

    raise AssertionError(f"unreachable: unknown ReuseDecision variant {decision!r}")


def orchestrate_page_object_class(
    method_needs: Sequence[PageObjectMethodNeed],
    catalog: AssetCatalog,
    matcher: SemanticMatcher,
    generator: PageObjectGenerator,
    *,
    target_package: str = DEFAULT_PAGE_OBJECT_TARGET_PACKAGE,
    customqa_constraints: tuple[str, ...] = DEFAULT_CUSTOMQA_PAGE_OBJECT_CONSTRAINTS,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> tuple[PageObjectMethodOutcome, ...]:
    """Reuse-first orchestration for every method-need destined for ONE
    page-object class -- the multi-method extension this build closes.

    Each ``method_need`` is still reuse-decided INDEPENDENTLY, exactly as
    :func:`orchestrate_page_object_method` already does (its own TRUSTED_REUSE
    precise-fit discharge and ESCALATION handling are mirrored here
    unchanged, not re-derived) -- a class can legitimately end up with SOME
    methods bound to an existing reused asset and OTHERS freshly generated,
    when different method-needs' own ``need.text`` resolve differently
    against the catalog. What changes is the NO_MATCH side only: every
    method-need this function finds NO_MATCH is collected, never generated
    one-at-a-time, and generated in exactly ONE seam call once every
    method-need has been reuse-decided -- so a class needing two-or-more
    fresh methods gets ONE class with ALL of them
    (:class:`~.page_object_generator.PageObjectGenerationContext`'s own new
    ``additional_method_needs`` field carries the siblings, and its
    ``method_name`` field carries the PRIMARY's own caller-chosen name --
    every method in the batch is caller-named, none left for a generator to
    invent), never a second, conflicting source under the same class name
    and never a silently dropped method. The single resulting
    :class:`~.models.GeneratedPageObject` carries every NO_MATCH method-need
    it satisfies (`method_need` for the first, `additional_method_needs` for
    the rest).

    Returns one outcome per DISTINCT resolution -- one
    :class:`~.models.BoundPageObjectMethod`/:class:`~.models.EscalatedPageObjectMethodNeed`
    per bound/escalated method-need (in ``method_needs``' own order among
    themselves), followed by at most one :class:`~.models.GeneratedPageObject`
    for the whole NO_MATCH batch, if any -- so the returned tuple's length
    can be SMALLER than ``len(method_needs)`` whenever two or more methods
    batch into one generated class; this is the point of the fix, not a
    dropped result, since every input method-need is still accounted for by
    exactly one outcome (directly, or via that outcome's own
    ``additional_method_needs``). ``method_needs=[]`` returns ``()``.

    Every NO_MATCH method-need in one call must agree on
    ``class_name_override`` (``None`` counts as agreeing with other
    ``None``s) -- they are, by construction, destined for the SAME class;
    raises :class:`ValueError` rather than silently picking one if they
    disagree, the same "never a silent fallback" discipline ADR-0044 D4
    states for the reuse-safety checks themselves.

    :func:`orchestrate_page_object_method`/:func:`generate_page_object_methods`
    are UNCHANGED by this addition -- neither is called by this function,
    and neither gains new behavior; this is a new, additive entry point for
    the one-class-many-methods shape, used by
    :mod:`.page_object_reference_derivation`'s own wiring.
    """
    resolved: list[PageObjectMethodOutcome] = []
    pending_generation: list[PageObjectMethodNeed] = []

    for method_need in method_needs:
        decision = decide_reuse(
            method_need.need, catalog, matcher, confidence_threshold=confidence_threshold
        )

        if isinstance(decision, TrustedReuse):
            if not isinstance(decision.asset, (PageObjectAsset, UtilityAsset)):
                # Mirrors `orchestrate_page_object_method`'s own guard --
                # cannot happen given this function's own matcher contract.
                raise TypeError(
                    f"orchestrate_page_object_class resolved a TrustedReuse against "
                    f"a {type(decision.asset).__name__}, not a page object/utility -- "
                    "the matcher passed in must only ever search catalog.page_objects."
                )
            method_fit_escalation = verify_specific_method_fit(
                method_need.need, decision.asset, decision.candidate, method_need.method_name
            )
            if method_fit_escalation is not None:
                resolved.append(
                    EscalatedPageObjectMethodNeed(
                        method_need=method_need, escalation=method_fit_escalation
                    )
                )
            else:
                resolved.append(
                    BoundPageObjectMethod(method_need=method_need, asset=decision.asset)
                )
            continue

        if isinstance(decision, Escalation):
            resolved.append(
                EscalatedPageObjectMethodNeed(method_need=method_need, escalation=decision)
            )
            continue

        if isinstance(decision, NoMatch):
            pending_generation.append(method_need)
            continue

        raise AssertionError(f"unreachable: unknown ReuseDecision variant {decision!r}")

    if pending_generation:
        overrides = {need.class_name_override for need in pending_generation}
        if len(overrides) > 1:
            raise ValueError(
                "orchestrate_page_object_class: NO_MATCH method-needs disagree on "
                f"class_name_override {sorted(o for o in overrides if o is not None)!r} -- "
                "every method-need destined for the same class must share the same "
                "override (or all omit it)."
            )
        primary, *rest = pending_generation
        class_name = primary.class_name_override or derive_page_object_class_name(
            primary.need.text
        )
        context = PageObjectGenerationContext(
            need=primary.need,
            class_name=class_name,
            target_package=target_package,
            customqa_constraints=customqa_constraints,
            additional_method_needs=tuple(rest),
            method_name=primary.method_name,
        )
        java_source = generator.generate(context)
        resolved.append(
            GeneratedPageObject(
                method_need=primary,
                java_source=java_source,
                target_package=target_package,
                class_name=class_name,
                additional_method_needs=tuple(rest),
            )
        )

    return tuple(resolved)


def generate_page_object_methods(
    method_needs: Sequence[PageObjectMethodNeed],
    catalog: AssetCatalog,
    matcher: SemanticMatcher,
    generator: PageObjectGenerator,
    *,
    target_package: str = DEFAULT_PAGE_OBJECT_TARGET_PACKAGE,
    customqa_constraints: tuple[str, ...] = DEFAULT_CUSTOMQA_PAGE_OBJECT_CONSTRAINTS,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> tuple[PageObjectMethodOutcome, ...]:
    """Reuse-first orchestration for a full set of page-object method-needs
    -- one :func:`orchestrate_page_object_method` call per need, in order."""
    return tuple(
        orchestrate_page_object_method(
            need,
            catalog,
            matcher,
            generator,
            target_package=target_package,
            customqa_constraints=customqa_constraints,
            confidence_threshold=confidence_threshold,
        )
        for need in method_needs
    )


__all__ = [
    "DEFAULT_CUSTOMQA_PAGE_OBJECT_CONSTRAINTS",
    "DEFAULT_PAGE_OBJECT_TARGET_PACKAGE",
    "PageObjectBindingRequest",
    "derive_page_object_class_name",
    "generate_page_object_methods",
    "orchestrate_page_object_class",
    "orchestrate_page_object_method",
]
