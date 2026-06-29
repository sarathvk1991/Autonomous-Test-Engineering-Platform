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
import platform as system_platform
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
_LAYER_DIR = _REPO_ROOT / "requirement_intelligence"
DEFAULT_OUTPUT_DIR = _REPO_ROOT / "output" / "executions"

# Make the platform importable when run as a standalone script.
sys.path.insert(0, str(_REPO_ROOT))

from requirement_intelligence.execution import (  # noqa: E402
    ExecutionData,
    ExecutionHistory,
    ExecutionWriter,
)
from requirement_intelligence.platform import PlatformContext  # noqa: E402
from requirement_intelligence.platform import platform_metadata as meta  # noqa: E402

DEFAULT_PROVIDER = "gemini"
SUPPORTED_PROVIDERS = meta.supported_provider_ids()
REASONING_CONTRACT_VERSION = meta.REASONING_CONTRACT_VERSION
# Synthetic request id used for --dry-run, where no execution_id is generated.
_DRY_RUN_REQUEST_ID = "dry-run"


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
        line = "=" * 52
        print(line)
        print("  Autonomous Test Engineering Platform")
        print("  Requirement Analysis CLI")
        print(line)
        print()

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


def run_engineering_pipeline(context: PlatformContext, console: Console) -> list[Any]:
    """Run Connectors -> Mappers -> Consolidation and return the artifacts.

    Connectors resolve their ``inputPath`` relative to the current working
    directory, so the pipeline runs from the layer directory and restores the
    previous working directory afterwards.
    """
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
    console.detail(f"SourceArtifacts: {len(source_artifacts)}")

    console.action("Running Consolidation")
    consolidated = context.create_consolidation_engine().consolidate(source_artifacts)
    console.ok(f"{len(consolidated)} Consolidated Artifacts")
    return consolidated


def _select_consolidated(consolidated: list[Any]) -> Any:
    """Deterministically select the consolidated artifact to analyse.

    Rule: the artifact with the greatest total grouped count; ties are broken by
    ``consolidated_id`` ascending. Fully reproducible for a given input.
    """

    def _key(c: Any) -> tuple[int, str]:
        total = (
            len(c.functional_artifacts)
            + len(c.security_artifacts)
            + len(c.quality_artifacts)
        )
        return (-total, c.consolidated_id)

    return sorted(consolidated, key=_key)[0]


def _resolve_selected(consolidated: list[Any], artifact_id: str | None) -> Any:
    """Return the consolidated artifact to analyse (by id, or deterministically)."""
    if not consolidated:
        raise CliError("No consolidated artifacts were produced from the inputs.")
    if artifact_id:
        for candidate in consolidated:
            if candidate.consolidated_id == artifact_id:
                return candidate
        raise CliError(f"No consolidated artifact found with id '{artifact_id}'.")
    return _select_consolidated(consolidated)


