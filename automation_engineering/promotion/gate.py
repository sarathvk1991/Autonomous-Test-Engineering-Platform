"""Promotion's decision (ADR-0045 D2/D3) -- pure, deterministic, no live call.

D2's promotable gate: a candidate auto-promotes iff (a) its owning feature
passed CP2 and its automation passed CP3 and CP4
(:class:`~automation_engineering.promotion.models.AssetGateOutcomes`), AND
(b) it is not a duplicate of an existing tracked-baseline asset -- checked
via the SAME identity the reuse engine already computes
(:meth:`~automation_engineering.catalog.models.AssetCatalog.by_content_hash`,
that method's own docstring: "the identity lookup ADR-0045 D2(b) reuses").
No new duplicate-detection mechanism is built here (D2's own text,
Recommendation 3).

**Per-asset, not whole-run (ADR-0045 D2 additive note, 2026-08-06).** D2(a)
is evaluated FOR THIS CANDIDATE alone --
:meth:`~automation_engineering.promotion.models.AssetGateOutcomes.
first_failure` decomposes the run's own whole-batch CP3 result down to what
is actually true or false about THIS candidate's own class
(:mod:`automation_engineering.promotion.cp3_decomposition`'s own module
docstring for the full per-criterion breakdown). Another candidate in the
same run failing its own CP3 criteria, or another need in the same run
escalating, no longer blocks THIS one -- the confirming live run's own gap
(30 clean binds promoted 0 because 30 unrelated needs escalated, failing
one shared whole-run gate) is exactly what this note closes.

D3's review model: an asset the reuse engine escalated (ADR-0044 D4) never
reaches :func:`evaluate_promotion` as a candidate at all -- there is nothing
generated to gate. :func:`evaluate_escalated_promotion` only re-homes the
SAME escalation record under this package's own decision vocabulary, for
reporting; it does not re-decide anything (Recommendation 2: one shared
review queue, never a second).
"""

from __future__ import annotations

from automation_engineering.catalog.models import AssetCatalog
from automation_engineering.promotion.cp3_decomposition import decompose_for_asset
from automation_engineering.promotion.models import (
    AssetGateOutcomes,
    NotPromotable,
    Promoted,
    PromotionBlockReason,
    PromotionCandidate,
    PromotionEscalated,
)
from automation_engineering.reuse.models import Escalation


def evaluate_promotion(
    candidate: PromotionCandidate,
    gates: AssetGateOutcomes,
    baseline_catalog: AssetCatalog,
) -> Promoted | NotPromotable:
    """D2's promotable gate for one already-resolved candidate.

    Checks (a) before (b) -- a candidate failing both a gate AND the
    duplicate check is reported for the gate failure, mirroring the reuse
    engine's own "checks run in order, first failure wins, never a silent
    fallback" discipline (:func:`automation_engineering.reuse.engine.
    decide_reuse`).

    (a) is evaluated PER CANDIDATE (ADR-0045 D2 additive note, module
    docstring) -- ``gates.first_failure`` is handed this candidate's own
    ``class_name``/``asset_id`` so a CP3 failure is decomposed down to what
    is actually true about THIS class, never the whole run's shared
    verdict.
    """
    class_name = candidate.asset.class_name
    asset_id = candidate.asset.asset_id
    gate_failure = gates.first_failure(class_name=class_name, asset_id=asset_id)
    if gate_failure is not None:
        detail = (
            f"{gate_failure.value} did not pass; promotion requires CP2, CP3, "
            "and CP4 to all pass (ADR-0045 D2(a))"
        )
        if gate_failure is PromotionBlockReason.CP3_FAILED:
            asset_cp3 = decompose_for_asset(
                gates.cp3_result, class_name=class_name, asset_id=asset_id
            )
            if asset_cp3.messages:
                detail = f"{detail}: {'; '.join(asset_cp3.messages)}"
        return NotPromotable(candidate=candidate, reason=gate_failure, detail=detail)

    duplicates = baseline_catalog.by_content_hash(candidate.asset.content_hash)
    if duplicates:
        existing = duplicates[0]
        return NotPromotable(
            candidate=candidate,
            reason=PromotionBlockReason.DUPLICATE,
            detail=(
                f"content_hash={candidate.asset.content_hash!r} already exists in "
                f"the tracked baseline as asset_id={existing.asset_id!r} "
                f"({existing.class_name!r}); promoting would create the duplicate "
                "the reuse engine exists to avoid (ADR-0045 D2(b))"
            ),
        )

    return Promoted(candidate=candidate)


def evaluate_escalated_promotion(escalation: Escalation) -> PromotionEscalated:
    """D3: carry an already-escalated reuse decision through, unedited, as a
    promotion decision -- see module docstring."""
    return PromotionEscalated(escalation=escalation)


__all__ = ["evaluate_escalated_promotion", "evaluate_promotion"]
