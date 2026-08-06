"""CP5, component 2 of 4 -- the cross-suite near-duplicate sweep (ADR-0046
D3, D6). This module builds ONLY this component. It does not build
orphaned-glue detection (component 1, already built, `.orphaned_glue`),
promotion-wrapping, or aggregate-release cohesion (ADR-0046 D4-D5) --
CP5's other three components.

ADR-0046 D3, quoted in full, is this component's own binding spec:

    "The sweep is scoped to step definitions only, matching both ADR-0040
    Decision 3's own literal text ('no near-duplicate step definitions
    across the suite') and `LiveSemanticMatcher`'s existing implementation
    scope... Mechanism: reuse the embedding boundary's existing
    one-batched-call shape, never rebuild it... Cluster threshold: default
    0.90, configurable... Action: flag the cluster for human consolidation
    review, never auto-merge."

**Distinct from ADR-0045 D2(b), by design, not by accident.** D2(b) is an
exact, content-hash duplicate check, performed per candidate, at PROMOTION
TIME, against the tracked baseline (`AssetCatalog.by_content_hash`) -- it
catches BYTE-IDENTICAL re-promotion only, nothing else. This sweep is
SEMANTIC, SUITE-WIDE, and RETROSPECTIVE: it finds clusters of step
definitions that are each individually content-hash-UNIQUE (so D2(b)
correctly let each one promote on its own run) but express near-identical
intent, most plausibly because independent generation across different
runs solved the same need slightly differently. D2(b) answers "is this
NEW candidate a byte-for-byte copy of something already in the baseline";
this sweep answers "do any TWO OR MORE assets already in the baseline do
nearly the same thing." Two different questions, two different mechanisms,
both legitimate -- this module proves the distinction directly
(`tests/unit/test_suite_quality_governance_cp5_near_duplicate_sweep.py::
TestDistinctFromD2bContentHashCheck`).

**Advisory, not gating (ADR-0046 D6).** ADR-0046 D6's own composition
table names this component "Advisory | Review-trigger only, never gates --
same discipline as the reuse engine's own confidence-based escalation
(ADR-0044 D4(a))." `Cp5NearDuplicateSweepResult` therefore carries no
`overall_verdict` -- there is no PASS/FAIL for a component that
structurally never gates CP5's own PASS/FAIL (see
`suite_quality_governance.cp5.models`'s own module docstring for why the
result shape itself encodes this, rather than a comment a future caller
could ignore).

**Read-only by construction**, mirroring component 1 exactly: this module
takes an already-reconciled `AssetCatalog` and an `EmbeddingProvider` and
returns a result. It never merges, modifies, or deletes any asset (ADR-0046
D3: "never auto-merge"; ADR-0046 Recommendation 2).

**`embedding_provider` is REQUIRED here, unlike component 1's optional
one.** Orphaned-glue detection has a genuine deterministic-only path (its
gate does not need embeddings at all); this sweep's ENTIRE determination
IS semantic similarity -- there is no non-embedding way to find a
near-duplicate CLUSTER. Making `embedding_provider` optional with a silent
`None`-skips-everything default would make "not swept" and "swept, found
nothing" indistinguishable from the return value alone; requiring a real
provider keeps a returned `Cp5NearDuplicateSweepResult` always meaning
"this catalog was actually compared."
"""

from __future__ import annotations

import itertools
from collections import defaultdict
from collections.abc import Iterable, Sequence

from automation_engineering.catalog.models import AssetCatalog, StepDefinitionAsset
from automation_engineering.reuse.embeddings import EmbeddingProvider, cosine_similarity
from automation_engineering.reuse.live_matcher import step_definition_embedding_text
from suite_quality_governance.cp5.models import (
    Cp5NearDuplicateSweepResult,
    NearDuplicateAssetRef,
    NearDuplicateClusterFinding,
    NearDuplicatePairScore,
)

#: ADR-0046 D3's own locked default: a small, explicit margin above the
#: real, live-measured paraphrase score (`0.8980`) already on record
#: (`automation_engineering.reuse.engine`'s own `DEFAULT_CONFIDENCE_THRESHOLD`/
#: `DEFAULT_GENERATE_FLOOR` docstrings) -- reused as evidence here, not
#: re-measured, because cosine similarity is symmetric regardless of which
#: side of a comparison is labeled "need" and which "catalog asset."
#: Configurable, not a proven constant (ADR-0046's own Consequences: "tune
#: against real observed near-duplicate pairs once the catalog has some").
DEFAULT_NEAR_DUPLICATE_THRESHOLD = 0.90


class _UnionFind:
    """Minimal disjoint-set over asset ids -- transitive clustering (A
    near-dups B, B near-dups C => A, B, and C are ONE cluster, even if A
    and C never independently score above threshold). Path compression
    only (no union-by-rank): this platform's real catalog scale (34
    step-definition-bearing files, component 1's own measurement) makes
    the asymptotic difference irrelevant; simplicity is the better trade
    here.
    """

    def __init__(self, items: Iterable[str]) -> None:
        self._parent: dict[str, str] = {item: item for item in items}

    def find(self, item: str) -> str:
        while self._parent[item] != item:
            self._parent[item] = self._parent[self._parent[item]]
            item = self._parent[item]
        return item

    def union(self, a: str, b: str) -> None:
        root_a, root_b = self.find(a), self.find(b)
        if root_a != root_b:
            self._parent[root_a] = root_b


