"""Unit tests for the internal stage coordinator (execution engine).

These tests exercise the *architecture* of the coordinator, not normalization
outputs: stage ordering, dependency injection, single invocation, exception
propagation, the Assembly State lifecycle (create → execute → dispose), and
``LLMResponse`` immutability.
"""

from __future__ import annotations

import pytest

from requirement_intelligence.llm.llm_models import LLMResponse
from requirement_intelligence.normalization.response.assembly import (
    AssemblyState,
    NormalizationStage,
    NormalizationStageCoordinator,
    NormalizationStageMetadata,
    RecoverCanonicalStructure,
    StageCoordinationError,
)


def _response(text: str = "text", *, provider: str = "gemini") -> LLMResponse:
    return LLMResponse(provider=provider, model="model", generated_text=text)


class _SpyStage(NormalizationStage):
    """A stage that records its invocation, may raise, and marks the shared state."""

    def __init__(
        self,
        stage_id: str,
        order_log: list[str],
        *,
        order: int = 0,
        raises: Exception | None = None,
    ) -> None:
        self._metadata = NormalizationStageMetadata(
            stage_id=stage_id, stage_name=stage_id, order=order
        )
        self._order_log = order_log
        self._raises = raises
        self.calls = 0
        self.seen_states: list[AssemblyState] = []

    @property
    def metadata(self) -> NormalizationStageMetadata:
        return self._metadata

    def execute(self, llm_response: LLMResponse, assembly_state: AssemblyState) -> None:
        self.calls += 1
        self.seen_states.append(assembly_state)
        self._order_log.append(self.stage_id)
        # Prove stages share one Assembly State (internal_metadata is not guarded).
        assembly_state.set_internal_metadata(self.stage_id, True)
        if self._raises is not None:
            raise self._raises


class _FixedRecoverer:
    def __init__(self, structure: dict | None) -> None:
        self._structure = structure

    def recover(self, text: str) -> dict | None:
        return self._structure


# ---------------------------------------------------------------------------
# Construction / dependency injection
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_rejects_non_stage_element(self) -> None:
        with pytest.raises(StageCoordinationError, match="NormalizationStage"):
            NormalizationStageCoordinator([object()])  # type: ignore[list-item]

    def test_stages_property_preserves_supplied_order(self) -> None:
        log: list[str] = []
        a, b, c = (
            _SpyStage("A", log),
            _SpyStage("B", log),
            _SpyStage("C", log),
        )
        coord = NormalizationStageCoordinator([a, b, c])
        assert coord.stages == (a, b, c)

    def test_runs_whatever_list_is_injected(self) -> None:
        log: list[str] = []
        coord1 = NormalizationStageCoordinator([_SpyStage("X", log)])
        coord2 = NormalizationStageCoordinator([_SpyStage("Y", log)])
        coord1.coordinate(_response(), lambda s: s)
        coord2.coordinate(_response(), lambda s: s)
        assert log == ["X", "Y"]


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


