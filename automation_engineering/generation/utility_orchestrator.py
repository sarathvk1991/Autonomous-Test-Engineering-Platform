"""Reuse-first utility orchestration (ADR-0044 D3/D5) PLUS the precise
method-fit discharge (ADR-0044 D4's clarification note) -- this build's own
Part 1 and Part 2, mirroring :mod:`.page_object_orchestrator` exactly.

THE UTILITY METHOD-FIT QUESTION -- investigated, not assumed
------------------------------------------------------------------
ADR-0044 D4's clarification note states check (c)'s METHOD-FIT realization
for "**Page objects / utilities**" in one paragraph, treating both asset
kinds identically in its own text -- no utility-specific carve-out anywhere
in D4. The page-object build's own discharge note repeated that framing
verbatim: utilities remained "that build's own, still-open,
honestly-carried-forward scope." Neither of those, by itself, proves the
PRECISE half is actually NEEDED for utilities -- it only proves the ADR's
text does not distinguish them. Whether the precise gap is a REAL risk
depends on how utilities are actually invoked, which this build examined
directly rather than accepting "identical treatment" as a foregone
conclusion:

* Page objects accumulate a GROWING, VARIED method surface as features add
  UI actions (`open`, `login`, `clickForgotPasswordLink`, ...) -- the
  precise gap is real because a reused class plausibly has SOME compatible
  method that is not the RIGHT one.
* This platform's own catalog scanner
  (`automation_engineering/catalog/scanner.py`) classifies ANY class that
  does not extend `BasePage` and carries no Cucumber step annotations as a
  `UtilityAsset` -- a broad catch-all, not a narrow, fixed shape by
  construction.
* The ONE real utility class this platform has ever committed,
  `test-suite-baseline/src/test/java/com/automation/base/ConfigReader.java`,
  makes the risk sharper than for page objects, not weaker: its two public
  methods, `env(String)` and `data(String)`, are DIFFERENT, semantically
  distinct accessors (SUT-binding vs. test-data, ADR-0037 D3's own
  boundary) that share an IDENTICAL parameter shape (`String -> String`).
  A coarse arity/type screen CANNOT distinguish them at all -- a step
  needing `ConfigReader.data("username")` reused against a candidate whose
  only relevantly-shaped method is `env` would pass the coarse screen (a
  compatible-shaped method genuinely exists) and bind to the WRONG
  accessor, reading an environment value where a test-data value was
  needed. This is not a contrived edge case; it is the natural consequence
  of a utility class exposing several same-shaped, different-meaning
  accessors, a pattern this platform's own real utility class already
  demonstrates.

**Finding: utilities DO need the precise method-fit discharge, for the same
structural reason page objects did, and the risk is at least as concrete.**
This module therefore reuses
:func:`automation_engineering.generation.method_fit.verify_specific_method_fit`
UNCHANGED -- it was already written generically over ``PageObjectAsset |
UtilityAsset`` for exactly this reason (that function's own module
docstring) -- wired into the TRUSTED_REUSE branch below the same way
:mod:`.page_object_orchestrator` wires it for page objects. No new
discharge LOGIC exists in this module; only the orchestration around it.

Generation (Part 1), mirroring :mod:`.page_object_orchestrator` exactly
----------------------------------------------------------------------------
* ``NoMatch`` -> GENERATE. The utility generation seam
  (:mod:`.utility_generator`) is called, customqa:*-constrained.
* ``TrustedReuse`` -> the COARSE screen already passed; the PRECISE check
  (above) verifies the SPECIFIC method. Present and fitting -> BIND (never
  regenerate). Absent or wrong shape -> ESCALATE.
* ``Escalation`` -> SURFACE, unedited.

This module never imports ``llm_factory`` or any LLM provider, and never
imports a live embedding provider.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from automation_engineering.catalog.models import AssetCatalog, PageObjectAsset, UtilityAsset
from automation_engineering.generation.method_fit import verify_specific_method_fit
from automation_engineering.generation.models import (
    BoundUtilityMethod,
    EscalatedUtilityMethodNeed,
    GeneratedUtility,
    UtilityMethodNeed,
    UtilityMethodOutcome,
)
from automation_engineering.generation.utility_generator import (
    UtilityGenerationContext,
    UtilityGenerator,
)
from automation_engineering.reuse.engine import DEFAULT_CONFIDENCE_THRESHOLD, decide_reuse
from automation_engineering.reuse.matcher import SemanticMatcher
from automation_engineering.reuse.models import Escalation, NoMatch, TrustedReuse

#: The tracked test-suite-baseline's own utility package -- referenced
#: consistently across ADR-0037/ADR-0041/ADR-0043 D7/ADR-0044 D7 and the
#: already-registered `generate-test-data` prompt (`docs/reference/
#: automation-poc/prompts/generate-test-data.md`), even though no COMMITTED
#: utility class lives there yet (the real `ConfigReader` lives at
#: `com.automation.base` today) -- this is the one convention every part of
#: this platform that mentions a Layer 3 utility package agrees on.
DEFAULT_UTILITY_TARGET_PACKAGE = "com.automation.utils"

#: ADR-0044 D5's "constrain at generation" -- ONLY `customqa:long-method` is
#: evidenced as applicable to utilities (`requirement_intelligence/input/
#: sonar/sonar-issues.json`, the same fixture the step-def/page-object
#: constraints cite). `customqa:direct-webdriver-action`'s own evidenced
#: target (`BadCheckoutPage.java`) and message ("route through the BasePage
#: action helpers") are page-object-specific; nothing ties it to a
#: non-page-object class, so it is NOT injected here as a customqa:* rule.
#: The plain architectural fact that a utility must not touch WebDriver at
#: all is stated below as a structural constraint, not dressed up as a
#: customqa:* rule this platform never evidenced against a utility file.
DEFAULT_CUSTOMQA_UTILITY_CONSTRAINTS: tuple[str, ...] = (
    "customqa:long-method -- keep every generated method under 40 lines; "
    "split a multi-step computation into smaller, composable methods.",
)

_STOPWORDS = frozenset({"a", "an", "the", "to", "on", "in", "of", "with", "for", "by"})
_LEADING_VERBS = frozenset(
    {"read", "format", "compute", "generate", "parse", "convert", "build", "get", "select"}
)
_WORD_RE = re.compile(r"[A-Za-z0-9']+")


def derive_utility_class_name(action_text: str) -> str:
    """Deterministic UpperCamelCase derivation from a utility action's own
    description -- unlike :func:`~.page_object_orchestrator.derive_page_object_class_name`,
    no fixed suffix is appended: the one real utility class this platform
    has ever committed, `ConfigReader`, carries no "Util"/"Utils" suffix
    convention, so inventing one here would not be following an evidenced
    convention, it would be fabricating one.

    INFORMATIONAL only for a freshly generated utility: handed to the
    generation seam as an instruction, never re-parsed out of the generated
    Java to confirm the model actually used it -- the same trust level
    :func:`~.page_object_orchestrator.derive_page_object_class_name` places
    in its own naming convention.
    """
    words = [w for w in _WORD_RE.findall(action_text) if w.lower() not in _STOPWORDS]
    if words and words[0].lower() in _LEADING_VERBS:
        stripped = words[1:]
        words = stripped if stripped else words
    return "".join(word.capitalize() for word in words)


@dataclass(frozen=True, slots=True)
class UtilityBindingRequest:
    """Everything the step-def orchestrator (:mod:`.orchestrator`) needs to
    resolve ONE step's required utility call: reuse-decide it, precisely
    verify a trusted reuse's specific method, or generate a brand-new
    utility if none reuses. Mirrors
    :class:`~.page_object_orchestrator.PageObjectBindingRequest` exactly.
    """

    method_need: UtilityMethodNeed
    matcher: SemanticMatcher
    generator: UtilityGenerator
    target_package: str = DEFAULT_UTILITY_TARGET_PACKAGE
    customqa_constraints: tuple[str, ...] = DEFAULT_CUSTOMQA_UTILITY_CONSTRAINTS


def orchestrate_utility_method(
    method_need: UtilityMethodNeed,
    catalog: AssetCatalog,
    matcher: SemanticMatcher,
    generator: UtilityGenerator,
    *,
    target_package: str = DEFAULT_UTILITY_TARGET_PACKAGE,
    customqa_constraints: tuple[str, ...] = DEFAULT_CUSTOMQA_UTILITY_CONSTRAINTS,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> UtilityMethodOutcome:
    """Reuse-first orchestration for exactly one utility method-need, with
    the precise method-fit discharge (Part 2) wired directly into the
    TRUSTED_REUSE branch -- mirrors
    :func:`~.page_object_orchestrator.orchestrate_page_object_method`
    exactly (see module docstring for why utilities need this too).
    """
    decision = decide_reuse(
        method_need.need, catalog, matcher, confidence_threshold=confidence_threshold
    )

    if isinstance(decision, TrustedReuse):
        if not isinstance(decision.asset, (PageObjectAsset, UtilityAsset)):
            # Cannot happen given this function's own matcher contract (it
            # only ever resolves a utility need against catalog.utilities)
            # -- narrows the type for verify_specific_method_fit's own
            # signature and fails loudly if that invariant is ever broken.
            raise TypeError(
                f"orchestrate_utility_method resolved a TrustedReuse against "
                f"a {type(decision.asset).__name__}, not a page object/utility -- "
                "the matcher passed in must only ever search catalog.utilities."
            )
        method_fit_escalation = verify_specific_method_fit(
            method_need.need, decision.asset, decision.candidate, method_need.method_name
        )
        if method_fit_escalation is not None:
            return EscalatedUtilityMethodNeed(
                method_need=method_need, escalation=method_fit_escalation
            )
        return BoundUtilityMethod(method_need=method_need, asset=decision.asset)

    if isinstance(decision, Escalation):
        return EscalatedUtilityMethodNeed(method_need=method_need, escalation=decision)

    if isinstance(decision, NoMatch):
        class_name = derive_utility_class_name(method_need.need.text)
        context = UtilityGenerationContext(
            need=method_need.need,
            class_name=class_name,
            target_package=target_package,
            customqa_constraints=customqa_constraints,
        )
        java_source = generator.generate(context)
        return GeneratedUtility(
            method_need=method_need,
            java_source=java_source,
            target_package=target_package,
            class_name=class_name,
        )

    raise AssertionError(f"unreachable: unknown ReuseDecision variant {decision!r}")


def generate_utility_methods(
    method_needs: Sequence[UtilityMethodNeed],
    catalog: AssetCatalog,
    matcher: SemanticMatcher,
    generator: UtilityGenerator,
    *,
    target_package: str = DEFAULT_UTILITY_TARGET_PACKAGE,
    customqa_constraints: tuple[str, ...] = DEFAULT_CUSTOMQA_UTILITY_CONSTRAINTS,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> tuple[UtilityMethodOutcome, ...]:
    """Reuse-first orchestration for a full set of utility method-needs --
    one :func:`orchestrate_utility_method` call per need, in order."""
    return tuple(
        orchestrate_utility_method(
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
    "DEFAULT_CUSTOMQA_UTILITY_CONSTRAINTS",
    "DEFAULT_UTILITY_TARGET_PACKAGE",
    "UtilityBindingRequest",
    "derive_utility_class_name",
    "generate_utility_methods",
    "orchestrate_utility_method",
]
