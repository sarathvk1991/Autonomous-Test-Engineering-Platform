"""Unit tests for the Requirement Analysis CLI and its supporting packages.

External dependencies (connectors, consolidation, prompt builder, provider,
analysis service) are mocked via a fake PlatformContext. No live Gemini call is
made and no real input files are read.
"""

from __future__ import annotations

import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock

import pytest

from requirement_intelligence.analysis.requirement_analysis_service import (
    RequirementAnalysisService,
)
from requirement_intelligence.consolidation.consolidation_engine import (
    ConsolidationEngine,
)
from requirement_intelligence.execution import (
    ExecutionData,
    ExecutionHistory,
    ExecutionWriter,
    ManifestBuilder,
)
from requirement_intelligence.platform import PlatformContext
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


def _live_data() -> ExecutionData:
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
        "Architecture Components",
        "Available Providers",
        "Supported CLI Commands",
        "System Information",
    ):
        assert section in out


@pytest.mark.unit
def test_version_shows_architecture_components(capsys: pytest.CaptureFixture[str]) -> None:
    cli.main(["version"])
    out = capsys.readouterr().out
    assert "✓ Connector Registry" in out
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
    for command in ("✓ analyze", "✓ list-artifacts", "✓ version", "✓ help"):
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
