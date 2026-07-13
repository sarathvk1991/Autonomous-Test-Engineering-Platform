#!/usr/bin/env python3
"""Requirement Analysis CLI — the official command-line tool for the platform.

A thin, subcommand-based orchestration layer (git/docker/kubectl style). It only:

    1. Parses CLI arguments.
    2. Creates a PlatformContext (dependency construction).
    3. Executes the requested subcommand (orchestration).
    4. Displays console progress.

All dependency construction lives in
``requirement_intelligence.platform.PlatformContext`` and all execution-package
file generation lives in ``requirement_intelligence.execution``. The CLT contains
no business logic and no file-format knowledge.

Pipeline (no layer is bypassed; the provider is never called directly):

    Connectors -> Mappers -> Consolidation Engine
        -> EngineeringContextOrchestrator -> EngineeringContext
        -> RequirementAnalysisService
            -> RequirementPromptBuilder -> PromptRequest -> LLMRequest
            -> LLM Provider -> LLMResponse
        -> AnalysisResult

Usage:
    python scripts/run_requirement_analysis.py <subcommand> [options]
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
_LAYER_DIR = _REPO_ROOT / "requirement_intelligence"
DEFAULT_OUTPUT_DIR = _REPO_ROOT / "output" / "executions"

# Make the platform importable when run as a standalone script.
sys.path.insert(0, str(_REPO_ROOT))

from requirement_intelligence.connectors.connector_exceptions import ConnectorError  # noqa: E402
from requirement_intelligence.context_orchestration import (  # noqa: E402
    ContextOrchestrationError,
)
from requirement_intelligence.execution import (  # noqa: E402
    ExecutionData,
    ExecutionHistory,
    ExecutionWriter,
)
from requirement_intelligence.mappers.base_mapper import MapperError  # noqa: E402
from requirement_intelligence.platform import (  # noqa: E402
    PlatformCapabilities,
    PlatformContext,
    StartupValidationError,
    check_connector_health,
    validate_startup,
)
from requirement_intelligence.platform import platform_metadata as meta  # noqa: E402
from requirement_intelligence.platform.connector_health import STATUS_READY  # noqa: E402
from requirement_intelligence.registry import (  # noqa: E402
    FILE_MODE,
    RegistryValidationError,
    resolve_execution_mode,
)

DEFAULT_PROVIDER = "gemini"
SUPPORTED_PROVIDERS = meta.supported_provider_ids()
REASONING_CONTRACT_VERSION = meta.REASONING_CONTRACT_VERSION
# Synthetic request id used for --dry-run, where no execution_id is generated.
_DRY_RUN_REQUEST_ID = "dry-run"
# Width of the demo banner rules and the dotted status leaders.
_BANNER_WIDTH = 52
_LEADER_WIDTH = 22


class CliError(Exception):
    """Raised for user-facing CLI errors (bad input, missing artifact, etc.)."""


# ===========================================================================
# Console output (presentation only)
# ===========================================================================


class Console:
    """Minimal, professional console reporter for CLI progress output."""

    def __init__(self, verbose: bool = False) -> None:
        """Create a console; *verbose* enables extra detail lines."""
        self.verbose = verbose

    def banner(self) -> None:
        """Print the CLI banner."""
        line = "=" * _BANNER_WIDTH
        print(line)
        print("  Autonomous Test Engineering Platform")
        print("  Requirement Intelligence Layer")
        print(line)
        print()

    def rule(self) -> None:
        """Print a horizontal rule."""
        print("=" * _BANNER_WIDTH)

    def field(self, label: str, value: str) -> None:
        """Print an aligned ``label : value`` line."""
        print(f"  {label:<{_LEADER_WIDTH}}: {value}")

    def status(self, label: str, value: str) -> None:
        """Print a dotted-leader status line (``JIRA ......... READY``)."""
        dots = "." * max(1, _LEADER_WIDTH - len(label))
        print(f"  {label} {dots} {value}")

    def action(self, message: str) -> None:
        """Announce the start of a step (e.g. ``Running Connectors...``)."""
        print(f"{message}...")

    def ok(self, message: str) -> None:
        """Print a success line (``  ✓ ...``)."""
        print(f"  ✓ {message}")

    def detail(self, message: str) -> None:
        """Print an indented detail line, only when verbose."""
        if self.verbose:
            print(f"    {message}")

    def note(self, message: str) -> None:
        """Print a plain line."""
        print(message)

    def error(self, message: str) -> None:
        """Print an error line to stderr (``  ✗ ...``)."""
        print(f"  ✗ {message}", file=sys.stderr)


# ===========================================================================
# CLI-level helpers (orchestration glue only)
# ===========================================================================


def _load_dotenv_if_present() -> None:
    """Load a local ``.env`` (gitignored) if python-dotenv is available."""
    env_file = _REPO_ROOT / ".env"
    if not env_file.exists():
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(env_file)


def _serialise_args(args: argparse.Namespace) -> dict[str, Any]:
    """Return a JSON-serialisable view of the parsed CLI arguments."""
    return {key: value for key, value in vars(args).items() if key != "func"}


def _enabled_source_names(registry: Any) -> list[str]:
    """Return display names of enabled sources, defensively (never raises)."""
    try:
        return [
            str(source.get("sourceName", source.get("sourceId", "?")))
            for source in registry.loader.get_enabled_sources()
        ]
    except Exception:
        return []


def _resolve_mode(console: Console) -> str | None:
    """Resolve the canonical ingestion mode, or report the error and return None."""
    try:
        return resolve_execution_mode()
    except RegistryValidationError as exc:
        console.error(str(exc))
        return None


def _run_preflight(console: Console, mode: str) -> bool:
    """Validate configuration before any source is touched.

    Returns ``True`` when the platform is configured to execute. A configuration
    problem is reported as plain, actionable text — never as a stack trace.
    """
    try:
        validate_startup(mode, base_dir=_LAYER_DIR)
    except StartupValidationError as exc:
        console.error(f"Startup validation failed ({mode} mode):")
        for failure in exc.failures:
            console.error(f"  - {failure}")
        return False
    return True


def _provider_display(provider: str, model: str | None) -> str:
    """Render ``provider (model)``, falling back to the environment-configured model."""
    effective = model or os.environ.get("GEMINI_MODEL", "")
    return f"{provider} ({effective})" if effective else provider


def _print_startup_banner(
    console: Console,
    mode: str,
    source_names: list[str],
    *,
    provider: str,
    model: str | None,
    validate_enabled: bool,
) -> None:
    """Print the concise operational summary shown at the start of a run.

    Reports what the run is configured to do. Never prints a credential, a
    token, or a resolved endpoint URL.

    Per-source status reflects what startup validation actually proved: in FILE
    mode the input file was opened, so the source is ``READY``; in API mode only
    configuration was resolved, so the source is ``CONFIGURED``. Use the
    ``health`` command to prove a live endpoint is reachable.
    """
    caps = PlatformCapabilities()
    versions = caps.platform_versions()
    enabled = "ENABLED" if validate_enabled else "DISABLED"
    source_status = STATUS_READY if mode == FILE_MODE else "CONFIGURED"

    console.rule()
    console.field("Version", versions["platformVersion"])
    console.field("Execution Mode", mode)
    console.field("Prompt Version", versions["promptVersion"])
    console.field("LLM Provider", _provider_display(provider, model))
    console.field("Registered Sources", ", ".join(source_names) or "none")
    console.field("Validation", enabled)
    console.field("CP1", enabled)
    console.field("Quality Governance", enabled)
    console.field("Execution Package", "ENABLED")
    console.rule()
    for name in source_names:
        console.status(name, source_status)
    console.rule()
    print()


def _print_orchestration_summary(console: Console, engineering_context: Any) -> None:
    """Report which groups composed the context, and what each domain contributed.

    Under a multi-source policy "Selected: <one id>" would misdescribe the run, so
    the summary states how many groups contributed and, per domain, how much of the
    available evidence reached the reasoner. An uncovered domain that *had* evidence
    is the CAP-074B defect, so it is called out rather than left to be inferred from
    a zero. Per-group attribution is verbose-only; the coverage line is not.

    Every figure is read from the context; the CLI computes none of them.
    """
    provenance = engineering_context.provenance
    evidence = engineering_context.evidence
    coverage = engineering_context.coverage

    console.note(
        f"\nEngineering Context\n"
        f"  groups   : {provenance.contributing_group_count} contributing "
        f"of {provenance.candidate_group_count} candidates\n"
        f"  evidence : functional={len(evidence.functional_artifacts)} "
        f"security={len(evidence.security_artifacts)} "
        f"quality={len(evidence.quality_artifacts)} "
        f"(total={evidence.total_count})"
    )
    for domain in coverage.domains:
        if domain.evidence_present and not domain.represented:
            console.note(
                f"  warning  : {domain.candidate_artifact_count} {domain.category} "
                f"artifact(s) available but not represented"
            )

    console.detail("")
    for contribution in provenance.contributions:
        truncation = (
            f" (of {contribution.candidate_artifact_count})" if contribution.truncated else ""
        )
        console.detail(
            f"#{contribution.rank} {contribution.consolidated_id} — "
            f"{contribution.artifact_count} artifact(s){truncation}"
        )


def run_engineering_pipeline(
    context: PlatformContext,
    console: Console,
    registry: Any | None = None,
) -> tuple[int, list[Any]]:
    """Run Connectors -> Mappers -> Consolidation.

    Returns ``(source_artifact_count, consolidated_artifacts)``. Connectors
    resolve their ``inputPath`` relative to the current working directory, so the
    pipeline runs from the layer directory and restores the previous working
    directory afterwards.

    A *registry* already built by the caller is reused; otherwise one is created.
    """
    if registry is None:
        console.action("Loading Registry")
        registry = context.create_connector_registry()
        console.ok("Success")

    source_names = _enabled_source_names(registry)
    console.action("Running Connectors")
    previous_cwd = Path.cwd()
    try:
        os.chdir(_LAYER_DIR)
        source_artifacts = registry.execute_all()
    finally:
        os.chdir(previous_cwd)
    for name in source_names:
        console.ok(name)
    source_count = len(source_artifacts)
    console.detail(f"SourceArtifacts: {source_count}")

    console.action("Running Consolidation")
    consolidated = context.create_consolidation_engine().consolidate(source_artifacts)
    console.ok(f"{len(consolidated)} Consolidated Artifacts")
    return source_count, consolidated


def _resolve_candidates(consolidated: list[Any], artifact_id: str | None) -> list[Any]:
    """Return the consolidation groups the orchestrator may choose between.

    The CLI narrows the *candidate set*; it never selects from it. ``--artifact-id``
    restricts the run to one named group, after which the orchestration policy has
    exactly one candidate and trivially selects it. Which group an unrestricted run
    analyses is decided by the governed ``OrchestrationPolicy`` alone (CAP-076C).
    """
    if not consolidated:
        raise CliError("No consolidated artifacts were produced from the inputs.")
    if not artifact_id:
        return consolidated
    for candidate in consolidated:
        if candidate.consolidated_id == artifact_id:
            return [candidate]
    raise CliError(f"No consolidated artifact found with id '{artifact_id}'.")


def _resolve_output_base(output_dir: str) -> Path:
    """Resolve the output base directory to an absolute path."""
    base = Path(output_dir)
    if not base.is_absolute():
        base = _REPO_ROOT / base
    return base.resolve()


def run_validation_phase(
    context: PlatformContext, result: Any, console: Console, profile: Any
) -> tuple[Any, Any]:
    """Optional Response Validation phase (additive; default behaviour unchanged).

    Flow: Requirement Analysis -> Response Normalization -> Response Validator ->
    ValidationResult. Per ADR-0003 the Response Validator consumes a
    ``ValidationInput`` (the analysed response bound to its ``NormalizationResult``),
    not a bare ``AnalysisResult``. This CLI acts as the *handoff seam* (ADR-0003 §4):
    it normalizes the response once, binds the ``ValidationInput``, and hands it to
    the Validator. It performs no validation and no judgment itself.

    The Validator is obtained from :class:`PlatformContext` — the single platform
    construction hub — which composes the validator for the selected governed
    *profile* (CAP-044). The profile only narrows which rules run; ordering stays
    governed by ``LAYER_ORDER``. The CLI performs no validator wiring of its own and
    chooses no rules itself.

    Returns ``(validation_result, normalization_result)``. The ``ValidationResult`` is
    handed to the execution package for persistence (CAP-042); the same-execution
    ``NormalizationResult`` is returned so the downstream Validation → CP1 handoff
    (CAP-067B) can bind its ``CP1Input`` **without re-normalizing** (normalize-once,
    ADR-0011). The CLI neither inspects nor mutates either object.
    """
    # Imported lazily so the default analysis path never pays for the normalization
    # subsystem, and so this phase is wholly opt-in.
    from requirement_intelligence.normalization.framework.normalization_pipeline import (
        NormalizationPipeline,
    )
    from requirement_intelligence.normalization.framework.normalization_registry import (
        NormalizationRegistry,
    )
    from requirement_intelligence.normalization.models.normalization_configuration import (
        NormalizationConfiguration,
    )
    from requirement_intelligence.normalization.response import ResponseNormalizer
    from requirement_intelligence.validation import ValidationInput

    console.action("\nRunning Response Validation")

    # Handoff seam: normalize once, then bind the canonical ValidationInput.
    normalization_registry = NormalizationRegistry()
    normalizer = ResponseNormalizer(
        normalization_registry,
        NormalizationPipeline(normalization_registry),
        NormalizationConfiguration(),
    )
    normalization_result = normalizer.normalize(result.llm_response)
    validation_input = ValidationInput(
        analysis_result=result,
        normalization_result=normalization_result,
    )

    validator = context.create_response_validator_for_profile(profile)

    validation = validator.validate(validation_input)
    summary = validation.validation_summary
    statistics = validation.validation_statistics

    console.ok(f"Overall Verdict : {validation.overall_verdict}")
    console.note(f"  Validation Profile  : {profile.name}")
    console.note(f"  Rules Executed      : {statistics.rules_executed}")
    console.note(f"  Issues Found        : {summary.total_issues}")
    console.note(f"  Validation Duration : {statistics.validation_duration_ms:.2f} ms")
    return validation, normalization_result


def run_cp1_phase(
    context: PlatformContext,
    validation_result: Any,
    normalization_result: Any,
    console: Console,
) -> Any:
    """CP1 engineering-readiness phase — Validation → CP1 handoff → CP1Service.run (CAP-067B).

    Flow: ValidationResult + NormalizationResult -> ValidationToCP1Handoff ->
    CP1Input (only when the verdict gate is open) -> CP1Service.run -> CP1Result.

    This CLI is *pure orchestration glue*: it obtains the governed seam and the single
    ``CP1Service`` **only** from :class:`PlatformContext` (the construction hub) and
    invokes them. It constructs **no** registry, pipeline, criterion, engine, or
    ``CP1Input``, aggregates nothing, and invents no gating policy — the seam owns the
    gate/bind (ADR-0011 §D4/§D5) and the engine owns execution/aggregation.

    Gate semantics (ADR-0011 §D5): the seam returns a ``CP1Input`` only for
    ``PASSED`` / ``PASSED_WITH_WARNINGS``; a ``FAILED`` / ``BLOCKED`` verdict returns
    ``None`` and CP1 is **skipped** — a ``FAILED``/``BLOCKED`` response never reaches CP1.

    Returns the ``CP1Result`` when CP1 executed, or ``None`` when the gate was closed.
    """
    console.action("\nRunning CP1 Engineering-Readiness Evaluation")

    handoff = context.create_validation_to_cp1_handoff()
    cp1_input = handoff.hand_off(validation_result, normalization_result)
    if cp1_input is None:
        console.note(
            f"  Skipped — validation verdict '{validation_result.overall_verdict}' "
            "does not open the CP1 gate (ADR-0011 §D5)."
        )
        return None

    cp1_result = context.cp1_service.run(cp1_input)

    console.ok(f"Overall Verdict : {cp1_result.overall_verdict}")
    console.note(f"  Findings            : {len(cp1_result.findings)}")
    return cp1_result


def run_requirement_enhancement_phase(
    context: PlatformContext,
    engineering_context: Any,
    analysis_result: Any,
    console: Console,
) -> Any:
    """Requirement Enhancement phase — a peer capability, immediately after Analysis
    (CAP-081C, ADR-0018 §D9).

    Runs strictly downstream of Analysis and upstream of Grounding, at the
    permanently frozen pipeline position::

        Engineering Context → Analysis → Requirement Enhancement → Grounding
            → Validation → CP1 → Quality Governance → Execution Package

    It consumes **only** the completed ``EngineeringContext`` and ``AnalysisResult``
    — the same two inputs Grounding consumes — and modifies neither. The single
    ``RequirementEnhancementService`` comes solely from :class:`PlatformContext`;
    this CLI is pure orchestration glue and invents no enrichment, relationship, or
    observation logic of its own. Mirroring Grounding, a failure here is surfaced
    but never fatal to the analysis run, and never corrupts the already-completed
    upstream results.
    """
    console.action("\nRequirement Enhancement")
    result = context.create_requirement_enhancement_service().enhance(
        engineering_context, analysis_result
    )
    summary = result.summary
    console.ok(f"Enhanced requirements: {summary.total_requirements_enhanced}")
    console.note(f"  {summary.headline}")
    console.note(f"  Relationships       : {summary.total_relationships}")
    console.note(f"  Observations        : {summary.total_observations}")
    console.note(f"  Findings            : {summary.total_findings}")
    return result


def run_quality_governance_phase(
    context: PlatformContext,
    grounding_result: Any,
    validation_result: Any,
    cp1_result: Any,
    console: Console,
) -> Any:
    """Quality Governance phase — the terminal release authority (CAP-080D, ADR-0017 §D30).

    Runs immediately after CP1, at the permanently frozen end of the pipeline::

        Engineering Context → Analysis → Grounding → Validation → CP1
            → Quality Governance → Execution Package

    It consumes **only** the three completed peer results — ``GroundingResult``,
    ``ValidationResult``, ``CP1Result`` — and modifies nothing upstream. The single
    ``QualityGovernanceService`` comes solely from :class:`PlatformContext`; this CLI is
    pure orchestration glue and invents no governance logic, evaluates no rule, and derives
    no decision of its own. The returned ``QualityDecision`` is the canonical release
    verdict; the CLI records it and never reinterprets or overrides it (ADR-0017 §D30,
    Recommendation 6).

    Governance is **one aggregate evaluation** (ADR-0017 §D29): it either returns a complete
    ``QualityGovernanceResult`` or raises. Mirroring grounding/validation/CP1, a governance
    failure is surfaced by the caller but is never fatal to the analysis run, and never
    corrupts the already-completed upstream results.
    """
    console.action("\nRunning Quality Governance")
    governance_result = context.create_quality_governance_service().evaluate(
        grounding_result, validation_result, cp1_result
    )
    assessment = governance_result.assessment
    console.ok(f"Release Decision : {assessment.decision}")
    console.note(f"  {assessment.summary.verdict}")
    console.note(f"  Findings            : {len(assessment.findings)}")
    return governance_result


# ===========================================================================
# Subcommand handlers
# ===========================================================================


def handle_analyze(args: argparse.Namespace) -> int:
    """Execute a complete AI analysis (or a --dry-run up to prompt generation)."""
    console = Console(verbose=args.verbose)
    console.banner()
    _load_dotenv_if_present()

    if args.provider not in SUPPORTED_PROVIDERS:
        console.error(
            f"Provider '{args.provider}' is not supported. "
            f"Supported providers: {', '.join(SUPPORTED_PROVIDERS)}."
        )
        return 2

    if not args.dry_run and args.provider == "gemini" and not os.environ.get("GOOGLE_API_KEY"):
        console.error(
            "GOOGLE_API_KEY is not set. Set it in your environment or a local "
            ".env file (or use --dry-run to skip the provider call)."
        )
        return 2

    mode = _resolve_mode(console)
    if mode is None:
        return 2
    if not _run_preflight(console, mode):
        return 2

    context = PlatformContext()

    # Resolve the governed Validation Profile up-front (fail fast on an unknown
    # name), only when validation is requested. PlatformContext owns selection;
    # the CLI just names the desired profile.
    validation_profile: Any = None
    if getattr(args, "validate", False):
        from requirement_intelligence.validation.profiles import (
            UnknownValidationProfileError,
        )

        try:
            validation_profile = context.get_validation_profile(args.validation_profile)
        except UnknownValidationProfileError as exc:
            console.error(str(exc))
            return 2

    registry = context.create_connector_registry()
    _print_startup_banner(
        console,
        mode,
        _enabled_source_names(registry),
        provider=args.provider,
        model=args.model,
        validate_enabled=bool(getattr(args, "validate", False)),
    )
    console.note("Starting execution...\n")

    try:
        source_count, consolidated = run_engineering_pipeline(context, console, registry)
        candidates = _resolve_candidates(consolidated, args.artifact_id)
    except CliError as exc:
        console.error(str(exc))
        return 1
    except (ConnectorError, RegistryValidationError) as exc:
        console.error(f"Source ingestion failed ({mode} mode): {exc}")
        console.error("Run 'health' to check every configured source.")
        return 1
    except MapperError as exc:
        console.error(f"Source mapping failed ({mode} mode): {exc}")
        return 1

    # Engineering Context Orchestration (CAP-076C; multi-source since CAP-076D).
    # The orchestrator applies the governed policy PlatformContext bound it to and
    # returns the composed context plus the groups that composed it, in rank order.
    # The CLI ranks nothing, selects nothing, and budgets nothing.
    console.action("\nOrchestrating Engineering Context")
    try:
        orchestration = context.create_engineering_context_orchestrator().orchestrate(candidates)
    except ContextOrchestrationError as exc:
        console.error(f"Engineering context orchestration failed: {exc}")
        return 1
    engineering_context = orchestration.context
    selected = orchestration.primary_group
    console.ok(f"{engineering_context.context_id}")
    console.detail(engineering_context.orchestration_reason)
    _print_orchestration_summary(console, engineering_context)

    console.action("\nBuilding Prompt")
    prompt_builder = context.create_prompt_builder()
    prompt_request = prompt_builder.build(engineering_context)
    console.ok("Complete")

    if args.dry_run:
        console.action("Dry run — skipping provider call")
        llm_request = prompt_request.to_llm_request(request_id=_DRY_RUN_REQUEST_ID)
        result: Any = None
        console.ok("Provider call skipped")
    else:
        console.action("Calling Provider")
        provider = context.create_provider(args.provider, args.model)
        provider.validate_connection()
        service = context.create_requirement_analysis_service(
            prompt_builder,
            provider,
            context.create_analysis_configuration(REASONING_CONTRACT_VERSION),
        )
        try:
            result = service.analyze(engineering_context)
        except Exception as exc:  # surface provider/orchestration errors cleanly
            console.error(f"Analysis failed: {exc}")
            return 1
        console.ok("Success")
        llm_request = prompt_request.to_llm_request(request_id=result.execution_id)

    # Requirement Enhancement phase (CAP-081C): strictly downstream of Analysis and
    # upstream of Grounding (Engineering Context → Analysis → Requirement Enhancement
    # → Grounding → Validation → CP1 → Quality Governance → Execution Package). It
    # consumes only EngineeringContext + AnalysisResult and modifies neither. Skipped
    # for dry runs (no response to enhance). Surfaced but never fatal, mirroring
    # Grounding/Validation/CP1.
    requirement_enhancement_result: Any = None
    if result is not None:
        try:
            requirement_enhancement_result = run_requirement_enhancement_phase(
                context, engineering_context, result, console
            )
        except Exception as exc:  # surface but never fail the analysis run
            console.error(f"Requirement enhancement failed: {exc}")

    # Grounding phase (CAP-077F.2): strictly downstream of Analysis. It grades the
    # generated requirements against the evidence the reasoner actually saw and returns a
    # GroundingResult, which the execution package serialises as-is. It never modifies the
    # AnalysisResult, prompt, EngineeringContext, Validation, or CP1. Skipped for dry runs
    # (no response to ground). Surfaced but never fatal — one grounding failure must not
    # deny the rest of the run, exactly as validation/CP1 failures are handled.
    grounding_result: Any = None
    if result is not None:
        console.action("\nGrounding")
        try:
            grounding_result = context.create_grounding_service().assess(
                engineering_context, result
            )
        except Exception as exc:  # surface but never fail the analysis run
            console.error(f"Grounding failed: {exc}")
        else:
            summary = grounding_result.assessment.summary
            console.ok(f"Grounding score: {summary.grounding_score}")
            console.note(f"  {summary.verdict}")

    # Optional, opt-in Response Validation phase. Default behaviour is unchanged:
    # validation runs only with --validate and only when a real result exists
    # (never for --dry-run, which produces no response to validate). It is executed
    # before the package is written so its complete ValidationResult is persisted
    # into the execution package (CAP-042); the package owns persistence, the CLI
    # only orchestrates.
    # After validation, the Validation → CP1 handoff gates on the verdict and, when
    # open, CP1Service.run produces a CP1Result (CAP-067B). Both the seam and the
    # single CP1Service come solely from PlatformContext; the CLI wires nothing itself
    # and re-normalizes nothing (the NormalizationResult is threaded through).
    validation_result: Any = None
    cp1_result: Any = None
    if getattr(args, "validate", False) and result is not None:
        try:
            validation_result, normalization_result = run_validation_phase(
                context, result, console, validation_profile
            )
        except Exception as exc:  # surface but never fail the analysis run
            console.error(f"Response validation failed: {exc}")
        else:
            try:
                cp1_result = run_cp1_phase(
                    context, validation_result, normalization_result, console
                )
            except Exception as exc:  # surface but never fail the analysis run
                console.error(f"CP1 engineering-readiness evaluation failed: {exc}")

    # Quality Governance phase (CAP-080D): the terminal release authority, immediately after
    # CP1 and at the permanently frozen end of the pipeline (Grounding → Validation → CP1 →
    # Quality Governance → Execution Package). It consumes only the three completed peer
    # results and runs exactly when all three exist — a live, validated, CP1-gate-open run.
    # It modifies nothing upstream. Mirroring grounding/validation/CP1, a governance failure
    # is surfaced but never fatal, and never corrupts the already-completed upstream results.
    quality_governance_result: Any = None
    if (
        grounding_result is not None
        and validation_result is not None
        and cp1_result is not None
    ):
        try:
            quality_governance_result = run_quality_governance_phase(
                context, grounding_result, validation_result, cp1_result, console
            )
        except Exception as exc:  # surface but never fail the analysis run
            console.error(f"Quality governance evaluation failed: {exc}")

    data = ExecutionData(
        selected=selected,
        engineering_context=engineering_context,
        prompt_request=prompt_request,
        llm_request=llm_request,
        result=result,
        dry_run=args.dry_run,
        provider_name=args.provider,
        requested_model=args.model,
        reasoning_contract_version=REASONING_CONTRACT_VERSION,
        execution_name=args.execution_name,
        command_line_arguments=_serialise_args(args),
        source_artifact_count=source_count,
        consolidated_artifacts=consolidated,
        validation_result=validation_result,
        validation_profile=validation_profile if validation_result is not None else None,
        cp1_result=cp1_result,
        grounding_result=grounding_result,
        quality_governance_result=quality_governance_result,
        requirement_enhancement_result=requirement_enhancement_result,
    )

    effective_save = args.save_execution or bool(args.execution_name)
    history = ExecutionHistory(_resolve_output_base(args.output_dir))
    target_dir = history.resolve_target(
        save_execution=effective_save, execution_name=args.execution_name
    )
    history.prepare(target_dir)

    console.action("Writing Execution Package")
    write_result = ExecutionWriter().write(target_dir, data)
    history.finalize(target_dir, save_execution=effective_save)
    console.ok("Complete")

    console.note("\nExecution Finished")
    console.note(f"  package : {write_result.target_dir}")
    console.note(f"  latest  : {history.latest_dir}")
    if result is not None:
        console.note(f"  provider={args.provider} model={result.model}")
        console.note(f"  json_valid={write_result.json_valid}")
    return 0


def handle_health(args: argparse.Namespace) -> int:
    """Probe every enabled source and report readiness. Runs no pipeline stage.

    Exercises the connector layer only — Consolidation, the LLM provider,
    Normalization, Validation, CP1, and the Execution Package are never invoked.
    Exit code is 0 when every source is READY, 1 otherwise, so the command is
    usable as a deployment gate.
    """
    console = Console(verbose=False)
    console.banner()
    _load_dotenv_if_present()

    mode = _resolve_mode(console)
    if mode is None:
        return 2

    console.field("Execution Mode", mode)
    console.rule()
    try:
        report = check_connector_health(mode, base_dir=_LAYER_DIR)
    except RegistryValidationError as exc:
        console.error(f"Source registry could not be loaded: {exc}")
        return 2

    for result in report.results:
        console.status(result.source_name, result.status)
        if result.detail and (args.verbose or not result.healthy):
            console.note(f"      {result.detail}")
    console.rule()

    if report.healthy:
        console.note(f"\nAll {len(report.results)} source(s) READY.")
        return 0
    unhealthy = [r.source_name for r in report.results if not r.healthy]
    console.error(f"\n{len(unhealthy)} source(s) not ready: {', '.join(unhealthy)}")
    return 1


def handle_list_artifacts(args: argparse.Namespace) -> int:
    """Run the engineering pipeline and display every ConsolidatedArtifact."""
    console = Console(verbose=args.verbose)
    console.banner()
    _load_dotenv_if_present()

    mode = _resolve_mode(console)
    if mode is None:
        return 2
    if not _run_preflight(console, mode):
        return 2

    context = PlatformContext()
    try:
        _, consolidated = run_engineering_pipeline(context, console)
    except CliError as exc:
        console.error(str(exc))
        return 1
    except (ConnectorError, RegistryValidationError) as exc:
        console.error(f"Source ingestion failed ({mode} mode): {exc}")
        console.error("Run 'health' to check every configured source.")
        return 1
    except MapperError as exc:
        console.error(f"Source mapping failed ({mode} mode): {exc}")
        return 1

    console.note(f"\nConsolidated Artifacts ({len(consolidated)}):\n")
    for artifact in consolidated:
        console.note(f"- {artifact.consolidated_id}")
        console.note(f"    Business Area : {artifact.business_area or '-'}")
        console.note(f"    Module        : {artifact.module}")
        console.note(f"    Risk Level    : {artifact.risk_level}")
        console.note(f"    Functional    : {len(artifact.functional_artifacts)}")
        console.note(f"    Security      : {len(artifact.security_artifacts)}")
        console.note(f"    Quality       : {len(artifact.quality_artifacts)}")
    return 0


def _print_capability_section(title: str, capabilities: Any) -> None:
    """Render one ✓/○ capability section."""
    print("-" * 52)
    print(f"  {title}")
    print("-" * 52)
    for capability in capabilities:
        mark = "✓" if capability.available else "○"
        label = getattr(capability, "display", None) or capability.name
        suffix = f" ({capability.note})" if capability.note else ""
        print(f"  {mark} {label}{suffix}")
    print()


def handle_version(args: argparse.Namespace) -> int:
    """Print full platform introspection sourced from PlatformCapabilities."""
    _load_dotenv_if_present()
    caps = PlatformCapabilities()
    identity = caps.platform_identity()
    versions = caps.platform_versions()

    line = "=" * 52
    print(line)
    print("  Platform Metadata")
    print(line)
    print()

    try:
        ingestion_mode = resolve_execution_mode()
    except RegistryValidationError:
        ingestion_mode = "INVALID (see EXECUTION_MODE)"

    print("Platform Identity")
    print(f"  Architecture      : {identity['architecture']}")
    print(f"  Deployment Model  : {identity['deploymentModel']}")
    print(f"  Execution Mode    : {ingestion_mode} (ingestion)")
    print()
    print(f"  Platform Version           : {versions['platformVersion']}")
    print(f"  CLI Version                : {versions['cliVersion']}")
    print(f"  Prompt Version             : {versions['promptVersion']}")
    print(f"  Reasoning Contract Version : {versions['reasoningContractVersion']}")
    print(f"  Execution Package Version  : {versions['executionPackageVersion']}")
    print(f"  Manifest Schema Version    : {versions['manifestSchemaVersion']}")
    print()

    for title, components in caps.component_groups():
        _print_capability_section(title, components)

    _print_capability_section("Available Providers", caps.providers())

    print("-" * 52)
    print("  Supported Commands")
    print("-" * 52)
    for command in caps.supported_commands():
        print(f"  {command}")
    print()

    system = caps.system_identity()
    print("-" * 52)
    print("  System Information")
    print("-" * 52)
    print(f"  Python Version        : {system['pythonVersion']}")
    print(f"  Operating System      : {system['operatingSystem']}")
    print(f"  Platform Architecture : {system['platformArchitecture']}")
    print(f"  Current Directory     : {system['currentWorkingDirectory']}")
    return 0


def handle_help(args: argparse.Namespace) -> int:
    """Print detailed usage and examples for every subcommand."""
    print(_HELP_TEXT)
    return 0


# ===========================================================================
# Argument parsing
# ===========================================================================


def build_parser() -> argparse.ArgumentParser:
    """Construct the argparse parser with one subparser per subcommand."""
    parser = argparse.ArgumentParser(
        prog="run_requirement_analysis.py",
        description="Requirement Analysis CLI for the Autonomous Test Engineering Platform.",
    )
    subparsers = parser.add_subparsers(dest="command")

    analyze = subparsers.add_parser("analyze", help="Execute a complete AI analysis.")
    analyze.add_argument(
        "--artifact-id",
        default=None,
        help="Restrict the run to one ConsolidatedArtifact id (default: policy selection).",
    )
    analyze.add_argument(
        "--provider", default=DEFAULT_PROVIDER, help=f"LLM provider (default: {DEFAULT_PROVIDER})."
    )
    analyze.add_argument(
        "--model", default=None, help="Override the configured model (default: env model)."
    )
    analyze.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Base directory for saved executions (default: output/executions/).",
    )
    analyze.add_argument(
        "--execution-name",
        default=None,
        help="Name this execution; stored under output/executions/<name>/ (implies save).",
    )
    analyze.add_argument(
        "--dry-run",
        action="store_true",
        help="Run through prompt generation only; do not call the provider.",
    )
    analyze.add_argument(
        "--save-execution",
        action="store_true",
        help="Persist a permanent, timestamped execution history copy.",
    )
    analyze.add_argument(
        "--validate",
        action="store_true",
        help="After a live analysis, run the Response Validator and show the validation summary.",
    )
    analyze.add_argument(
        "--validation-profile",
        default="default",
        help=(
            "Governed validation profile selecting which layers' rules run "
            "(default: default). Choices: default, strict, transport-only, "
            "syntax-only, schema-only, content-review. Requires --validate."
        ),
    )
    analyze.add_argument("--verbose", action="store_true", help="Display detailed progress output.")
    analyze.set_defaults(func=handle_analyze)

    health = subparsers.add_parser(
        "health",
        help="Check that every enabled source is reachable. Runs no pipeline stage.",
    )
    health.add_argument(
        "--verbose", action="store_true", help="Show the detail line for every source."
    )
    health.set_defaults(func=handle_health)

    list_artifacts = subparsers.add_parser(
        "list-artifacts",
        help="Run the engineering pipeline and list all ConsolidatedArtifacts.",
    )
    list_artifacts.add_argument(
        "--verbose", action="store_true", help="Display detailed progress output."
    )
    list_artifacts.set_defaults(func=handle_list_artifacts)

    version = subparsers.add_parser("version", help="Show platform introspection.")
    version.set_defaults(func=handle_version)

    help_cmd = subparsers.add_parser("help", help="Detailed usage and examples.")
    help_cmd.set_defaults(func=handle_help)

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    return int(args.func(args))


_HELP_TEXT = """\
Autonomous Test Engineering Platform — Requirement Analysis CLI

