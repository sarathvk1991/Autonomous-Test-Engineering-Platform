"""CP5, component 3 of 4 -- the CAPSTONE: promotion-wrapping (ADR-0046 D4).
Composes the other three CP5 components (orphaned-glue detection, the
cross-suite near-duplicate sweep, aggregate-release cohesion) into ONE
suite-level gate that wraps ADR-0045's per-asset promotion mechanism --
exactly what ADR-0045 D1 anticipated: "Layer 4, once built, may wrap this
promotion decision in richer suite-level governance."

ADR-0046 D4, quoted in full, is this component's own binding spec:

    "CP5 runs after per-asset promotion stages (`git add`, never `git
    commit`... and before whatever turns that staged change into a
    commit... A suite-level reject leaves the staged diff exactly as
    promotion left it -- untouched, visible, unresolved... Routing: the
    same shared human review queue ADR-0045 D3 already established -- not
    a third, CP5-specific queue... This does not re-litigate ADR-0045
    D2/D3 -- it wraps them, unchanged."

**DECISION 1 (composition) -- resolved by the ALREADY-ACCEPTED ADR-0046
D6, not invented here.** D6's own composition table states this directly:
"Promotion-wrapping reject (D4) | Composed | A deterministic-check
failure (orphan-by-pattern, exact glue collision, compile failure) MAY
GATE CP5 DIRECTLY; a near-dup-only finding routes to review... WITHOUT by
itself flipping CP5's verdict." **This is a direct instruction from the
task that built this module, surfaced and resolved here per the task's
own governing rule ("where this prompt and an Accepted ADR disagree, the
ADR wins"):** the task's own pre-flight framing suggested orphaned-glue
might be "arguably flag-for-review, not a hard block" -- ADR-0046 D6's own
table, already Accepted before this task began, says otherwise: orphan-
by-pattern is named explicitly, alongside cohesion, as a check that "may
gate CP5 directly." `overall_verdict` below therefore composes BOTH
`cohesion` and `orphaned_glue` as hard gates, and `near_duplicates` as
advisory-only, per D6's literal text, not the task's own suggested lean.

**DECISION 2 (the pre-existing compile failure) -- resolved as an
ABSOLUTE gate plus honest attribution, not a delta gate.** ADR-0046 D5's
own text locks "does the assembled suite compile" -- a check on the suite
AS ASSEMBLED, not "did this promotion's own delta make compilation worse."
No delta-gating language exists anywhere in the Accepted ADR-0046 text;
building one here would be unauthorized scope, not a faithful
implementation of D5. Component 4's own build already found, live, that
the real tracked baseline does not currently compile (`suite_quality_
governance/README.md`) -- under an absolute gate, this is a genuine,
correct suite-reject, not a bug. What this module adds, so a real
pre-existing defect is never silently mistaken for something a specific
promotion caused, is `CompileAttribution` (`.models`): whenever the
`compiles` criterion fails, its error messages (which carry real file
paths, `compile_check.py`'s own `_parse_compile_errors`) are checked
against the paths THIS run's promotion just staged. This is enrichment
only -- it changes nothing about whether the gate fails, only what a
reviewer is told about why.

**Wrap order and the working-tree read -- zero new plumbing.** This
module reconciles `baseline_root` AFTER per-asset promotion has already
run `apply_promotion`/`stage_promoted_assets` (`automation_engineering.
promotion.mechanism`, unchanged, not called from here) -- `scanner.
reconcile()` reads the working tree directly, not git's index or commit
history (proven end-to-end by `tests/unit/
test_automation_engineering_promotion_loop.py`'s own loop-closing proof),
so a fresh `reconcile()` call here already sees the assembled
baseline-plus-staged state with no new file-reading mechanism.

**Read-only w.r.t. git, always.** This module never calls `git commit`,
`git add`, `git restore`, or any other git-mutating command -- it reads
(`reconcile`, the compile checker's own subprocess) and returns a
verdict. A suite-reject leaves the staged diff exactly as per-asset
promotion left it; this module does not unstage it, does not commit it,
does not modify any asset. `automation_engineering.promotion.mechanism`
(staging) and whatever future step turns a clean, reviewed stage into a
commit are both entirely outside this module's own responsibility.

**Routing -- no new queue, the same discipline every layer in this
platform already uses.** `Cp5PromotionWrapResult` (`.models`) IS the
routing record: a structured finding, for a future human-in-the-loop
surface to render, mirroring `automation_engineering.reuse.engine`'s own
module docstring exactly ("a structured record carrying everything a
human needs... no separate queue, no new mechanism, built here"). No
`Escalation`/`PromotionEscalated` object is constructed or consulted here
-- those are need-shaped (ADR-0044 D4) and asset-promotion-shaped
(ADR-0045 D3) respectively, neither fits a SUITE-level composed verdict,
the same reasoning components 1/2 already used to justify CP5's own
finding shapes rather than forcing a fit.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from automation_engineering.catalog.scanner import reconcile
from automation_engineering.reuse.embeddings import EmbeddingProvider
from automation_engineering.reuse.models import GherkinStepNeed
from shared.enums.base import ValidationVerdict
from suite_quality_governance.cp5.cohesion import evaluate_cohesion
from suite_quality_governance.cp5.compile_check import CompileChecker
from suite_quality_governance.cp5.models import (
    CRITERION_COMPILES,
    CompileAttribution,
    Cp5PromotionWrapResult,
)
from suite_quality_governance.cp5.near_duplicate_sweep import (
    DEFAULT_NEAR_DUPLICATE_THRESHOLD,
    sweep_near_duplicates,
)
from suite_quality_governance.cp5.orphaned_glue import (
    DEFAULT_SEMANTIC_HINT_FLOOR,
    detect_orphaned_glue,
)


def _compile_attribution(
    cohesion_compile_messages: tuple[str, ...],
    staged_paths: Sequence[Path],
) -> CompileAttribution:
    """Does ANY compile-error message reference a file THIS run just
    staged (a plain substring check against each staged path's own
    POSIX-form relative path, present verbatim inside Maven's own
    absolute-path error text -- `compile_check.py`'s own real, observed
    output shape)? Enrichment only (module docstring) -- never gates."""
    staged_suffixes = tuple(path.as_posix() for path in staged_paths)
    involves_staged = any(
        any(suffix in message for suffix in staged_suffixes)
        for message in cohesion_compile_messages
    )
    if not staged_suffixes:
        detail = (
            "no files were staged by this promotion run; this compile failure predates it "
            "entirely (see suite_quality_governance/README.md's own recorded finding)"
        )
    elif involves_staged:
        detail = (
            f"{sum(1 for m in cohesion_compile_messages if any(s in m for s in staged_suffixes))} "
            f"of {len(cohesion_compile_messages)} compile error(s) reference a file this "
            "promotion just staged"
        )
    else:
        detail = (
            f"none of the {len(cohesion_compile_messages)} compile error(s) reference a file "
            "this promotion just staged -- this appears to be a pre-existing baseline compile "
            "failure, not introduced by this promotion"
        )
    return CompileAttribution(involves_staged_files=involves_staged, detail=detail)


def evaluate_promotion_wrap(
    baseline_root: Path,
    staged_paths: Sequence[Path],
    current_needs: Sequence[GherkinStepNeed],
    *,
    compile_checker: CompileChecker,
    embedding_provider: EmbeddingProvider,
    near_dup_threshold: float = DEFAULT_NEAR_DUPLICATE_THRESHOLD,
    semantic_hint_floor: float = DEFAULT_SEMANTIC_HINT_FLOOR,
) -> Cp5PromotionWrapResult:
    """CP5's capstone (ADR-0046 D4). Call this AFTER per-asset promotion
    (`automation_engineering.promotion`) has already applied and staged
    its own candidates -- `baseline_root` is that same tracked-baseline
    root, `staged_paths` are the `relative_path`s of whatever this run
    just staged (`Promoted.candidate.relative_path`, unchanged shape),
    used only for `CompileAttribution`'s own enrichment.

    Reconciles `baseline_root` fresh (module docstring: sees the
    assembled, post-staging state with no new plumbing), then runs the
    three prior CP5 components against that ONE reconciled catalog --
    never a second, independently-reconciled view -- and composes them
    per ADR-0046 D6 (module docstring, Decision 1).
    """
    catalog = reconcile(baseline_root)

    cohesion = evaluate_cohesion(catalog, baseline_root, compile_checker)
    orphaned_glue = detect_orphaned_glue(
        catalog,
        current_needs,
        embedding_provider=embedding_provider,
        semantic_hint_floor=semantic_hint_floor,
    )
    near_duplicates = sweep_near_duplicates(
        catalog, embedding_provider=embedding_provider, threshold=near_dup_threshold
    )

    compile_criterion = cohesion.criterion(CRITERION_COMPILES)
    compile_attribution = (
        _compile_attribution(compile_criterion.messages, staged_paths)
        if compile_criterion.verdict == ValidationVerdict.FAIL
        else None
    )

    overall_verdict = (
        ValidationVerdict.PASS
        if cohesion.overall_verdict == ValidationVerdict.PASS
        and orphaned_glue.overall_verdict == ValidationVerdict.PASS
        else ValidationVerdict.FAIL
    )

    return Cp5PromotionWrapResult(
        overall_verdict=overall_verdict,
        cohesion=cohesion,
        compile_attribution=compile_attribution,
        orphaned_glue=orphaned_glue,
        near_duplicates=near_duplicates,
    )


__all__ = ["evaluate_promotion_wrap"]
