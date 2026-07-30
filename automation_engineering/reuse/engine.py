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
(a) confidence >= threshold; (b) content-hash freshness; (c) signature/
parameter fit. All three must pass for :class:`TrustedReuse`; any one
failing produces an :class:`Escalation` naming exactly that check -- never a
silent fallback to a different check or a reduced-confidence acceptance
(ADR-0044 D4's own "a match that clears confidence but fails either
deterministic check... escalates, the same outcome as failing (a)
outright"). Checks are evaluated in order and the function returns at the
first failure, so a candidate failing more than one check is still reported
against the earliest one -- deterministic, not incidental.
"""

from __future__ import annotations

from automation_engineering.catalog.models import AssetCatalog, StepDefinitionAsset
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


def decide_reuse(
    need: GherkinStepNeed,
    catalog: AssetCatalog,
    matcher: SemanticMatcher,
    *,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
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
    """
    candidates = matcher.match(need, catalog)
    if not candidates:
        return NoMatch(need=need)

    best = candidates[0]

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

    signature_escalation = _check_signature_fit(need, catalog, best)
    if signature_escalation is not None:
        return signature_escalation

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


def _check_signature_fit(
    need: GherkinStepNeed, catalog: AssetCatalog, candidate: MatchCandidate
) -> Escalation | None:
    """ADR-0044 D4(c): the candidate's own recorded capture-parameter
    correlation (`StepDefinitionAsset.signature_alignment`, computed once by
    :func:`automation_engineering.catalog.alignment.correlate` and never
    re-derived here) must FIT `need`'s own required captures -- count,
    order, and type.

    Only :class:`StepDefinitionAsset` carries a signature to fit against; a
    page-object/utility candidate (no Gherkin-step capture concept applies
    to either) passes this check vacuously -- there is nothing here for it
    to fail. A future page-object/utility reuse discipline, if one is ever
    needed, is out of this task's scope (the prompt's own D4(c) example --
    "a 1-capture step -> 2-param method" -- is a step-definition-only
    concern).
    """
    asset = catalog.get(candidate.asset_id)
    if not isinstance(asset, StepDefinitionAsset):
        return None

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


__all__ = ["DEFAULT_CONFIDENCE_THRESHOLD", "decide_reuse"]
