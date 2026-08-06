"""Stage 16 -- Suite Quality Governance (ADR-0036, ADR-0046): CP5 wired as a
resumable, persisted run/stage-state stage, mirroring stage 15's own
integration shape (:mod:`automation_engineering.stage.runner`) exactly.

**This module composes CP5's already-built capstone
(:func:`suite_quality_governance.cp5.promotion_wrap.evaluate_promotion_wrap`)
-- it builds no new CP5 logic.** Every orphan/near-dup/cohesion decision is
made by the CP5 package itself; this module only resolves CP5's own inputs
from stage 15's already-persisted artifacts, derives the one input CP5
needs that no prior module derives (the WHOLE tracked feature corpus's own
step needs, ADR-0046 D2/D7), and persists the result -- the identical "GLUE,
not a fifth CP5 component" posture stage 15's own module docstring already
establishes for ITS six subsystems.

**Wrap order (ADR-0046 D4), satisfied by WHEN this stage is invoked, not by
anything in this module's own code.** D4 requires CP5 to run "after
per-asset promotion stages (`git add`)... and before whatever turns that
staged change into a commit." Nothing in this codebase ever calls `git
commit` (`automation_engineering.promotion.mechanism`'s own module
docstring: stage-for-review, never auto-commit), so the only ordering this
module must honor is running AFTER stage 15's own `stage_promoted_assets`
call has returned. The CLI wiring (`scripts.run_requirement_analysis
.handle_analyze`) enforces this by construction: this stage's own
`execute_suite_quality_governance_stage` is only ever invoked once
`execute_automation_engineering_stage` has already returned (SUCCEEDED or
SKIPPED-unchanged) for the current invocation -- nothing runs between stage
15's own promotion-staging step and this stage's own `reconcile()` call
inside CP5's capstone.

**Run-state choice: a real stage (16), not a sub-step folded into stage
15's own record -- the ADR wins over this task's own pre-flight framing.**
ADR-0036's own `requirement_intelligence.run_state.stages.STAGE_DEFINITIONS`
already reserves `stage_id="suite_quality_governance"`, `stage_number=16`,
`layer="L4"` -- distinct from stage 15's own `"automation_engineering"` /
`layer="L3"` entry -- Accepted before this task began. ADR-0031 draws
Layer 3/4's boundary deliberately, layer by layer; CP5 is explicitly
Layer 4's own content (ADR-0046 D1), not Layer 3's, and folding it
anonymously into stage 15's own run-state record would leave the
already-reserved stage-16 slot permanently PENDING even once CP5 has a
real, live entry point -- silently re-opening exactly the class of
ADR-0036-vs-implementation mismatch `stages.py`'s own module docstring is
already vigilant about flagging for stages 1-13. This is reported per this
task's own governing rule: where the task's pre-flight framing ("the
wiring is INTO the existing stage-15 promotion flow, NOT a standalone new
stage") and the Accepted ADR disagree, the ADR wins. The two are not
actually in tension on the only question ADR-0046 D4 itself binds (WHEN
CP5 runs, relative to staging) -- D4 says nothing about which run-state
record owns the bookkeeping, and stage 15's own precedent (CP3/CP4/
promotion folded into ONE `automation_engineering` record) is not
analogous: CP3/CP4/promotion are Layer 3's OWN control points, while CP5 is
a DIFFERENT layer's, with its own ADR-0036-reserved number already on the
books.
"""

from __future__ import annotations

from pathlib import Path

