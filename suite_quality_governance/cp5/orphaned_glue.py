"""CP5, component 1 of 4 -- orphaned-glue detection (ADR-0046 D2, D6).

Detects tracked-baseline step-definition assets that **no current feature
references** -- dead automation accumulated across runs (ADR-0040 Decision
3: "every step definition resolves to at least one scenario (no orphaned
glue)"). This module builds ONLY this component. It does not build the
cross-suite near-duplicate sweep, promotion-wrapping, or aggregate-release
cohesion (ADR-0046 D3-D5) -- CP5's other three components, future tasks.

**Read-only by construction.** This module takes an already-reconciled
`AssetCatalog` and an already-derived sequence of current `GherkinStepNeed`s
as inputs and returns a result -- it performs no file write, no `git`
call, no catalog mutation of any kind. It never deletes or modifies a
baseline asset (ADR-0046 D2: "flag for review, never auto-remove"; ADR-0046
Recommendation 2, binding). The caller is responsible for deriving
`current_needs` from the WHOLE current tracked feature corpus (every
`.feature` file the baseline carries, not merely one run's own new ones,
ADR-0046 D2) via `automation_engineering.stage.gherkin_needs.
derive_feature_step_needs`/`derive_unique_step_needs`, unchanged, and for
reconciling `catalog` via `automation_engineering.catalog.scanner.
reconcile` -- this module never scans a filesystem itself, mirroring
`automation_engineering.cp4.gate.evaluate_cp4`'s own "gates on what it's
handed" discipline.

**The deterministic gate (primary, ADR-0046 D6).** A step-definition asset
is orphaned iff `suite_quality_governance.cp5.pattern_matching.
pattern_matches_text` returns `False` for every current need's own text
against that asset's own pattern -- reproducing Cucumber-JVM's own literal
glue-binding rule, no embedding, no live call. This is CP5's own PASS/FAIL
evidence (ADR-0040 Decision 2's deterministic-only gate discipline).

**The semantic advisory (secondary, non-gating, ADR-0046 D6).** For an
asset the deterministic gate already flagged, an OPTIONAL embedding-based
hint records whether some current need's text is close in meaning to the
orphaned asset's own text -- e.g. a feature reworded a step so the literal
pattern no longer matches even though the intent is plausibly still
wanted. Supplying `embedding_provider=None` (the default) skips this
entirely -- the deterministic verdict is complete and correct without it.
When supplied, this reuses the SAME embedding boundary the reuse engine
already uses (`automation_engineering.reuse.embeddings.EmbeddingProvider`,
`.cosine_similarity`) and the SAME per-asset text recipe
(`automation_engineering.reuse.live_matcher.step_definition_embedding_text`)
-- one batched `embed()` call for every orphaned asset plus every current
need, never a call per asset. The hint NEVER changes which assets are
orphaned; `Cp5OrphanedGlueResult.overall_verdict` is computed from the
deterministic gate's own findings before any hint is attached (see
`detect_orphaned_glue`'s own body -- the verdict line runs first).

**Layer 4 depending on Layer 3's own machinery.** This module -- and this
whole `cp5` package -- lives under `suite_quality_governance/`, ADR-0033's
own Layer 4 package, but imports `automation_engineering`'s catalog,
reuse-engine, and embedding modules directly: CP5 consumes what Layer 3
already built (ADR-0046 D7's own "reuses, does not rebuild" list), the
same cross-layer hand-off ADR-0044 D1 already describes for the Validated
Automation Package.
"""

from __future__ import annotations

from collections.abc import Sequence

from automation_engineering.catalog.models import AssetCatalog, StepDefinitionAsset
from automation_engineering.reuse.embeddings import EmbeddingProvider, cosine_similarity
from automation_engineering.reuse.engine import DEFAULT_GENERATE_FLOOR
from automation_engineering.reuse.live_matcher import step_definition_embedding_text
from automation_engineering.reuse.models import GherkinStepNeed
from shared.enums.base import ValidationVerdict
from suite_quality_governance.cp5.models import (
    Cp5OrphanedGlueResult,
    OrphanedAssetFinding,
    SemanticOrphanHint,
)
from suite_quality_governance.cp5.pattern_matching import pattern_matches_text

