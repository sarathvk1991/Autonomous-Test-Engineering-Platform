"""Stage 14 -- Feature Engineering, wired as a resumable, persisted
run/stage-state stage (ADR-0036, ADR-0043 D8).

Wraps the already-built generate -> CP2 -> D5 remediate -> re-gate unit
(`feature_engineering.generation`, `.cp2`, `.remediation`) as a stage. No new
generation, CP2, or remediation logic lives here -- only orchestration,
per-requirement persistence, and the reuse decision.

Two functions:

* :func:`run_feature_engineering_stage` -- pure business logic (no
  `run_state.json` I/O), mirroring how every Layer 1 phase function
  (`run_testable_requirement_emission_phase`, `run_recommendation_phase`,
  etc. in `scripts/run_requirement_analysis.py`) is itself pure and knows
  nothing about `RunStateManager`. Given a `TestableRequirementSet`, it
  produces or reuses one `.feature` file per requirement in the untracked
  workspace (`features_root`) and one Validated Feature Package (this run's
  per-requirement CP2/remediation outcomes, a report, a derived
  `traceability.json`, and ADR-0043 D7's own test-data specification --
  `test_data_specifications.json`, one entry per requirement, derived
  fresh every run from that requirement's own acceptance criteria; see
  `.test_data_spec`'s own module docstring for the derivation and its
  honest-empty finding against the real, live corpus) in the run
  directory.
* :func:`execute_feature_engineering_stage` -- the SAME
  `start_stage`/try-except/`fail_stage`/`succeed_stage` idiom every Layer 1
  phase already uses, applied to stage 14, plus stage 14's own
  `should_skip` check (ADR-0036's two-invariant predicate: prior SUCCEEDED,
  the declared inputs' content hash unchanged, AND every declared output
  still exists and is valid). Layer 1's own stages never exercise a
  per-stage skip today (see `requirement_intelligence/run_state/stages.py`'s
  own module docstring: every Layer 1 result lives in memory until
  `ExecutionWriter.write()` runs once, at the very end, so no earlier stage
  has an on-disk artifact to check before that point) -- stage 14 is the
  FIRST stage with its own on-disk artifacts before the pipeline's final
  bundle write, so this is also the first time a per-stage (not just
  whole-run) skip check actually fires. This function also owns per-run
  workspace materialization (`.workspace.materialize_workspace`, ADR-0037
  Path A) -- it derives `features_root` itself rather than trusting a
  caller-supplied path, so a caller can never accidentally point it at the
  shared tracked baseline.

Not hand-wired into `scripts/run_requirement_analysis.py`'s automatic
`handle_analyze` sequence by this task (see the accompanying report):
`LiveFeatureContentGenerator` already exists (an earlier task), but no live
`FeatureRemediator` does, and this task's own instructions are to wire
against the deterministic stubs only, never a live model. Hooking stage 14
into the CLI's unconditional sequence would force a premature choice of
production `content_generator`/`remediator` that this task is not
authorized to make. `execute_feature_engineering_stage` is the ready-to-call
integration point a future CLI-wiring task uses -- it accepts any
`FeatureContentGenerator`/`FeatureRemediator` (stub or, later, live), exactly
as `RunStateManager` accepts any stage's business logic today.

Idempotency (ADR-0042 Decision 3, ADR-0043 D8): each `TestableRequirement`'s
own `content_hash` is compared against the prior Validated Feature Package's
record for that `requirement_id`. Unchanged (same `content_hash`, and its
workspace `.feature` file still exists and is non-empty) -> reused,
unconditionally -- neither `content_generator` nor `remediator` is called
for it, and its prior `FeatureRecord` (including any prior escalation) is
carried forward verbatim. Changed, new, or missing-output -> regenerated
through the full generate -> CP2 -> remediate unit. Where live-model
nondeterminism would enter: a live `FeatureContentGenerator`/`FeatureRemediator`
could return different content across two calls for the SAME requirement
(unlike the deterministic stubs used here) -- this stage's own reuse
decision is unaffected either way, since it only ever calls the generator
again when `content_hash` changed; nondeterminism across regenerations of
the SAME unchanged requirement is a live-model property this stage never
exercises, because it never regenerates an unchanged one.

A FAILED feature (CP2 FAIL after D5 exhaustion, a pre-assembly generation
contract violation, or -- as of 2026-08-04, the Layer 1-3 integration run's
F1 fix -- a transport failure at the content-generator/remediator boundary
itself, `TransportFailureError`) is never dropped: it is recorded as an
escalated `FeatureRecord` in the package, and its final content (whatever it
is) is still written to the workspace when content exists at all, so a human
reviewer has something to open. The stage's own run-state verdict is
SUCCEEDED even when escalations exist -- see this module's report for the
rationale, mirrored from how every other Layer 1 tail phase (grounding,
validation, CP1, quality governance, recommendation) already treats a
content-level gate outcome as informational, never as a reason to mark the
stage itself FAILED. Only a genuine, unexpected exception (an I/O error, a
corrupt input, a bug) marks the stage FAILED -- the same distinction
`execution_package_write` already draws as the one hard-fail phase in the
existing CLI.

**Transport failures are per-requirement recoverable, not stage-fatal
(2026-08-04, the Layer 1-3 end-to-end integration run's F1 fix).** Before
this fix, `content_generator.generate()`/`remediator.remediate()` were
called unguarded here: a live provider's `LiveGenerationError`/
`LiveRemediationError` (a 429/quota rejection, a timeout, an empty
response) is a class this module's own `except FeatureGenerationError`
handler never caught -- a sibling exception, not a subclass -- so it
propagated out of this function entirely, and `execute_feature_engineering
_stage`'s outer `except Exception` caught it there instead, failing the
WHOLE STAGE over one requirement's transport failure. Reproduced live: a
single 429 on the first of 20 requirements failed stage 14 outright with
zero requirements processed. Fixed by giving the LLM boundary a shared,
seam-level exception, `feature_engineering.generation.errors
.TransportFailureError` (both `LiveGenerationError` and
`LiveRemediationError` now subclass it), and catching it here exactly like
`FeatureGenerationError` -- per-requirement, escalated, the loop continues.
The two failure kinds are still distinguished: a `TransportFailureError`
records `escalation_reason="transport failure (no retry attempted): ..."`,
never the `"pre-assembly generation contract violation: ..."` wording a
content failure gets -- a human reviewing an escalation needs to know
whether to look at the generated content or at provider/network
conditions. No retry is attempted (the platform has none anywhere in this
call path today, unchanged by this fix) -- the requirement is escalated
immediately, the minimal fix for "one 429 doesn't kill the batch." Bounded
transport retry-with-backoff remains a possible, deliberate follow-up, not
smuggled into this fix.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from contracts.testable_requirement import TestableRequirement, TestableRequirementSet
from feature_engineering.cp2 import evaluate_cp2
from feature_engineering.generation import (
    FeatureContentGenerator,
    FeatureGenerationError,
    GeneratedFeature,
    TransportFailureError,
    derive_feature_file_path,
    generate_feature_file,
    write_generated_feature,
)
from feature_engineering.gherkin_lint import LintResult, load_config, parse_source_text
from feature_engineering.gherkin_lint.linter import lint_source
from feature_engineering.remediation import (
    FeatureRemediator,
    RemediationStatus,
    rebuild_generated_feature,
    run_cp2_remediation,
)
from feature_engineering.stage.models import (
    CONTRACT_VERSION,
    FEATURE_ENGINEERING_PACKAGE_FILENAME,
    FEATURE_ENGINEERING_REPORT_FILENAME,
    FeatureEngineeringPackage,
    FeatureEngineeringStageResult,
    FeatureRecord,
)
from feature_engineering.stage.report import build_report
from feature_engineering.stage.test_data_spec import (
    TEST_DATA_SPECIFICATIONS_FILENAME,
    build_test_data_specifications,
    test_data_specifications_to_json,
)
from feature_engineering.stage.traceability import TRACEABILITY_FILENAME, build_traceability_index
from feature_engineering.stage.workspace import (
    DEFAULT_BASELINE_ROOT,
    features_root_for,
    materialize_workspace,
)
from requirement_intelligence.run_state.atomic_write import atomic_write_json, read_json_if_valid
from requirement_intelligence.run_state.run_state_manager import RunStateManager
from shared.enums.base import ValidationVerdict

STAGE_ID = "feature_engineering"

_LINTRC_PATH = Path("docs/reference/automation-poc/.gherkin-lintrc")


def _lint(content: str) -> LintResult:
    return lint_source(parse_source_text(content), load_config(_LINTRC_PATH))


def _load_prior_package(run_dir: Path) -> FeatureEngineeringPackage | None:
    raw = read_json_if_valid(run_dir / FEATURE_ENGINEERING_PACKAGE_FILENAME)
    if raw is None:
        return None
    return FeatureEngineeringPackage.from_json(raw)


def _relative_to(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _can_reuse(prior: FeatureRecord | None, requirement: TestableRequirement) -> bool:
    """Both invariants required, mirroring ADR-0036's own SKIP predicate at
    the per-requirement level: (a) the prior record's `content_hash` still
    matches, and (b) its declared output -- the workspace `.feature` file --
    still exists and is non-empty. Hash-match alone is never sufficient."""
    if prior is None or prior.content_hash != requirement.content_hash:
        return False
    if prior.feature_path is None:
        return False  # a prior pre-assembly escalation had no file to reuse
    return True  # existence/non-emptiness checked by the caller, which holds features_root


def run_feature_engineering_stage(
    requirement_set: TestableRequirementSet,
    *,
    features_root: Path,
    run_dir: Path,
    content_generator: FeatureContentGenerator,
    remediator: FeatureRemediator,
) -> FeatureEngineeringStageResult:
    """Run stage 14 over every requirement in `requirement_set`.

    Idempotent and resumable purely by being invoked again with the same
    `run_dir`/`features_root`: an unchanged requirement (same `content_hash`,
    workspace file still present and non-empty) is reused verbatim.
    """
    prior_package = _load_prior_package(run_dir)
    prior_by_id = {r.requirement_id: r for r in (prior_package.records if prior_package else ())}
    requirement_by_id = {r.requirement_id: r for r in requirement_set.requirements}

    reused_features: dict[str, GeneratedFeature] = {}
    reused_records: dict[str, FeatureRecord] = {}
    to_generate: list[TestableRequirement] = []

    for requirement in requirement_set.requirements:
        prior_record = prior_by_id.get(requirement.requirement_id)
        if _can_reuse(prior_record, requirement):
            assert prior_record is not None and prior_record.feature_path is not None
            path = features_root / prior_record.feature_path
            content = path.read_text(encoding="utf-8") if path.exists() else ""
            if content.strip():
                reused_features[requirement.requirement_id] = rebuild_generated_feature(
                    requirement, content, prior_record.req_tag, _lint(content)
                )
                reused_records[requirement.requirement_id] = prior_record
                continue
        to_generate.append(requirement)

    # -- generate fresh content for everything not reused ------------------
    fresh_features: dict[str, GeneratedFeature] = {}
    dirty_by_id: dict[str, tuple[str, str]] = {}  # requirement_id -> (content, req_tag)
    unrecoverable: dict[str, str] = {}  # requirement_id -> reason; no content at all
    transport_failed: dict[str, str] = {}  # requirement_id -> reason; boundary call itself failed

    for requirement in to_generate:
        try:
            feature = generate_feature_file(
                requirement, content_generator, features_root=features_root
            )
        except FeatureGenerationError as exc:
            if exc.content is None:
                unrecoverable[requirement.requirement_id] = str(exc)
            else:
                dirty_by_id[requirement.requirement_id] = (
                    exc.content,
                    f"@{requirement.requirement_id}",
                )
            continue
        except TransportFailureError as exc:
            # A provider/quota/timeout failure at the LLM boundary itself --
            # no content was ever returned to validate. Per-requirement
            # recoverable, exactly like FeatureGenerationError above, but a
            # DIFFERENT escalation reason (see the transport_failed loop
            # below): this requirement never reached content validation at
            # all, so there is nothing content-shaped to report on it.
            transport_failed[requirement.requirement_id] = str(exc)
            continue
        fresh_features[requirement.requirement_id] = feature

    # Full corpus for CP2's cross-file checks: every feature-shaped object
    # currently held (reused + freshly generated), a fixed snapshot for this
    # first evaluation pass.
    corpus = [*reused_features.values(), *fresh_features.values()]

    records: list[FeatureRecord] = list(reused_records.values())
    workspace_paths: list[Path] = [
        features_root / r.feature_path for r in reused_records.values() if r.feature_path
    ]

    for requirement_id, feature in fresh_features.items():
        requirement = requirement_by_id[requirement_id]
        cp2_result = evaluate_cp2(feature, feature_set=corpus)
        if cp2_result.passed:
            write_generated_feature(feature)
            workspace_paths.append(feature.file_path)
            records.append(
                FeatureRecord(
                    requirement_id=requirement_id,
                    content_hash=requirement.content_hash,
                    req_tag=feature.req_tag,
                    feature_path=_relative_to(feature.file_path, features_root),
                    scn_ids=tuple(s.scn_id for s in feature.scenarios),
                    ac_ids_covered=tuple(
                        ac
                        for ac, covered in feature.acceptance_criteria_coverage.items()
                        if covered
                    ),
                    cp2_verdict=cp2_result.overall_verdict.value,
                    remediated=False,
                    escalated=False,
                )
            )
            continue
        # CP2 failed even though generation/lint succeeded (e.g. cross-file
        # duplicate detection, or acceptance-criteria coverage) -- enter D5.
        dirty_by_id[requirement_id] = (feature.content, feature.req_tag)

    for requirement_id, (dirty_content, req_tag) in dirty_by_id.items():
        requirement = requirement_by_id[requirement_id]
        try:
            result = run_cp2_remediation(requirement, dirty_content, req_tag, remediator)
        except TransportFailureError as exc:
            # Symmetric to the generation-phase case above: the remediator's
            # own LLM boundary failed (provider/quota/timeout), not the
            # content it would have returned. Per-requirement recoverable,
            # same as any other transport failure -- recorded via
            # transport_failed below, the loop continues to the rest of
            # dirty_by_id rather than aborting the stage.
            transport_failed[requirement_id] = str(exc)
            continue
        file_path = derive_feature_file_path(requirement, features_root=features_root)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(result.final_content, encoding="utf-8")
        workspace_paths.append(file_path)
        rebuilt = rebuild_generated_feature(
            requirement, result.final_content, req_tag, _lint(result.final_content)
        )
        records.append(
            FeatureRecord(
                requirement_id=requirement_id,
                content_hash=requirement.content_hash,
                req_tag=req_tag,
                feature_path=_relative_to(file_path, features_root),
                scn_ids=tuple(s.scn_id for s in rebuilt.scenarios),
                ac_ids_covered=tuple(
                    ac for ac, covered in rebuilt.acceptance_criteria_coverage.items() if covered
                ),
                cp2_verdict=result.final_cp2_result.overall_verdict.value,
                remediated=True,
                escalated=(result.status == RemediationStatus.ESCALATED),
                escalation_reason=result.escalation_reason,
            )
        )

    for requirement_id, reason in unrecoverable.items():
        records.append(
            FeatureRecord(
                requirement_id=requirement_id,
                content_hash=requirement_by_id[requirement_id].content_hash,
                req_tag=f"@{requirement_id}",
                feature_path=None,
                scn_ids=(),
                ac_ids_covered=(),
                cp2_verdict=ValidationVerdict.FAIL.value,
                remediated=False,
                escalated=True,
                escalation_reason=f"pre-assembly generation contract violation: {reason}",
            )
        )

    for requirement_id, reason in transport_failed.items():
        # A different escalation REASON from unrecoverable above, by design
        # (ADR-0043 D5's escalation model applies to both, but a human
        # reviewing this record needs to know which: no retry was attempted
        # -- the platform has none anywhere in this call path today -- so a
        # transport failure is not evidence of anything about the generated
        # content, unlike a pre-assembly contract violation.
        records.append(
            FeatureRecord(
                requirement_id=requirement_id,
                content_hash=requirement_by_id[requirement_id].content_hash,
                req_tag=f"@{requirement_id}",
                feature_path=None,
                scn_ids=(),
                ac_ids_covered=(),
                cp2_verdict=ValidationVerdict.FAIL.value,
                remediated=False,
                escalated=True,
                escalation_reason=f"transport failure (no retry attempted): {reason}",
            )
        )

    order = {r.requirement_id: i for i, r in enumerate(requirement_set.requirements)}
    records.sort(key=lambda r: order[r.requirement_id])

    package = FeatureEngineeringPackage(
        contract_version=CONTRACT_VERSION,
        run_id=requirement_set.run_id,
        requirement_set_run_id=requirement_set.run_id,
        generated_at=datetime.now(UTC).isoformat(),
        records=tuple(records),
    )

    package_path = run_dir / FEATURE_ENGINEERING_PACKAGE_FILENAME
    atomic_write_json(package_path, package.to_json())

    traceability_path = run_dir / TRACEABILITY_FILENAME
    atomic_write_json(
        traceability_path,
        {"entries": build_traceability_index(package.records, features_root=features_root)},
    )

    report_path = run_dir / FEATURE_ENGINEERING_REPORT_FILENAME
    report_path.write_text(build_report(package), encoding="utf-8")

    test_data_specifications = build_test_data_specifications(requirement_set.requirements)
    test_data_specifications_path = run_dir / TEST_DATA_SPECIFICATIONS_FILENAME
    atomic_write_json(
        test_data_specifications_path,
        test_data_specifications_to_json(test_data_specifications),
    )

    return FeatureEngineeringStageResult(
        package=package,
        package_path=package_path,
        traceability_path=traceability_path,
        report_path=report_path,
        test_data_specifications_path=test_data_specifications_path,
        workspace_feature_paths=tuple(workspace_paths),
    )


def execute_feature_engineering_stage(
    run_state_mgr: RunStateManager,
    run_dir: Path,
    requirement_set: TestableRequirementSet,
    *,
    content_generator: FeatureContentGenerator,
    remediator: FeatureRemediator,
    input_artifacts: list[Path],
    baseline_root: Path = DEFAULT_BASELINE_ROOT,
) -> FeatureEngineeringStageResult | None:
    """Wire stage 14 into `run_state_mgr` with the SAME
    `start_stage`/try-except/`fail_stage`/`succeed_stage` idiom every Layer 1
    phase already uses in `scripts/run_requirement_analysis.py` -- not a
    parallel mechanism.

    Unlike `run_feature_engineering_stage` (which takes an explicit
    `features_root` from its caller), this function derives its own
    `features_root`: it materializes `run_dir`'s own isolated workspace copy
    of `baseline_root` (`.workspace.materialize_workspace`, ADR-0037 Path A)
    and generates into THAT copy's `src/test/resources/features/`, never
    into the shared tracked `baseline_root` itself and never into another
    run's copy. Materialization is idempotent -- a resumed run finds its
    existing copy (and whatever it already generated) untouched.

    Returns `None` both when the stage was SKIPPED (both ADR-0036 skip
    invariants held) and when it FAILED (a genuine exception, recorded via
    `fail_stage`) -- the caller reads `run_state_mgr.state` for which, the
    same way `handle_analyze` already does for every existing phase; this
    mirrors that no existing phase function returns a skip/fail-distinguishing
    sentinel either.
    """
    prior = next((s for s in run_state_mgr.state.stages if s.stage_id == STAGE_ID), None)
    prior_outputs = [Path(p) for p in (prior.output_artifacts if prior else ())]
    if prior_outputs and run_state_mgr.should_skip(
        STAGE_ID, input_artifacts=input_artifacts, output_artifacts=prior_outputs
    ):
        run_state_mgr.skip_stage(STAGE_ID)
        return None

    run_state_mgr.start_stage(STAGE_ID, input_artifacts=input_artifacts)
    try:
        workspace_dir = materialize_workspace(run_dir, baseline_root=baseline_root)
        result = run_feature_engineering_stage(
            requirement_set,
            features_root=features_root_for(workspace_dir),
            run_dir=run_dir,
            content_generator=content_generator,
            remediator=remediator,
        )
    except Exception as exc:  # surfaced via run_state.json, never fatal to the caller's process
        run_state_mgr.fail_stage(STAGE_ID, error=exc)
        return None
    else:
        run_state_mgr.succeed_stage(STAGE_ID, output_artifacts=list(result.all_output_paths))
        return result


__all__ = ["STAGE_ID", "execute_feature_engineering_stage", "run_feature_engineering_stage"]