from automation_engineering.catalog.scanner import JAVA_SOURCE_SUBPATH
from automation_engineering.reuse.embeddings import EmbeddingProvider
from automation_engineering.reuse.models import GherkinStepNeed
from automation_engineering.stage.gherkin_needs import (
    derive_feature_step_needs,
    derive_unique_step_needs,
)
from automation_engineering.stage.models import (
    AUTOMATION_ENGINEERING_PACKAGE_FILENAME,
    PROMOTION_REPORT_FILENAME,
)
from feature_engineering.stage.workspace import DEFAULT_BASELINE_ROOT, FEATURES_SUBPATH
from requirement_intelligence.run_state.atomic_write import atomic_write_json, read_json_if_valid
from requirement_intelligence.run_state.run_state_manager import RunStateManager
from shared.enums.base import ValidationVerdict
from suite_quality_governance.cp5.compile_check import CompileChecker
from suite_quality_governance.cp5.models import Cp5PromotionWrapResult
from suite_quality_governance.cp5.near_duplicate_sweep import DEFAULT_NEAR_DUPLICATE_THRESHOLD
from suite_quality_governance.cp5.orphaned_glue import DEFAULT_SEMANTIC_HINT_FLOOR
from suite_quality_governance.cp5.promotion_wrap import evaluate_promotion_wrap
from suite_quality_governance.stage.models import (
    CP5_REPORT_FILENAME,
    SUITE_QUALITY_GOVERNANCE_REPORT_FILENAME,
    SuiteQualityGovernanceStageResult,
)

STAGE_ID = "suite_quality_governance"


def _derive_whole_corpus_step_needs(baseline_root: Path) -> tuple[GherkinStepNeed, ...]:
    """CP5's orphan check must be handed "every `.feature` file the
    tracked baseline carries, not merely the run's own newly generated
    ones" (ADR-0046 D2) -- a different scope than stage 15's own
    `derive_feature_step_needs` callers, which derive needs from only THIS
    run's eligible `FeatureRecord`s. ADR-0046 D7 names exactly this as
    "new wiring, unchanged functions": this reuses
    `derive_feature_step_needs`/`derive_unique_step_needs` verbatim,
    pointed at every `.feature` file already committed under
    `baseline_root / FEATURES_SUBPATH` instead of one run's workspace.

    No promoted asset is ever a `.feature` file (promotion's own type
    signature excludes it -- step definitions and test-data classes only,
    ADR-0044 D7), so this glob need not special-case "assembled state"
    the way CP5's own `reconcile()` call already does for Java sources --
    the tracked baseline's feature corpus does not change shape as a
    side effect of promotion.
    """
    features_root = baseline_root / FEATURES_SUBPATH
    if not features_root.exists():
        return ()
    per_feature = tuple(
        derive_feature_step_needs(
            feature_path.read_text(encoding="utf-8"), file_path=feature_path
        )
        for feature_path in sorted(features_root.rglob("*.feature"))
    )
    return derive_unique_step_needs(per_feature)


def _read_staged_relative_paths(run_dir: Path) -> tuple[Path, ...]:
    """CP5's `CompileAttribution` enrichment (`suite_quality_governance.cp5
    .promotion_wrap`) expects `staged_paths` shaped like
    `Promoted.candidate.relative_path` -- relative to
    `JAVA_SOURCE_SUBPATH`, e.g. `com/automation/steps/X.java`. Stage 15's
    own `promotion_report.json` persists `promotedPaths` relative to
    `baseline_root` instead (`src/test/java/com/automation/steps/X.java`,
    `.runner._build_report`'s own neighbor code), so this strips the
    shared `JAVA_SOURCE_SUBPATH` prefix rather than re-deriving anything --
    reads an already-persisted artifact, per ADR-0036 D2, never the
    in-memory `AutomationEngineeringStageResult` object (this stage is
    independently resumable, the same standalone-from-artifacts posture
    stage 15 itself already established relative to stage 14).

    An empty tuple both when the file is missing and when this run (or the
    run being resumed from) staged nothing -- both are legitimate,
    already-tested CP5 inputs (`test_suite_quality_governance_cp5_
    promotion_wrap.py::TestDecision2CompileAttributionEnrichmentNeverAGate
    ::test_no_staged_paths_at_all_is_attributed_as_predating_this_run`).
    """
    raw = read_json_if_valid(run_dir / PROMOTION_REPORT_FILENAME)
    if raw is None:
        return ()
    return tuple(
        Path(p).relative_to(JAVA_SOURCE_SUBPATH) for p in raw.get("promotedPaths", ())
    )