class TestExecution:
    def test_zero_stages_produces_empty_state(self) -> None:
        coord = NormalizationStageCoordinator([])
        state = coord.coordinate(_response(), lambda s: s)
        assert isinstance(state, AssemblyState)
        assert state.normalized_structure_recorded is False
        assert state.internal_metadata == {}

    def test_single_stage_executes_once(self) -> None:
        log: list[str] = []
        stage = _SpyStage("A", log)
        NormalizationStageCoordinator([stage]).coordinate(_response(), lambda s: s)
        assert stage.calls == 1
        assert log == ["A"]

    def test_multiple_stages_all_execute_in_supplied_order(self) -> None:
        log: list[str] = []
        stages = [_SpyStage(sid, log) for sid in ("A", "B", "C", "D", "E")]
        NormalizationStageCoordinator(stages).coordinate(_response(), lambda s: s)
        assert log == ["A", "B", "C", "D", "E"]
        assert all(s.calls == 1 for s in stages)  # exactly once each; none skipped

    def test_does_not_reorder_by_metadata_order(self) -> None:
        # Supplied order must win even when metadata.order disagrees.
        log: list[str] = []
        stages = [
            _SpyStage("first", log, order=9),
            _SpyStage("second", log, order=1),
            _SpyStage("third", log, order=5),
        ]
        NormalizationStageCoordinator(stages).coordinate(_response(), lambda s: s)
        assert log == ["first", "second", "third"]

    def test_stages_share_one_assembly_state(self) -> None:
        log: list[str] = []
        a, b = _SpyStage("A", log), _SpyStage("B", log)
        state = NormalizationStageCoordinator([a, b]).coordinate(
            _response(), lambda s: s
        )
        assert a.seen_states[0] is b.seen_states[0]
        assert state.internal_metadata == {"A": True, "B": True}

    def test_consumer_receives_completed_state_and_result_is_returned(self) -> None:
        stage = RecoverCanonicalStructure(_FixedRecoverer({"a": 1}))
        result = NormalizationStageCoordinator([stage]).coordinate(
            _response(), lambda s: s.normalized_structure
        )
        assert result == {"a": 1}

    def test_does_not_mutate_llm_response(self) -> None:
        log: list[str] = []
        response = _response("original")
        NormalizationStageCoordinator([_SpyStage("A", log)]).coordinate(
            response, lambda s: s
        )
        assert response.generated_text == "original"


# ---------------------------------------------------------------------------
# Assembly State lifecycle
# ---------------------------------------------------------------------------


class TestAssemblyStateLifecycle:
    def test_fresh_state_per_call(self) -> None:
        log: list[str] = []
        coord = NormalizationStageCoordinator([_SpyStage("A", log)])
        first = coord.coordinate(_response(), lambda s: s)
        second = coord.coordinate(_response(), lambda s: s)
        assert first is not second  # a new Assembly State each execution

    def test_coordinator_retains_no_assembly_state(self) -> None:
        # Disposal: the coordinator holds only its injected stages, never a state.
        log: list[str] = []
        coord = NormalizationStageCoordinator([_SpyStage("A", log)])
        coord.coordinate(_response(), lambda s: s)
        held = [v for v in vars(coord).values() if isinstance(v, AssemblyState)]
        assert held == []

    def test_raw_state_only_reaches_the_consumer(self) -> None:
        # The coordinator returns the consumer's result, not the raw state, unless
        # the consumer itself chooses to surface it.
        log: list[str] = []
        sentinel = object()
        out = NormalizationStageCoordinator([_SpyStage("A", log)]).coordinate(
            _response(), lambda s: sentinel
        )
        assert out is sentinel


# ---------------------------------------------------------------------------
# Exception handling
# ---------------------------------------------------------------------------


class TestExceptionHandling:
    def test_infrastructure_failure_stops_pipeline_immediately(self) -> None:
        log: list[str] = []
        boom = RuntimeError("infrastructure failure")
        first = _SpyStage("first", log, raises=boom)
        second = _SpyStage("second", log)
        with pytest.raises(RuntimeError, match="infrastructure failure"):
            NormalizationStageCoordinator([first, second]).coordinate(
                _response(), lambda s: s
            )
        assert first.calls == 1
        assert second.calls == 0  # never reached
        assert log == ["first"]

    def test_exception_propagates_unchanged(self) -> None:
        log: list[str] = []
        boom = ValueError("exact instance")
        with pytest.raises(ValueError) as excinfo:
            NormalizationStageCoordinator([_SpyStage("A", log, raises=boom)]).coordinate(
                _response(), lambda s: s
            )
        assert excinfo.value is boom  # not wrapped, not swallowed

    def test_consumer_not_called_on_failure(self) -> None:
        log: list[str] = []
        consumer_calls = 0

        def consumer(state: AssemblyState) -> AssemblyState:
            nonlocal consumer_calls
            consumer_calls += 1
            return state

        with pytest.raises(RuntimeError):
            NormalizationStageCoordinator(
                [_SpyStage("A", log, raises=RuntimeError("x"))]
            ).coordinate(_response(), consumer)
        assert consumer_calls == 0
