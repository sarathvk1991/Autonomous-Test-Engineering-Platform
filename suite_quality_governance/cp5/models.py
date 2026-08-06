"""CP5's result contracts: orphaned-glue detection (component 1, ADR-0046
D2/D6) and the cross-suite near-duplicate sweep (component 2, ADR-0046
D3/D6).

Mirrors `automation_engineering.cp3.models`/`automation_engineering.cp4.
models`'s own `<Prefix>CriterionResult`/`<Prefix>Result` shape and
`overall_verdict`-derived-from-evidence discipline for orphaned-glue, its
first, gating component -- this is CP5's first TWO of four components
(ADR-0046 D2-D5); a future task composes these alongside the remaining two
(promotion-wrapping, aggregate cohesion) into CP5's own full result.
Nothing here builds that composition.

**Orphaned-glue is a gate; the near-dup sweep is not, and its own result
shape says so structurally.** ADR-0046 D6's own composition table names
orphaned-glue's deterministic check as gating CP5's PASS/FAIL, and the
near-dup sweep as "Advisory | Review-trigger only, never gates -- same
discipline as the reuse engine's own confidence-based escalation." Rather
than give `Cp5NearDuplicateSweepResult` a `overall_verdict` field that
would misleadingly suggest it participates in CP5's own gate, it carries
only `clusters` -- there is no PASS/FAIL concept for a component that
structurally never gates.

Three record shapes, deliberately distinct, mirroring `automation_engineering.
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
* `NearDuplicateClusterFinding` -- the flag-for-consolidation-review record
  ADR-0046 D3 requires ("flag the cluster for human consolidation review,
  never auto-merge"). CLUSTER-shaped (two or more distinct assets, plus the
  pairwise scores that connected them), a different shape again from both
  `Escalation` and `OrphanedAssetFinding` -- a near-duplicate is a
  relationship between assets, not a property of one asset alone.
"""

from __future__ import annotations

from dataclasses import dataclass

from shared.enums.base import ValidationVerdict

#: This component's own criterion name -- for a future CP5 composite result
#: to key on, alongside the near-dup-sweep/promotion-wrap/cohesion criteria
#: ADR-0046 D3-D5 name but do not yet build.
CRITERION_ORPHANED_GLUE = "orphaned_glue"

#: The near-dup sweep's own finding-source name -- deliberately not named
#: "CRITERION_*" (module docstring: it never gates, so it is not a
#: criterion in this codebase's own vocabulary, e.g. `CP3_CRITERIA`/
#: `CP4_CRITERIA`, both PASS/FAIL contributors).
FINDING_SOURCE_NEAR_DUPLICATE_SWEEP = "near_duplicate_sweep"


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


@dataclass(frozen=True, slots=True)
class NearDuplicateAssetRef:
    """One catalogued step-definition asset's own identifying data, snapshot
    at sweep time -- enough for a human reviewer to locate and compare the
    asset without a second catalog lookup."""

    asset_id: str
    class_name: str
    method_name: str
    pattern: str


@dataclass(frozen=True, slots=True)
class NearDuplicatePairScore:
    """One pair of distinct assets whose embedding cosine similarity met
    the sweep's own threshold -- the actual evidence a cluster is built
    from. A cluster's `members` may be transitively connected through a
    CHAIN of such pairs (A near-dups B, B near-dups C) without every pair
    inside the cluster independently qualifying (A vs C might score below
    threshold) -- `pairwise_scores` lists only the qualifying edges, never
    a fabricated full-connectivity claim.
    """

    asset_id_a: str
    asset_id_b: str
    confidence: float


@dataclass(frozen=True, slots=True)
class NearDuplicateClusterFinding:
    """Two or more distinct step-definition assets the sweep found
    semantically near-duplicate -- flagged for human consolidation review
    (ADR-0046 D3: "flag the cluster for human consolidation review, never
    auto-merge"). This record is the entire "action" the sweep takes: it
    is never used to merge, modify, or delete any asset (module docstring,
    and `suite_quality_governance.cp5.near_duplicate_sweep`'s own read-only
    contract).
    """

    members: tuple[NearDuplicateAssetRef, ...]
    pairwise_scores: tuple[NearDuplicatePairScore, ...]


@dataclass(frozen=True, slots=True)
class Cp5NearDuplicateSweepResult:
    """The near-dup sweep's own output -- `clusters` alone, deliberately no
    `overall_verdict` (module docstring: this component never gates,
    ADR-0046 D6). An empty `clusters` tuple means "nothing found," not
    "not swept" -- `suite_quality_governance.cp5.near_duplicate_sweep.
    sweep_near_duplicates` requires a real `embedding_provider` (no silent
    no-op default), so a result always reflects an actual sweep.
    """

    clusters: tuple[NearDuplicateClusterFinding, ...]


__all__ = [
    "CRITERION_ORPHANED_GLUE",
    "FINDING_SOURCE_NEAR_DUPLICATE_SWEEP",
    "Cp5NearDuplicateSweepResult",
    "Cp5OrphanedGlueResult",
    "NearDuplicateAssetRef",
    "NearDuplicateClusterFinding",
    "NearDuplicatePairScore",
    "OrphanedAssetFinding",
    "SemanticOrphanHint",
]