def _resolve_output_base(output_dir: str) -> Path:
    """Resolve the output base directory to an absolute path."""
    base = Path(output_dir)
    if not base.is_absolute():
        base = _REPO_ROOT / base
    return base.resolve()


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

    if (
        not args.dry_run
        and args.provider == "gemini"
        and not os.environ.get("GOOGLE_API_KEY")
    ):
        console.error(
            "GOOGLE_API_KEY is not set. Set it in your environment or a local "
            ".env file (or use --dry-run to skip the provider call)."
        )
        return 2

    context = PlatformContext()

    try:
        consolidated = run_engineering_pipeline(context, console)
        selected = _resolve_selected(consolidated, args.artifact_id)
    except CliError as exc:
        console.error(str(exc))
        return 1

    console.note(f"\nSelected\n  {selected.consolidated_id}")

    console.action("\nBuilding Prompt")
    prompt_builder = context.create_prompt_builder()
    prompt_request = prompt_builder.build(selected)
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
            result = service.analyze(selected)
        except Exception as exc:  # surface provider/orchestration errors cleanly
            console.error(f"Analysis failed: {exc}")
            return 1
        console.ok("Success")
        llm_request = prompt_request.to_llm_request(request_id=result.execution_id)

    data = ExecutionData(
        selected=selected,
        prompt_request=prompt_request,
        llm_request=llm_request,
        result=result,
        dry_run=args.dry_run,
        provider_name=args.provider,
        requested_model=args.model,
        reasoning_contract_version=REASONING_CONTRACT_VERSION,
        execution_name=args.execution_name,
        command_line_arguments=_serialise_args(args),
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


def handle_list_artifacts(args: argparse.Namespace) -> int:
    """Run the engineering pipeline and display every ConsolidatedArtifact."""
    console = Console(verbose=args.verbose)
    console.banner()
    _load_dotenv_if_present()

    context = PlatformContext()
    try:
        consolidated = run_engineering_pipeline(context, console)
    except CliError as exc:
        console.error(str(exc))
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


def handle_validate(args: argparse.Namespace) -> int:
    """Reserved subcommand — no validation logic exists yet."""
    print("This capability will be implemented in a future phase.")
    return 0


def handle_benchmark(args: argparse.Namespace) -> int:
    """Reserved subcommand — no benchmarking logic exists yet."""
    print("This capability will be implemented in a future phase.")
    return 0


def handle_version(args: argparse.Namespace) -> int:
    """Print full platform introspection (metadata, capabilities, system info)."""
    line = "=" * 52
    print(line)
    print("  Autonomous Test Engineering Platform")
    print(line)
    print()

    print("Platform Metadata")
    print("-" * 52)
    print(f"  Platform Version           : {meta.PLATFORM_VERSION}")
    print(f"  CLI Version                : {meta.CLI_VERSION}")
    print(f"  Prompt Version             : {meta.PROMPT_VERSION}")
    print(f"  Reasoning Contract Version : {meta.REASONING_CONTRACT_VERSION}")
    print(f"  Execution Package Version  : {meta.EXECUTION_PACKAGE_VERSION}")
    print()

    print("Architecture Components")
    print("-" * 52)
    for component in meta.ARCHITECTURE_COMPONENTS:
        mark = "✓" if component.available else "○"
        suffix = f" ({component.note})" if component.note else ""
        print(f"  {mark} {component.name}{suffix}")
    print()

    print("Available Providers")
    print("-" * 52)
    for provider in meta.PROVIDERS:
        mark = "✓" if provider.available else "○"
        suffix = f" ({provider.note})" if provider.note else ""
        print(f"  {mark} {provider.display}{suffix}")
    print()

    print("Supported CLI Commands")
    print("-" * 52)
    for command in meta.CLI_COMMANDS:
        print(f"  ✓ {command}")
    print()

    print("System Information")
    print("-" * 52)
    print(f"  Python Version        : {system_platform.python_version()}")
    print(f"  Operating System      : {system_platform.system()} {system_platform.release()}")
    print(f"  Platform Architecture : {system_platform.machine()}")
    print(f"  Current Directory     : {Path.cwd()}")
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
        help="Analyse a specific ConsolidatedArtifact id (default: deterministic selection).",
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
        "--verbose", action="store_true", help="Display detailed progress output."
    )
    analyze.set_defaults(func=handle_analyze)

    list_artifacts = subparsers.add_parser(
        "list-artifacts",
        help="Run the engineering pipeline and list all ConsolidatedArtifacts.",
    )
    list_artifacts.add_argument(
        "--verbose", action="store_true", help="Display detailed progress output."
    )
    list_artifacts.set_defaults(func=handle_list_artifacts)

    validate = subparsers.add_parser("validate", help="Reserved for a future phase.")
    validate.set_defaults(func=handle_validate)

    benchmark = subparsers.add_parser("benchmark", help="Reserved for a future phase.")
    benchmark.set_defaults(func=handle_benchmark)

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
  list-artifacts  Run the engineering pipeline and list ConsolidatedArtifacts.
  validate        Reserved for a future phase.
  benchmark       Reserved for a future phase.
  version         Show platform metadata, capabilities, providers, and system info.
  help            Show this detailed help.

analyze OPTIONS
  --artifact-id <id>     Analyse a specific ConsolidatedArtifact (default:
                         deterministic selection — the largest by grouped count).
  --provider <name>      LLM provider (default: gemini). Supported today: gemini.
  --model <name>         Override the configured model (default: env model).
  --output-dir <dir>     Base dir for saved executions (default: output/executions/).
  --execution-name <n>   Store under output/executions/<n>/ instead of a timestamp
                         (implies --save-execution; never overwrites — adds -1, -2…).
  --dry-run              Stop after prompt generation; do not call the provider.
  --save-execution       Keep a permanent, timestamped execution history copy.
  --verbose              Detailed progress output.

EXAMPLES
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