def _qualifying_pairs(
    assets: Sequence[StepDefinitionAsset],
    vectors: Sequence[tuple[float, ...]],
    threshold: float,
) -> tuple[tuple[StepDefinitionAsset, StepDefinitionAsset, float], ...]:
    """Every DISTINCT pair of assets (no self-comparison -- `itertools.
    combinations` never pairs an index with itself) whose cosine similarity
    meets `threshold`. O(n^2) comparisons, but pure in-memory arithmetic
    over already-fetched vectors -- no further network call (module
    docstring)."""
    pairs: list[tuple[StepDefinitionAsset, StepDefinitionAsset, float]] = []
    for i, j in itertools.combinations(range(len(assets)), 2):
        score = cosine_similarity(vectors[i], vectors[j])
        if score >= threshold:
            pairs.append((assets[i], assets[j], score))
    return tuple(pairs)


def _build_clusters(
    qualifying_pairs: Sequence[tuple[StepDefinitionAsset, StepDefinitionAsset, float]],
    assets_by_id: dict[str, StepDefinitionAsset],
) -> tuple[NearDuplicateClusterFinding, ...]:
    """Group qualifying pairs into transitively-connected clusters (a
    connected component of size >= 2 in the "scores >= threshold" graph),
    each carrying only the pairwise scores that actually qualified -- never
    a fabricated full-connectivity claim (see `NearDuplicatePairScore`'s
    own docstring)."""
    involved_ids = {a.asset_id for a, _, _ in qualifying_pairs} | {
        b.asset_id for _, b, _ in qualifying_pairs
    }
    union_find = _UnionFind(involved_ids)
    for asset_a, asset_b, _ in qualifying_pairs:
        union_find.union(asset_a.asset_id, asset_b.asset_id)

    member_ids_by_root: dict[str, set[str]] = defaultdict(set)
    for asset_id in involved_ids:
        member_ids_by_root[union_find.find(asset_id)].add(asset_id)

    clusters: list[NearDuplicateClusterFinding] = []
    for member_ids in member_ids_by_root.values():
        sorted_ids = sorted(member_ids)
        members = tuple(
            NearDuplicateAssetRef(
                asset_id=assets_by_id[asset_id].asset_id,
                class_name=assets_by_id[asset_id].class_name,
                method_name=assets_by_id[asset_id].method_name,
                pattern=assets_by_id[asset_id].pattern,
            )
            for asset_id in sorted_ids
        )
        member_id_set = set(sorted_ids)
        pairwise_scores = tuple(
            sorted(
                (
                    NearDuplicatePairScore(
                        asset_id_a=asset_a.asset_id, asset_id_b=asset_b.asset_id, confidence=score
                    )
                    for asset_a, asset_b, score in qualifying_pairs
                    if asset_a.asset_id in member_id_set and asset_b.asset_id in member_id_set
                ),
                key=lambda pair: (pair.asset_id_a, pair.asset_id_b),
            )
        )
        clusters.append(
            NearDuplicateClusterFinding(members=members, pairwise_scores=pairwise_scores)
        )

    # Deterministic output order, independent of union-find's own
    # arbitrary root choice -- sort by each cluster's own (already sorted)
    # first member id.
    clusters.sort(key=lambda cluster: cluster.members[0].asset_id)
    return tuple(clusters)


def sweep_near_duplicates(
    catalog: AssetCatalog,
    *,
    embedding_provider: EmbeddingProvider,
    threshold: float = DEFAULT_NEAR_DUPLICATE_THRESHOLD,
) -> Cp5NearDuplicateSweepResult:
    """CP5's cross-suite near-duplicate sweep (ADR-0046 D3). `catalog` is
    an already-reconciled, caller-supplied input -- this function never
    scans a filesystem or mutates it.

    Scoped to `catalog.step_definitions` only (module docstring; ADR-0040
    Decision 3's own literal text, and `LiveSemanticMatcher`'s existing
    scope). Embeds every step-definition's text in exactly ONE batched
    `embedding_provider.embed(...)` call -- the whole catalog, regardless
    of size, never one call per asset or per pair -- then computes every
    pairwise cosine similarity in memory (no further call) and groups
    qualifying pairs into transitively-connected clusters.

    Deterministic given a deterministic `embedding_provider` (true of the
    stub used throughout this module's own test suite): the same
    `(catalog, threshold)` pair, against the same embedding responses,
    always yields the same clusters, same order.
    """
    assets = catalog.step_definitions
    if len(assets) < 2:
        return Cp5NearDuplicateSweepResult(clusters=())

    texts = [step_definition_embedding_text(asset) for asset in assets]
    vectors = embedding_provider.embed(texts)

    qualifying_pairs = _qualifying_pairs(assets, vectors, threshold)
    if not qualifying_pairs:
        return Cp5NearDuplicateSweepResult(clusters=())

    assets_by_id = {asset.asset_id: asset for asset in assets}
    return Cp5NearDuplicateSweepResult(clusters=_build_clusters(qualifying_pairs, assets_by_id))


__all__ = ["DEFAULT_NEAR_DUPLICATE_THRESHOLD", "sweep_near_duplicates"]
