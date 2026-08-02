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

D3's review model: an asset the reuse engine escalated (ADR-0044 D4) never
reaches :func:`evaluate_promotion` as a candidate at all -- there is nothing
generated to gate. :func:`evaluate_escalated_promotion` only re-homes the
SAME escalation record under this package's own decision vocabulary, for
reporting; it does not re-decide anything (Recommendation 2: one shared
review queue, never a second).
"""

from __future__ import annotations

from automation_engineering.catalog.models import AssetCatalog
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
    """
    gate_failure = gates.first_failure()
    if gate_failure is not None:
        return NotPromotable(
            candidate=candidate,
            reason=gate_failure,
            detail=(
                f"{gate_failure.value} did not pass; promotion requires CP2, CP3, "
                "and CP4 to all pass (ADR-0045 D2(a))"
            ),
        )

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
