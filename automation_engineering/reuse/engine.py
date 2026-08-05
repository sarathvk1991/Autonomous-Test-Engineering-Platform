"""The reuse-safety decision (ADR-0044 D4) -- the single most load-bearing
piece of Layer 3's design, per the ADR's own text: "a wrong reuse binding
produces a test that runs green while testing the wrong behavior, invisible
to every deterministic downstream gate."

This module builds ONLY the decision: given one semantic match (the
:mod:`.matcher` seam's own, only-nondeterministic output), decide whether the
binding is trusted. It does not build generation (a future task consumes
:class:`~automation_engineering.reuse.models.NoMatch`/
:class:`~automation_engineering.reuse.models.Escalation` and acts on them);
it does not build CP3/CP4 or promotion (ADR-0045).

Escalation routing -- no new queue
-----------------------------------
ADR-0044 D4's "escalate to human review" and ADR-0045 D3's "promotion
escalation and reuse escalation are the same review, not two separate ones"
both describe a discipline this platform already has a shape for, not a
literal shared service to call into: every other layer's own escalation is
a plain record -- a boolean plus a reason string, surfaced in that layer's
own report (`feature_engineering.stage.models.FeatureRecord.escalated`/
`.escalation_reason`, rendered by `feature_engineering.stage.report`;
`feature_engineering.remediation.models.RemediationResult.escalation_reason`)
-- explicitly consumed later by "a future human-in-the-loop mechanism...
never built here" (`feature_engineering/remediation/models.py`'s own
docstring). This engine's :class:`~automation_engineering.reuse.models.Escalation`
is that same shape: a structured record carrying everything a human needs
(the failing check, the candidate, the confidence, a detail string) for a
future HITL surface to render -- no separate queue, no new mechanism, built
here.

The three checks, in ADR-0044 D4's own order
---------------------------------------------
(a) confidence >= threshold; (b) content-hash freshness; (c) structural fit.
All three must pass for :class:`TrustedReuse`; any one failing produces an
:class:`Escalation` naming exactly that check -- never a silent fallback to
a different check or a reduced-confidence acceptance (ADR-0044 D4's own "a
match that clears confidence but fails either deterministic check...
escalates, the same outcome as failing (a) outright"). Checks are evaluated
in order and the function returns at the first failure, so a candidate
failing more than one check is still reported against the earliest one --
deterministic, not incidental.

The generate floor -- NO_MATCH made reachable post-bootstrap
--------------------------------------------------------------
`decide_reuse` is not only a two-outcome (trust/escalate) decision below the
top of the catalog -- a third, lower tier (`DEFAULT_GENERATE_FLOOR`) now
sits beneath the three checks above: a best-candidate similarity too low to
be even PLAUSIBLE (not merely untrustworthy) is `NoMatch`, exactly like an
empty catalog, never an `Escalation`. This closes a real gap (additive note,
2026-08-05): `LiveSemanticMatcher.match` returns one candidate per catalog
asset unconditionally (`.matcher`'s/`.live_matcher`'s own module docstrings),
so once a catalog has ever been populated, `NoMatch` was previously
reachable only via an empty catalog -- every need, including a genuinely
novel one with nothing relevant in the catalog, escalated instead of
generating. The floor is calibrated from a live run's real score data (see
`DEFAULT_GENERATE_FLOOR`'s own docstring, above), not guessed. This tier
sits strictly BELOW check (a) -- it narrows what counts as "below
threshold" into "not even plausible" (NO_MATCH) vs. "plausible but
unproven" (ESCALATE); it does not touch checks (a)/(b)/(c)'s own logic once
a candidate clears the floor, and it can never mask a should-have-been-
trusted or should-have-escalated case, since generating is only reachable
when NO candidate is even plausibly close.

Check (c), generalized: signature-fit and method-fit
-------------------------------------------------------
ADR-0044 D4's own text exemplifies check (c) on step definitions
("Signature/parameter fit between the step definition and the Gherkin step
it is bound to"). This module reads that check's underlying principle -- a
plausible match whose STRUCTURE doesn't fit the binding must escalate,
never be trusted on confidence alone -- as asset-type-agnostic (D4's own
rationale paragraph names no asset type; D1/D3 already establish the
catalog and reuse-first discipline as spanning step definitions, page
objects, AND utilities alike). A page-object/utility candidate therefore
gets the SAME discipline under a different structural dimension:
METHOD-FIT (``_check_method_fit``) in place of SIGNATURE-FIT
(``_check_signature_fit``) -- closing the page-object analogue of the
1-capture-to-2-param mis-binding D4 exists to prevent (a confident,
current-hash match to a page object that lacks the method the binding
needs). See the additive clarification note on ADR-0044 D4
(`docs/adr/0044-layer-3-automation-engineering-architecture-freeze.md`) for
the full reasoning; the step-definition path (``_check_signature_fit``) is
completely unchanged by this generalization.

**Method-fit is a COARSE, decision-time check, by necessity, not by
oversight.** At this decision point, the engine knows a candidate
page-object/utility class's full method inventory (the catalog, D3) and
the step-need's own required capture shape (`GherkinStepNeed.captures`) --
enough to check "does *some* method on this class have a parameter shape
that could accept this call." It does NOT know, and cannot know here,
WHICH specific method a not-yet-written step definition will actually
invoke -- that choice, and the PRECISE verification that the chosen method
is both structurally AND semantically the right one, is the future
generator's own obligation, not performed here (`TrustedReuse`'s own
docstring records this contract: the full `asset.methods` inventory is
handed over precisely so that future check has what it needs).
"""

