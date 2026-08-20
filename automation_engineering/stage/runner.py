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
4. Reuse-decide/generate every unique step need, one call per need -- not
   the batch ``generate_step_definitions`` helper, since 2026-08-05 (the
   free-tier survivability build): a per-need loop is what lets a transport
   failure on ONE need be escalated and the loop continue, rather than
   aborting the whole run (this module's own report, FIX 2).
   ``matcher.prime(...)`` is called once, first, so the embeddings MATCH
   itself still makes at most one batched call for the whole run's needs
   (FIX 1), not one call per need despite the per-need loop. When
   ``page_object_matcher``/``page_object_generator`` are BOTH supplied
   (additive, both default ``None`` -- this stage's report found the
   proven co-generation chain built and tested but never actually CALLED
   from here), each need is generated via
   :func:`automation_engineering.generation.page_object_reference_derivation.generate_step_definition_with_derived_page_objects`
   instead of :func:`automation_engineering.generation.orchestrator.orchestrate_step_definition`
   directly -- deriving which page-object class/method(s) the freshly
   generated step-definition's own body actually calls, then reuse-
   deciding/generating each, exactly the same way step 4 already does for
   the step-definition itself (:mod:`.page_object_reference_derivation`'s
   own module docstring). ``utility_request`` is still never supplied --
   utilities remain this module's own carried-forward, honestly deferred
   scope boundary, unchanged by this addition. When ``page_object_matcher``/
   ``page_object_generator`` are omitted (the live CLI's own current
   default -- see this module's own report: no live ``SemanticMatcher``
   implementation exists yet that correctly matches a page-object need
   against ``catalog.page_objects``, only against ``catalog.step_definitions``
   -- :mod:`automation_engineering.reuse.live_matcher`'s own docstring,
   "Only step definitions are matched" -- building one is flagged, not
   built, by that same report), this step's behavior is exactly what it
   always was: no page-object asset is ever produced.
5. Generate every test-data specification stage 14 emitted (spec-driven,
   unconditional, no reuse decision -- ADR-0044 D7), also per-specification
   rather than batched, for the same transport-isolation reason as step 4.
6. Write every freshly generated class's Java source into the workspace
   (never the tracked baseline directly -- ADR-0037 D2), at the exact path
   :func:`automation_engineering.promotion.identity.resolve_candidate_identity`
   resolves it to -- the SAME identity mechanism promotion itself uses, so
   a written file and its own future promotion identity can never drift
   apart. Two independently generated needs can resolve to the SAME class
   name (the generator derives it from "the step's own subject," a
   many-to-one function, with no cross-need visibility) -- ``_write_generated_java``
   DETECTS this (a class name already written earlier in this run) and
   merges the two deterministically (:mod:`.class_collision`) rather than
   silently overwriting the earlier write, the exact gap a live regeneration
   run caught only by luck (a catalog count mismatch), fixed by hand at the
   time. A merge that is not safe to resolve automatically (different
   package/superclass, or a same-named member with a conflicting body)
   escalates the SECOND need instead (``escalation_check="class_name_collision"``)
   rather than guessing a winner. A merged class is written once, to the
   workspace, for THIS run's compilation/CP3 evaluation; only the FIRST
   contributing need's own (unmerged, single-method) outcome is promoted
   through the existing per-candidate promotion mechanism (:mod:`.promotion.identity`
   requires exactly one asset per candidate, a step-def class with more than
   one annotated method is not a shape that mechanism accepts) -- the
   SECOND need's own contribution reaches the tracked baseline only once a
   future promotion extension accepts a multi-method merged candidate; it is
   never lost from the workspace or from THIS run's own coverage/CP3
   evaluation in the meantime.
7. CP3 (:func:`automation_engineering.cp3.gate.evaluate_cp3`) over every
   feature's own outcomes, the Sonar adapter, and every freshly generated
   class; CP4 (:func:`automation_engineering.cp4.gate.evaluate_cp4`) over
   every freshly generated PAGE OBJECT this run actually wrote (step 4's own
   opt-in) -- non-vacuous for the first time whenever at least one was
   produced; still evaluates vacuously (its own established "empty input"
   convention) when step 4 produced none, including the live CLI's own
   current default (step 4's own note).
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
from automation_engineering.cp4.models import Cp4PageObjectInput, Cp4Result
from automation_engineering.errors import TransportFailureError
from automation_engineering.generation.class_collision import (
    UnsafeClassMergeError,
    merge_java_classes,
)
from automation_engineering.generation.models import (
    BoundPageObjectMethod,
    BoundStepDefinition,
    EscalatedStepNeed,
    GeneratedPageObject,
    GeneratedStepDefinition,
    GeneratedTestDataClass,
    PageObjectMethodOutcome,
    StepDefinitionOutcome,
)
from automation_engineering.generation.orchestrator import orchestrate_step_definition
from automation_engineering.generation.page_object_generator import PageObjectGenerator
from automation_engineering.generation.page_object_reference_derivation import (
    CoGeneratedStepDefinition,
    generate_step_definition_with_derived_page_objects,
)
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


@dataclass(frozen=True, slots=True)
class _GeneratedJava:
    class_name: str
    java_source: str
    workspace_path: Path
    #: "step_definition" | "page_object" | "test_data" -- which of this
    #: run's own generated-class inputs (CP3's `generated_classes`, CP4's
    #: page-object-only input) this write belongs to. Set once at write
    #: time, carried through a collision-merge unchanged (a merge only ever
    #: happens between two writes of the SAME kind -- two step-defs or two
    #: page objects resolving to the same class name -- never across kinds).
    kind: str


def _write_generated_java(
    java_source: str,
    workspace_dir: Path,
    generated_java: list[_GeneratedJava],
    index_by_class_name: dict[str, int],
    *,
    kind: str,
) -> tuple[str, Path, bool]:
    """Write ``java_source`` into ``workspace_dir``'s own ``src/test/java``
    tree, at the exact path its own resolved identity implies -- the SAME
    mechanism (:func:`~automation_engineering.promotion.identity.
    resolve_candidate_identity`) promotion itself uses, so a freshly
    written workspace file and its own future promotion identity can never
    drift apart.

    ``generated_java``/``index_by_class_name`` are this RUN's own collision
    ledger, mutated in place: if ``java_source``'s own class name was never
    written before this call, it is written as-is and recorded. If it WAS
    (two independently generated needs resolving to the same class name --
    the generator derives a class name from "the step's own subject," a
    many-to-one function with no cross-need visibility, module docstring
    step 6), the two are merged deterministically
    (:func:`~automation_engineering.generation.class_collision.merge_java_classes`)
    and the SAME workspace file is rewritten with the merged content --
    never silently overwritten with only the newer side. Raises
    :class:`~automation_engineering.generation.class_collision.UnsafeClassMergeError`
    if the two classes are not safe to merge (different package/superclass,
    or a same-named member whose two declarations disagree) -- the caller
    must escalate that need rather than write anything for it.

    Returns ``(class_name, written_path, merged)`` -- ``merged`` is ``True``
    iff this call's class name collided with an earlier write in THIS run.
    """
    asset, relative_path = resolve_candidate_identity(java_source)
    class_name = asset.class_name
    target = workspace_dir / JAVA_SOURCE_SUBPATH / relative_path

    existing_index = index_by_class_name.get(class_name)
    if existing_index is None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(java_source, encoding="utf-8")
        index_by_class_name[class_name] = len(generated_java)
        generated_java.append(
            _GeneratedJava(
                class_name=class_name, java_source=java_source, workspace_path=target, kind=kind
            )
        )
        return class_name, target, False

    existing = generated_java[existing_index]
    merged_source = merge_java_classes(existing.java_source, java_source)
    if merged_source != existing.java_source:
        existing.workspace_path.write_text(merged_source, encoding="utf-8")
        generated_java[existing_index] = _GeneratedJava(
            class_name=class_name,
            java_source=merged_source,
            workspace_path=existing.workspace_path,
            kind=existing.kind,
        )
    return class_name, existing.workspace_path, True


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
    page_object_matcher: SemanticMatcher | None = None,
    page_object_generator: PageObjectGenerator | None = None,
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

    ``page_object_matcher``/``page_object_generator`` (additive, both
    default ``None`` -- every pre-existing caller's behavior is completely
    unchanged): when BOTH are supplied, each need is generated via
    :func:`~automation_engineering.generation.page_object_reference_derivation.generate_step_definition_with_derived_page_objects`
    instead of :func:`~automation_engineering.generation.orchestrator.orchestrate_step_definition`
    directly -- deriving, then reuse-deciding/generating, whichever page
    objects the freshly generated step-definition's own body turns out to
    reference (module docstring, updated). When either is omitted (the
    live CLI's own current default -- see this module's own report: no
    live ``SemanticMatcher`` implementation exists yet that correctly
    matches a page-object need against ``catalog.page_objects``, only
    against ``catalog.step_definitions`` --
    :mod:`automation_engineering.reuse.live_matcher`'s own docstring, "Only
    step definitions are matched"), this stage's behavior is byte-for-byte
    what it always was: no page-object asset is produced, CP4 evaluates
    vacuously.
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
    generated_java_by_class_name: dict[str, int] = {}
    asset_records: list[AssetRecord] = []
    # Outcomes merged into an EARLIER need's own class this run (module
    # docstring step 6) -- excluded from the promotion loop below so the
    # SAME class is never independently promoted twice, and so promotion
    # never has to resolve a merged, multi-method candidate's identity
    # (:mod:`.promotion.identity` requires exactly one asset per candidate).
    # Shared across step-definition AND page-object outcomes below -- a
    # plain `id()`-keyed set, agnostic to which outcome type it is holding.
    not_independently_promotable: set[int] = set()
    # Every page-object outcome this run resolved (Generated or Bound --
    # never Escalated, module docstring of `.page_object_reference_
    # derivation`'s own `generate_step_definition_with_derived_page_objects`:
    # a page-object-side escalation diverts the WHOLE step to
    # `EscalatedStepNeed` instead of ever reaching here), paired with the
    # index of its own already-appended `AssetRecord` -- so the promotion
    # loop below can update that SAME record in place without a `need_text`
    # search (one step can derive method calls against more than one
    # page-object class, so `need_text` alone is not unique per page-object
    # outcome the way it is per step-definition outcome).
    page_object_outcomes: list[tuple[PageObjectMethodOutcome, int]] = []
    page_object_generation_enabled = (
        page_object_matcher is not None and page_object_generator is not None
    )

    for need in unique_needs:
        try:
            if page_object_generation_enabled:
                assert page_object_matcher is not None  # narrowed by the flag above
                assert page_object_generator is not None
                outcome = generate_step_definition_with_derived_page_objects(
                    need,
                    tracked_catalog,
                    matcher,
                    step_definition_generator,
                    page_object_matcher,
                    page_object_generator,
                )
            else:
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

        if isinstance(outcome, CoGeneratedStepDefinition):
            # Unwrap to the SAME `GeneratedStepDefinition` shape the branch
            # below already handles -- `generate_step_definition_with_
            # derived_page_objects` never changes the step-definition's own
            # generation outcome, only derives+resolves what its BODY
            # references afterwards (module docstring). This keeps CP3 and
            # step-definition promotion completely untouched by this
            # wiring: they see the identical `GeneratedStepDefinition` they
            # always did. NOTE: `CoGeneratedStepDefinition` itself carries
            # no `generation_identity` field (the proven chain's own
            # pre-existing shape, not altered here -- see this module's own
            # report) -- so a co-generated step-definition's own
            # `AssetRecord.generation_identity` is `None` even when the
            # underlying generation call did produce one. A real, known
            # gap, flagged rather than silently patched around.
            step_def_outcome: StepDefinitionOutcome = GeneratedStepDefinition(
                need=outcome.need,
                java_source=outcome.java_source,
                target_package=outcome.target_package,
            )
            for po_outcome in outcome.page_object_outcomes:
                if isinstance(po_outcome, GeneratedPageObject):
                    try:
                        po_class_name, po_written_path, po_merged = _write_generated_java(
                            po_outcome.java_source,
                            workspace_dir,
                            generated_java,
                            generated_java_by_class_name,
                            kind="page_object",
                        )
                    except UnsafeClassMergeError as exc:
                        asset_records.append(
                            AssetRecord(
                                need_text=outcome.need.text,
                                need_kind="page_object",
                                outcome="escalated",
                                escalated=True,
                                escalation_check="class_name_collision",
                                escalation_reason=str(exc),
                            )
                        )
                        continue
                    if po_merged:
                        not_independently_promotable.add(id(po_outcome))
                    asset_records.append(
                        AssetRecord(
                            need_text=outcome.need.text,
                            need_kind="page_object",
                            outcome="generated",
                            class_name=po_class_name,
                            target_package=po_outcome.target_package,
                            workspace_path=po_written_path.relative_to(workspace_dir).as_posix(),
                        )
                    )
                    page_object_outcomes.append((po_outcome, len(asset_records) - 1))
                elif isinstance(po_outcome, BoundPageObjectMethod):
                    asset_records.append(
                        AssetRecord(
                            need_text=outcome.need.text,
                            need_kind="page_object",
                            outcome="bound",
                            class_name=po_outcome.asset.class_name,
                        )
                    )
                    page_object_outcomes.append((po_outcome, len(asset_records) - 1))
                else:  # pragma: no cover - see this branch's own docstring note above
                    raise AssertionError(
                        f"unreachable: EscalatedPageObjectMethodNeed inside "
                        f"CoGeneratedStepDefinition.page_object_outcomes {po_outcome!r}"
                    )
            outcome = step_def_outcome

        if isinstance(outcome, GeneratedStepDefinition):
            try:
                class_name, written_path, merged = _write_generated_java(
                    outcome.java_source,
                    workspace_dir,
                    generated_java,
                    generated_java_by_class_name,
                    kind="step_definition",
                )
            except UnsafeClassMergeError as exc:
                asset_records.append(
                    AssetRecord(
                        need_text=outcome.need.text,
                        need_kind="step_definition",
                        outcome="escalated",
                        escalated=True,
                        escalation_check="class_name_collision",
                        escalation_reason=str(exc),
                    )
                )
                continue
            step_outcomes.append(outcome)
            if merged:
                not_independently_promotable.add(id(outcome))
            asset_records.append(
                AssetRecord(
                    need_text=outcome.need.text,
                    need_kind="step_definition",
                    outcome="generated",
                    class_name=class_name,
                    target_package=outcome.target_package,
                    workspace_path=written_path.relative_to(workspace_dir).as_posix(),
                    generation_identity=outcome.generation_identity,
                )
            )
        elif isinstance(outcome, BoundStepDefinition):
            step_outcomes.append(outcome)
            asset_records.append(
                AssetRecord(
                    need_text=outcome.need.text,
                    need_kind="step_definition",
                    outcome="bound",
                    class_name=outcome.asset.class_name,
                )
            )
        elif isinstance(outcome, EscalatedStepNeed):
            step_outcomes.append(outcome)
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
        try:
            class_name, written_path, _merged = _write_generated_java(
                td_outcome.java_source,
                workspace_dir,
                generated_java,
                generated_java_by_class_name,
                kind="test_data",
            )
        except UnsafeClassMergeError as exc:
            asset_records.append(
                AssetRecord(
                    need_text=td_outcome.specification.requirement_id,
                    need_kind="test_data",
                    outcome="escalated",
                    escalated=True,
                    escalation_check="class_name_collision",
                    escalation_reason=str(exc),
                )
            )
            continue
        asset_records.append(
            AssetRecord(
                need_text=td_outcome.specification.requirement_id,
                need_kind="test_data",
                outcome="generated",
                class_name=class_name,
                target_package=td_outcome.target_package,
                workspace_path=written_path.relative_to(workspace_dir).as_posix(),
                generation_identity=td_outcome.generation_identity,
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
    # OBJECT this run actually wrote (module docstring, step 4) -- non-empty
    # whenever `page_object_matcher`/`page_object_generator` were supplied
    # and at least one step's own body was found to reference a page
    # object; still evaluates vacuously (the same established "empty input"
    # convention CP4 itself already documents) when neither was supplied,
    # or when no step this run needed a fresh/bound page-object call. Reads
    # `generated_java`'s own `kind` tag, not a second, parallel list -- the
    # SAME (possibly merged) java_source CP3 and promotion also see. -------
    cp4_page_object_inputs = tuple(
        Cp4PageObjectInput(class_name=g.class_name, java_source=g.java_source)
        for g in generated_java
        if g.kind == "page_object"
    )
    cp4_result: Cp4Result = evaluate_cp4(cp4_page_object_inputs)

    # -- Promotion: every Generated step-definition outcome (never Bound --
    # nothing new to promote; never test-data -- structurally excluded from
    # promote_outcome's own type signature, ADR-0044 D7); never a need MERGED
    # into an earlier need's own class this run either (`not_independently_
    # promotable`, module docstring step 6) -- the merged class already
    # promotes once, through the FIRST contributing need's own outcome. -----
    gates = AssetGateOutcomes(
        cp2_verdict=ValidationVerdict.PASS,  # every eligible record is CP2-clean by construction
        cp3_result=cp3_result,  # decomposed per-candidate inside AssetGateOutcomes.first_failure
        cp4_verdict=cp4_result.overall_verdict,
    )
    promoted_paths: list[Path] = []
    for outcome in step_outcomes:
        if id(outcome) in not_independently_promotable:
            continue
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

    # -- Promotion, page objects: the SAME per-candidate gate
    # (`gates`, including the CP4 verdict just computed above -- no longer
    # vacuous whenever a page object was actually generated this run) --
    # `promote_outcome` already accepts a `PageObjectMethodOutcome`
    # (`automation_engineering.promotion.outcomes.GeneratedOutcome`/
    # `BoundOutcome` are typed as unions across step-definition, page-object,
    # and utility outcomes) -- this loop is new, but the promotion decision
    # itself is not: it reuses the exact mechanism step-definition promotion
    # already exercises. Indexed by `page_object_outcomes`'s own paired
    # `AssetRecord` index (module docstring, per-need loop) rather than a
    # `need_text` search -- one step can derive calls against more than one
    # page-object class, so `need_text` alone does not identify one record.
    for po_outcome, record_index in page_object_outcomes:
        if id(po_outcome) in not_independently_promotable:
            continue
        po_decision = promote_outcome(po_outcome, gates, tracked_catalog)
        if po_decision is None:
            continue
        if isinstance(po_decision, Promoted):
            written = apply_promotion(po_decision, baseline_root)
            promoted_paths.append(written)
            asset_records[record_index] = _with_promotion(
                asset_records[record_index],
                status="promoted",
                detail=None,
                promoted_path=written.relative_to(baseline_root).as_posix(),
            )
        elif isinstance(po_decision, NotPromotable):
            asset_records[record_index] = _with_promotion(
                asset_records[record_index],
                status="not_promotable",
                detail=f"{po_decision.reason.value}: {po_decision.detail}",
                promoted_path=None,
            )
        elif isinstance(po_decision, PromotionEscalated):
            # Cannot happen in practice -- `page_object_outcomes` never
            # holds an `EscalatedPageObjectMethodNeed` (this branch's own
            # per-need-loop docstring note) -- kept only for the same
            # exhaustive-union discipline the step-definition loop above
            # already follows.
            continue  # pragma: no cover
        else:  # pragma: no cover - exhaustive per PromotionDecision's own union
            raise AssertionError(f"unreachable: unknown PromotionDecision {po_decision!r}")

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
        generation_identity=record.generation_identity,
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
    page_object_matcher: SemanticMatcher | None = None,
    page_object_generator: PageObjectGenerator | None = None,
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

    ``page_object_matcher``/``page_object_generator`` are passed straight
    through to :func:`run_automation_engineering_stage` unchanged (both
    default ``None`` there too -- see that function's own docstring for
    what supplying them changes, and this module's own report for why the
    live CLI does not supply them yet).
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
            page_object_matcher=page_object_matcher,
            page_object_generator=page_object_generator,
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
