"""Stage 15 -- Automation Engineering, wired as a resumable, persisted
run/stage-state stage (ADR-0036, ADR-0044), mirroring stage 14's own
integration shape (:mod:`feature_engineering.stage.runner`) exactly.

This module chains Layer 3's six already-built, independently-tested
subsystems -- catalog, reuse, generation, CP3, CP4, promotion -- into one
runnable stage. It is GLUE: every reuse/generation/gate/promotion decision
is made by the subsystem itself; this module only sequences the calls,
derives step needs from real Gherkin text (:mod:`.gherkin_needs`, the one
genuinely new but minimal piece), and persists the result.

The chain, in order
--------------------
1. Materialize (or reuse, idempotently) this run's per-run workspace
   (:func:`feature_engineering.stage.workspace.materialize_workspace`, the
   SAME function/workspace stage 14 already uses -- ADR-0037 Path A's
   workspace is one per RUN, not one per stage).
2. Reconcile the asset catalog from the TRACKED baseline, never the
   workspace (:func:`automation_engineering.catalog.scanner.reconcile`,
   ADR-0044 D3).
3. For every non-escalated feature stage 14 produced, derive its own
   ordered step needs from its real ``.feature`` text
   (:mod:`.gherkin_needs`), then dedupe to one need per unique step text
   across the whole run.
4. Reuse-decide/generate every unique step need, one
   (:func:`automation_engineering.generation.orchestrator.orchestrate_step_definition`)
   call per need -- not the batch ``generate_step_definitions`` helper,
   since 2026-08-05 (the free-tier survivability build): a per-need loop is
   what lets a transport failure on ONE need be escalated and the loop
   continue, rather than aborting the whole run (this module's own report,
   FIX 2). ``matcher.prime(...)`` is called once, first, so the embeddings
   MATCH itself still makes at most one batched call for the whole run's
   needs (FIX 1), not one call per need despite the per-need loop.
   ``page_object_request``/``utility_request`` are never supplied (see this
   module's own report: no subsystem derives "which specific page-object/
   utility method does this step need" from raw text), so every generated
   step definition's own ``page_object_outcome``/``utility_outcome`` stays
   ``None``, and no page-object/utility asset is ever produced by this
   initial wiring.
5. Generate every test-data specification stage 14 emitted (spec-driven,
   unconditional, no reuse decision -- ADR-0044 D7), also per-specification
   rather than batched, for the same transport-isolation reason as step 4.
6. Write every freshly generated class's Java source into the workspace
   (never the tracked baseline directly -- ADR-0037 D2), at the exact path
   :func:`automation_engineering.promotion.identity.resolve_candidate_identity`
   resolves it to -- the SAME identity mechanism promotion itself uses, so
   a written file and its own future promotion identity can never drift
   apart.
7. CP3 (:func:`automation_engineering.cp3.gate.evaluate_cp3`) over every
   feature's own outcomes, the Sonar adapter, and every freshly generated
   class; CP4 (:func:`automation_engineering.cp4.gate.evaluate_cp4`) over
   every freshly generated PAGE OBJECT -- honestly empty in this wiring
   (step 4's own scope boundary), so CP4 passes vacuously, exactly as its
   own established "empty input" convention already allows.
8. Promote every generated, non-test-data outcome
   (:func:`automation_engineering.promotion.outcomes.promote_outcome`),
   gated PER-CANDIDATE (ADR-0045 D2 additive note, 2026-08-06) against the
   SAME whole-run CP3 result and CP4 verdict step 7 already computed
   (:class:`~automation_engineering.promotion.models.AssetGateOutcomes`
   decomposes CP3 down to this candidate's own class; CP4 stays whole-batch,
   the same nature as CP3's own Sonar criterion) plus that outcome's owning
   feature's own CP2 verdict; write and stage (never commit) every
   ``Promoted`` result. A clean candidate promotes even when OTHER needs in
   the same run escalated or failed their own CP3 criteria.
9. Persist the Validated Automation Package plus the CP3/CP4/promotion
   reports.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from automation_engineering.catalog.models import AssetCatalog
from automation_engineering.catalog.scanner import JAVA_SOURCE_SUBPATH, reconcile
from automation_engineering.cp3.architecture import Cp3GeneratedClassInput
from automation_engineering.cp3.gate import Cp3SonarInput, evaluate_cp3
from automation_engineering.cp3.models import Cp3CoverageInput, Cp3FeatureInput, Cp3Result
from automation_engineering.cp3.sonar.adapter import SonarQualityGateAdapter
from automation_engineering.cp4.gate import evaluate_cp4
from automation_engineering.cp4.models import Cp4Result
from automation_engineering.errors import TransportFailureError
from automation_engineering.generation.models import (
    BoundStepDefinition,
    EscalatedStepNeed,
    GeneratedStepDefinition,
    GeneratedTestDataClass,
    StepDefinitionOutcome,
)
from automation_engineering.generation.orchestrator import orchestrate_step_definition
from automation_engineering.generation.step_definition_generator import StepDefinitionGenerator
from automation_engineering.generation.test_data_generator import TestDataGenerator
from automation_engineering.generation.test_data_orchestrator import generate_test_data_class
from automation_engineering.promotion.identity import resolve_candidate_identity
from automation_engineering.promotion.mechanism import apply_promotion, stage_promoted_assets
from automation_engineering.promotion.models import (
    AssetGateOutcomes,
    NotPromotable,
    Promoted,
    PromotionEscalated,
)
from automation_engineering.promotion.outcomes import promote_outcome
from automation_engineering.reuse.matcher import SemanticMatcher
from automation_engineering.stage.gherkin_needs import (
    FeatureStepNeeds,
    derive_feature_step_needs,
    derive_unique_step_needs,
)
from automation_engineering.stage.models import (
    AUTOMATION_ENGINEERING_PACKAGE_FILENAME,
    AUTOMATION_ENGINEERING_REPORT_FILENAME,
    CONTRACT_VERSION,
    CP3_REPORT_FILENAME,
    CP4_REPORT_FILENAME,
    PROMOTION_REPORT_FILENAME,
    AssetRecord,
    AutomationEngineeringPackage,
    AutomationEngineeringStageResult,
)
from contracts.test_data_specification import TestDataSpecification
from feature_engineering.stage.models import (
    FEATURE_ENGINEERING_PACKAGE_FILENAME,
    FeatureEngineeringPackage,
    FeatureRecord,
)
from feature_engineering.stage.test_data_spec import (
    TEST_DATA_SPECIFICATIONS_FILENAME as _FE_TEST_DATA_SPECIFICATIONS_FILENAME,
)
from feature_engineering.stage.workspace import (
    DEFAULT_BASELINE_ROOT,
    features_root_for,
    materialize_workspace,
)
from requirement_intelligence.run_state.atomic_write import atomic_write_json, read_json_if_valid
from requirement_intelligence.run_state.run_state_manager import RunStateManager
from shared.enums.base import ValidationVerdict

STAGE_ID = "automation_engineering"

#: The live SonarQube project this platform's own CP3 adapter, promotion
#: mechanism, and `test-suite-baseline/sonar/README.md` all already name
#: (`CUSTOMQA_PROFILE_NAME`'s own module docstring; the README's live proof).
#: One shared constant here so a future change to the target project is
#: made once, not independently in every caller.
DEFAULT_SONAR_PROJECT_KEY = "Automation-POC"


def _read_feature_engineering_package(run_dir: Path) -> FeatureEngineeringPackage:
    raw = read_json_if_valid(run_dir / FEATURE_ENGINEERING_PACKAGE_FILENAME)
    if raw is None:
        raise FileNotFoundError(
            f"{run_dir / FEATURE_ENGINEERING_PACKAGE_FILENAME} is missing or not valid JSON -- "
            "stage 15 requires stage 14's own Validated Feature Package to have "
            "succeeded first."
        )
    return FeatureEngineeringPackage.from_json(raw)


def _read_test_data_specifications(run_dir: Path) -> tuple[TestDataSpecification, ...]:
    raw = read_json_if_valid(run_dir / _FE_TEST_DATA_SPECIFICATIONS_FILENAME)
    if raw is None:
        return ()
    return tuple(
        TestDataSpecification.model_validate(entry) for entry in raw.get("specifications", ())
    )


def _eligible_records(package: FeatureEngineeringPackage) -> tuple[FeatureRecord, ...]:
    """Every ``FeatureRecord`` Layer 3 may safely generate automation
    against: a real workspace ``.feature`` file exists, and CP2 was never
    escalated on it (ADR-0044 D1: Layer 3 consumes the VALIDATED Feature
    Package -- an escalated feature is, by definition, not that)."""
    return tuple(r for r in package.records if r.feature_path is not None and not r.escalated)


def _write_generated_java(java_source: str, workspace_dir: Path) -> tuple[str, Path]:
    """Write ``java_source`` into ``workspace_dir``'s own ``src/test/java``
    tree, at the exact path its own resolved identity implies -- the SAME
    mechanism (:func:`~automation_engineering.promotion.identity.
    resolve_candidate_identity`) promotion itself uses, so a freshly
    written workspace file and its own future promotion identity can never
    drift apart. Returns ``(class_name, written_path)``.
    """
    asset, relative_path = resolve_candidate_identity(java_source)
    target = workspace_dir / JAVA_SOURCE_SUBPATH / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(java_source, encoding="utf-8")
    return asset.class_name, target


@dataclass(frozen=True, slots=True)
class _GeneratedJava:
    class_name: str
    java_source: str
    workspace_path: Path


def run_automation_engineering_stage(
    package: FeatureEngineeringPackage,
    test_data_specifications: Sequence[TestDataSpecification],
    *,
    workspace_dir: Path,
    matcher: SemanticMatcher,
    step_definition_generator: StepDefinitionGenerator,
    test_data_generator: TestDataGenerator,
    sonar_adapter: SonarQualityGateAdapter,
    baseline_root: Path = DEFAULT_BASELINE_ROOT,
    sonar_project_key: str = DEFAULT_SONAR_PROJECT_KEY,
    repo_root: Path = Path("."),
) -> AutomationEngineeringStageResult:
    """Run stage 15 over every eligible feature record plus every test-data
    specification stage 14 produced.

    ``workspace_dir`` must already be materialized (:func:`.execute_automation_engineering_stage`
    owns that, mirroring stage 14's own split between pure business logic
    and run-state wiring). Idempotent in the same sense stage 14's own
    business-logic function is: re-running it against an unchanged
    ``package``/``test_data_specifications`` and the SAME tracked baseline
    produces the identical set of reuse/generation/CP3/CP4/promotion
    decisions (the only nondeterministic seams are ``matcher``/the
    generators/``sonar_adapter`` themselves).
    """
    features_root = features_root_for(workspace_dir)
    eligible = _eligible_records(package)

    per_feature: list[FeatureStepNeeds] = []
    for record in eligible:
        assert record.feature_path is not None  # narrowed by _eligible_records
        feature_path = features_root / record.feature_path
        content = feature_path.read_text(encoding="utf-8") if feature_path.exists() else ""
        per_feature.append(derive_feature_step_needs(content, file_path=feature_path))

    unique_needs = derive_unique_step_needs(tuple(per_feature))

    tracked_catalog = reconcile(baseline_root)
    # Whole-run embedding warm-up (FIX 1, 2026-08-05): a no-op for a matcher
    # that needs no vectors (StubSemanticMatcher); for LiveSemanticMatcher,
    # embeds every need's/catalog asset's text in as few `embed(...)` calls
    # as the provider needs, ONCE, so every `match()` call in the loop below
    # is a cache hit -- collapsing what was previously one embedding call
    # PER NEED into (up to) one call for the whole run. A transport failure
    # DURING this shared warm-up call is caught and swallowed, deliberately
    # -- priming is a call-count OPTIMIZATION (FIX 1), not a correctness
    # requirement; letting it propagate would mean one failed batched call
    # aborts the WHOLE stage, defeating FIX 2's own per-need isolation for
    # every need at once. Swallowed, `match()` simply falls back to
    # embedding on its own cache miss, per need, in the loop below -- where
    # a persistent failure is caught and escalated ONE NEED AT A TIME
    # instead.
    try:
        matcher.prime(list(unique_needs), tracked_catalog)
    except TransportFailureError:
        pass

    # Per-need loop, not the batch `generate_step_definitions` call (FIX 2,
    # 2026-08-05): a transport failure (embedding or generation) on ANY one
    # need previously propagated out of the batch call entirely, failing the
    # WHOLE stage before any need was recorded -- reproduced live, mirroring
    # exactly the class of bug Layer 2's own F1 fix closed for stage 14
    # (architecture-baseline-v2.md §4 item 16(a)). `TransportFailureError`
    # (embedding-call or generation-call) is caught HERE, per need, and
    # recorded as an escalated `AssetRecord` distinct from a genuine
    # NO_MATCH/reuse-engine escalation (`escalation_check="transport"`,
    # never one of the reuse engine's own three deterministic checks) --
    # the loop CONTINUES with the remaining needs either way.
    step_outcomes: list[StepDefinitionOutcome] = []
    generated_java: list[_GeneratedJava] = []
    asset_records: list[AssetRecord] = []

    for need in unique_needs:
        try:
            outcome = orchestrate_step_definition(
                need, tracked_catalog, matcher, step_definition_generator
            )
        except TransportFailureError as exc:
            asset_records.append(
                AssetRecord(
                    need_text=need.text,
                    need_kind="step_definition",
                    outcome="escalated",
                    escalated=True,
                    escalation_check="transport",
                    escalation_reason=f"transport failure: {exc}",
                )
            )
            continue
        step_outcomes.append(outcome)

        if isinstance(outcome, GeneratedStepDefinition):
            class_name, written_path = _write_generated_java(outcome.java_source, workspace_dir)
            generated_java.append(
                _GeneratedJava(
                    class_name=class_name,
                    java_source=outcome.java_source,
                    workspace_path=written_path,
                )
            )
            asset_records.append(
                AssetRecord(
                    need_text=outcome.need.text,
                    need_kind="step_definition",
                    outcome="generated",
                    class_name=class_name,
                    target_package=outcome.target_package,
                    workspace_path=written_path.relative_to(workspace_dir).as_posix(),
                )
            )
        elif isinstance(outcome, BoundStepDefinition):
            asset_records.append(
                AssetRecord(
                    need_text=outcome.need.text,
                    need_kind="step_definition",
                    outcome="bound",
                    class_name=outcome.asset.class_name,
                )
            )
        elif isinstance(outcome, EscalatedStepNeed):
            asset_records.append(
                AssetRecord(
                    need_text=outcome.need.text,
                    need_kind="step_definition",
                    outcome="escalated",
                    escalated=True,
                    escalation_check=outcome.escalation.check.value,
                    escalation_reason=outcome.escalation.detail,
                )
            )
        else:  # pragma: no cover - exhaustive per StepDefinitionOutcome's own union
            raise AssertionError(f"unreachable: unknown StepDefinitionOutcome {outcome!r}")

    outcome_by_text: dict[str, StepDefinitionOutcome] = {o.need.text: o for o in step_outcomes}

    # Per-specification loop, same discipline as the step-definition loop
    # above (FIX 2): a transport failure generating one test-data class no
    # longer aborts every other specification's generation.
    generated_test_data: list[GeneratedTestDataClass] = []
    for specification in test_data_specifications:
        try:
            td_outcome = generate_test_data_class(specification, test_data_generator)
        except TransportFailureError as exc:
            asset_records.append(
                AssetRecord(
                    need_text=specification.requirement_id,
                    need_kind="test_data",
                    outcome="escalated",
                    escalated=True,
                    escalation_check="transport",
                    escalation_reason=f"transport failure: {exc}",
                )
            )
            continue
        generated_test_data.append(td_outcome)

    for td_outcome in generated_test_data:
        class_name, written_path = _write_generated_java(td_outcome.java_source, workspace_dir)
        generated_java.append(
            _GeneratedJava(
                class_name=class_name,
                java_source=td_outcome.java_source,
                workspace_path=written_path,
            )
        )
        asset_records.append(
            AssetRecord(
                need_text=td_outcome.specification.requirement_id,
                need_kind="test_data",
                outcome="generated",
                class_name=class_name,
                target_package=td_outcome.target_package,
                workspace_path=written_path.relative_to(workspace_dir).as_posix(),
            )
        )

    # -- CP3: coverage (per feature) + Sonar (generic quality) + the two
    # static customqa:* checks, over every freshly generated class. --------
    cp3_feature_inputs = tuple(
        Cp3FeatureInput(
            content=feature_needs.content,
            file_path=feature_needs.file_path,
            outcomes=tuple(
                outcome_by_text[need.text]
                for need in feature_needs.needs
                if need.text in outcome_by_text
            ),
        )
        for feature_needs in per_feature
    )
    # The post-generation catalog (workspace, not tracked baseline) is what
    # CP3's own duplicate-steps criterion must see -- two step definitions
    # generated in the SAME run could collide with each other, not only
    # with something already in the tracked baseline.
    post_generation_catalog: AssetCatalog = reconcile(workspace_dir)
    cp3_coverage_input = Cp3CoverageInput(
        features=cp3_feature_inputs,
        step_definition_assets=post_generation_catalog.step_definitions,
    )
    cp3_generated_classes = tuple(
        Cp3GeneratedClassInput(class_name=g.class_name, java_source=g.java_source)
        for g in generated_java
    )
    cp3_result: Cp3Result = evaluate_cp3(
        cp3_coverage_input,
        Cp3SonarInput(project_root=workspace_dir, project_key=sonar_project_key),
        sonar_adapter,
        generated_classes=cp3_generated_classes,
    )

    # -- CP4: static locator health over every freshly generated PAGE
    # OBJECT -- honestly empty in this wiring (module docstring, step 4):
    # no page object is ever produced without a page_object_request, which
    # this stage never supplies. Evaluates vacuously, the same established
    # convention CP4 itself already documents for an empty input. ---------
    cp4_result: Cp4Result = evaluate_cp4(())

    # -- Promotion: every Generated step-definition outcome (never Bound --
    # nothing new to promote; never test-data -- structurally excluded from
    # promote_outcome's own type signature, ADR-0044 D7). ------------------
    gates = AssetGateOutcomes(
        cp2_verdict=ValidationVerdict.PASS,  # every eligible record is CP2-clean by construction
        cp3_result=cp3_result,  # decomposed per-candidate inside AssetGateOutcomes.first_failure
        cp4_verdict=cp4_result.overall_verdict,
    )
    promoted_paths: list[Path] = []
    for outcome in step_outcomes:
        decision = promote_outcome(outcome, gates, tracked_catalog)
        if decision is None:
            continue
        record_index = next(
            i
            for i, r in enumerate(asset_records)
            if r.need_text == outcome.need.text and r.need_kind == "step_definition"
        )
        if isinstance(decision, Promoted):
            written = apply_promotion(decision, baseline_root)
            promoted_paths.append(written)
            asset_records[record_index] = _with_promotion(
                asset_records[record_index],
                status="promoted",
                detail=None,
                promoted_path=written.relative_to(baseline_root).as_posix(),
            )
        elif isinstance(decision, NotPromotable):
            asset_records[record_index] = _with_promotion(
                asset_records[record_index],
                status="not_promotable",
                detail=f"{decision.reason.value}: {decision.detail}",
                promoted_path=None,
            )
        elif isinstance(decision, PromotionEscalated):
            # Already recorded as an escalated AssetRecord above (the same
            # Escalation, ADR-0045 D3's own "one shared queue") -- nothing
            # further to add.
            continue
        else:  # pragma: no cover - exhaustive per PromotionDecision's own union
            raise AssertionError(f"unreachable: unknown PromotionDecision {decision!r}")

    if promoted_paths:
        stage_promoted_assets(promoted_paths, repo_root)

    # -- Persist -------------------------------------------------------
    run_dir = workspace_dir.parent
    generated_at = datetime.now(UTC).isoformat()
    automation_package = AutomationEngineeringPackage(
        contract_version=CONTRACT_VERSION,
        run_id=package.run_id,
        feature_engineering_run_id=package.run_id,
        generated_at=generated_at,
        records=tuple(asset_records),
    )
    package_path = run_dir / AUTOMATION_ENGINEERING_PACKAGE_FILENAME
    atomic_write_json(package_path, automation_package.to_json())

    cp3_report_path = run_dir / CP3_REPORT_FILENAME
    atomic_write_json(cp3_report_path, _cp3_result_to_json(cp3_result))

    cp4_report_path = run_dir / CP4_REPORT_FILENAME
    atomic_write_json(cp4_report_path, _cp4_result_to_json(cp4_result))

    promotion_report_path = run_dir / PROMOTION_REPORT_FILENAME
    atomic_write_json(
        promotion_report_path,
        {
            "promotedCount": len(promoted_paths),
            "promotedPaths": [p.relative_to(baseline_root).as_posix() for p in promoted_paths],
        },
    )

    report_path = run_dir / AUTOMATION_ENGINEERING_REPORT_FILENAME
    report_path.write_text(
        _build_report(automation_package, cp3_result, cp4_result, promoted_paths), encoding="utf-8"
    )

    return AutomationEngineeringStageResult(
        package=automation_package,
        package_path=package_path,
        cp3_report_path=cp3_report_path,
        cp4_report_path=cp4_report_path,
        promotion_report_path=promotion_report_path,
        report_path=report_path,
        workspace_java_paths=tuple(g.workspace_path for g in generated_java),
        promoted_baseline_paths=tuple(promoted_paths),
        cp3_passed=cp3_result.passed,
        cp4_passed=cp4_result.passed,
    )


def _with_promotion(
    record: AssetRecord, *, status: str, detail: str | None, promoted_path: str | None
) -> AssetRecord:
    return AssetRecord(
        need_text=record.need_text,
        need_kind=record.need_kind,
        outcome=record.outcome,
        class_name=record.class_name,
        target_package=record.target_package,
        workspace_path=record.workspace_path,
        escalated=record.escalated,
        escalation_check=record.escalation_check,
        escalation_reason=record.escalation_reason,
        promotion_status=status,
        promotion_detail=detail,
        promoted_path=promoted_path,
    )


def _cp3_result_to_json(result: Cp3Result) -> dict[str, object]:
    return {
        "overallVerdict": result.overall_verdict.value,
        "criteria": [
            {"criterion": c.criterion, "verdict": c.verdict.value, "messages": list(c.messages)}
            for c in result.criteria
        ],
        "reuse": {
            "reused": result.reuse.reused,
            "generated": result.reuse.generated,
            "escalated": result.reuse.escalated,
            "reusePercentage": result.reuse.reuse_percentage,
        },
    }


def _cp4_result_to_json(result: Cp4Result) -> dict[str, object]:
    return {
        "overallVerdict": result.overall_verdict.value,
        "criteria": [
            {"criterion": c.criterion, "verdict": c.verdict.value, "messages": list(c.messages)}
            for c in result.criteria
        ],
    }


def _build_report(
    package: AutomationEngineeringPackage,
    cp3_result: Cp3Result,
    cp4_result: Cp4Result,
    promoted_paths: list[Path],
) -> str:
    generated = sum(1 for r in package.records if r.outcome == "generated")
    bound = sum(1 for r in package.records if r.outcome == "bound")
    escalated = len(package.escalated_records)
    lines = [
        "# Automation Engineering Stage Report (Stage 15)",
        "",
        f"- Needs processed: {len(package.records)}",
        f"- Generated: {generated}",
        f"- Bound (reused): {bound}",
        f"- Escalated: {escalated}",
        f"- CP3 verdict: {cp3_result.overall_verdict.value}",
        f"- CP4 verdict: {cp4_result.overall_verdict.value}",
        f"- Promoted to tracked baseline: {len(promoted_paths)}",
    ]
    if escalated:
        lines.append("")
        lines.append("## Escalations")
        for record in package.escalated_records:
            lines.append(f"- {record.need_text!r} ({record.escalation_check}): "
                          f"{record.escalation_reason}")
    return "\n".join(lines) + "\n"


def execute_automation_engineering_stage(
    run_state_mgr: RunStateManager,
    run_dir: Path,
    *,
    matcher: SemanticMatcher,
    step_definition_generator: StepDefinitionGenerator,
    test_data_generator: TestDataGenerator,
    sonar_adapter: SonarQualityGateAdapter,
    baseline_root: Path = DEFAULT_BASELINE_ROOT,
    sonar_project_key: str = DEFAULT_SONAR_PROJECT_KEY,
    repo_root: Path = Path("."),
) -> AutomationEngineeringStageResult | None:
    """Wire stage 15 into `run_state_mgr` with the SAME
    `start_stage`/try-except/`fail_stage`/`succeed_stage` idiom stage 14's
    own `execute_feature_engineering_stage` already uses.

    Unlike stage 14 (which receives its own upstream `TestableRequirementSet`
    as an in-memory object from the same CLI process), this function reads
    its own upstream artifacts -- `feature_engineering_package.json` and
    `test_data_specifications.json` -- directly from `run_dir`, never from
    an in-process handoff (ADR-0036 D2: "stage inputs must be artifact
    paths"). This makes stage 15 genuinely resumable standalone: a process
    that only wants to (re)run stage 15 against an already-`SUCCEEDED`
    stage 14 needs no in-memory object from that earlier phase at all.

    Returns `None` both when the stage was SKIPPED and when it FAILED --
    the caller reads `run_state_mgr.state` for which, mirroring stage 14's
    own contract exactly.
    """
    input_artifacts = [
        run_dir / FEATURE_ENGINEERING_PACKAGE_FILENAME,
        run_dir / _FE_TEST_DATA_SPECIFICATIONS_FILENAME,
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
        package = _read_feature_engineering_package(run_dir)
        test_data_specifications = _read_test_data_specifications(run_dir)
        workspace_dir = materialize_workspace(run_dir, baseline_root=baseline_root)
        result = run_automation_engineering_stage(
            package,
            test_data_specifications,
            workspace_dir=workspace_dir,
            matcher=matcher,
            step_definition_generator=step_definition_generator,
            test_data_generator=test_data_generator,
            sonar_adapter=sonar_adapter,
            baseline_root=baseline_root,
            sonar_project_key=sonar_project_key,
            repo_root=repo_root,
        )
    except Exception as exc:  # surfaced via run_state.json, never fatal to the caller's process
        run_state_mgr.fail_stage(STAGE_ID, error=exc)
        return None
    else:
        run_state_mgr.succeed_stage(STAGE_ID, output_artifacts=list(result.all_output_paths))
        return result


__all__ = [
    "DEFAULT_SONAR_PROJECT_KEY",
    "STAGE_ID",
    "execute_automation_engineering_stage",
    "run_automation_engineering_stage",
]
