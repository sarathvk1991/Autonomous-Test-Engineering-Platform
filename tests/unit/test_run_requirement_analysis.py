"""Unit tests for the Requirement Analysis CLI and its supporting packages.

External dependencies (connectors, consolidation, prompt builder, provider,
analysis service) are mocked via a fake PlatformContext. No live Gemini call is
made and no real input files are read.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock

import pytest

from requirement_intelligence.analysis.analysis_models import AnalysisResult
from requirement_intelligence.analysis.requirement_analysis_service import (
    RequirementAnalysisService,
)
from requirement_intelligence.consolidation.consolidation_engine import (
    ConsolidationEngine,
)
from requirement_intelligence.execution import (
    BaselineMetricsBuilder,
    ExecutionData,
    ExecutionHistory,
    ExecutionSummaryBuilder,
    ExecutionWriter,
    ManifestBuilder,
    ReviewBuilder,
    ValidationReportBuilder,
)
from requirement_intelligence.execution.execution_metrics import (
    engineering_metrics,
    execution_package_identifier,
)
from requirement_intelligence.llm.llm_models import LLMResponse
from requirement_intelligence.platform import PlatformCapabilities, PlatformContext
from requirement_intelligence.prompts.requirement_prompt_builder import (
    RequirementPromptBuilder,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "run_requirement_analysis.py"


def _load_cli() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_requirement_analysis", _SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cli = _load_cli()


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeArtifact:
    def __init__(
        self,
        consolidated_id: str,
        functional: int = 0,
        security: int = 0,
        quality: int = 0,
        module: str = "module-x",
        business_area: str | None = None,
        risk: str = "low",
    ) -> None:
        self.consolidated_id = consolidated_id
        self.module = module
        self.business_area = business_area
        self.risk_level = risk
        self.functional_artifacts = [object()] * functional
        self.security_artifacts = [object()] * security
        self.quality_artifacts = [object()] * quality

    def model_dump(self, **_: Any) -> dict[str, Any]:
        return {"consolidatedId": self.consolidated_id}


class FakeLLMRequest:
    def __init__(self, request_id: str) -> None:
        self.request_id = request_id

    def model_dump(self, **_: Any) -> dict[str, Any]:
        return {"request_id": self.request_id, "prompt": "FULL"}


class FakePromptRequest:
    system_prompt = "SYSTEM"
    user_prompt = "USER"
    prompt_version = "1.0.0"

    @property
    def full_prompt(self) -> str:
        return "SYSTEM\n\nUSER"

    def to_llm_request(self, request_id: str) -> FakeLLMRequest:
        return FakeLLMRequest(request_id)


class FakeUsage:
    prompt_tokens = 10
    completion_tokens = 20
    total_tokens = 30


class FakeLLMResponse:
    generated_text = (
        '{"summary":"s","functional_requirements":[],"security_requirements":[],'
        '"quality_requirements":["q"],"risks":[],"recommendations":["r"]}'
    )
    usage = FakeUsage()

    def model_dump(self, **_: Any) -> dict[str, Any]:
        return {"generated_text": self.generated_text}


class FakeResult:
    analysis_id = "analysis-123"
    execution_id = "execution-456"
    model = "gemini-2.5-flash"
    provider = "gemini"
    prompt_version = "1.0.0"
    reasoning_contract_version = "1.0.0"
    duration_ms = 123.4
    started_at = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    completed_at = datetime(2026, 1, 1, 0, 0, 1, tzinfo=UTC)
    llm_response = FakeLLMResponse()

    def model_dump(self, **_: Any) -> dict[str, Any]:
        return {"analysisId": self.analysis_id}


class FakeContext:
    """A drop-in fake PlatformContext returning mocked components."""

    def __init__(self, consolidated: list[FakeArtifact], result: Any = None) -> None:
        self._consolidated = consolidated
        self._result = result

    def create_connector_registry(self) -> MagicMock:
        registry = MagicMock()
        registry.execute_all.return_value = [object()]
        return registry

    def create_consolidation_engine(self) -> MagicMock:
        engine = MagicMock()
        engine.consolidate.return_value = self._consolidated
        return engine

    def create_prompt_builder(self) -> MagicMock:
        builder = MagicMock()
        builder.build.return_value = FakePromptRequest()
        return builder

    def create_provider(self, provider_name: str, model: str | None = None) -> MagicMock:
        return MagicMock()

    def create_analysis_configuration(self, reasoning_contract_version: str) -> MagicMock:
        return MagicMock()

    def create_requirement_analysis_service(
        self, prompt_builder: Any, provider: Any, configuration: Any
    ) -> MagicMock:
        service = MagicMock()
        service.analyze.return_value = self._result
        return service

    def create_response_validator(self) -> Any:
        # Faithful drop-in: the real hub composes the fully-wired validator.
        return PlatformContext().create_response_validator()

    def get_validation_profile(self, name: str | None = None) -> Any:
        return PlatformContext().get_validation_profile(name)

    def create_response_validator_for_profile(self, profile: Any) -> Any:
        return PlatformContext().create_response_validator_for_profile(profile)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _no_dotenv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "_load_dotenv_if_present", lambda: None)


def _use_context(
    monkeypatch: pytest.MonkeyPatch,
    consolidated: list[FakeArtifact],
    result: Any = None,
) -> None:
    monkeypatch.setattr(cli, "PlatformContext", lambda: FakeContext(consolidated, result))


def _read_manifest(directory: Path) -> dict[str, Any]:
    return json.loads((directory / "manifest.json").read_text())


def _dry_run_data(execution_name: str | None = None) -> ExecutionData:
    return ExecutionData(
        selected=FakeArtifact("cons-a", quality=2),
        prompt_request=FakePromptRequest(),
        llm_request=FakeLLMRequest("rid"),
        result=None,
        dry_run=True,
        provider_name="gemini",
        requested_model=None,
        reasoning_contract_version="1.0.0",
        execution_name=execution_name,
        command_line_arguments={},
    )


def _live_data(validation_result: Any = None) -> ExecutionData:
    return ExecutionData(
        selected=FakeArtifact("cons-a", quality=2),
        prompt_request=FakePromptRequest(),
        llm_request=FakeLLMRequest("execution-456"),
        result=FakeResult(),
        dry_run=False,
        provider_name="gemini",
        requested_model="gemini-2.5-flash",
        reasoning_contract_version="1.0.0",
        execution_name=None,
        command_line_arguments={},
        validation_result=validation_result,
    )


# ===========================================================================
# PlatformContext
# ===========================================================================

@pytest.mark.unit
def test_platform_context_constructs_components() -> None:
    ctx = PlatformContext()
    assert isinstance(ctx.create_prompt_builder(), RequirementPromptBuilder)
    assert isinstance(ctx.create_consolidation_engine(), ConsolidationEngine)

    config = ctx.create_analysis_configuration("rc-9")
    assert config.reasoning_contract_version == "rc-9"

    provider = ctx.create_provider("gemini")
    assert provider.provider_name == "gemini"

    service = ctx.create_requirement_analysis_service(
        ctx.create_prompt_builder(), provider, config
    )
    assert isinstance(service, RequirementAnalysisService)

    # PlatformContext is the single construction hub for the Response Validator too.
    from requirement_intelligence.validation.response import ResponseValidator

    assert isinstance(ctx.create_response_validator(), ResponseValidator)


# ===========================================================================
# ExecutionHistory
# ===========================================================================

@pytest.mark.unit
def test_history_latest_when_not_saved(tmp_path: Path) -> None:
    history = ExecutionHistory(tmp_path / "executions")
    target = history.resolve_target(save_execution=False, execution_name=None)
    assert target == tmp_path / "latest"


@pytest.mark.unit
def test_history_timestamp_when_saved(tmp_path: Path) -> None:
    history = ExecutionHistory(tmp_path / "executions")
    target = history.resolve_target(save_execution=True, execution_name=None)
    assert target.parent == tmp_path / "executions"
    assert target != tmp_path / "latest"


@pytest.mark.unit
def test_history_named_directory(tmp_path: Path) -> None:
    history = ExecutionHistory(tmp_path / "executions")
    target = history.resolve_target(save_execution=True, execution_name="prompt-v1.1")
    assert target == tmp_path / "executions" / "prompt-v1.1"


@pytest.mark.unit
def test_history_named_collision_appends_suffix(tmp_path: Path) -> None:
    base = tmp_path / "executions"
    (base / "prompt-v1.1").mkdir(parents=True)
    history = ExecutionHistory(base)
    target = history.resolve_target(save_execution=True, execution_name="prompt-v1.1")
    assert target == base / "prompt-v1.1-1"


@pytest.mark.unit
def test_history_finalize_copies_to_latest(tmp_path: Path) -> None:
    base = tmp_path / "executions"
    history = ExecutionHistory(base)
    target = base / "run"
    target.mkdir(parents=True)
    (target / "x.txt").write_text("hi", encoding="utf-8")
    history.finalize(target, save_execution=True)
    assert (history.latest_dir / "x.txt").read_text() == "hi"


# ===========================================================================
# ExecutionWriter / ManifestBuilder
# ===========================================================================

@pytest.mark.unit
def test_writer_dry_run_writes_core_only(tmp_path: Path) -> None:
    result = ExecutionWriter().write(tmp_path, _dry_run_data())
    names = {p.name for p in tmp_path.iterdir()}
    assert names == {
        "consolidated_artifact.json",
        "prompt.txt",
        "llm_request.json",
        "manifest.json",
    }
    assert result.json_valid is None
    assert result.manifest["executionMode"] == "dry-run"


@pytest.mark.unit
def test_writer_live_writes_full_package(tmp_path: Path) -> None:
    result = ExecutionWriter().write(tmp_path, _live_data())
    for name in (
        "analysis_result.json",
        "raw_llm_response.json",
        "execution_summary.md",
        "baseline_metrics.md",
        "review.md",
        "manifest.json",
    ):
        assert (tmp_path / name).exists()
    assert result.json_valid is True
    assert result.manifest["executionMode"] == "live"
    assert result.manifest["analysisId"] == "analysis-123"
    assert result.manifest["manifestSchemaVersion"] == "1.0.0"


@pytest.mark.unit
def test_manifest_builder_includes_execution_name() -> None:
    manifest = ManifestBuilder().build(
        _dry_run_data(execution_name="prompt-v1.1"),
        started_timestamp="t1",
        completed_timestamp="t2",
        generated_artifacts=[],
    )
    assert manifest["executionName"] == "prompt-v1.1"
    assert manifest["subcommand"] == "analyze"
    assert manifest["dryRun"] is True
    assert manifest["platformVersion"] == "1.0.0"


@pytest.mark.unit
def test_manifest_includes_schema_and_component_versions() -> None:
    manifest = ManifestBuilder().build(
        _dry_run_data(),
        started_timestamp="t1",
        completed_timestamp="t2",
        generated_artifacts=[],
    )
    for key in (
        "manifestSchemaVersion",
        "connectorRegistryVersion",
        "mapperVersion",
        "consolidationEngineVersion",
        "promptFrameworkVersion",
        "llmFrameworkVersion",
        "analysisServiceVersion",
        "executionWriterVersion",
        "platformCapabilitiesVersion",
    ):
        assert manifest[key] == "1.0.0"
    # Existing fields are retained.
    assert manifest["platformVersion"] == "1.0.0"
    assert manifest["executionPackageVersion"] == "1.0.0"


# ===========================================================================
# PlatformCapabilities
# ===========================================================================

@pytest.mark.unit
def test_platform_capabilities_versions_and_groups() -> None:
    caps = PlatformCapabilities()
    versions = caps.platform_versions()
    assert versions["manifestSchemaVersion"] == "1.0.0"
    assert {
        "platformVersion",
        "cliVersion",
        "promptVersion",
        "reasoningContractVersion",
        "executionPackageVersion",
        "manifestSchemaVersion",
    } <= set(versions)

    components = caps.architecture_components()
    assert len(components) == len(caps.implemented_components()) + len(
        caps.planned_components()
    )
    assert [title for title, _ in caps.component_groups()] == [
        "Core Platform",
        "AI Platform",
        "Execution Platform",
        "Future Platform",
    ]


@pytest.mark.unit
def test_platform_capabilities_providers_commands_identity() -> None:
    caps = PlatformCapabilities()
    assert any(p.id == "gemini" and p.available for p in caps.providers())
    assert "analyze" in caps.supported_commands()
    assert caps.platform_identity()["architecture"] == "Modular Monolith"
    system = caps.system_identity()
    assert "pythonVersion" in system
    assert "currentWorkingDirectory" in system


# ===========================================================================
# Engineering metrics + execution package identity
# ===========================================================================

@pytest.mark.unit
def test_engineering_metrics_from_pipeline_only() -> None:
    consolidated = [
        FakeArtifact("a", quality=1),
        FakeArtifact("b", quality=9),
        FakeArtifact("c", quality=4),
    ]
    data = ExecutionData(
        selected=consolidated[1],
        prompt_request=FakePromptRequest(),
        llm_request=FakeLLMRequest("r"),
        result=None,
        dry_run=True,
        provider_name="gemini",
        requested_model=None,
        reasoning_contract_version="1.0.0",
        execution_name=None,
        command_line_arguments={},
        source_artifact_count=42,
        consolidated_artifacts=consolidated,
    )
    metrics = engineering_metrics(data)
    assert metrics["source_artifacts_processed"] == 42
    assert metrics["consolidated_artifacts_produced"] == 3
    assert metrics["selected_consolidated_artifact"] == "b"
    assert metrics["selected_artifact_rank"] == 1
    assert metrics["largest_consolidation_group"] == 9
    assert metrics["smallest_consolidation_group"] == 1
    assert metrics["average_artifacts_per_group"] == round((1 + 9 + 4) / 3, 2)
    assert metrics["quality_artifact_count"] == 9


@pytest.mark.unit
def test_engineering_metrics_na_without_pipeline_data() -> None:
    metrics = engineering_metrics(_dry_run_data())  # no consolidated list
    assert metrics["source_artifacts_processed"] == "N/A"
    assert metrics["consolidated_artifacts_produced"] == "N/A"
    assert metrics["selected_artifact_rank"] == "N/A"


@pytest.mark.unit
def test_baseline_metrics_has_engineering_and_ai_sections() -> None:
    md = BaselineMetricsBuilder().build(_live_data())
    assert "## Engineering Metrics" in md
    assert "Source Artifacts Processed" in md
    assert "Selected Artifact Rank" in md
    assert "## AI Metrics" in md  # existing metrics preserved
    assert "Baseline Version" in md


@pytest.mark.unit
def test_execution_package_identifier_format() -> None:
    assert execution_package_identifier(FakeResult()) == "EP-20260101-000000-executio"


@pytest.mark.unit
def test_summary_and_review_include_package_identity() -> None:
    summary = ExecutionSummaryBuilder().build(_live_data())
    review = ReviewBuilder().build(_live_data())
    for text in (summary, review):
        assert "Execution Package Id" in text
        assert "EP-20260101-000000-executio" in text
        assert "Manifest Schema Version" in text


# ===========================================================================
# Argument parsing
# ===========================================================================

@pytest.mark.unit
def test_parser_analyze_defaults() -> None:
    args = cli.build_parser().parse_args(["analyze"])
    assert args.command == "analyze"
    assert args.provider == "gemini"
    assert args.artifact_id is None
    assert args.model is None
    assert args.execution_name is None
    assert args.dry_run is False
    assert args.save_execution is False
    assert args.func is cli.handle_analyze


@pytest.mark.unit
def test_parser_analyze_all_options() -> None:
    args = cli.build_parser().parse_args(
        [
            "analyze",
            "--artifact-id", "cons-x",
            "--provider", "gemini",
            "--model", "gemini-2.5-flash",
            "--output-dir", "/tmp/out",
            "--execution-name", "run-1",
            "--dry-run",
            "--save-execution",
            "--verbose",
        ]
    )
    assert args.execution_name == "run-1"
    assert args.dry_run is True
    assert args.save_execution is True


@pytest.mark.unit
def test_parser_subcommands_wired() -> None:
    parser = cli.build_parser()
    assert parser.parse_args(["list-artifacts"]).func is cli.handle_list_artifacts
    assert parser.parse_args(["validate"]).func is cli.handle_validate
    assert parser.parse_args(["benchmark"]).func is cli.handle_benchmark
    assert parser.parse_args(["version"]).func is cli.handle_version
    assert parser.parse_args(["help"]).func is cli.handle_help


@pytest.mark.unit
def test_no_command_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main([]) == 0
    assert "usage" in capsys.readouterr().out.lower()


# ===========================================================================
# Reserved + help + version subcommands
# ===========================================================================

@pytest.mark.unit
def test_validate_placeholder(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["validate"]) == 0
    assert "future phase" in capsys.readouterr().out


@pytest.mark.unit
def test_benchmark_placeholder(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["benchmark"]) == 0
    assert "future phase" in capsys.readouterr().out


@pytest.mark.unit
def test_help_outputs_examples(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["help"]) == 0
    out = capsys.readouterr().out
    assert "EXAMPLES" in out
    assert "--execution-name" in out


@pytest.mark.unit
def test_version_outputs_all_sections(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["version"]) == 0
    out = capsys.readouterr().out
    for section in (
        "Platform Metadata",
        "Platform Identity",
        "Available Providers",
        "Supported Commands",
        "System Information",
    ):
        assert section in out
    # Platform identity + new manifest schema version line.
    assert "Architecture   : Modular Monolith" in out
    assert "Manifest Schema Version" in out


@pytest.mark.unit
def test_version_groups_components(capsys: pytest.CaptureFixture[str]) -> None:
    cli.main(["version"])
    out = capsys.readouterr().out
    for group in ("Core Platform", "AI Platform", "Execution Platform", "Future Platform"):
        assert group in out
    assert "✓ Connector Registry" in out
    assert "✓ Requirement Analysis CLI" in out
    assert "○ Response Validator (Planned)" in out


@pytest.mark.unit
def test_version_shows_providers(capsys: pytest.CaptureFixture[str]) -> None:
    cli.main(["version"])
    out = capsys.readouterr().out
    assert "✓ Gemini" in out
    assert "○ Azure OpenAI (Reserved)" in out


@pytest.mark.unit
def test_version_shows_commands_and_system_info(
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli.main(["version"])
    out = capsys.readouterr().out
    for command in ("analyze", "list-artifacts", "version", "help"):
        assert command in out
    assert "Python Version" in out
    assert "Operating System" in out
    assert "Platform Architecture" in out


# ===========================================================================
# list-artifacts
# ===========================================================================

@pytest.mark.unit
def test_list_artifacts_displays_all(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _use_context(
        monkeypatch,
        [
            FakeArtifact("cons-a", functional=2, risk="high"),
            FakeArtifact("cons-b", quality=5, business_area="auth"),
        ],
    )
    assert cli.main(["list-artifacts"]) == 0
    out = capsys.readouterr().out
    assert "cons-a" in out and "cons-b" in out
    assert "Functional" in out and "Security" in out and "Quality" in out
    assert "auth" in out


# ===========================================================================
# analyze — validation, dry-run, live, selection
# ===========================================================================

@pytest.mark.unit
def test_invalid_provider_rejected(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["analyze", "--provider", "nope", "--dry-run"]) == 2
    assert "not supported" in capsys.readouterr().err.lower()


@pytest.mark.unit
def test_live_without_api_key_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    assert cli.main(["analyze"]) == 2
    assert "GOOGLE_API_KEY" in capsys.readouterr().err


@pytest.mark.unit
def test_dry_run_writes_only_core(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _use_context(monkeypatch, [FakeArtifact("cons-a", quality=3)])
    assert cli.main(
        ["analyze", "--dry-run", "--output-dir", str(tmp_path / "executions")]
    ) == 0
    latest = tmp_path / "latest"
    assert not (latest / "analysis_result.json").exists()
    manifest = _read_manifest(latest)
    assert manifest["executionMode"] == "dry-run"
    assert manifest["analysisId"] is None


@pytest.mark.unit
def test_live_writes_full_package(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _use_context(monkeypatch, [FakeArtifact("cons-a", quality=3)], result=FakeResult())
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    assert cli.main(["analyze", "--output-dir", str(tmp_path / "executions")]) == 0
    latest = tmp_path / "latest"
    assert (latest / "analysis_result.json").exists()
    manifest = _read_manifest(latest)
    assert manifest["executionMode"] == "live"
    assert manifest["analysisId"] == "analysis-123"
    assert manifest["model"] == "gemini-2.5-flash"


@pytest.mark.unit
def test_default_selection_is_largest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _use_context(
        monkeypatch,
        [
            FakeArtifact("cons-small", quality=1),
            FakeArtifact("cons-big", quality=9),
            FakeArtifact("cons-mid", quality=4),
        ],
    )
    cli.main(["analyze", "--dry-run", "--output-dir", str(tmp_path / "executions")])
    assert _read_manifest(tmp_path / "latest")["selectedArtifactId"] == "cons-big"


@pytest.mark.unit
def test_explicit_artifact_id(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _use_context(
        monkeypatch,
        [FakeArtifact("cons-a", quality=9), FakeArtifact("cons-b", quality=1)],
    )
    cli.main(
        [
            "analyze", "--dry-run", "--artifact-id", "cons-b",
            "--output-dir", str(tmp_path / "executions"),
        ]
    )
    assert _read_manifest(tmp_path / "latest")["selectedArtifactId"] == "cons-b"


@pytest.mark.unit
def test_unknown_artifact_id_errors(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    _use_context(monkeypatch, [FakeArtifact("cons-a", quality=1)])
    rc = cli.main(
        [
            "analyze", "--dry-run", "--artifact-id", "missing",
            "--output-dir", str(tmp_path / "executions"),
        ]
    )
    assert rc == 1
    assert "missing" in capsys.readouterr().err


# ===========================================================================
# Execution history via the CLI / named executions
# ===========================================================================

@pytest.mark.unit
def test_save_execution_creates_history_and_latest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _use_context(monkeypatch, [FakeArtifact("cons-a", quality=2)])
    base = tmp_path / "executions"
    cli.main(["analyze", "--dry-run", "--save-execution", "--output-dir", str(base)])
    history_dirs = [p for p in base.iterdir() if p.is_dir()]
    assert len(history_dirs) == 1
    assert (history_dirs[0] / "manifest.json").exists()
    assert (tmp_path / "latest" / "manifest.json").exists()


@pytest.mark.unit
def test_named_execution_persisted_with_manifest_entry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _use_context(monkeypatch, [FakeArtifact("cons-a", quality=2)])
    base = tmp_path / "executions"
    cli.main(
        ["analyze", "--dry-run", "--execution-name", "prompt-v1.1", "--output-dir", str(base)]
    )
    target = base / "prompt-v1.1"
    assert (target / "manifest.json").exists()
    assert (tmp_path / "latest" / "manifest.json").exists()
    assert _read_manifest(target)["executionName"] == "prompt-v1.1"


@pytest.mark.unit
def test_named_execution_collision_never_overwrites(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    base = tmp_path / "executions"
    (base / "prompt-v1.1").mkdir(parents=True)
    (base / "prompt-v1.1" / "sentinel.txt").write_text("keep", encoding="utf-8")
    _use_context(monkeypatch, [FakeArtifact("cons-a", quality=2)])
    cli.main(
        ["analyze", "--dry-run", "--execution-name", "prompt-v1.1", "--output-dir", str(base)]
    )
    assert (base / "prompt-v1.1" / "sentinel.txt").read_text() == "keep"
    assert (base / "prompt-v1.1-1" / "manifest.json").exists()


# ===========================================================================
# Response Validation phase (CAP-041) — PlatformContext-owned wiring
# ===========================================================================
#
# CAP-041 is pure orchestration: the CLI no longer wires a validator by hand.
# It asks PlatformContext — the single construction hub — for a fully-wired
# ResponseValidator and hands it the canonical ValidationInput (ADR-0003 seam).

# The full set of implemented rules, in Rule-Catalog order
# (Transport -> Syntax -> Schema -> Content -> Reasoning).
_EXPECTED_RULE_IDS = [
    "TRANSPORT-0001",
    "TRANSPORT-0002",
    "TRANSPORT-0003",
    "TRANSPORT-0004",
    "SYNTAX-0001",
    "SYNTAX-0002",
    "SYNTAX-0003",
    "SCHEMA-0001",
    "SCHEMA-0002",
    "SCHEMA-0004",
    "CONTENT-0001",
    "CONTENT-0002",
    "REASONING-0002",
]

_DEFERRED_RULE_IDS = [
    "SCHEMA-0003",
    "CONTENT-0003",
    "CONTENT-0004",
    "REASONING-0001",
    "REASONING-0003",
]

# A fully-conformant governed response — passes every implemented rule.
_GOVERNED_JSON = json.dumps(
    {
        "summary": "s",
        "functional_requirements": ["fr"],
        "security_requirements": ["sr"],
        "quality_requirements": ["qr"],
        "risks": ["r"],
        "recommendations": ["rec"],
    }
)


def _real_analysis_result(text: str = _GOVERNED_JSON) -> AnalysisResult:
    """A genuine AnalysisResult so the real normalizer + validator run end-to-end."""
    response = LLMResponse(provider="gemini", model="model", generated_text=text)
    return AnalysisResult(
        analysis_id="AN-1",
        execution_id="EX-1",
        source_consolidated_id="C-1",
        prompt_version="p1",
        reasoning_contract_version="r1",
        provider="gemini",
        model="model",
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
        completed_at=datetime(2026, 1, 1, tzinfo=UTC),
        duration_ms=1.0,
        llm_response=response,
    )


@pytest.mark.unit
def test_create_response_validator_returns_wired_validator() -> None:
    from requirement_intelligence.validation.response import ResponseValidator

    validator = PlatformContext().create_response_validator()
    assert isinstance(validator, ResponseValidator)


@pytest.mark.unit
def test_create_response_validator_wires_all_13_rules_in_order() -> None:
    # A fully wired validator: every implemented rule, in Rule-Catalog order,
    # identical to the validation subsystem's own composition root.
    from requirement_intelligence.validation.response import build_validation_registry

    validator = PlatformContext().create_response_validator()
    assert validator._registry.rule_count() == 13
    assert validator._registry.list_rule_ids() == _EXPECTED_RULE_IDS
    assert validator._registry.list_rule_ids() == build_validation_registry().list_rule_ids()


@pytest.mark.unit
def test_create_response_validator_excludes_deferred_rules() -> None:
    validator = PlatformContext().create_response_validator()
    ids = set(validator._registry.list_rule_ids())
    assert ids.isdisjoint(_DEFERRED_RULE_IDS)


@pytest.mark.unit
def test_validation_phase_executes_all_13_rules(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # End-to-end through the CLI seam: normalize -> ValidationInput -> validate.
    ctx = PlatformContext()
    profile = ctx.get_validation_profile("default")
    cli.run_validation_phase(ctx, _real_analysis_result(), cli.Console(), profile)
    out = capsys.readouterr().out
    assert "Running Response Validation" in out
    assert "Rules Executed      : 13" in out
    assert "Issues Found        : 0" in out
    assert "Overall Verdict : passed" in out
    assert "Validation Profile  : default" in out


@pytest.mark.unit
def test_validation_phase_obtains_validator_only_from_context() -> None:
    # Proves the CLI performs no wiring of its own: the validator comes solely
    # from PlatformContext, the single construction hub.
    real = PlatformContext()

    class HubContext:
        def __init__(self) -> None:
            self.calls = 0

        def create_response_validator_for_profile(self, profile: Any) -> Any:
            self.calls += 1
            return real.create_response_validator_for_profile(profile)

    ctx = HubContext()
    profile = real.get_validation_profile("default")
    cli.run_validation_phase(ctx, _real_analysis_result(), cli.Console(), profile)
    assert ctx.calls == 1


@pytest.mark.unit
def test_validate_flag_invokes_validation_phase_with_context(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[Any, Any, Any]] = []
    monkeypatch.setattr(
        cli,
        "run_validation_phase",
        lambda ctx, result, console, profile: calls.append((ctx, result, profile)),
    )
    _use_context(monkeypatch, [FakeArtifact("cons-a", quality=3)], result=FakeResult())
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    assert cli.main(["analyze", "--validate", "--output-dir", str(tmp_path / "executions")]) == 0
    assert len(calls) == 1
    ctx, result, profile = calls[0]
    assert isinstance(ctx, FakeContext)  # the single hub is threaded through
    assert isinstance(result, FakeResult)
    assert profile.name == "default"  # default profile resolved when flag omitted


@pytest.mark.unit
def test_default_run_does_not_validate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[Any] = []
    monkeypatch.setattr(cli, "run_validation_phase", lambda *a: calls.append(a))
    _use_context(monkeypatch, [FakeArtifact("cons-a", quality=3)], result=FakeResult())
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    assert cli.main(["analyze", "--output-dir", str(tmp_path / "executions")]) == 0
    assert calls == []  # validation is opt-in


@pytest.mark.unit
def test_dry_run_with_validate_does_not_validate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[Any] = []
    monkeypatch.setattr(cli, "run_validation_phase", lambda *a: calls.append(a))
    _use_context(monkeypatch, [FakeArtifact("cons-a", quality=3)])
    assert (
        cli.main(
            ["analyze", "--dry-run", "--validate", "--output-dir", str(tmp_path / "executions")]
        )
        == 0
    )
    assert calls == []  # no response to validate on a dry run


# ===========================================================================
# ValidationResult persistence (CAP-042) — the execution package owns storage
# ===========================================================================
#
# CAP-042 is purely additive: when validation is executed, the complete
# ValidationResult is serialised into the execution package as
# ``validation_result.json``. The validator stays read-only; the ExecutionWriter
# only serialises the result it is handed; the CLI only orchestrates.

_VALIDATION_ARTIFACT = "validation_result.json"


def _real_validation_result(text: str = _GOVERNED_JSON) -> Any:
    """Produce a genuine ValidationResult via the real hub-wired validator."""
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

    analysis = _real_analysis_result(text)
    registry = NormalizationRegistry()
    normalization = ResponseNormalizer(
        registry, NormalizationPipeline(registry), NormalizationConfiguration()
    ).normalize(analysis.llm_response)
    validation_input = ValidationInput(
        analysis_result=analysis, normalization_result=normalization
    )
    return PlatformContext().create_response_validator().validate(validation_input)


def _validation_input(text: str = _GOVERNED_JSON) -> Any:
    """Build a canonical ValidationInput from a governed response *text*."""
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

    analysis = _real_analysis_result(text)
    registry = NormalizationRegistry()
    normalization = ResponseNormalizer(
        registry, NormalizationPipeline(registry), NormalizationConfiguration()
    ).normalize(analysis.llm_response)
    return ValidationInput(analysis_result=analysis, normalization_result=normalization)


# --- ExecutionWriter: serialises the ValidationResult it receives -----------


@pytest.mark.unit
def test_writer_persists_validation_result_when_present(tmp_path: Path) -> None:
    validation = _real_validation_result()
    result = ExecutionWriter().write(tmp_path, _live_data(validation_result=validation))

    artifact = tmp_path / _VALIDATION_ARTIFACT
    assert artifact.exists()
    assert _VALIDATION_ARTIFACT in result.generated_artifacts
    # The file is the ValidationResult serialised as-is (canonical camelCase JSON).
    on_disk = json.loads(artifact.read_text())
    assert on_disk == validation.model_dump(mode="json", by_alias=True)
    assert on_disk["overallVerdict"] == "passed"
    assert on_disk["validationStatistics"]["rulesExecuted"] == len(_EXPECTED_RULE_IDS)


@pytest.mark.unit
def test_writer_omits_validation_result_when_absent(tmp_path: Path) -> None:
    # A live run without validation: no validation artifact, full package intact.
    result = ExecutionWriter().write(tmp_path, _live_data())
    assert not (tmp_path / _VALIDATION_ARTIFACT).exists()
    assert _VALIDATION_ARTIFACT not in result.generated_artifacts
    # Backward compatible: every classic live artifact is still written.
    for name in (
        "analysis_result.json",
        "raw_llm_response.json",
        "execution_summary.md",
        "baseline_metrics.md",
        "review.md",
        "manifest.json",
    ):
        assert (tmp_path / name).exists()


@pytest.mark.unit
def test_writer_dry_run_never_persists_validation_result(tmp_path: Path) -> None:
    # Dry runs produce no response and therefore never a validation artifact;
    # the core-only artifact set is unchanged.
    ExecutionWriter().write(tmp_path, _dry_run_data())
    assert not (tmp_path / _VALIDATION_ARTIFACT).exists()
    assert {p.name for p in tmp_path.iterdir()} == {
        "consolidated_artifact.json",
        "prompt.txt",
        "llm_request.json",
        "manifest.json",
    }


@pytest.mark.unit
def test_manifest_references_validation_artifact(tmp_path: Path) -> None:
    validation = _real_validation_result()
    result = ExecutionWriter().write(tmp_path, _live_data(validation_result=validation))

    entries = {a["name"]: a for a in result.manifest["generatedArtifacts"]}
    assert _VALIDATION_ARTIFACT in entries
    entry = entries[_VALIDATION_ARTIFACT]
    # The manifest records the artifact's real size and content hash.
    raw = (tmp_path / _VALIDATION_ARTIFACT).read_bytes()
    assert entry["bytes"] == len(raw)
    assert entry["sha256"] == hashlib.sha256(raw).hexdigest()
    # Additive only: the manifest schema version is unchanged.
    assert result.manifest["manifestSchemaVersion"] == "1.0.0"


@pytest.mark.unit
def test_manifest_omits_validation_artifact_when_absent(tmp_path: Path) -> None:
    result = ExecutionWriter().write(tmp_path, _live_data())
    names = [a["name"] for a in result.manifest["generatedArtifacts"]]
    assert _VALIDATION_ARTIFACT not in names


@pytest.mark.unit
def test_validation_result_serialization_is_deterministic(tmp_path: Path) -> None:
    validation = _real_validation_result()
    first = tmp_path / "a"
    second = tmp_path / "b"
    first.mkdir()
    second.mkdir()
    ExecutionWriter().write(first, _live_data(validation_result=validation))
    ExecutionWriter().write(second, _live_data(validation_result=validation))
    assert (first / _VALIDATION_ARTIFACT).read_bytes() == (
        second / _VALIDATION_ARTIFACT
    ).read_bytes()


@pytest.mark.unit
def test_writer_does_not_mutate_validation_result(tmp_path: Path) -> None:
    validation = _real_validation_result()
    before = validation.model_copy(deep=True)
    ExecutionWriter().write(tmp_path, _live_data(validation_result=validation))
    assert validation == before


# --- CLI end-to-end: persistence + history behaviour ------------------------


@pytest.mark.unit
def test_cli_validate_persists_validation_result(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _use_context(
        monkeypatch, [FakeArtifact("cons-a", quality=3)], result=_real_analysis_result()
    )
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    assert cli.main(["analyze", "--validate", "--output-dir", str(tmp_path / "executions")]) == 0

    latest = tmp_path / "latest"
    artifact = latest / _VALIDATION_ARTIFACT
    assert artifact.exists()
    manifest = _read_manifest(latest)
    assert _VALIDATION_ARTIFACT in [a["name"] for a in manifest["generatedArtifacts"]]
    on_disk = json.loads(artifact.read_text())
    assert on_disk["overallVerdict"] == "passed"
    assert on_disk["validationStatistics"]["rulesExecuted"] == len(_EXPECTED_RULE_IDS)


@pytest.mark.unit
def test_cli_live_without_validate_writes_no_validation_artifact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _use_context(
        monkeypatch, [FakeArtifact("cons-a", quality=3)], result=_real_analysis_result()
    )
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    assert cli.main(["analyze", "--output-dir", str(tmp_path / "executions")]) == 0

    latest = tmp_path / "latest"
    assert not (latest / _VALIDATION_ARTIFACT).exists()
    assert (latest / "analysis_result.json").exists()  # package otherwise intact


@pytest.mark.unit
def test_cli_dry_run_with_validate_writes_no_validation_artifact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _use_context(monkeypatch, [FakeArtifact("cons-a", quality=3)])
    assert (
        cli.main(
            ["analyze", "--dry-run", "--validate", "--output-dir", str(tmp_path / "executions")]
        )
        == 0
    )
    assert not (tmp_path / "latest" / _VALIDATION_ARTIFACT).exists()


@pytest.mark.unit
def test_cli_validate_persists_into_saved_history(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Execution history behaviour is unchanged: the artifact is persisted in the
    # timestamped history copy and mirrored to latest/.
    _use_context(
        monkeypatch, [FakeArtifact("cons-a", quality=3)], result=_real_analysis_result()
    )
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    base = tmp_path / "executions"
    assert (
        cli.main(["analyze", "--validate", "--save-execution", "--output-dir", str(base)]) == 0
    )

    history_dirs = [p for p in base.iterdir() if p.is_dir()]
    assert len(history_dirs) == 1
    assert (history_dirs[0] / _VALIDATION_ARTIFACT).exists()
    assert (tmp_path / "latest" / _VALIDATION_ARTIFACT).exists()


# ===========================================================================
# Validation report (CAP-043) — human-readable, presentation only
# ===========================================================================
#
# CAP-043 is purely additive: whenever validation_result.json is written, the
# ExecutionWriter also emits validation_report.md — a Markdown rendering derived
# entirely from the ValidationResult. It executes nothing and derives no new
# findings; it only formats what the result already contains.

_VALIDATION_REPORT = "validation_report.md"

# A response that fails three implemented rules across three layers.
_INVALID_JSON = json.dumps(
    {
        "functional_requirements": ["A", "A"],
        "security_requirements": [],
        "quality_requirements": [],
        "risks": [],
        "recommendations": ["X", "X"],
    }
)


# --- ExecutionWriter emits the report alongside the JSON --------------------


@pytest.mark.unit
def test_writer_emits_validation_report_when_present(tmp_path: Path) -> None:
    validation = _real_validation_result()
    result = ExecutionWriter().write(tmp_path, _live_data(validation_result=validation))

    report = tmp_path / _VALIDATION_REPORT
    assert report.exists()
    assert _VALIDATION_REPORT in result.generated_artifacts
    # It is written together with the canonical JSON, never on its own.
    assert (tmp_path / _VALIDATION_ARTIFACT).exists()


@pytest.mark.unit
def test_writer_omits_report_when_validation_absent(tmp_path: Path) -> None:
    result = ExecutionWriter().write(tmp_path, _live_data())
    assert not (tmp_path / _VALIDATION_REPORT).exists()
    assert _VALIDATION_REPORT not in result.generated_artifacts


@pytest.mark.unit
def test_writer_dry_run_never_emits_report(tmp_path: Path) -> None:
    ExecutionWriter().write(tmp_path, _dry_run_data())
    assert not (tmp_path / _VALIDATION_REPORT).exists()


@pytest.mark.unit
def test_manifest_includes_validation_report(tmp_path: Path) -> None:
    validation = _real_validation_result()
    result = ExecutionWriter().write(tmp_path, _live_data(validation_result=validation))

    entries = {a["name"]: a for a in result.manifest["generatedArtifacts"]}
    assert _VALIDATION_REPORT in entries
    raw = (tmp_path / _VALIDATION_REPORT).read_bytes()
    assert entries[_VALIDATION_REPORT]["bytes"] == len(raw)
    assert entries[_VALIDATION_REPORT]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert result.manifest["manifestSchemaVersion"] == "1.0.0"


# --- Report content is faithful to the ValidationResult --------------------


@pytest.mark.unit
def test_report_reflects_passing_result() -> None:
    validation = _real_validation_result()
    report = ValidationReportBuilder().build(_live_data(validation_result=validation))
    assert report.startswith("# Validation Report")
    assert "**PASSED**" in report
    assert f"| Rules Executed | {len(_EXPECTED_RULE_IDS)} |" in report
    assert "| Issues Found | 0 |" in report
    assert "_No issues found._" in report
    # All five implemented layers appear in the layer summary.
    for layer in ("Transport", "Syntax", "Schema", "Content", "Reasoning"):
        assert f"| {layer} |" in report


@pytest.mark.unit
def test_report_reflects_failing_result_issues() -> None:
    validation = _real_validation_result(_INVALID_JSON)
    report = ValidationReportBuilder().build(_live_data(validation_result=validation))
    assert "**FAILED**" in report
    # Every issue in the result is rendered with its identity and guidance.
    for issue in validation.validation_issues:
        assert issue.rule_id in report
        assert issue.message in report
        assert issue.recommendation in report
        assert issue.location in report
    # Issues-by-layer roll-up counts match the result's own issues.
    assert "| Schema | 1 |" in report
    assert "| Content | 1 |" in report
    assert "| Reasoning | 1 |" in report


@pytest.mark.unit
def test_report_only_contains_result_data() -> None:
    # Statistics printed in the report come verbatim from the ValidationResult.
    validation = _real_validation_result(_INVALID_JSON)
    stats = validation.validation_statistics
    report = ValidationReportBuilder().build(_live_data(validation_result=validation))
    assert f"| Rules Passed | {stats.rules_passed} |" in report
    assert f"| Rules Failed | {stats.rules_failed} |" in report
    assert f"| Validator Version | {stats.validator_version} |" in report
    assert validation.validation_id in report
    assert validation.execution_id in report


@pytest.mark.unit
def test_report_is_deterministic_for_same_result() -> None:
    validation = _real_validation_result(_INVALID_JSON)
    builder = ValidationReportBuilder()
    data = _live_data(validation_result=validation)
    assert builder.build(data) == builder.build(data) == builder.build(data)


@pytest.mark.unit
def test_report_written_deterministically(tmp_path: Path) -> None:
    validation = _real_validation_result(_INVALID_JSON)
    first = tmp_path / "a"
    second = tmp_path / "b"
    first.mkdir()
    second.mkdir()
    ExecutionWriter().write(first, _live_data(validation_result=validation))
    ExecutionWriter().write(second, _live_data(validation_result=validation))
    assert (first / _VALIDATION_REPORT).read_bytes() == (second / _VALIDATION_REPORT).read_bytes()


@pytest.mark.unit
def test_report_does_not_mutate_validation_result(tmp_path: Path) -> None:
    validation = _real_validation_result(_INVALID_JSON)
    before = validation.model_copy(deep=True)
    ExecutionWriter().write(tmp_path, _live_data(validation_result=validation))
    ValidationReportBuilder().build(_live_data(validation_result=validation))
    assert validation == before


# --- CLI end-to-end + history / backward compatibility ----------------------


@pytest.mark.unit
def test_cli_validate_emits_report(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _use_context(
        monkeypatch, [FakeArtifact("cons-a", quality=3)], result=_real_analysis_result()
    )
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    assert cli.main(["analyze", "--validate", "--output-dir", str(tmp_path / "executions")]) == 0

    latest = tmp_path / "latest"
    assert (latest / _VALIDATION_REPORT).exists()
    manifest = _read_manifest(latest)
    assert _VALIDATION_REPORT in [a["name"] for a in manifest["generatedArtifacts"]]
    assert (latest / _VALIDATION_REPORT).read_text().startswith("# Validation Report")


@pytest.mark.unit
def test_cli_live_without_validate_emits_no_report(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Backward compatible: an ordinary live run is byte-for-byte as before.
    _use_context(
        monkeypatch, [FakeArtifact("cons-a", quality=3)], result=_real_analysis_result()
    )
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    assert cli.main(["analyze", "--output-dir", str(tmp_path / "executions")]) == 0
    assert not (tmp_path / "latest" / _VALIDATION_REPORT).exists()


@pytest.mark.unit
def test_cli_validate_report_persists_into_saved_history(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _use_context(
        monkeypatch, [FakeArtifact("cons-a", quality=3)], result=_real_analysis_result()
    )
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    base = tmp_path / "executions"
    assert (
        cli.main(["analyze", "--validate", "--save-execution", "--output-dir", str(base)]) == 0
    )
    history_dirs = [p for p in base.iterdir() if p.is_dir()]
    assert len(history_dirs) == 1
    assert (history_dirs[0] / _VALIDATION_REPORT).exists()
    assert (tmp_path / "latest" / _VALIDATION_REPORT).exists()


# ===========================================================================
# Validation Profiles (CAP-044) — governed, immutable rule-selection identities
# ===========================================================================
#
# Profiles are orchestration only: the ValidationProfileRegistry owns the governed
# definitions, the Validation Factory builds a registry for a profile, and the
# profile narrows *which* rules run — never their order (LAYER_ORDER governs that).
# Rules remain wholly unaware of profiles.

# Expected rule set per governed profile, in Rule-Catalog order.
_PROFILE_RULE_IDS = {
    "default": _EXPECTED_RULE_IDS,
    "strict": _EXPECTED_RULE_IDS,
    "content-review": _EXPECTED_RULE_IDS,
    "transport-only": ["TRANSPORT-0001", "TRANSPORT-0002", "TRANSPORT-0003", "TRANSPORT-0004"],
    "syntax-only": [
        "TRANSPORT-0001", "TRANSPORT-0002", "TRANSPORT-0003", "TRANSPORT-0004",
        "SYNTAX-0001", "SYNTAX-0002", "SYNTAX-0003",
    ],
    "schema-only": [
        "TRANSPORT-0001", "TRANSPORT-0002", "TRANSPORT-0003", "TRANSPORT-0004",
        "SYNTAX-0001", "SYNTAX-0002", "SYNTAX-0003",
        "SCHEMA-0001", "SCHEMA-0002", "SCHEMA-0004",
    ],
}


# --- Registry: owns governed, immutable, non-alias definitions --------------


@pytest.mark.unit
def test_profile_registry_lists_all_governed_profiles() -> None:
    from requirement_intelligence.validation.profiles import ValidationProfileRegistry

    assert ValidationProfileRegistry().names() == [
        "default",
        "strict",
        "transport-only",
        "syntax-only",
        "schema-only",
        "content-review",
    ]


@pytest.mark.unit
def test_profile_registry_get_default_and_unknown() -> None:
    from requirement_intelligence.validation.profiles import (
        UnknownValidationProfileError,
        ValidationProfileRegistry,
    )

    registry = ValidationProfileRegistry()
    assert registry.get().name == "default"  # None resolves to default
    assert registry.get("strict").name == "strict"
    with pytest.raises(UnknownValidationProfileError):
        registry.get("nope")


@pytest.mark.unit
def test_profiles_are_distinct_identities_not_aliases() -> None:
    # default, strict, and content-review share a rule set today but remain
    # separate governed identities.
    from requirement_intelligence.validation.profiles import ValidationProfileRegistry

    registry = ValidationProfileRegistry()
    default = registry.get("default")
    strict = registry.get("strict")
    content_review = registry.get("content-review")
    assert default.name != strict.name != content_review.name
    assert default.enabled_layers == strict.enabled_layers == content_review.enabled_layers
    assert default is not strict


# --- Factory / registry contents + ordering per profile ---------------------


@pytest.mark.unit
@pytest.mark.parametrize("profile_name", list(_PROFILE_RULE_IDS))
def test_profile_builds_expected_rule_set_in_order(profile_name: str) -> None:
    ctx = PlatformContext()
    profile = ctx.get_validation_profile(profile_name)
    validator = ctx.create_response_validator_for_profile(profile)
    assert validator._registry.list_rule_ids() == _PROFILE_RULE_IDS[profile_name]


@pytest.mark.unit
def test_profile_subsets_never_reorder_rules() -> None:
    # Every profile's rules are a LAYER_ORDER-consistent prefix-by-layer subset of
    # the full set — ordering is governed by LAYER_ORDER, not the profile.
    ctx = PlatformContext()
    for profile_name, expected in _PROFILE_RULE_IDS.items():
        ids = ctx.create_response_validator_for_profile(
            ctx.get_validation_profile(profile_name)
        )._registry.list_rule_ids()
        assert ids == [rid for rid in _EXPECTED_RULE_IDS if rid in set(expected)]


# --- Validator execution honours the profile's rule set ---------------------


@pytest.mark.unit
def test_transport_only_profile_executes_four_rules() -> None:
    ctx = PlatformContext()
    profile = ctx.get_validation_profile("transport-only")
    result = ctx.create_response_validator_for_profile(profile).validate(
        _validation_input(_GOVERNED_JSON)
    )
    assert result.validation_statistics.rules_executed == 4


@pytest.mark.unit
def test_schema_only_skips_content_and_reasoning_issues() -> None:
    # The invalid response fails SCHEMA-0001, CONTENT-0002, REASONING-0002 under the
    # full set; under schema-only only the Schema issue can be produced.
    ctx = PlatformContext()
    profile = ctx.get_validation_profile("schema-only")
    result = ctx.create_response_validator_for_profile(profile).validate(
        _validation_input(_INVALID_JSON)
    )
    rule_ids = {issue.rule_id for issue in result.validation_issues}
    assert rule_ids == {"SCHEMA-0001"}
    assert result.validation_statistics.rules_executed == 10


@pytest.mark.unit
def test_profile_identity_rides_into_validation_result() -> None:
    # The selected profile is preserved on the ValidationResult (configuration
    # metadata) — so validation_result.json contains it without touching a model.
    ctx = PlatformContext()
    profile = ctx.get_validation_profile("transport-only")
    result = ctx.create_response_validator_for_profile(profile).validate(
        _validation_input(_GOVERNED_JSON)
    )
    dumped = result.model_dump(mode="json", by_alias=True)
    assert dumped["validationConfiguration"]["metadata"]["validationProfile"] == "transport-only"
    assert dumped["validationConfiguration"]["enabledLayers"] == ["transport"]


# --- PlatformContext is the single hub for profile selection ----------------


@pytest.mark.unit
def test_platform_context_owns_profile_selection() -> None:
    from requirement_intelligence.validation.profiles import ValidationProfileDefinition
    from requirement_intelligence.validation.response import ResponseValidator

    ctx = PlatformContext()
    profile = ctx.get_validation_profile("syntax-only")
    assert isinstance(profile, ValidationProfileDefinition)
    assert isinstance(ctx.create_response_validator_for_profile(profile), ResponseValidator)


# --- CLI accepts --validation-profile ---------------------------------------


@pytest.mark.unit
def test_cli_parser_validation_profile_default_and_override() -> None:
    assert cli.build_parser().parse_args(["analyze"]).validation_profile == "default"
    args = cli.build_parser().parse_args(["analyze", "--validation-profile", "schema-only"])
    assert args.validation_profile == "schema-only"


@pytest.mark.unit
def test_cli_unknown_profile_rejected(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    _use_context(
        monkeypatch, [FakeArtifact("cons-a", quality=3)], result=_real_analysis_result()
    )
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    rc = cli.main(
        ["analyze", "--validate", "--validation-profile", "nope", "--output-dir", str(tmp_path)]
    )
    assert rc == 2
    assert "Unknown validation profile" in capsys.readouterr().err


@pytest.mark.unit
def test_cli_profile_selects_rule_subset_end_to_end(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _use_context(
        monkeypatch, [FakeArtifact("cons-a", quality=3)], result=_real_analysis_result()
    )
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    assert (
        cli.main(
            [
                "analyze", "--validate", "--validation-profile", "transport-only",
                "--output-dir", str(tmp_path / "executions"),
            ]
        )
        == 0
    )
    latest = tmp_path / "latest"
    on_disk = json.loads((latest / _VALIDATION_ARTIFACT).read_text())
    assert on_disk["validationStatistics"]["rulesExecuted"] == 4
    assert on_disk["validationConfiguration"]["metadata"]["validationProfile"] == "transport-only"
    # The report displays the profile.
    report = (latest / _VALIDATION_REPORT).read_text()
    assert "| Validation Profile | transport-only |" in report
    # The manifest records the requested profile (via command-line arguments).
    manifest = _read_manifest(latest)
    assert manifest["commandLineArguments"]["validation_profile"] == "transport-only"


@pytest.mark.unit
def test_cli_default_profile_runs_all_rules(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Backward compatible: omitting --validation-profile runs the full set.
    _use_context(
        monkeypatch, [FakeArtifact("cons-a", quality=3)], result=_real_analysis_result()
    )
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    assert cli.main(["analyze", "--validate", "--output-dir", str(tmp_path / "executions")]) == 0
    on_disk = json.loads((tmp_path / "latest" / _VALIDATION_ARTIFACT).read_text())
    assert on_disk["validationStatistics"]["rulesExecuted"] == len(_EXPECTED_RULE_IDS)
    assert on_disk["validationConfiguration"]["metadata"]["validationProfile"] == "default"


# --- Determinism ------------------------------------------------------------


@pytest.mark.unit
def test_profile_registry_selection_is_deterministic() -> None:
    ctx = PlatformContext()
    for profile_name in _PROFILE_RULE_IDS:
        first = ctx.create_response_validator_for_profile(
            ctx.get_validation_profile(profile_name)
        )._registry.list_rule_ids()
        second = ctx.create_response_validator_for_profile(
            ctx.get_validation_profile(profile_name)
        )._registry.list_rule_ids()
        assert first == second