from __future__ import annotations

from automation_engineering.catalog.alignment import CUCUMBER_EXPRESSION_TYPES
from automation_engineering.catalog.models import (
    AssetCatalog,
    JavaMethod,
    PageObjectAsset,
    StepCapture,
    StepDefinitionAsset,
    UtilityAsset,
)
from automation_engineering.reuse.matcher import SemanticMatcher
from automation_engineering.reuse.models import (
    Escalation,
    EscalationCheck,
    GherkinStepNeed,
    MatchCandidate,
    NoMatch,
    ReuseDecision,
    TrustedReuse,
)

#: ADR-0044 D4(a)'s "a set threshold" -- configurable (the `confidence_threshold`
#: parameter below), defaulted here. Not derived from any measurement; a
#: conservative starting point pending real embedding-similarity calibration
#: (ADR-0044 D3's own embeddings lean -- Consequences, D3's TBD).
DEFAULT_CONFIDENCE_THRESHOLD = 0.75

#: ADR-0044 D3's NO_MATCH/generate boundary, made reachable post-bootstrap
#: (additive note, 2026-08-05, the three-tier reuse-decision fix). Below
#: this similarity, the best candidate is not even PLAUSIBLE -- "nothing
#: relevant," not "something relevant but untrustworthy" -- and the need
#: routes to NO_MATCH/generate, exactly as an empty catalog already does,
#: never to escalation.
#:
#: **Calibrated from a live run's real score data, not guessed.** A live
#: run (`output/executions/run-20260805T105026014856Z-987575c0/
#: automation_engineering_report.md`) matched 49 real Gherkin step-needs
#: (SauceDemo login/cart/checkout/logout steps) against the tracked
#: baseline's real 2-asset catalog (`SmokeSteps`'s own two steps -- neither
#: remotely related to any of the 49). Every one of the 49 scored in
#: [0.5707, 0.6688] -- genuinely unrelated short technical text has a HIGH
#: embedding-similarity floor with this model family, never near 0. A fresh
#: live probe (same catalog, same embedding model) against two more
#: deliberately-novel, unrelated needs ("a satellite uplink telemetry
#: buffer is flushed...", "a two-factor authentication backup code...")
#: scored [0.5196, 0.5696] -- consistent with the live run's own band, not
#: an outlier. The SAME catalog's own exact-text match scored 0.9843, and a
#: full paraphrase of it scored 0.8980 -- both far above
#: `DEFAULT_CONFIDENCE_THRESHOLD`. The real "nothing relevant" ceiling
#: (0.6688) and the real "genuinely relevant" floor (0.8980) leave a wide,
#: cleanly-separated gap; this floor sits at its midpoint with
#: `DEFAULT_CONFIDENCE_THRESHOLD`, comfortably above every observed
#: unrelated score (>=0.03 margin) and comfortably below every observed
#: relevant one -- a simple global floor, not a guess, and not a smarter
#: (relative-gap/normalized) criterion, because the data did not call for
#: one: the two observed bands do not overlap. See ADR-0044 D3/D4's
#: additive note (docs/adr/0044-...) for the full investigation.
DEFAULT_GENERATE_FLOOR = 0.70