USAGE
  python scripts/run_requirement_analysis.py <subcommand> [options]

SUBCOMMANDS
  analyze         Execute a complete AI analysis (live, or --dry-run).
  health          Check every enabled source is reachable; runs no pipeline stage.
  list-artifacts  Run the engineering pipeline and list ConsolidatedArtifacts.
  version         Show platform metadata, capabilities, providers, and system info.
  help            Show this detailed help.

EXECUTION MODE
  One environment variable selects how every source is ingested:

    EXECUTION_MODE=FILE   Read exported artifacts from disk (default).
    EXECUTION_MODE=API    Fetch live from JIRA / SonarQube / OWASP ZAP.

  The mode applies to all sources at once. API mode additionally requires the
  per-source credentials listed in .env.example; startup validation checks they
  are present before any source is contacted.

analyze OPTIONS
  --artifact-id <id>     Restrict the run to one ConsolidatedArtifact (default:
                         the governed orchestration policy selects — today, the
                         largest group by grouped count).
  --provider <name>      LLM provider (default: gemini). Supported today: gemini.
  --model <name>         Override the configured model (default: env model).
  --output-dir <dir>     Base dir for saved executions (default: output/executions/).
  --execution-name <n>   Store under output/executions/<n>/ instead of a timestamp
                         (implies --save-execution; never overwrites — adds -1, -2…).
  --dry-run              Stop after prompt generation; do not call the provider.
  --save-execution       Keep a permanent, timestamped execution history copy.
  --validate             After a live analysis, run the Response Validator and
                         print a validation summary (rules executed, issues,
                         verdict, duration). Optional; default behaviour is
                         unchanged. Has no effect with --dry-run.
  --validation-profile <name>
                         Governed profile selecting which layers' rules run
                         (default: default). Choices: default, strict,
                         transport-only, syntax-only, schema-only,
                         content-review. Requires --validate.
  --verbose              Detailed progress output.

EXAMPLES
  # Check every source before demonstrating anything
  python scripts/run_requirement_analysis.py health

  # Same check against the live source systems
  EXECUTION_MODE=API python scripts/run_requirement_analysis.py health

  # Backward-compatible baseline run (live), writing to output/latest/
  python scripts/run_requirement_analysis.py analyze

  # Dry run (no provider call), verbose
  python scripts/run_requirement_analysis.py analyze --dry-run --verbose

  # Named execution (persisted under output/executions/prompt-v1.1/)
  python scripts/run_requirement_analysis.py analyze --execution-name prompt-v1.1

  # Override provider/model and keep a timestamped history entry
  python scripts/run_requirement_analysis.py analyze --model gemini-2.5-flash \\
      --save-execution

  # List every consolidated artifact (no LLM call)
  python scripts/run_requirement_analysis.py list-artifacts

  # Platform introspection
  python scripts/run_requirement_analysis.py version

OUTPUT
  output/latest/                      Always the most recent execution package.
  output/executions/<timestamp>/      Permanent history (with --save-execution).
  output/executions/<name>/           Named history (with --execution-name).
  manifest.json                       Canonical entry point for each package.
"""


if __name__ == "__main__":
    raise SystemExit(main())
