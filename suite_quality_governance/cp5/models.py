"""CP5's orphaned-glue result contract (ADR-0046 D2/D6).

Mirrors `automation_engineering.cp3.models`/`automation_engineering.cp4.
models`'s own `<Prefix>CriterionResult`/`<Prefix>Result` shape and
`overall_verdict`-derived-from-evidence discipline -- this is CP5's FIRST
of four components (ADR-0046 D2-D5); a future task composes this criterion
alongside the other three (near-dup sweep, promotion-wrapping, aggregate
cohesion) into CP5's own full result. Nothing here builds that composition.

Two record shapes, deliberately distinct, mirroring `automation_engineering.
reuse.models`'s own "carries no matching/decision logic" split:

* `SemanticOrphanHint` -- ADVISORY ONLY (ADR-0046 D6). Attached to a finding
  that is ALREADY deterministically orphaned; it never causes an asset to
  be flagged, and its absence never un-flags one.
* `OrphanedAssetFinding` -- the flag-for-review record ADR-0046 D2 requires
  ("flag for review, never auto-remove"). This is not the same shape as
  `automation_engineering.reuse.models.Escalation` -- that record is
  NEED-shaped (a `GherkinStepNeed` plus a failed reuse-safety CHECK);
  this one is ASSET-shaped (a catalogued step definition with no matching
  need). Reusing `Escalation`'s own fields here would force an artificial
  fit; this module defines CP5's own record instead, carrying the same
  "everything a human needs to decide, nothing more" discipline
  `Escalation`'s own docstring already establishes, without pretending to
  be a fourth `EscalationCheck` variant of a check that never actually ran.
"""

from __future__ import annotations

from dataclasses import dataclass

from shared.enums.base import ValidationVerdict

#: This component's own criterion name -- for a future CP5 composite result
#: to key on, alongside the near-dup-sweep/promotion-wrap/cohesion criteria
#: ADR-0046 D3-D5 name but do not yet build.
CRITERION_ORPHANED_GLUE = "orphaned_glue"


@dataclass(frozen=True, slots=True)
class SemanticOrphanHint:
    """An ADVISORY-ONLY signal on an already-orphaned finding: some current
    need's text scored close enough (embedding cosine similarity) to this
    asset's own text to suggest a feature may have reworded a step so the
    pattern no longer matches, even though the intent is plausibly still
    wanted. Never changes the deterministic orphan verdict (ADR-0046 D6) --
    a human reviewing the finding may find this useful context, nothing
    more.
    """

    closest_need_text: str
    confidence: float


@dataclass(frozen=True, slots=True)
class OrphanedAssetFinding:
    """One step-definition asset the deterministic gate found no current
    feature references -- flagged for human review (ADR-0046 D2). This
    record is the entire "action" CP5's orphan detection takes: it is
    never used to delete or modify the baseline (module docstring, and
    `suite_quality_governance.cp5.orphaned_glue`'s own read-only contract).

    `semantic_hint` is `None` whenever no embedding provider was supplied,
    or no current need scored above the hint floor -- "no hint available"
    is a normal outcome, not a partial failure.
    """

    asset_id: str
    class_name: str
    method_name: str
    pattern: str
    semantic_hint: SemanticOrphanHint | None = None


@dataclass(frozen=True, slots=True)
class Cp5OrphanedGlueResult:
    """This component's own verdict: `FAIL` iff at least one step-definition
    asset was deterministically orphaned, `PASS` iff every catalogued step
    definition is referenced by at least one current need.

    Computed from `findings` alone -- a `SemanticOrphanHint` attached to a
    finding never participates in this computation (ADR-0046 D6: the
    semantic part is advisory, never gating). An orphan WITH a hint and an
    orphan WITHOUT one both count toward `FAIL` identically.
    """

    overall_verdict: ValidationVerdict
    findings: tuple[OrphanedAssetFinding, ...]

    @property
    def passed(self) -> bool:
        return self.overall_verdict == ValidationVerdict.PASS


__all__ = [
    "CRITERION_ORPHANED_GLUE",
    "Cp5OrphanedGlueResult",
    "OrphanedAssetFinding",
    "SemanticOrphanHint",
]