def decide_reuse(
    need: GherkinStepNeed,
    catalog: AssetCatalog,
    matcher: SemanticMatcher,
    *,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    generate_floor: float = DEFAULT_GENERATE_FLOOR,
) -> ReuseDecision:
    """Decide reuse-or-generate-or-escalate for one Gherkin step-need.

    Calls `matcher.match(need, catalog)` exactly once -- the only
    nondeterministic step. Every check after that is pure comparison against
    already-known data (the candidate's own fields, a fresh catalog lookup,
    and `need`'s own captures) -- no live call, no randomness; the same
    `(need, catalog, matcher)` triple always produces the same
    :data:`~automation_engineering.reuse.models.ReuseDecision`, for any
    matcher whose own `match` is itself deterministic (true of
    :class:`~automation_engineering.reuse.matcher.StubSemanticMatcher` by
    construction).

    **Three tiers, in order (additive, 2026-08-05).** `matcher.match`
    returning `()` (an empty catalog, `.matcher`'s own only unconditional
    case) is still NO_MATCH, unchanged. Given at least one candidate:
    (1) `best.confidence < generate_floor` -- NOT EVEN PLAUSIBLE -- NO_MATCH,
    the same outcome as an empty catalog, for the same reason (nothing
    worth a human's time reviewing); this is the tier this fix adds, and
    the ONLY thing it changes -- it was previously unreachable once a
    catalog had ever been populated (Finding 1), since `LiveSemanticMatcher`
    always returns one candidate per catalog asset. (2) `generate_floor <=
    best.confidence < confidence_threshold` -- PLAUSIBLE BUT NOT
    TRUSTWORTHY -- ESCALATE(CONFIDENCE), exactly ADR-0044 D4(a)'s
    pre-existing behavior, merely bounded below now. (3)
    `best.confidence >= confidence_threshold` -- ADR-0044 D4's own
    three-check safety (content-hash, structural fit) -- entirely
    UNCHANGED by this fix, still the only path to `TrustedReuse`.
    """
    candidates = matcher.match(need, catalog)
    if not candidates:
        return NoMatch(need=need)

    best = candidates[0]

    if best.confidence < generate_floor:
        return NoMatch(need=need)

    if best.confidence < confidence_threshold:
        return Escalation(
            need=need,
            check=EscalationCheck.CONFIDENCE,
            candidate=best,
            detail=(
                f"match confidence {best.confidence!r} is below the configured "
                f"threshold {confidence_threshold!r}"
            ),
        )

    hash_escalation = _check_content_hash(need, catalog, best)
    if hash_escalation is not None:
        return hash_escalation

    structural_escalation = _check_structural_fit(need, catalog, best)
    if structural_escalation is not None:
        return structural_escalation

    # Both deterministic checks passed; the catalog lookup performed inside
    # `_check_content_hash` already proved the asset exists and is current --
    # re-look it up (rather than thread it through) keeps each check's own
    # function self-contained and independently testable.
    asset = catalog.get(best.asset_id)
    assert asset is not None  # proven by _check_content_hash's own lookup above
    return TrustedReuse(asset=asset, candidate=best)


def _check_content_hash(
    need: GherkinStepNeed, catalog: AssetCatalog, candidate: MatchCandidate
) -> Escalation | None:
    """ADR-0044 D4(b): the candidate asset's CURRENT content-hash (a fresh
    catalog lookup, not the matcher's own cached view) must match what the
    match was computed against (`candidate.content_hash`).

    **Why this is still needed even though the catalog is reconciled fresh
    at run start (ADR-0044 D3):** reconciliation happens once, at the start
    of a run -- it is not re-run before every single binding decision within
    that run. A semantic match may be computed once per run (or batched
    across many step-needs, ADR-0044 D3's own embeddings-batching
    rationale) and then consumed across several bindings; if the underlying
    Java changes *within* that same run (a prior step-need's own generation
    and promotion, ADR-0045, landing mid-run; or a concurrent edit) before a
    later binding actually happens, the match a matcher computed earlier can
    describe an asset that has since drifted -- staleness *within* a run,
    between match and bind, which run-start reconciliation alone cannot
    catch. This check is what catches that specific gap; (a) and (c) do not.
    """
    asset = catalog.get(candidate.asset_id)
    if asset is None:
        return Escalation(
            need=need,
            check=EscalationCheck.CONTENT_HASH,
            candidate=candidate,
            detail=(
                f"asset_id={candidate.asset_id!r} matched but no longer exists "
                "in a fresh catalog lookup"
            ),
        )
    if asset.content_hash != candidate.content_hash:
        return Escalation(
            need=need,
            check=EscalationCheck.CONTENT_HASH,
            candidate=candidate,
            detail=(
                f"asset_id={candidate.asset_id!r} content-hash drifted: match was "
                f"computed against {candidate.content_hash!r}, catalog's current "
                f"entry is {asset.content_hash!r}"
            ),
        )
    return None