def _cp5_result_to_json(result: Cp5PromotionWrapResult) -> dict[str, object]:
    return {
        "overallVerdict": result.overall_verdict.value,
        "cohesion": {
            "overallVerdict": result.cohesion.overall_verdict.value,
            "criteria": [
                {"criterion": c.criterion, "verdict": c.verdict.value, "messages": list(c.messages)}
                for c in result.cohesion.criteria
            ],
        },
        "compileAttribution": (
            {
                "involvesStagedFiles": result.compile_attribution.involves_staged_files,
                "detail": result.compile_attribution.detail,
            }
            if result.compile_attribution is not None
            else None
        ),
        "orphanedGlue": {
            "overallVerdict": result.orphaned_glue.overall_verdict.value,
            "findings": [
                {
                    "assetId": f.asset_id,
                    "className": f.class_name,
                    "methodName": f.method_name,
                    "pattern": f.pattern,
                    "semanticHint": (
                        {
                            "closestNeedText": f.semantic_hint.closest_need_text,
                            "confidence": f.semantic_hint.confidence,
                        }
                        if f.semantic_hint is not None
                        else None
                    ),
                }
                for f in result.orphaned_glue.findings
            ],
        },
        "nearDuplicates": {
            "clusters": [
                {
                    "members": [
                        {
                            "assetId": m.asset_id,
                            "className": m.class_name,
                            "methodName": m.method_name,
                            "pattern": m.pattern,
                        }
                        for m in cluster.members
                    ],
                    "pairwiseScores": [
                        {
                            "assetIdA": p.asset_id_a,
                            "assetIdB": p.asset_id_b,
                            "confidence": p.confidence,
                        }
                        for p in cluster.pairwise_scores
                    ],
                }
                for cluster in result.near_duplicates.clusters
            ],
        },
        "hasReviewWorthyFindings": result.has_review_worthy_findings,
    }


def _build_report(result: Cp5PromotionWrapResult, staged_paths: tuple[Path, ...]) -> str:
    lines = [
        "# Suite Quality Governance Stage Report (Stage 16, CP5)",
        "",
        f"- Assets staged by this run's promotion: {len(staged_paths)}",
        f"- Cohesion verdict: {result.cohesion.overall_verdict.value}",
        f"- Orphaned-glue verdict: {result.orphaned_glue.overall_verdict.value}",
        f"- Near-duplicate clusters found (advisory): {len(result.near_duplicates.clusters)}",
        f"- CP5 overall verdict: {result.overall_verdict.value}",
    ]
    if result.compile_attribution is not None:
        lines.append(f"- Compile-failure attribution: {result.compile_attribution.detail}")
    if not result.passed:
        lines.append("")
        lines.append(
            "## Suite-level reject -- routed to the shared human review queue "
            "(ADR-0045 D3/ADR-0046 D4)"
        )
        lines.append(
            "The staged diff this run's promotion left is untouched -- never unstaged, "
            "never committed, never auto-fixed (ADR-0046 D4/D5)."
        )
        for finding in result.orphaned_glue.findings:
            lines.append(
                f"- orphaned glue: {finding.class_name}.{finding.method_name} "
                f"(pattern: {finding.pattern!r})"
            )
        for c in result.cohesion.criteria:
            if c.verdict != ValidationVerdict.PASS:
                for message in c.messages:
                    lines.append(f"- {c.criterion}: {message}")
    if result.near_duplicates.clusters:
        lines.append("")
        lines.append("## Near-duplicate clusters (advisory -- never blocks)")
        for cluster in result.near_duplicates.clusters:
            names = ", ".join(f"{m.class_name}.{m.method_name}" for m in cluster.members)
            lines.append(f"- {names}")
    return "\n".join(lines) + "\n"


