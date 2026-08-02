"""Promotion's own decision vocabulary (ADR-0045 D2/D3).

Mirrors :mod:`automation_engineering.reuse.models`'s own discipline: closed
unions, one variant per outcome, exhaustive so a caller (or ``mypy``, via
structural matching) cannot silently drop a case.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from automation_engineering.catalog.models import CatalogAsset
from automation_engineering.reuse.models import Escalation
from shared.enums.base import ValidationVerdict


class PromotionBlockReason(StrEnum):
    """Why a candidate that reached the promotion gate did NOT promote --
    distinct from :class:`PromotionEscalated`, which never reaches the gate
    at all (D3). Exactly one reason per :class:`NotPromotable`, reported for
    the first check that failed (D2(a) before D2(b), mirroring the reuse
    engine's own "(a) then (b) then (c), first failure wins" discipline)."""

    CP2_FAILED = "cp2_failed"
    CP3_FAILED = "cp3_failed"
    CP4_FAILED = "cp4_failed"
    DUPLICATE = "duplicate"


@dataclass(frozen=True, slots=True)
class AssetGateOutcomes:
    """D2(a)'s three preconditions for one generated asset.

    ``cp2_verdict`` is the asset's OWNING FEATURE's own CP2 verdict
    (ADR-0043) -- genuinely per-feature, the same granularity
    ``feature_engineering.stage.models.FeatureRecord.cp2_verdict`` already
    records. ``cp3_verdict``/``cp4_verdict`` are supplied at the granularity
    CP3/CP4 are actually computed at TODAY: one verdict for the whole batch
    a run's Sonar scan (:class:`automation_engineering.cp3.models.Cp3Result`)
    and locator-health sweep
    (:class:`automation_engineering.cp4.models.Cp4Result`) cover -- neither
    gate is computed per individual asset in this platform yet (CP3's own
    Sonar criterion is inherently a whole-Maven-project scan; CP4 evaluates
    a run's full page-object set in one call). Passing a run's own
    ``Cp3Result.passed``/``Cp4Result.passed`` straight through here is
    therefore reusing the EXISTING validation report exactly as ADR-0045 D2
    requires ("no new validation surface is introduced"), not inventing a
    finer-grained check this platform does not otherwise have. A future
    Layer-3 stage runner may persist a genuinely per-asset CP3/CP4 record;
    building that manifest is out of this ADR's own scope (D1) and this
    package's.
    """

    cp2_verdict: ValidationVerdict
    cp3_verdict: ValidationVerdict
    cp4_verdict: ValidationVerdict

    def first_failure(self) -> PromotionBlockReason | None:
        """The first of CP2/CP3/CP4 (in that order) that did not pass, or
        ``None`` if all three passed."""
        if self.cp2_verdict != ValidationVerdict.PASS:
            return PromotionBlockReason.CP2_FAILED
        if self.cp3_verdict != ValidationVerdict.PASS:
            return PromotionBlockReason.CP3_FAILED
        if self.cp4_verdict != ValidationVerdict.PASS:
            return PromotionBlockReason.CP4_FAILED
        return None


@dataclass(frozen=True, slots=True)
class PromotionCandidate:
    """One generated asset awaiting a promotion decision.

    ``asset``/``relative_path`` are resolved by
    :func:`automation_engineering.promotion.identity.resolve_candidate_identity`
    -- the SAME scan the tracked-baseline catalog itself uses
    (:func:`automation_engineering.catalog.scanner.reconcile`), never
    re-derived by this package. ``java_source`` is the EXACT text that
    identity was computed from -- :mod:`.mechanism` writes this string
    verbatim into the tracked baseline, so the promoted file and the
    identity that gated its promotion can never drift apart.
    """

    java_source: str
    asset: CatalogAsset
    relative_path: Path


@dataclass(frozen=True, slots=True)
class Promoted:
    """D2(a)+(b) both satisfied -- auto-promoted (D3), no human review
    gates this candidate's promotion decision (though :mod:`.mechanism`
    still stages rather than commits the resulting change -- a separate
    question, D5)."""

    candidate: PromotionCandidate


@dataclass(frozen=True, slots=True)
class NotPromotable:
    """D2(a) or D2(b) failed -- blocked, not escalated: there is no
    ambiguity for a human to resolve here (a failed gate or a proven
    duplicate is a deterministic NO, not a judgment call), so this is
    reported and dropped, never queued for review."""

    candidate: PromotionCandidate
    reason: PromotionBlockReason
    detail: str


@dataclass(frozen=True, slots=True)
class PromotionEscalated:
    """D3: an asset the reuse engine escalated (ADR-0044 D4) never becomes a
    :class:`PromotionCandidate` at all -- nothing was generated for it to
    promote. ``escalation`` is the SAME
    :class:`~automation_engineering.reuse.models.Escalation` record the
    reuse engine (or the precise method-fit discharge) already produced,
    carried through unedited -- joining the ONE shared human-in-the-loop
    review every other escalation in this platform already uses, never a
    second, promotion-specific queue (Recommendation 2)."""

    escalation: Escalation


#: ADR-0045's exhaustive promotion-decision vocabulary. A caller handles all
#: three; there is no fourth case.
PromotionDecision = Promoted | NotPromotable | PromotionEscalated

__all__ = [
    "AssetGateOutcomes",
    "NotPromotable",
    "Promoted",
    "PromotionBlockReason",
    "PromotionCandidate",
    "PromotionDecision",
    "PromotionEscalated",
]
