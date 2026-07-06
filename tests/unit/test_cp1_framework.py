"""Unit tests for the CP1 engine framework (CAP-063).

Covers the reusable, behaviour-free infrastructure — mirroring the frozen Response
Validation Framework, adapted to CP1's flat namespace:

* version constants
* criterion metadata (immutable identity, defaults, reserved fields)
* criterion contract (abstract; convenience wrappers read metadata)
* registry registration, duplicate protection, ordering, introspection
* registry sealing (explicit + via pipeline construction)
* empty registry / independent registries
* pipeline construction guard + registry sealing on construction
* deterministic, order-independent execution
* pipeline collects findings and derives NO verdict / NO CP1Result
* empty run is a valid execution
* criterion exception → FAILED state + propagation
* framework metadata provenance

Design constraints
------------------
* No criterion, readiness judgement, scoring, threshold, or policy is exercised —
  the framework is behaviour-free.  Test doubles stand in for future criteria.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from requirement_intelligence.cp1.framework import (
    CP1_FRAMEWORK_VERSION,
    CP1_PIPELINE_VERSION,
    CP1_REGISTRY_VERSION,
    DEFAULT_CP1_CRITERIA_CONTRACT_VERSION,
    DEFAULT_CRITERION_VERSION,
    CP1Criterion,
    CP1CriterionMetadata,
    CP1CriterionPipeline,
    CP1CriterionRegistry,
    CP1FrameworkMetadata,
    CP1PipelineError,
    CP1PipelineState,
    CP1RegistryError,
    CP1RegistryState,
    build_cp1_criterion_pipeline,
    build_cp1_criterion_registry,
)
from requirement_intelligence.cp1.models import CP1Finding
from shared.enums.base import ValidationVerdict

_TS = datetime(2026, 7, 6, 12, 0, 0, tzinfo=UTC)
_SENTINEL_INPUT = object()  # the framework is input-shape-agnostic (typed Any)


# ---------------------------------------------------------------------------
# Test doubles — stand in for future criteria (the framework is behaviour-free)
# ---------------------------------------------------------------------------


def _finding(criterion_id: str, finding_id: str) -> CP1Finding:
    return CP1Finding(
        finding_id=finding_id,
        criterion_id=criterion_id,
        criterion_version="1.0",
        verdict_contribution=ValidationVerdict.WARN,
        message="m",
        location="l",
        recommendation="r",
        correlation_id="EX-1",
        created_at=_TS,
    )


class _Criterion(CP1Criterion):
    """A minimal, deterministic test-double criterion (no readiness logic)."""

    def __init__(
        self,
        criterion_id: str,
        *,
        findings: tuple[CP1Finding, ...] = (),
        enabled: bool = True,
        raises: Exception | None = None,
    ) -> None:
        self._meta = CP1CriterionMetadata(
            criterion_id=criterion_id, criterion_name=f"{criterion_id} name", enabled=enabled
        )
        self._findings = findings
        self._raises = raises
        self.calls = 0
        self.seen_input: object = None

    @property
    def metadata(self) -> CP1CriterionMetadata:
        return self._meta

    def evaluate(self, cp1_input: object) -> list[CP1Finding]:
        self.calls += 1
        self.seen_input = cp1_input
        if self._raises is not None:
            raise self._raises
        return list(self._findings)


# ---------------------------------------------------------------------------
# 1. Version constants
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestVersionConstants:
    def test_framework_version_constants(self) -> None:
        assert CP1_FRAMEWORK_VERSION == "1.0.0"
        assert CP1_PIPELINE_VERSION == "1.0.0"
        assert CP1_REGISTRY_VERSION == "1.0.0"

    def test_contract_version_constants(self) -> None:
        assert DEFAULT_CP1_CRITERIA_CONTRACT_VERSION == "1.0"
        assert DEFAULT_CRITERION_VERSION == "1.0.0"


# ---------------------------------------------------------------------------
# 2. Criterion metadata
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCriterionMetadata:
    def test_defaults(self) -> None:
        meta = CP1CriterionMetadata(criterion_id="CP1-0001", criterion_name="n")
        assert meta.criterion_version == DEFAULT_CRITERION_VERSION
        assert meta.enabled is True
        assert meta.tags == ()
        assert meta.documentation_reference is None

    def test_is_frozen(self) -> None:
        meta = CP1CriterionMetadata(criterion_id="CP1-0001", criterion_name="n")
        with pytest.raises(FrozenInstanceError):
            meta.criterion_id = "CP1-0002"  # type: ignore[misc]

    def test_value_equality(self) -> None:
        a = CP1CriterionMetadata(criterion_id="CP1-0001", criterion_name="n")
        b = CP1CriterionMetadata(criterion_id="CP1-0001", criterion_name="n")
        assert a == b

    def test_has_no_layer_attribute(self) -> None:
        # CP1 is flat (ADR-0012 §4): metadata must not carry a validation layer.
        meta = CP1CriterionMetadata(criterion_id="CP1-0001", criterion_name="n")
        assert not hasattr(meta, "validation_layer")


# ---------------------------------------------------------------------------
# 3. Criterion contract
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCriterionContract:
    def test_cannot_instantiate_abstract_criterion(self) -> None:
        with pytest.raises(TypeError):
            CP1Criterion()  # type: ignore[abstract]

    def test_convenience_wrappers_read_metadata(self) -> None:
        criterion = _Criterion("CP1-0001", enabled=False)
        assert criterion.criterion_id == "CP1-0001"
        assert criterion.criterion_name == "CP1-0001 name"
        assert criterion.criterion_version == DEFAULT_CRITERION_VERSION
        assert criterion.enabled is False


# ---------------------------------------------------------------------------
# 4. Registry registration & introspection
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRegistryRegistration:
    def test_register_and_count(self) -> None:
        registry = CP1CriterionRegistry()
        registry.register(_Criterion("CP1-0001"))
        registry.register(_Criterion("CP1-0002"))
        assert registry.criterion_count() == 2
        assert registry.list_criterion_ids() == ["CP1-0001", "CP1-0002"]

    def test_get_all_criteria_preserves_registration_order(self) -> None:
        registry = CP1CriterionRegistry()
        ids = ["CP1-0003", "CP1-0001", "CP1-0002"]
        for cid in ids:
            registry.register(_Criterion(cid))
        assert [c.criterion_id for c in registry.get_all_criteria()] == ids

    def test_get_enabled_filters_disabled(self) -> None:
        registry = CP1CriterionRegistry()
        registry.register(_Criterion("CP1-0001", enabled=True))
        registry.register(_Criterion("CP1-0002", enabled=False))
        registry.register(_Criterion("CP1-0003", enabled=True))
        assert [c.criterion_id for c in registry.get_enabled_criteria()] == [
            "CP1-0001",
            "CP1-0003",
        ]

    def test_get_all_returns_a_copy(self) -> None:
        registry = CP1CriterionRegistry()
        registry.register(_Criterion("CP1-0001"))
        got = registry.get_all_criteria()
        got.clear()
        assert registry.criterion_count() == 1


@pytest.mark.unit
class TestDuplicateProtection:
    def test_duplicate_criterion_id_rejected(self) -> None:
        registry = CP1CriterionRegistry()
        registry.register(_Criterion("CP1-0001"))
        with pytest.raises(CP1RegistryError):
            registry.register(_Criterion("CP1-0001"))


# ---------------------------------------------------------------------------
# 5. Registry sealing
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRegistrySealing:
    def test_new_registry_is_open(self) -> None:
        registry = CP1CriterionRegistry()
        assert registry.state is CP1RegistryState.OPEN
        assert registry.is_sealed is False

    def test_seal_blocks_registration(self) -> None:
        registry = CP1CriterionRegistry()
        registry.seal()
        assert registry.is_sealed is True
        with pytest.raises(CP1RegistryError):
            registry.register(_Criterion("CP1-0001"))

    def test_seal_is_idempotent(self) -> None:
        registry = CP1CriterionRegistry()
        registry.seal()
        registry.seal()  # no raise
        assert registry.is_sealed is True

    def test_retrieval_works_after_sealing(self) -> None:
        registry = CP1CriterionRegistry()
        registry.register(_Criterion("CP1-0001"))
        registry.seal()
        assert registry.list_criterion_ids() == ["CP1-0001"]

    def test_pipeline_construction_seals_registry(self) -> None:
        registry = CP1CriterionRegistry()
        assert registry.is_sealed is False
        CP1CriterionPipeline(registry)
        assert registry.is_sealed is True


# ---------------------------------------------------------------------------
# 6. Empty & independent registries
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRegistryIsolation:
    def test_empty_registry(self) -> None:
        registry = CP1CriterionRegistry()
        assert registry.criterion_count() == 0
        assert registry.get_all_criteria() == []
        assert registry.get_enabled_criteria() == []
        assert registry.list_criterion_ids() == []

    def test_registries_are_independent(self) -> None:
        a = CP1CriterionRegistry()
        b = CP1CriterionRegistry()
        a.register(_Criterion("CP1-0001"))
        assert a.criterion_count() == 1
        assert b.criterion_count() == 0
        a.seal()
        assert b.is_sealed is False


# ---------------------------------------------------------------------------
# 7. Pipeline construction
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPipelineConstruction:
    def test_requires_registry_instance(self) -> None:
        with pytest.raises(CP1PipelineError):
            CP1CriterionPipeline("not-a-registry")  # type: ignore[arg-type]

    def test_ready_after_construction(self) -> None:
        pipeline = CP1CriterionPipeline(CP1CriterionRegistry())
        assert pipeline.state is CP1PipelineState.READY

    def test_get_ordered_criteria_returns_enabled_in_order(self) -> None:
        registry = CP1CriterionRegistry()
        registry.register(_Criterion("CP1-0001"))
        registry.register(_Criterion("CP1-0002", enabled=False))
        registry.register(_Criterion("CP1-0003"))
        pipeline = CP1CriterionPipeline(registry)
        assert [c.criterion_id for c in pipeline.get_ordered_criteria()] == [
            "CP1-0001",
            "CP1-0003",
        ]


# ---------------------------------------------------------------------------
# 8. Pipeline execution
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPipelineExecution:
    def test_empty_run_returns_empty_tuple(self) -> None:
        pipeline = CP1CriterionPipeline(CP1CriterionRegistry())
        result = pipeline.run(_SENTINEL_INPUT)
        assert result == ()
        assert pipeline.state is CP1PipelineState.COMPLETED

    def test_collects_findings_in_criterion_order(self) -> None:
        registry = CP1CriterionRegistry()
        registry.register(_Criterion("CP1-0001", findings=(_finding("CP1-0001", "F1"),)))
        registry.register(_Criterion("CP1-0002", findings=(_finding("CP1-0002", "F2"),)))
        pipeline = CP1CriterionPipeline(registry)
        result = pipeline.run(_SENTINEL_INPUT)
        assert [f.finding_id for f in result] == ["F1", "F2"]
        assert isinstance(result, tuple)

    def test_returns_no_verdict_only_findings(self) -> None:
        # The framework collects findings; it produces no verdict / CP1Result.
        registry = CP1CriterionRegistry()
        registry.register(_Criterion("CP1-0001", findings=(_finding("CP1-0001", "F1"),)))
        result = CP1CriterionPipeline(registry).run(_SENTINEL_INPUT)
        assert all(isinstance(f, CP1Finding) for f in result)

    def test_each_criterion_receives_same_input(self) -> None:
        c1 = _Criterion("CP1-0001")
        c2 = _Criterion("CP1-0002")
        registry = CP1CriterionRegistry()
        registry.register(c1)
        registry.register(c2)
        CP1CriterionPipeline(registry).run(_SENTINEL_INPUT)
        assert c1.seen_input is _SENTINEL_INPUT
        assert c2.seen_input is _SENTINEL_INPUT

    def test_disabled_criterion_not_executed(self) -> None:
        enabled = _Criterion("CP1-0001", findings=(_finding("CP1-0001", "F1"),))
        disabled = _Criterion("CP1-0002", findings=(_finding("CP1-0002", "F2"),), enabled=False)
        registry = CP1CriterionRegistry()
        registry.register(enabled)
        registry.register(disabled)
        result = CP1CriterionPipeline(registry).run(_SENTINEL_INPUT)
        assert [f.finding_id for f in result] == ["F1"]
        assert enabled.calls == 1
        assert disabled.calls == 0

    def test_state_transitions_to_completed(self) -> None:
        pipeline = CP1CriterionPipeline(CP1CriterionRegistry())
        assert pipeline.state is CP1PipelineState.READY
        pipeline.run(_SENTINEL_INPUT)
        assert pipeline.state is CP1PipelineState.COMPLETED

    def test_criterion_exception_propagates_and_sets_failed(self) -> None:
        boom = _Criterion("CP1-0001", raises=RuntimeError("boom"))
        registry = CP1CriterionRegistry()
        registry.register(boom)
        pipeline = CP1CriterionPipeline(registry)
        with pytest.raises(RuntimeError, match="boom"):
            pipeline.run(_SENTINEL_INPUT)
        assert pipeline.state is CP1PipelineState.FAILED

    def test_execution_is_order_independent_over_the_finding_set(self) -> None:
        # Registration order changes result *order* but not the *set* of findings.
        f1, f2, f3 = (
            _finding("CP1-0001", "F1"),
            _finding("CP1-0002", "F2"),
            _finding("CP1-0003", "F3"),
        )

        def run_with(order: list[str]) -> list[str]:
            mapping = {"F1": ("CP1-0001", f1), "F2": ("CP1-0002", f2), "F3": ("CP1-0003", f3)}
            registry = CP1CriterionRegistry()
            for fid in order:
                cid, finding = mapping[fid]
                registry.register(_Criterion(cid, findings=(finding,)))
            return [f.finding_id for f in CP1CriterionPipeline(registry).run(_SENTINEL_INPUT)]

        forward = run_with(["F1", "F2", "F3"])
        reverse = run_with(["F3", "F2", "F1"])
        assert forward == ["F1", "F2", "F3"]  # order follows registration (deterministic)
        assert reverse == ["F3", "F2", "F1"]
        assert set(forward) == set(reverse)  # same finding set regardless of order

    def test_repeated_runs_are_deterministic(self) -> None:
        registry = CP1CriterionRegistry()
        registry.register(_Criterion("CP1-0001", findings=(_finding("CP1-0001", "F1"),)))
        pipeline = CP1CriterionPipeline(registry)
        assert pipeline.run(_SENTINEL_INPUT) == pipeline.run(_SENTINEL_INPUT)


# ---------------------------------------------------------------------------
# 9. Framework metadata
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFrameworkMetadata:
    def test_pipeline_exposes_framework_metadata(self) -> None:
        meta = CP1CriterionPipeline(CP1CriterionRegistry()).framework_metadata()
        assert isinstance(meta, CP1FrameworkMetadata)
        assert meta.framework_version == CP1_FRAMEWORK_VERSION
        assert meta.pipeline_version == CP1_PIPELINE_VERSION
        assert meta.registry_version == CP1_REGISTRY_VERSION
        assert meta.criteria_contract_version == DEFAULT_CP1_CRITERIA_CONTRACT_VERSION

    def test_serializes_to_camel(self) -> None:
        dumped = CP1FrameworkMetadata(
            framework_version="1.0.0",
            criteria_contract_version="1.0",
            pipeline_version="1.0.0",
            registry_version="1.0.0",
        ).model_dump(by_alias=True)
        assert "frameworkVersion" in dumped
        assert "criteriaContractVersion" in dumped
        assert "framework_version" not in dumped

    def test_is_frozen(self) -> None:
        meta = CP1CriterionPipeline(CP1CriterionRegistry()).framework_metadata()
        with pytest.raises(ValidationError):
            meta.framework_version = "9.9"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 10. Composition helpers
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestComposition:
    def test_build_registry_is_empty_and_open(self) -> None:
        registry = build_cp1_criterion_registry()
        assert isinstance(registry, CP1CriterionRegistry)
        assert registry.criterion_count() == 0
        assert registry.is_sealed is False

    def test_build_pipeline_default_is_ready_and_empty(self) -> None:
        pipeline = build_cp1_criterion_pipeline()
        assert pipeline.state is CP1PipelineState.READY
        assert pipeline.run(_SENTINEL_INPUT) == ()

    def test_build_pipeline_from_registry_seals_it(self) -> None:
        registry = build_cp1_criterion_registry()
        registry.register(_Criterion("CP1-0001"))
        pipeline = build_cp1_criterion_pipeline(registry)
        assert registry.is_sealed is True
        assert [c.criterion_id for c in pipeline.get_ordered_criteria()] == ["CP1-0001"]
