"""Unit tests for the CLI's ``run_recommendation_phase`` (CAP-082C, ADR-0019 §D10).

Mirrors the Quality Governance phase tests in ``test_run_requirement_analysis.py``:
the phase obtains ``RecommendationService`` exclusively from ``PlatformContext``,
invokes ``recommend`` exactly once on exactly the five consumed peer results (in
order), surfaces the headline, and never computes recommendation, priority, or
grouping logic itself.
"""

from __future__ import annotations

import importlib.util
from types import ModuleType
from typing import Any

import pytest

from requirement_intelligence.enhancement.models.enums import ObservationCategory
from requirement_intelligence.platform.platform_context import PlatformContext
from tests.unit.recommendation_helpers import (
    make_cp1_result,
    make_enhancement_finding,
    make_enhancement_result,
    make_grounding_result,
    make_quality_governance_result,
    make_validation_result,
)

_REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "run_requirement_analysis.py"


def _load_cli() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_requirement_analysis", _SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cli = _load_cli()


class _RecordingRecommendationService:
    """A stand-in RecommendationService recording every call it receives."""

    def __init__(self, result: Any) -> None:
        self.calls: list[tuple[Any, Any, Any, Any, Any]] = []
        self._result = result

    def recommend(
        self,
        enhancement_result: Any,
        grounding_result: Any,
        validation_result: Any,
        cp1_result: Any,
        quality_governance_result: Any,
    ) -> Any:
        self.calls.append(
            (
                enhancement_result,
                grounding_result,
                validation_result,
                cp1_result,
                quality_governance_result,
            )
        )
        return self._result


class _FakeRecommendationResult:
    """A stand-in RecommendationResult exposing only what the phase reads."""

    class _Summary:
        headline = "1 recommendation(s) across 1 group(s)."
        total_recommendations = 1
        total_groups = 1

    def __init__(self) -> None:
        self.summary = self._Summary()


class _RecCtx:
    """A minimal context exposing only create_recommendation_service."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def create_recommendation_service(self) -> Any:
        return self._service


@pytest.mark.unit
def test_recommendation_phase_recommends_exactly_once_on_the_five_peer_results() -> None:
    sentinel = _FakeRecommendationResult()
    service = _RecordingRecommendationService(sentinel)
    ctx = _RecCtx(service)
    enhancement, grounding, validation, cp1, governance = (
        object(),
        object(),
        object(),
        object(),
        object(),
    )

    result = cli.run_recommendation_phase(
        ctx, enhancement, grounding, validation, cp1, governance, cli.Console()
    )

    assert result is sentinel
    # Exactly one recommendation call, on exactly the five consumed peer results, in order.
    assert service.calls == [(enhancement, grounding, validation, cp1, governance)]


@pytest.mark.unit
def test_recommendation_phase_obtains_service_only_from_context() -> None:
    real = PlatformContext()

    class HubContext:
        def __init__(self) -> None:
            self.calls = 0

        def create_recommendation_service(self) -> Any:
            self.calls += 1
            return real.create_recommendation_service()

    ctx = HubContext()
    finding = make_enhancement_finding("ef-1", category=ObservationCategory.DEPENDENCY)
    cli.run_recommendation_phase(
        ctx,
        make_enhancement_result(findings=(finding,)),
        make_grounding_result(),
        make_validation_result(),
        make_cp1_result(),
        make_quality_governance_result(),
        cli.Console(),
    )
    assert ctx.calls == 1


@pytest.mark.unit
def test_recommendation_phase_reports_the_headline(
    capsys: pytest.CaptureFixture[str],
) -> None:
    ctx = _RecCtx(_RecordingRecommendationService(_FakeRecommendationResult()))
    cli.run_recommendation_phase(
        ctx, object(), object(), object(), object(), object(), cli.Console()
    )
    out = capsys.readouterr().out
    assert "Running Recommendation" in out
    assert "1 recommendation(s) across 1 group(s)." in out
    assert "Recommendations     : 1" in out
    assert "Groups              : 1" in out


@pytest.mark.unit
def test_recommendation_phase_is_pure_orchestration_glue() -> None:
    """The CLI phase invents no recommendation, priority, or grouping logic of its own.

    It is a thin passthrough: the returned object is exactly what the service
    returned — the phase does not construct, mutate, or wrap it.
    """
    sentinel = _FakeRecommendationResult()
    service = _RecordingRecommendationService(sentinel)
    ctx = _RecCtx(service)
    result = cli.run_recommendation_phase(
        ctx, object(), object(), object(), object(), object(), cli.Console()
    )
    assert result is sentinel
