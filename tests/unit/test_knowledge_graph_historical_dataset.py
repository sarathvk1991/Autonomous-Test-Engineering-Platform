"""Unit tests for the Historical Dataset Resolution Principle (CAP-084B).

``HistoricalDatasetProvider`` / ``HistoricalDataset`` / ``HistoricalExecutionRecord``
are engine-internal only — never a runtime contract. These tests exercise the
CAP-084B default provider's determinism and reproducibility, mirroring
``test_continuous_improvement_engine.py``'s coverage of its own default provider.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from requirement_intelligence.knowledge_graph.engine.historical_dataset import (
    DeterministicHistoricalDatasetProvider,
    HistoricalDataset,
    HistoricalDatasetProvider,
    HistoricalExecutionRecord,
)
from requirement_intelligence.knowledge_graph.models.historical_dataset_reference import (
    HistoricalDatasetReference,
)


def _reference(**overrides: object) -> HistoricalDatasetReference:
    defaults: dict[str, object] = dict(
        dataset_id="ds-hd",
        dataset_version="1.0.0",
        first_execution_id="ex-first",
        last_execution_id="ex-last",
        execution_count=10,
        history_window=25,
        generated_at=datetime(2026, 7, 15, tzinfo=UTC),
    )
    defaults.update(overrides)
    return HistoricalDatasetReference(**defaults)  # type: ignore[arg-type]


@pytest.mark.unit
class TestHistoricalExecutionRecord:
    def test_is_a_plain_frozen_dataclass(self) -> None:
        record = HistoricalExecutionRecord(
            execution_id="ex-1",
            ordinal=0,
            requirement_id="req-1",
            recommendation_id=None,
            finding_id=None,
            capability_id=None,
            document_id=None,
            depends_on_previous=False,
        )
        with pytest.raises(AttributeError):
            record.ordinal = 1  # type: ignore[misc]


@pytest.mark.unit
class TestDeterministicHistoricalDatasetProvider:
    def test_resolve_returns_one_record_per_execution(self) -> None:
        dataset = DeterministicHistoricalDatasetProvider().resolve(_reference(execution_count=7))
        assert len(dataset.executions) == 7

    def test_resolve_is_a_pure_function_of_the_reference(self) -> None:
        reference = _reference()
        d1 = DeterministicHistoricalDatasetProvider().resolve(reference)
        d2 = DeterministicHistoricalDatasetProvider().resolve(reference)
        assert d1 == d2

    def test_dataset_id_matches_reference(self) -> None:
        dataset = DeterministicHistoricalDatasetProvider().resolve(_reference(dataset_id="ds-x"))
        assert dataset.dataset_id == "ds-x"

    def test_first_execution_uses_first_execution_id(self) -> None:
        dataset = DeterministicHistoricalDatasetProvider().resolve(
            _reference(first_execution_id="ex-alpha")
        )
        assert dataset.executions[0].execution_id == "ex-alpha"

    def test_last_execution_uses_last_execution_id(self) -> None:
        dataset = DeterministicHistoricalDatasetProvider().resolve(
            _reference(last_execution_id="ex-omega")
        )
        assert dataset.executions[-1].execution_id == "ex-omega"

    def test_ordinals_are_sequential(self) -> None:
        dataset = DeterministicHistoricalDatasetProvider().resolve(_reference(execution_count=5))
        assert [execution.ordinal for execution in dataset.executions] == [0, 1, 2, 3, 4]

    def test_requirement_id_always_present(self) -> None:
        dataset = DeterministicHistoricalDatasetProvider().resolve(_reference())
        assert all(execution.requirement_id for execution in dataset.executions)

    def test_first_execution_never_depends_on_previous(self) -> None:
        dataset = DeterministicHistoricalDatasetProvider().resolve(_reference())
        assert dataset.executions[0].depends_on_previous is False

    def test_non_first_executions_depend_on_previous(self) -> None:
        dataset = DeterministicHistoricalDatasetProvider().resolve(_reference(execution_count=5))
        assert all(execution.depends_on_previous for execution in dataset.executions[1:])

    def test_varies_with_dataset_id(self) -> None:
        d1 = DeterministicHistoricalDatasetProvider().resolve(_reference(dataset_id="ds-a"))
        d2 = DeterministicHistoricalDatasetProvider().resolve(_reference(dataset_id="ds-b"))
        assert d1.executions[0].requirement_id != d2.executions[0].requirement_id

    def test_optional_entity_ids_vary_across_datasets(self) -> None:
        """Recommendation/finding/capability/document presence is hash-derived, not constant."""
        seen_recommendation_present = set()
        seen_finding_present = set()
        for i in range(10):
            dataset = DeterministicHistoricalDatasetProvider().resolve(
                _reference(dataset_id=f"ds-{i}", execution_count=25, history_window=25)
            )
            seen_recommendation_present.add(
                any(execution.recommendation_id for execution in dataset.executions)
            )
            seen_finding_present.add(any(execution.finding_id for execution in dataset.executions))
        assert True in seen_recommendation_present
        assert True in seen_finding_present

    def test_provider_is_a_historical_dataset_provider(self) -> None:
        assert isinstance(DeterministicHistoricalDatasetProvider(), HistoricalDatasetProvider)

    def test_resolved_dataset_is_a_plain_historical_dataset(self) -> None:
        dataset = DeterministicHistoricalDatasetProvider().resolve(_reference())
        assert isinstance(dataset, HistoricalDataset)