def run_suite_quality_governance_stage(
    run_dir: Path,
    staged_paths: tuple[Path, ...],
    *,
    compile_checker: CompileChecker,
    embedding_provider: EmbeddingProvider,
    baseline_root: Path = DEFAULT_BASELINE_ROOT,
    near_dup_threshold: float = DEFAULT_NEAR_DUPLICATE_THRESHOLD,
    semantic_hint_floor: float = DEFAULT_SEMANTIC_HINT_FLOOR,
) -> SuiteQualityGovernanceStageResult:
    """Run CP5's capstone over `baseline_root`'s assembled, post-staging
    state and persist the result. Call this only after stage 15's own
    `stage_promoted_assets` has already run for the current invocation
    (module docstring) -- this function performs no promotion itself and
    never calls `git`.
    """
    current_needs = _derive_whole_corpus_step_needs(baseline_root)
    result = evaluate_promotion_wrap(
        baseline_root,
        staged_paths,
        current_needs,
        compile_checker=compile_checker,
        embedding_provider=embedding_provider,
        near_dup_threshold=near_dup_threshold,
        semantic_hint_floor=semantic_hint_floor,
    )

    cp5_report_path = run_dir / CP5_REPORT_FILENAME
    atomic_write_json(cp5_report_path, _cp5_result_to_json(result))

    report_path = run_dir / SUITE_QUALITY_GOVERNANCE_REPORT_FILENAME
    report_path.write_text(_build_report(result, staged_paths), encoding="utf-8")

    return SuiteQualityGovernanceStageResult(
        result=result, cp5_report_path=cp5_report_path, report_path=report_path
    )


def execute_suite_quality_governance_stage(
    run_state_mgr: RunStateManager,
    run_dir: Path,
    *,
    compile_checker: CompileChecker,
    embedding_provider: EmbeddingProvider,
    baseline_root: Path = DEFAULT_BASELINE_ROOT,
    near_dup_threshold: float = DEFAULT_NEAR_DUPLICATE_THRESHOLD,
    semantic_hint_floor: float = DEFAULT_SEMANTIC_HINT_FLOOR,
) -> SuiteQualityGovernanceStageResult | None:
    """Wire stage 16 into `run_state_mgr` with the SAME
    `start_stage`/try-except/`fail_stage`/`succeed_stage` idiom stages 14
    and 15 both already use.

    Reads its own upstream artifacts -- `automation_engineering_package
    .json` and `promotion_report.json` -- directly from `run_dir`, never
    an in-process handoff from stage 15 (ADR-0036 D2: "stage inputs must
    be artifact paths"), the same standalone-resumable posture
    `execute_automation_engineering_stage` already established relative
    to stage 14.

    Returns `None` both when the stage was SKIPPED and when it FAILED --
    the caller reads `run_state_mgr.state` for which, mirroring stage 15's
    own contract exactly.
    """
    input_artifacts = [
        run_dir / AUTOMATION_ENGINEERING_PACKAGE_FILENAME,
        run_dir / PROMOTION_REPORT_FILENAME,
    ]
    prior = next((s for s in run_state_mgr.state.stages if s.stage_id == STAGE_ID), None)
    prior_outputs = [Path(p) for p in (prior.output_artifacts if prior else ())]
    if prior_outputs and run_state_mgr.should_skip(
        STAGE_ID, input_artifacts=input_artifacts, output_artifacts=prior_outputs
    ):
        run_state_mgr.skip_stage(STAGE_ID)
        return None

    run_state_mgr.start_stage(STAGE_ID, input_artifacts=input_artifacts)
    try:
        staged_paths = _read_staged_relative_paths(run_dir)
        result = run_suite_quality_governance_stage(
            run_dir,
            staged_paths,
            compile_checker=compile_checker,
            embedding_provider=embedding_provider,
            baseline_root=baseline_root,
            near_dup_threshold=near_dup_threshold,
            semantic_hint_floor=semantic_hint_floor,
        )
    except Exception as exc:  # surfaced via run_state.json, never fatal to the caller's process
        run_state_mgr.fail_stage(STAGE_ID, error=exc)
        return None
    else:
        run_state_mgr.succeed_stage(STAGE_ID, output_artifacts=list(result.all_output_paths))
        return result


__all__ = [
    "STAGE_ID",
    "execute_suite_quality_governance_stage",
    "run_suite_quality_governance_stage",
]