def _check_structural_fit(
    need: GherkinStepNeed, catalog: AssetCatalog, candidate: MatchCandidate
) -> Escalation | None:
    """ADR-0044 D4(c), generalized (module docstring): dispatches to the
    realization that fits the candidate's own catalog asset kind --
    SIGNATURE-FIT for a step definition (`_check_signature_fit`, unchanged),
    METHOD-FIT for a page object or utility (`_check_method_fit`, new).

    The catalog lookup happens exactly once, here, and the resolved asset
    is threaded into whichever check applies -- neither check re-looks it
    up. `asset` is guaranteed non-`None` at this point: `_check_content_hash`
    (called immediately before this, in `decide_reuse`) already proved the
    candidate's `asset_id` resolves in a fresh catalog lookup, or this
    function would never have been reached.
    """
    asset = catalog.get(candidate.asset_id)
    assert asset is not None  # proven by _check_content_hash's own lookup
    if isinstance(asset, StepDefinitionAsset):
        return _check_signature_fit(need, asset, candidate)
    return _check_method_fit(need, asset, candidate)


def _check_signature_fit(
    need: GherkinStepNeed, asset: StepDefinitionAsset, candidate: MatchCandidate
) -> Escalation | None:
    """ADR-0044 D4(c), step-definition realization -- UNCHANGED by this
    generalization. The candidate's own recorded capture-parameter
    correlation (`StepDefinitionAsset.signature_alignment`, computed once by
    :func:`automation_engineering.catalog.alignment.correlate` and never
    re-derived here) must FIT `need`'s own required captures -- count,
    order, and type.
    """
    if not asset.signature_alignment.is_aligned:
        return Escalation(
            need=need,
            check=EscalationCheck.SIGNATURE_FIT,
            candidate=candidate,
            detail=(
                f"asset_id={candidate.asset_id!r} own signature is not "
                f"self-aligned (mismatch_reason="
                f"{asset.signature_alignment.mismatch_reason!r}); it cannot be "
                "trusted as a binding target"
            ),
        )

    candidate_captures = asset.signature_alignment.captures
    need_captures = need.captures

    if len(need_captures) != len(candidate_captures):
        return Escalation(
            need=need,
            check=EscalationCheck.SIGNATURE_FIT,
            candidate=candidate,
            detail=(
                f"asset_id={candidate.asset_id!r} capture-count mismatch: step "
                f"needs {len(need_captures)} capture(s), candidate declares "
                f"{len(candidate_captures)}"
            ),
        )

    for index, (need_capture, candidate_capture) in enumerate(
        zip(need_captures, candidate_captures, strict=True)
    ):
        if (
            need_capture.expression_type is not None
            and candidate_capture.expression_type is not None
            and need_capture.expression_type != candidate_capture.expression_type
        ):
            return Escalation(
                need=need,
                check=EscalationCheck.SIGNATURE_FIT,
                candidate=candidate,
                detail=(
                    f"asset_id={candidate.asset_id!r} capture #{index} type "
                    f"mismatch: step needs {need_capture.expression_type!r}, "
                    f"candidate declares {candidate_capture.expression_type!r}"
                ),
            )

    return None