#: The semantic hint's own "worth mentioning at all" floor. Reuses
#: `automation_engineering.reuse.engine.DEFAULT_GENERATE_FLOOR` (0.70) --
#: the SAME real, live-calibrated "not even plausible" floor the reuse
#: engine already established (ADR-0044 D4's additive note: unrelated text
#: scored `[0.52, 0.67]` against this platform's embedding model; a
#: paraphrase of an existing pattern scored `0.8980`) -- rather than
#: inventing a second, uncalibrated threshold for a structurally identical
#: "is this even plausibly related" question.
DEFAULT_SEMANTIC_HINT_FLOOR = DEFAULT_GENERATE_FLOOR


def _find_orphaned(
    catalog: AssetCatalog, current_needs: Sequence[GherkinStepNeed]
) -> tuple[StepDefinitionAsset, ...]:
    """The deterministic gate: a step-definition asset is orphaned iff no
    current need's own text matches its own pattern. Pure, no embedding, no
    live call -- `pattern_matches_text` alone decides every case."""
    return tuple(
        asset
        for asset in catalog.step_definitions
        if not any(pattern_matches_text(asset.pattern, need.text) for need in current_needs)
    )


def _semantic_hints(
    orphaned: Sequence[StepDefinitionAsset],
    current_needs: Sequence[GherkinStepNeed],
    embedding_provider: EmbeddingProvider,
    semantic_hint_floor: float,
) -> dict[str, SemanticOrphanHint | None]:
    """One hint per orphaned asset (keyed by `asset_id`), or `None` where no
    current need scored above `semantic_hint_floor`. ONE batched
    `embed()` call for every orphaned asset's text plus every current
    need's text -- never a call per asset (mirrors
    `automation_engineering.reuse.live_matcher.LiveSemanticMatcher.prime`'s
    own one-batched-call discipline). A no-op (empty dict) when `orphaned`
    or `current_needs` is empty -- nothing to compare, nothing to embed.
    """
    if not orphaned or not current_needs:
        return {asset.asset_id: None for asset in orphaned}

    asset_texts = [step_definition_embedding_text(asset) for asset in orphaned]
    need_texts = [need.text for need in current_needs]
    vectors = embedding_provider.embed([*asset_texts, *need_texts])
    asset_vectors = vectors[: len(orphaned)]
    need_vectors = vectors[len(orphaned) :]

    hints: dict[str, SemanticOrphanHint | None] = {}
    for asset, asset_vector in zip(orphaned, asset_vectors, strict=True):
        best_need: GherkinStepNeed | None = None
        best_score = -1.0
        for need, need_vector in zip(current_needs, need_vectors, strict=True):
            score = cosine_similarity(asset_vector, need_vector)
            if score > best_score:
                best_score, best_need = score, need
        if best_need is not None and best_score >= semantic_hint_floor:
            hints[asset.asset_id] = SemanticOrphanHint(
                closest_need_text=best_need.text, confidence=best_score
            )
        else:
            hints[asset.asset_id] = None
    return hints


def detect_orphaned_glue(
    catalog: AssetCatalog,
    current_needs: Sequence[GherkinStepNeed],
    *,
    embedding_provider: EmbeddingProvider | None = None,
    semantic_hint_floor: float = DEFAULT_SEMANTIC_HINT_FLOOR,
) -> Cp5OrphanedGlueResult:
    """CP5's orphaned-glue component (ADR-0046 D2). `catalog` and
    `current_needs` are both already-derived, caller-supplied inputs --
    this function never scans a filesystem or mutates either.

    Deterministic and side-effect-free with `embedding_provider=None`
    (every test in this module's own test suite uses this path): the same
    `(catalog, current_needs)` pair always yields the same
    `overall_verdict` and the same orphaned-asset set. Supplying a live
    `embedding_provider` only ever ADDS `semantic_hint` data to an
    already-orphaned finding -- it can never add, remove, or reorder which
    assets are orphaned (see module docstring).
    """
    orphaned = _find_orphaned(catalog, current_needs)
    overall_verdict = ValidationVerdict.FAIL if orphaned else ValidationVerdict.PASS

    hints: dict[str, SemanticOrphanHint | None] = (
        _semantic_hints(orphaned, current_needs, embedding_provider, semantic_hint_floor)
        if embedding_provider is not None
        else {asset.asset_id: None for asset in orphaned}
    )

    findings = tuple(
        OrphanedAssetFinding(
            asset_id=asset.asset_id,
            class_name=asset.class_name,
            method_name=asset.method_name,
            pattern=asset.pattern,
            semantic_hint=hints[asset.asset_id],
        )
        for asset in orphaned
    )
    return Cp5OrphanedGlueResult(overall_verdict=overall_verdict, findings=findings)


__all__ = ["DEFAULT_SEMANTIC_HINT_FLOOR", "detect_orphaned_glue"]
