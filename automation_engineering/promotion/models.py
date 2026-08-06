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
from automation_engineering.cp3.models import Cp3Result
from automation_engineering.promotion.cp3_decomposition import decompose_for_asset
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
    """D2(a)'s three preconditions for one generated asset -- PER-ASSET,
    not whole-run (ADR-0045 D2 additive note, 2026-08-06).

    ``cp2_verdict`` is the asset's OWNING FEATURE's own CP2 verdict
    (ADR-0043) -- genuinely per-feature, the same granularity
    ``feature_engineering.stage.models.FeatureRecord.cp2_verdict`` already
    records, unchanged by this note.

    ``cp3_result`` is the WHOLE-RUN ``Cp3Result``
    (:func:`automation_engineering.cp3.gate.evaluate_cp3` is still called
    once per run, not once per candidate -- no new validation surface is
    introduced, ADR-0045 D2's own text) -- but :meth:`first_failure` no
    longer reads its ``overall_verdict`` directly. It decomposes ``cp3_result``
    PER CANDIDATE via :func:`automation_engineering.promotion.
    cp3_decomposition.decompose_for_asset`: three of CP3's seven criteria
    (``direct_webdriver_action``, ``long_method``, ``duplicate_steps``)
    already carry per-class/per-asset attribution in their own message text
    and are filtered to just THIS candidate; the coverage family
    (``step_coverage``/``scenario_coverage``/``unmapped_steps``) can only
    fail because of a DIFFERENT, unresolved need and is excluded from a
    resolved candidate's own gate; ``sonar_quality_gate`` stays whole-batch
    (the server reports one verdict per project, no file/class
    attribution -- :mod:`.cp3_decomposition`'s own module docstring).

    ``cp4_verdict`` stays whole-batch, unchanged -- CP4 evaluates a run's
    full page-object set in one call
    (:class:`automation_engineering.cp4.models.Cp4Result`), the same
    whole-scan nature as the Sonar criterion above; decomposing it is out of
    this note's own scope (no live per-asset case exists to build or prove
    against in the current wiring, where CP4 is always vacuously PASS --
    :mod:`automation_engineering.stage.runner`'s own module docstring, step
    7).
    """

    cp2_verdict: ValidationVerdict
    cp3_result: Cp3Result
    cp4_verdict: ValidationVerdict

    def first_failure(self, *, class_name: str, asset_id: str) -> PromotionBlockReason | None:
        """The first of CP2/CP3/CP4 (in that order) that does not pass FOR
        THIS CANDIDATE, or ``None`` if all three passed. CP3 is decomposed
        per-candidate (class docstring); CP2/CP4 stay the batch verdicts
        they already were."""
        if self.cp2_verdict != ValidationVerdict.PASS:
            return PromotionBlockReason.CP2_FAILED
        asset_cp3 = decompose_for_asset(self.cp3_result, class_name=class_name, asset_id=asset_id)
        if asset_cp3.verdict != ValidationVerdict.PASS:
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