def _check_method_fit(
    need: GherkinStepNeed,
    asset: PageObjectAsset | UtilityAsset,
    candidate: MatchCandidate,
) -> Escalation | None:
    """COARSE, decision-time CLASS-COMPATIBILITY SCREEN -- this is
    everything this function does, stated plainly up front so it is never
    mistaken for more: it escalates ONLY if the candidate class has NO
    method whose parameter shape (arity, per-position type, via
    `CUCUMBER_EXPRESSION_TYPES`) is compatible with `need`'s own required
    captures. It does NOT verify the candidate provides the SPECIFIC method
    the binding will actually call.

    **What this catches, and what it structurally cannot.** It catches
    GROSS class-level incompatibility -- e.g. a step needing an `{int}`
    argument matched to a page object whose every method is zero-arg. It
    CANNOT catch a page object that has SOME shape-compatible method but
    not the RIGHT one -- e.g. a `LoginPage` reused for a step that needs
    `clickForgotPasswordLink()` (no capture) passes this screen the moment
    `LoginPage` has ANY other zero-arg method (`open()`, say), even though
    it has no `clickForgotPasswordLink` at all. That gap is not an
    oversight: which specific method a not-yet-written step definition
    will call is not knowable at reuse-decision time (module docstring,
    "Method-fit is a COARSE, decision-time check, by necessity") -- only
    the future generator, at the point it actually writes the call, knows
    the target method's name and can verify it precisely. `TrustedReuse`'s
    own docstring records that obligation and the data (`asset.methods`,
    the full inventory) the generator needs to discharge it; this function
    does not attempt it.

    Utilities get the SAME coarse screen as page objects, not a weaker
    one: the catalog records both identically (a `.methods` tuple of
    `JavaMethod`s, D3), and this task found no principled reason to trust a
    utility's structural fit less rigorously than a page object's. In
    practice a utility "need" will often carry zero captures (D7's
    config-driven utility classes are typically called with no step-derived
    arguments) -- the screen is still REAL for that case (only a genuine
    zero-arg method qualifies; a utility class with none still escalates),
    not vacuous, even though it is exactly as coarse as the page-object
    case above.
    """
    need_captures = need.captures
    if any(method_shape_fits(method, need_captures) for method in asset.methods):
        return None
    return Escalation(
        need=need,
        check=EscalationCheck.METHOD_FIT,
        candidate=candidate,
        detail=(
            f"asset_id={candidate.asset_id!r} ({type(asset).__name__}) provides no "
            f"method whose parameter shape fits the {len(need_captures)} required "
            f"capture(s); available method signature(s): "
            f"{_method_signatures(asset.methods)!r}"
        ),
    )


def method_shape_fits(method: JavaMethod, need_captures: tuple[StepCapture, ...]) -> bool:
    """Arity plus per-position type compatibility -- the same two
    dimensions `_check_signature_fit` compares, applied to one candidate
    method's own parameters instead of a step definition's correlated
    captures.

    **Public** (unlike this module's other check helpers) because the
    page-object/utility generator (`automation_engineering.generation.
    method_fit`) needs this exact shape-compatibility rule a second time --
    once here, for the COARSE decision-time class-compatibility screen
    (`_check_method_fit`, above), and once there, for the PRECISE
    generation-time check on one already-named method (ADR-0044 D4's own
    clarification note: the precise check is "the generator's own
    obligation, not this engine's"). Promoted rather than duplicated so both
    checks apply IDENTICAL shape logic, never two hand-maintained copies
    that could silently drift apart.
    """
    if len(method.parameters) != len(need_captures):
        return False
    return all(
        _capture_type_compatible(capture, parameter.java_type)
        for capture, parameter in zip(need_captures, method.parameters, strict=True)
    )


def _capture_type_compatible(capture: StepCapture, java_type: str) -> bool:
    """Mirrors `automation_engineering.catalog.alignment`'s own (private)
    capture/parameter type-compatibility rule exactly, via the same
    exported `CUCUMBER_EXPRESSION_TYPES` table -- not re-derived, reused."""
    if capture.expression_type is None:
        return True  # regex capture -- no independently declared type to disagree with
    accepted = CUCUMBER_EXPRESSION_TYPES.get(capture.expression_type)
    if accepted is None:
        return True  # unrecognized/custom expression type -- not determinable, not a mismatch
    return java_type in accepted


def _method_signatures(methods: tuple[JavaMethod, ...]) -> tuple[str, ...]:
    return tuple(
        f"{method.name}({', '.join(p.java_type for p in method.parameters)})"
        for method in methods
    )


__all__ = [
    "DEFAULT_CONFIDENCE_THRESHOLD",
    "DEFAULT_GENERATE_FLOOR",
    "decide_reuse",
    "method_shape_fits",
]
