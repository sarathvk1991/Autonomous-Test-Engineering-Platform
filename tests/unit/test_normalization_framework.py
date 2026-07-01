"""Unit tests for the Response Normalization Framework.

Covers
------
* NormalizationResponsibility abstract behaviour — cannot instantiate directly;
  concrete subclasses must implement ``metadata`` and ``normalize``; convenience
  wrappers read from metadata.
* NormalizationResponsibilityMetadata — immutability and defaults.
* NormalizationRegistry — registration, duplicate detection, registration-order
  retrieval, enabled filtering, sealing, state, counts.
* NormalizationPipeline — construction (seals registry), input guard, ordering
  delegation, observation collection, statistics, framework metadata, the
  ParsedResponse placeholder, state transitions, exception translation.
* NormalizationLayer — composition, lazy build, idempotent build, register-after-
  build guard, normalize delegation.
* Framework exceptions — hierarchy and message propagation.
* README — the documentation file exists alongside the package.

Design constraints
------------------
* No real responses are normalized; the source is an opaque sentinel.
* No concrete normalization responsibilities ship in the framework; all
  behaviour is exercised through lightweight local stub subclasses.
* No parsing, no ParsedResponse, no provider behaviour anywhere.
* External I/O is absent; these tests run entirely in memory.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType

import pytest

from requirement_intelligence.normalization.framework import (
    NormalizationFrameworkError,
    NormalizationLayer,
    NormalizationPipeline,
    NormalizationPipelineError,
    NormalizationRegistry,
    NormalizationRegistryError,
    NormalizationResponsibility,
    NormalizationResponsibilityError,
    NormalizationResponsibilityMetadata,
    PipelineState,
    RegistryState,
)
from requirement_intelligence.normalization.framework.normalization_metadata import (
    DEFAULT_RESPONSIBILITY_ORDER,
    DEFAULT_RESPONSIBILITY_VERSION,
)
from requirement_intelligence.normalization.models import (
    FRAMEWORK_VERSION,
    NORMALIZATION_CONTRACT_VERSION,
    PIPELINE_VERSION,
    REGISTRY_VERSION,
    RESPONSIBILITY_CATALOG_VERSION,
    NormalizationConfiguration,
    NormalizationObservation,
    NormalizationResult,
)

_FRAMEWORK_DIR = (
    Path(__file__).resolve().parents[2]
    / "requirement_intelligence"
    / "normalization"
    / "framework"
)

_TS = datetime(2026, 6, 30, 12, 0, 0, tzinfo=UTC)

#: An opaque normalization source.  The framework never inspects it.
_SOURCE = object()


# ---------------------------------------------------------------------------
# Local stub responsibilities — used exclusively within this test module
# ---------------------------------------------------------------------------


def _observation(obs_id: str) -> NormalizationObservation:
    """Build a minimal, valid NormalizationObservation fact."""
    return NormalizationObservation(
        observation_id=obs_id,
        observation_type="duplicate_identifier",
        detail="a fact was recorded",
        created_at=_TS,
    )


class _StubResponsibility(NormalizationResponsibility):
    """A configurable stub recording a fixed number of observations."""

    def __init__(
        self,
        responsibility_id: str,
        *,
        enabled: bool = True,
        observation_count: int = 0,
        order: int = DEFAULT_RESPONSIBILITY_ORDER,
    ) -> None:
        self._metadata = NormalizationResponsibilityMetadata(
            responsibility_id=responsibility_id,
            responsibility_name=f"Stub {responsibility_id}",
            enabled=enabled,
            order=order,
        )
        self._observation_count = observation_count
        self.calls = 0

    @property
    def metadata(self) -> NormalizationResponsibilityMetadata:
        return self._metadata

    def normalize(self, source: object) -> list[NormalizationObservation]:
        self.calls += 1
        return [
            _observation(f"{self.responsibility_id}:{i}")
            for i in range(self._observation_count)
        ]


class _RecordingOrderResponsibility(NormalizationResponsibility):
    """Records its id into a shared list when executed (to assert ordering)."""

    def __init__(
        self,
        responsibility_id: str,
        order_log: list[str],
        *,
        order: int = DEFAULT_RESPONSIBILITY_ORDER,
    ) -> None:
        self._metadata = NormalizationResponsibilityMetadata(
            responsibility_id=responsibility_id,
            responsibility_name=responsibility_id,
            order=order,
        )
        self._order_log = order_log

    @property
    def metadata(self) -> NormalizationResponsibilityMetadata:
        return self._metadata

    def normalize(self, source: object) -> list[NormalizationObservation]:
        self._order_log.append(self.responsibility_id)
        return []


class _ExplodingResponsibility(NormalizationResponsibility):
    """Raises inside normalize() to exercise pipeline exception translation."""

    @property
    def metadata(self) -> NormalizationResponsibilityMetadata:
        return NormalizationResponsibilityMetadata(
            responsibility_id="NORMALIZATION-9999",
            responsibility_name="Exploding",
        )

    def normalize(self, source: object) -> list[NormalizationObservation]:
        raise RuntimeError("boom")


# ---------------------------------------------------------------------------
# NormalizationResponsibility — abstract contract
# ---------------------------------------------------------------------------


class TestNormalizationResponsibility:
    def test_cannot_instantiate_abstract_base(self) -> None:
        with pytest.raises(TypeError):
            NormalizationResponsibility()  # type: ignore[abstract]

    def test_convenience_wrappers_read_metadata(self) -> None:
        r = _StubResponsibility("NORMALIZATION-0001")
        assert r.responsibility_id == "NORMALIZATION-0001"
        assert r.responsibility_name == "Stub NORMALIZATION-0001"
        assert r.responsibility_version == DEFAULT_RESPONSIBILITY_VERSION
        assert r.order == DEFAULT_RESPONSIBILITY_ORDER
        assert r.enabled is True

    def test_order_wrapper_reads_metadata(self) -> None:
        r = _StubResponsibility("NORMALIZATION-0001", order=1)
        assert r.order == 1
        assert r.order == r.metadata.order

    def test_wrappers_are_read_through_not_stored(self) -> None:
        # Every wrapper is a pure delegate to the single metadata value; changing
        # the value object (a fresh one) would change what the wrappers report.
        r = _StubResponsibility("NORMALIZATION-0001", order=3)
        assert r.responsibility_id is r.metadata.responsibility_id
        assert r.responsibility_name is r.metadata.responsibility_name
        assert r.responsibility_version is r.metadata.responsibility_version
        assert r.order == r.metadata.order
        assert r.enabled == r.metadata.enabled

    def test_disabled_flag_is_read_from_metadata(self) -> None:
        r = _StubResponsibility("NORMALIZATION-0002", enabled=False)
        assert r.enabled is False

    def test_normalize_returns_observations(self) -> None:
        r = _StubResponsibility("NORMALIZATION-0001", observation_count=2)
        out = r.normalize(_SOURCE)
        assert len(out) == 2
        assert all(isinstance(o, NormalizationObservation) for o in out)


# ---------------------------------------------------------------------------
# NormalizationResponsibilityMetadata — immutability and defaults
# ---------------------------------------------------------------------------


class TestNormalizationResponsibilityMetadata:
    def _meta(self, **overrides: object) -> NormalizationResponsibilityMetadata:
        kwargs: dict[str, object] = {
            "responsibility_id": "NORMALIZATION-0001",
            "responsibility_name": "x",
        }
        kwargs.update(overrides)
        return NormalizationResponsibilityMetadata(**kwargs)  # type: ignore[arg-type]

    def test_is_frozen(self) -> None:
        meta = self._meta()
        with pytest.raises(dataclasses.FrozenInstanceError):
            meta.responsibility_id = "other"  # type: ignore[misc]

    def test_all_active_and_reserved_fields_are_frozen(self) -> None:
        meta = self._meta()
        for attr, value in (
            ("responsibility_name", "y"),
            ("responsibility_version", "2.0.0"),
            ("order", 9),
            ("enabled", False),
            ("tags", ("a",)),
            ("documentation_reference", "doc"),
            ("responsibility_catalog_version", "1.0"),
            ("future_schema_compatibility", "1.0"),
            ("normalization_contract_version", "1.0"),
            ("metadata", {}),
        ):
            with pytest.raises(dataclasses.FrozenInstanceError):
                setattr(meta, attr, value)

    def test_defaults(self) -> None:
        meta = self._meta()
        assert meta.responsibility_version == DEFAULT_RESPONSIBILITY_VERSION
        assert meta.order == DEFAULT_RESPONSIBILITY_ORDER
        assert meta.order == 0
        assert meta.enabled is True
        assert meta.tags == ()
        assert meta.documentation_reference is None
        assert meta.responsibility_catalog_version is None
        assert meta.future_schema_compatibility is None
        assert meta.normalization_contract_version is None
        assert dict(meta.metadata) == {}

    def test_all_fields_can_be_set(self) -> None:
        meta = NormalizationResponsibilityMetadata(
            responsibility_id="NORMALIZATION-0002",
            responsibility_name="Determine outcome",
            responsibility_version="2.1.0",
            order=2,
            enabled=False,
            tags=("structure", "outcome"),
            documentation_reference="catalog#NORMALIZATION-0002",
            responsibility_catalog_version="1.0.0",
            future_schema_compatibility="parsed-response>=1",
            normalization_contract_version="1.2.0",
            metadata={"team": "platform"},
        )
        assert meta.responsibility_id == "NORMALIZATION-0002"
        assert meta.responsibility_name == "Determine outcome"
        assert meta.responsibility_version == "2.1.0"
        assert meta.order == 2
        assert meta.enabled is False
        assert meta.tags == ("structure", "outcome")
        assert meta.documentation_reference == "catalog#NORMALIZATION-0002"
        assert meta.responsibility_catalog_version == "1.0.0"
        assert meta.future_schema_compatibility == "parsed-response>=1"
        assert meta.normalization_contract_version == "1.2.0"
        assert dict(meta.metadata) == {"team": "platform"}

    def test_free_form_metadata_is_read_only(self) -> None:
        # The whole value object is immutable in *content*, not merely in its
        # attribute bindings: the free-form map is a read-only MappingProxyType.
        meta = self._meta(metadata={"k": "v"})
        assert isinstance(meta.metadata, MappingProxyType)
        with pytest.raises(TypeError):
            meta.metadata["k"] = "other"  # type: ignore[index]

    def test_free_form_metadata_copies_source_mapping(self) -> None:
        # Mutating the caller's original dict must not leak into the frozen value.
        source = {"k": "v"}
        meta = self._meta(metadata=source)
        source["k"] = "mutated"
        assert dict(meta.metadata) == {"k": "v"}

    def test_value_equality(self) -> None:
        assert self._meta() == self._meta()

    def test_value_equality_includes_new_fields(self) -> None:
        assert self._meta(order=1, metadata={"a": 1}) == self._meta(
            order=1, metadata={"a": 1}
        )
        assert self._meta(order=1) != self._meta(order=2)
        assert self._meta(metadata={"a": 1}) != self._meta(metadata={"a": 2})
        assert self._meta(responsibility_catalog_version="1.0") != self._meta(
            responsibility_catalog_version="2.0"
        )

    def test_has_no_layer_attribute(self) -> None:
        # Deliberate deviation from ValidationRuleMetadata: normalization has no
        # layers — it carries a descriptive `order` instead.
        meta = self._meta()
        assert not hasattr(meta, "validation_layer")
        assert not hasattr(meta, "layer")
        assert hasattr(meta, "order")

    def test_readme_example_shape(self) -> None:
        # Mirrors the README's worked example for NORMALIZATION-0001.
        meta = NormalizationResponsibilityMetadata(
            responsibility_id="NORMALIZATION-0001",
            responsibility_name="Recover canonical structure",
            order=1,
        )
        assert meta.responsibility_id == "NORMALIZATION-0001"
        assert meta.order == 1


# ---------------------------------------------------------------------------
# NormalizationRegistry
# ---------------------------------------------------------------------------


class TestNormalizationRegistry:
    def test_starts_open_and_empty(self) -> None:
        reg = NormalizationRegistry()
        assert reg.state is RegistryState.OPEN
        assert reg.is_sealed is False
        assert reg.responsibility_count() == 0
        assert reg.get_all_responsibilities() == []

    def test_register_and_retrieve(self) -> None:
        reg = NormalizationRegistry()
        r = _StubResponsibility("NORMALIZATION-0001")
        reg.register(r)
        assert reg.responsibility_count() == 1
        assert reg.get_all_responsibilities() == [r]
        assert reg.list_responsibility_ids() == ["NORMALIZATION-0001"]

    def test_duplicate_id_rejected(self) -> None:
        reg = NormalizationRegistry()
        reg.register(_StubResponsibility("NORMALIZATION-0001"))
        with pytest.raises(NormalizationRegistryError, match="already registered"):
            reg.register(_StubResponsibility("NORMALIZATION-0001"))

    def test_retrieval_preserves_registration_order(self) -> None:
        # Deviation: ordering is registration order, not layer order.
        reg = NormalizationRegistry()
        reg.register(_StubResponsibility("NORMALIZATION-0003"))
        reg.register(_StubResponsibility("NORMALIZATION-0001"))
        reg.register(_StubResponsibility("NORMALIZATION-0002"))
        assert reg.list_responsibility_ids() == [
            "NORMALIZATION-0003",
            "NORMALIZATION-0001",
            "NORMALIZATION-0002",
        ]

    def test_order_field_does_not_influence_registry_ordering(self) -> None:
        # `order` is descriptive identity only (Catalog §8: no separate ordering
        # dimension). The registry must still return registration order even when
        # the declared `order` disagrees.
        reg = NormalizationRegistry()
        reg.register(_StubResponsibility("NORMALIZATION-0002", order=2))
        reg.register(_StubResponsibility("NORMALIZATION-0001", order=1))
        assert reg.list_responsibility_ids() == [
            "NORMALIZATION-0002",
            "NORMALIZATION-0001",
        ]

    def test_registration_consumes_metadata_identity(self) -> None:
        # Registration keys duplicate detection on metadata.responsibility_id.
        reg = NormalizationRegistry()
        r = _StubResponsibility("NORMALIZATION-0001")
        reg.register(r)
        assert reg.get_all_responsibilities()[0].metadata.responsibility_id == (
            "NORMALIZATION-0001"
        )
        with pytest.raises(NormalizationRegistryError, match="already registered"):
            reg.register(_StubResponsibility("NORMALIZATION-0001"))

    def test_enabled_filtering(self) -> None:
        reg = NormalizationRegistry()
        reg.register(_StubResponsibility("NORMALIZATION-0001", enabled=True))
        reg.register(_StubResponsibility("NORMALIZATION-0002", enabled=False))
        enabled = reg.get_enabled_responsibilities()
        assert [r.responsibility_id for r in enabled] == ["NORMALIZATION-0001"]
        # disabled responsibilities still counted by the total.
        assert reg.responsibility_count() == 2

    def test_seal_is_idempotent_and_blocks_registration(self) -> None:
        reg = NormalizationRegistry()
        reg.seal()
        reg.seal()  # idempotent — no raise
        assert reg.is_sealed is True
        with pytest.raises(NormalizationRegistryError, match="sealed"):
            reg.register(_StubResponsibility("NORMALIZATION-0001"))

    def test_retrieval_allowed_after_sealing(self) -> None:
        reg = NormalizationRegistry()
        reg.register(_StubResponsibility("NORMALIZATION-0001"))
        reg.seal()
        assert reg.list_responsibility_ids() == ["NORMALIZATION-0001"]


# ---------------------------------------------------------------------------
# NormalizationPipeline
# ---------------------------------------------------------------------------


class TestNormalizationPipeline:
    def test_construction_requires_registry(self) -> None:
        with pytest.raises(NormalizationPipelineError, match="NormalizationRegistry"):
            NormalizationPipeline(object())  # type: ignore[arg-type]

    def test_construction_seals_registry_and_is_ready(self) -> None:
        reg = NormalizationRegistry()
        pipe = NormalizationPipeline(reg)
        assert reg.is_sealed is True
        assert pipe.state is PipelineState.READY

    def test_run_requires_non_none_source(self) -> None:
        pipe = NormalizationPipeline(NormalizationRegistry())
        with pytest.raises(NormalizationPipelineError, match="non-None source"):
            pipe.run(None)

    def test_empty_run_returns_populated_result(self) -> None:
        pipe = NormalizationPipeline(NormalizationRegistry())
        result = pipe.run(_SOURCE)
        assert isinstance(result, NormalizationResult)
        assert result.observations == ()
        assert result.normalization_statistics.responsibilities_executed == 0
        assert result.normalization_statistics.observations_recorded == 0
        assert pipe.state is PipelineState.COMPLETED

    def test_parsed_response_placeholder_is_none(self) -> None:
        pipe = NormalizationPipeline(NormalizationRegistry())
        result = pipe.run(_SOURCE)
        assert result.parsed_response is None

    def test_result_has_no_verdict_or_summary(self) -> None:
        # Facts, not judgments (Contract §10).
        pipe = NormalizationPipeline(NormalizationRegistry())
        result = pipe.run(_SOURCE)
        assert not hasattr(result, "overall_verdict")
        assert not hasattr(result, "validation_summary")
        assert not hasattr(result, "summary")

    def test_collects_observations_and_counts(self) -> None:
        reg = NormalizationRegistry()
        reg.register(_StubResponsibility("NORMALIZATION-0001", observation_count=2))
        reg.register(_StubResponsibility("NORMALIZATION-0002", observation_count=1))
        result = NormalizationPipeline(reg).run(_SOURCE)
        assert len(result.observations) == 3
        assert result.normalization_statistics.responsibilities_executed == 2
        assert result.normalization_statistics.observations_recorded == 3

    def test_disabled_responsibility_is_skipped(self) -> None:
        reg = NormalizationRegistry()
        enabled = _StubResponsibility("NORMALIZATION-0001", observation_count=1)
        disabled = _StubResponsibility(
            "NORMALIZATION-0002", enabled=False, observation_count=5
        )
        reg.register(enabled)
        reg.register(disabled)
        result = NormalizationPipeline(reg).run(_SOURCE)
        assert enabled.calls == 1
        assert disabled.calls == 0
        assert result.normalization_statistics.responsibilities_executed == 1
        assert len(result.observations) == 1

    def test_execution_order_follows_registration(self) -> None:
        order_log: list[str] = []
        reg = NormalizationRegistry()
        reg.register(_RecordingOrderResponsibility("NORMALIZATION-0003", order_log))
        reg.register(_RecordingOrderResponsibility("NORMALIZATION-0001", order_log))
        NormalizationPipeline(reg).run(_SOURCE)
        assert order_log == ["NORMALIZATION-0003", "NORMALIZATION-0001"]

    def test_execution_ignores_declared_order_field(self) -> None:
        # Even when the declared `order` disagrees with registration, the pipeline
        # executes in registration order — `order` is never an execution driver.
        order_log: list[str] = []
        reg = NormalizationRegistry()
        reg.register(
            _RecordingOrderResponsibility("NORMALIZATION-0002", order_log, order=2)
        )
        reg.register(
            _RecordingOrderResponsibility("NORMALIZATION-0001", order_log, order=1)
        )
        NormalizationPipeline(reg).run(_SOURCE)
        assert order_log == ["NORMALIZATION-0002", "NORMALIZATION-0001"]

    def test_responsibility_exception_marks_failed_and_propagates(self) -> None:
        reg = NormalizationRegistry()
        reg.register(_ExplodingResponsibility())
        pipe = NormalizationPipeline(reg)
        with pytest.raises(RuntimeError, match="boom"):
            pipe.run(_SOURCE)
        assert pipe.state is PipelineState.FAILED

    def test_framework_metadata_versions(self) -> None:
        result = NormalizationPipeline(NormalizationRegistry()).run(_SOURCE)
        meta = result.normalization_framework_metadata
        assert meta.framework_version == FRAMEWORK_VERSION
        assert meta.pipeline_version == PIPELINE_VERSION
        assert meta.registry_version == REGISTRY_VERSION
        assert meta.responsibility_catalog_version == RESPONSIBILITY_CATALOG_VERSION
        assert meta.normalization_contract_version == NORMALIZATION_CONTRACT_VERSION

    def test_correlation_id_threaded_through(self) -> None:
        result = NormalizationPipeline(NormalizationRegistry()).run(
            _SOURCE, correlation_id="EX-42"
        )
        assert result.correlation_id == "EX-42"
        assert result.normalization_statistics.correlation_id == "EX-42"

    def test_custom_configuration_is_referenced(self) -> None:
        config = NormalizationConfiguration(normalization_contract_version="9.9")
        result = NormalizationPipeline(NormalizationRegistry()).run(_SOURCE, config)
        assert result.normalization_configuration is config
        assert result.normalization_statistics.normalization_contract_version == "9.9"

    def test_get_ordered_responsibilities_returns_enabled_only(self) -> None:
        reg = NormalizationRegistry()
        reg.register(_StubResponsibility("NORMALIZATION-0001"))
        reg.register(_StubResponsibility("NORMALIZATION-0002", enabled=False))
        pipe = NormalizationPipeline(reg)
        assert [r.responsibility_id for r in pipe.get_ordered_responsibilities()] == [
            "NORMALIZATION-0001"
        ]


# ---------------------------------------------------------------------------
# NormalizationLayer — framework facade
# ---------------------------------------------------------------------------


class TestNormalizationLayer:
    def test_register_and_normalize(self) -> None:
        layer = NormalizationLayer()
        layer.register(_StubResponsibility("NORMALIZATION-0001", observation_count=1))
        result = layer.normalize(_SOURCE)
        assert isinstance(result, NormalizationResult)
        assert len(result.observations) == 1

    def test_lazy_build_on_normalize(self) -> None:
        layer = NormalizationLayer()
        assert layer.is_built is False
        layer.normalize(_SOURCE)
        assert layer.is_built is True

    def test_build_is_idempotent(self) -> None:
        layer = NormalizationLayer()
        first = layer.build()
        second = layer.build()
        assert first is second

    def test_register_after_build_raises(self) -> None:
        layer = NormalizationLayer()
        layer.build()
        with pytest.raises(NormalizationRegistryError, match="sealed"):
            layer.register(_StubResponsibility("NORMALIZATION-0001"))

    def test_accepts_prepopulated_registry(self) -> None:
        reg = NormalizationRegistry()
        reg.register(_StubResponsibility("NORMALIZATION-0001"))
        layer = NormalizationLayer(reg)
        assert layer.registry is reg
        result = layer.normalize(_SOURCE)
        assert result.normalization_statistics.responsibilities_executed == 1


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TestExceptions:
    def test_hierarchy(self) -> None:
        assert issubclass(NormalizationPipelineError, NormalizationFrameworkError)
        assert issubclass(NormalizationRegistryError, NormalizationFrameworkError)
        assert issubclass(NormalizationResponsibilityError, NormalizationFrameworkError)

    def test_base_catches_all(self) -> None:
        for exc in (
            NormalizationPipelineError,
            NormalizationRegistryError,
            NormalizationResponsibilityError,
        ):
            with pytest.raises(NormalizationFrameworkError):
                raise exc("x")

    def test_message_propagation(self) -> None:
        with pytest.raises(NormalizationRegistryError, match="custom message"):
            raise NormalizationRegistryError("custom message")


# ---------------------------------------------------------------------------
# Documentation
# ---------------------------------------------------------------------------


class TestReadme:
    def test_readme_exists(self) -> None:
        assert (_FRAMEWORK_DIR / "README.md").is_file()
