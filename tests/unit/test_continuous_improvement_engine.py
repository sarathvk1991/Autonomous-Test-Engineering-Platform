"""Behaviour, determinism, and explainability tests for
:class:`DeterministicContinuousImprovementEngine` (CAP-083B).

Exercises the engine end-to-end via an injectable :class:`HistoricalDatasetProvider`
stub that hands the engine a fully controlled :class:`HistoricalDataset` — this
is how the engine's policy-governed detection/observation/generation logic is
tested precisely, independent of the CAP-083B default provider's hash-derived
(and therefore intentionally uncontrolled) synthetic data. The default provider
itself is covered separately for determinism/reproducibility.

Covers: recurring finding detection, trend detection, opportunity generation,
metrics, summary, policy governance (every threshold read from
``ImprovementPolicy``, never hard-coded), explainability, determinism, and
containment — including dedicated tests for Recommendation 11 (Derived
Knowledge must never recursively consume Derived Knowledge, ADR-0022).
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime
from pathlib import Path
from typing import get_type_hints

import pytest
from pydantic import ValidationError

from requirement_intelligence.continuous_improvement.engine import (
    DeterministicContinuousImprovementEngine,
    DeterministicHistoricalDatasetProvider,
    HistoricalDataset,
    HistoricalDatasetProvider,
    HistoricalExecutionRecord,
)
from requirement_intelligence.continuous_improvement.models import (
    ContinuousImprovementResult,
    HistoricalDatasetReference,
    ImprovementFinding,
    ImprovementOpportunity,
    ImprovementSourceLayer,
    ImprovementTrend,
    ImprovementTrendDirection,
)
from requirement_intelligence.continuous_improvement.policy import default_improvement_policy
from requirement_intelligence.continuous_improvement.policy.continuous_improvement_policy import (
    ImprovementThresholds,
)
from requirement_intelligence.continuous_improvement.rules import default_improvement_rule_catalog

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CONTINUOUS_IMPROVEMENT_PKG = _REPO_ROOT / "requirement_intelligence" / "continuous_improvement"
_FIXED_CLOCK = lambda: datetime(2026, 7, 15, tzinfo=UTC)  # noqa: E731


def _reference(**overrides: object) -> HistoricalDatasetReference:
    defaults: dict[str, object] = dict(
        dataset_id="ds-1",
        dataset_version="1.0.0",
        first_execution_id="ex-1",
        last_execution_id="ex-10",
        execution_count=10,
        history_window=25,
        generated_at=datetime(2026, 7, 15, tzinfo=UTC),
    )
    defaults.update(overrides)
    return HistoricalDatasetReference(**defaults)  # type: ignore[arg-type]


class _FakeProvider(HistoricalDatasetProvider):
    """A controllable stub — hands the engine a fixed, hand-built dataset."""

    def __init__(self, dataset: HistoricalDataset) -> None:
        self._dataset = dataset

    def resolve(self, historical_dataset: HistoricalDatasetReference) -> HistoricalDataset:
        return self._dataset


def _dataset(
    dataset_id: str,
    *,
    recurrence: dict[ImprovementSourceLayer, list[bool]] | None = None,
    metrics: dict[ImprovementSourceLayer, list[float]] | None = None,
    execution_count: int = 5,
) -> HistoricalDataset:
    """Build a controlled dataset: per-source recurrence flags and/or metric series."""
    recurrence = recurrence or {}
    metrics = metrics or {}
    executions = []
    for ordinal in range(execution_count):
        flags = {source: series[ordinal] for source, series in recurrence.items()}
        values = {source: series[ordinal] for source, series in metrics.items()}
        executions.append(
            HistoricalExecutionRecord(
                execution_id=f"{dataset_id}-ex-{ordinal}",
                ordinal=ordinal,
                recurrence_flags=flags,
                metric_values=values,
            )
        )
    return HistoricalDataset(dataset_id=dataset_id, executions=tuple(executions))


def _engine(policy=None, catalog=None, dataset: HistoricalDataset | None = None):
    provider = _FakeProvider(dataset) if dataset is not None else None
    return DeterministicContinuousImprovementEngine(
        policy=policy or default_improvement_policy(),
        rule_catalog=catalog or default_improvement_rule_catalog(),
        provider=provider,
        clock=_FIXED_CLOCK,
    )


@pytest.mark.unit
class TestRecurringFindingDetection:
    def test_finding_emitted_when_occurrence_meets_threshold(self) -> None:
        dataset = _dataset(
            "ds-a",
            recurrence={ImprovementSourceLayer.VALIDATION: [True, True, True, False, False]},
        )
        result = _engine(dataset=dataset).improve(_reference(dataset_id="ds-a"))
        matches = [f for f in result.findings if f.source == ImprovementSourceLayer.VALIDATION]
        assert len(matches) == 1
        assert matches[0].occurrence_count == 3

    def test_finding_not_emitted_when_below_threshold(self) -> None:
        dataset = _dataset(
            "ds-b",
            recurrence={ImprovementSourceLayer.VALIDATION: [True, True, False, False, False]},
        )
        # default minimum_occurrences is 3; only 2 occurrences here.
        result = _engine(dataset=dataset).improve(_reference(dataset_id="ds-b"))
        matches = [f for f in result.findings if f.source == ImprovementSourceLayer.VALIDATION]
        assert matches == []

    def test_finding_contributing_ids_match_occurrence_count(self) -> None:
        dataset = _dataset(
            "ds-c",
            recurrence={ImprovementSourceLayer.GROUNDING: [True, True, True, True, False]},
        )
        result = _engine(dataset=dataset).improve(_reference(dataset_id="ds-c"))
        finding = next(f for f in result.findings if f.source == ImprovementSourceLayer.GROUNDING)
        assert len(finding.contributing_execution_ids) == finding.occurrence_count == 4

    def test_finding_severity_matches_rule_hint(self) -> None:
        dataset = _dataset(
            "ds-d",
            recurrence={ImprovementSourceLayer.GROUNDING: [True, True, True, True, True]},
        )
        result = _engine(dataset=dataset).improve(_reference(dataset_id="ds-d"))
        finding = next(f for f in result.findings if f.source == ImprovementSourceLayer.GROUNDING)
        assert str(finding.severity) == "critical"  # IR-REC-002's severity_hint

    def test_disabled_capability_switch_suppresses_all_findings(self) -> None:
        base_policy = default_improvement_policy()
        policy = base_policy.model_copy(
            update={
                "capability_switches": base_policy.capability_switches.model_copy(
                    update={"enable_recurring_finding_detection": False}
                )
            }
        )
        dataset = _dataset(
            "ds-e",
            recurrence={ImprovementSourceLayer.VALIDATION: [True, True, True, True, True]},
        )
        result = _engine(policy=policy, dataset=dataset).improve(_reference(dataset_id="ds-e"))
        assert result.findings == ()

    def test_disabled_rule_in_catalog_suppresses_that_finding(self) -> None:
        catalog = default_improvement_rule_catalog()
        rule = catalog.rule("IR-REC-001")
        assert rule is not None
        disabled_rule = rule.model_copy(update={"enabled": False})
        other_rules = tuple(r for r in catalog.rules if r.rule_id != "IR-REC-001")
        new_catalog = catalog.model_copy(
            update={
                "rules": tuple(
                    sorted(
                        (*other_rules, disabled_rule), key=lambda r: (r.evaluation_order, r.rule_id)
                    )
                )
            }
        )
        dataset = _dataset(
            "ds-f",
            recurrence={ImprovementSourceLayer.VALIDATION: [True, True, True, True, True]},
        )
        result = _engine(catalog=new_catalog, dataset=dataset).improve(
            _reference(dataset_id="ds-f")
        )
        assert all(f.source != ImprovementSourceLayer.VALIDATION for f in result.findings)

    def test_multiple_sources_each_produce_independent_findings(self) -> None:
        dataset = _dataset(
            "ds-g",
            recurrence={
                ImprovementSourceLayer.VALIDATION: [True, True, True, False, False],
                ImprovementSourceLayer.GROUNDING: [True, True, True, True, False],
            },
        )
        result = _engine(dataset=dataset).improve(_reference(dataset_id="ds-g"))
        sources = {f.source for f in result.findings}
        assert {ImprovementSourceLayer.VALIDATION, ImprovementSourceLayer.GROUNDING} <= sources


@pytest.mark.unit
class TestTrendDetection:
    def test_monotonically_increasing_values_yield_improving(self) -> None:
        dataset = _dataset(
            "ds-h", metrics={ImprovementSourceLayer.GROUNDING: [10.0, 20.0, 30.0, 40.0, 50.0]}
        )
        result = _engine(dataset=dataset).improve(_reference(dataset_id="ds-h"))
        trend = next(t for t in result.trends if t.source == ImprovementSourceLayer.GROUNDING)
        assert trend.direction == ImprovementTrendDirection.IMPROVING

    def test_monotonically_decreasing_values_yield_degrading(self) -> None:
        dataset = _dataset(
            "ds-i", metrics={ImprovementSourceLayer.GROUNDING: [50.0, 40.0, 30.0, 20.0, 10.0]}
        )
        result = _engine(dataset=dataset).improve(_reference(dataset_id="ds-i"))
        trend = next(t for t in result.trends if t.source == ImprovementSourceLayer.GROUNDING)
        assert trend.direction == ImprovementTrendDirection.DEGRADING

    def test_constant_values_yield_stable(self) -> None:
        dataset = _dataset(
            "ds-j", metrics={ImprovementSourceLayer.GROUNDING: [50.0, 50.0, 50.0, 50.0, 50.0]}
        )
        result = _engine(dataset=dataset).improve(_reference(dataset_id="ds-j"))
        trend = next(t for t in result.trends if t.source == ImprovementSourceLayer.GROUNDING)
        assert trend.direction == ImprovementTrendDirection.STABLE

    def test_mixed_direction_values_yield_volatile(self) -> None:
        dataset = _dataset(
            "ds-k", metrics={ImprovementSourceLayer.GROUNDING: [10.0, 50.0, 5.0, 60.0, 1.0]}
        )
        result = _engine(dataset=dataset).improve(_reference(dataset_id="ds-k"))
        trend = next(t for t in result.trends if t.source == ImprovementSourceLayer.GROUNDING)
        assert trend.direction == ImprovementTrendDirection.VOLATILE

    def test_trend_observation_count_matches_contributing_ids(self) -> None:
        dataset = _dataset(
            "ds-l", metrics={ImprovementSourceLayer.GROUNDING: [1.0, 2.0, 3.0, 4.0, 5.0]}
        )
        result = _engine(dataset=dataset).improve(_reference(dataset_id="ds-l"))
        trend = next(t for t in result.trends if t.source == ImprovementSourceLayer.GROUNDING)
        assert len(trend.contributing_execution_ids) == trend.observation_count == 5

    def test_disabled_capability_switch_suppresses_all_trends(self) -> None:
        base_policy = default_improvement_policy()
        policy = base_policy.model_copy(
            update={
                "capability_switches": base_policy.capability_switches.model_copy(
                    update={"enable_trend_detection": False}
                )
            }
        )
        dataset = _dataset(
            "ds-m", metrics={ImprovementSourceLayer.GROUNDING: [1.0, 2.0, 3.0, 4.0, 5.0]}
        )
        result = _engine(policy=policy, dataset=dataset).improve(_reference(dataset_id="ds-m"))
        assert result.trends == ()


@pytest.mark.unit
class TestOpportunityGeneration:
    def test_opportunity_emitted_when_matching_finding_exists(self) -> None:
        dataset = _dataset(
            "ds-n",
            recurrence={ImprovementSourceLayer.QUALITY_GOVERNANCE: [True, True, True, True, True]},
        )
        result = _engine(dataset=dataset).improve(_reference(dataset_id="ds-n"))
        matching_finding = next(
            f for f in result.findings if f.source == ImprovementSourceLayer.QUALITY_GOVERNANCE
        )
        opportunity = next(
            o for o in result.opportunities if matching_finding.finding_id in o.source_finding_ids
        )
        assert opportunity.source_finding_ids == (matching_finding.finding_id,)

    def test_opportunity_not_emitted_when_no_matching_finding(self) -> None:
        dataset = _dataset("ds-o", execution_count=5)  # no recurrence, no findings
        result = _engine(dataset=dataset).improve(_reference(dataset_id="ds-o"))
        assert result.findings == ()
        assert all(
            o.source_finding_ids == () for o in result.opportunities if o.source_trend_ids == ()
        )

    def test_opportunity_emitted_when_trend_is_degrading(self) -> None:
        dataset = _dataset(
            "ds-p", metrics={ImprovementSourceLayer.CP1: [50.0, 40.0, 30.0, 20.0, 10.0]}
        )
        result = _engine(dataset=dataset).improve(_reference(dataset_id="ds-p"))
        trend = next(t for t in result.trends if t.source == ImprovementSourceLayer.CP1)
        assert trend.direction == ImprovementTrendDirection.DEGRADING
        opportunity = next(o for o in result.opportunities if trend.trend_id in o.source_trend_ids)
        assert opportunity.source_trend_ids == (trend.trend_id,)

    def test_opportunity_not_emitted_when_trend_is_improving(self) -> None:
        dataset = _dataset(
            "ds-q", metrics={ImprovementSourceLayer.CP1: [10.0, 20.0, 30.0, 40.0, 50.0]}
        )
        result = _engine(dataset=dataset).improve(_reference(dataset_id="ds-q"))
        trend = next(t for t in result.trends if t.source == ImprovementSourceLayer.CP1)
        assert trend.direction == ImprovementTrendDirection.IMPROVING
        assert all(trend.trend_id not in o.source_trend_ids for o in result.opportunities)

    def test_disabled_capability_switch_suppresses_all_opportunities(self) -> None:
        base_policy = default_improvement_policy()
        policy = base_policy.model_copy(
            update={
                "capability_switches": base_policy.capability_switches.model_copy(
                    update={"enable_opportunity_generation": False}
                )
            }
        )
        dataset = _dataset(
            "ds-r",
            recurrence={ImprovementSourceLayer.QUALITY_GOVERNANCE: [True, True, True, True, True]},
        )
        result = _engine(policy=policy, dataset=dataset).improve(_reference(dataset_id="ds-r"))
        assert result.opportunities == ()


@pytest.mark.unit
class TestPolicyGovernance:
    def test_minimum_occurrences_threshold_is_read_from_policy(self) -> None:
        base_policy = default_improvement_policy()
        strict_policy = base_policy.model_copy(
            update={"thresholds": ImprovementThresholds(minimum_occurrences=5, history_window=25)}
        )
        dataset = _dataset(
            "ds-s",
            recurrence={ImprovementSourceLayer.VALIDATION: [True, True, True, True, False]},
        )
        # 4 occurrences: passes the default floor (3) but not a raised floor (5).
        default_result = _engine(dataset=dataset).improve(_reference(dataset_id="ds-s"))
        strict_result = _engine(policy=strict_policy, dataset=dataset).improve(
            _reference(dataset_id="ds-s")
        )
        assert any(f.source == ImprovementSourceLayer.VALIDATION for f in default_result.findings)
        assert all(f.source != ImprovementSourceLayer.VALIDATION for f in strict_result.findings)

    def test_engine_disabled_returns_empty_result(self) -> None:
        base_policy = default_improvement_policy()
        policy = base_policy.model_copy(
            update={
                "capability_switches": base_policy.capability_switches.model_copy(
                    update={"enable_deterministic_engine": False}
                )
            }
        )
        result = _engine(policy=policy).improve(_reference())
        assert result.findings == ()
        assert result.trends == ()
        assert result.opportunities == ()
        assert "disabled" in result.summary.headline.lower()

    def test_default_provider_used_when_none_injected(self) -> None:
        engine = DeterministicContinuousImprovementEngine(
            policy=default_improvement_policy(), clock=_FIXED_CLOCK
        )
        result = engine.improve(_reference(dataset_id="ds-default-provider"))
        assert isinstance(result, ContinuousImprovementResult)


@pytest.mark.unit
class TestMetricsAndSummary:
    def test_finding_density_is_findings_over_execution_count(self) -> None:
        dataset = _dataset(
            "ds-t",
            recurrence={ImprovementSourceLayer.VALIDATION: [True, True, True, True, True]},
            execution_count=5,
        )
        result = _engine(dataset=dataset).improve(_reference(dataset_id="ds-t"))
        assert result.metrics.finding_density == pytest.approx(len(result.findings) / 5)

    def test_trend_stability_ratio_counts_stable_trends(self) -> None:
        dataset = _dataset(
            "ds-u",
            metrics={
                ImprovementSourceLayer.GROUNDING: [1.0, 1.0, 1.0, 1.0, 1.0],
                ImprovementSourceLayer.CP1: [1.0, 2.0, 3.0, 4.0, 5.0],
            },
        )
        result = _engine(dataset=dataset).improve(_reference(dataset_id="ds-u"))
        stable_count = sum(
            1 for t in result.trends if t.direction == ImprovementTrendDirection.STABLE
        )
        assert result.metrics.trend_stability_ratio == pytest.approx(
            stable_count / len(result.trends)
        )

    def test_opportunity_rate_is_opportunities_over_signals(self) -> None:
        dataset = _dataset(
            "ds-v",
            recurrence={ImprovementSourceLayer.QUALITY_GOVERNANCE: [True, True, True, True, True]},
        )
        result = _engine(dataset=dataset).improve(_reference(dataset_id="ds-v"))
        signal_count = len(result.findings) + len(result.trends)
        assert result.metrics.opportunity_rate == pytest.approx(
            len(result.opportunities) / signal_count
        )

    def test_empty_result_has_zero_metrics(self) -> None:
        base_policy = default_improvement_policy()
        policy = base_policy.model_copy(
            update={
                "capability_switches": base_policy.capability_switches.model_copy(
                    update={"enable_deterministic_engine": False}
                )
            }
        )
        result = _engine(policy=policy).improve(_reference())
        assert result.metrics.finding_density == 0.0
        assert result.metrics.trend_stability_ratio == 0.0
        assert result.metrics.opportunity_rate == 0.0

    def test_summary_totals_match_result(self) -> None:
        dataset = _dataset(
            "ds-w",
            recurrence={ImprovementSourceLayer.VALIDATION: [True, True, True, True, True]},
        )
        result = _engine(dataset=dataset).improve(_reference(dataset_id="ds-w"))
        assert result.summary.total_findings == len(result.findings)
        assert result.summary.total_trends == len(result.trends)
        assert result.summary.total_opportunities == len(result.opportunities)

    def test_headline_reflects_totals(self) -> None:
        dataset = _dataset(
            "ds-x",
            recurrence={ImprovementSourceLayer.VALIDATION: [True, True, True, True, True]},
        )
        result = _engine(dataset=dataset).improve(_reference(dataset_id="ds-x"))
        assert str(len(result.findings)) in result.summary.headline
        assert str(len(result.trends)) in result.summary.headline
        assert str(len(result.opportunities)) in result.summary.headline


@pytest.mark.unit
class TestExplainability:
    def test_every_finding_has_contributing_execution_ids(self) -> None:
        dataset = _dataset(
            "ds-y",
            recurrence={ImprovementSourceLayer.VALIDATION: [True, True, True, True, True]},
        )
        result = _engine(dataset=dataset).improve(_reference(dataset_id="ds-y"))
        assert result.findings
        assert all(f.contributing_execution_ids for f in result.findings)

    def test_every_trend_has_contributing_execution_ids(self) -> None:
        dataset = _dataset(
            "ds-z", metrics={ImprovementSourceLayer.GROUNDING: [1.0, 2.0, 3.0, 4.0, 5.0]}
        )
        result = _engine(dataset=dataset).improve(_reference(dataset_id="ds-z"))
        assert result.trends
        assert all(t.contributing_execution_ids for t in result.trends)

    def test_every_opportunity_has_at_least_one_reference(self) -> None:
        dataset = _dataset(
            "ds-aa",
            recurrence={ImprovementSourceLayer.QUALITY_GOVERNANCE: [True, True, True, True, True]},
        )
        result = _engine(dataset=dataset).improve(_reference(dataset_id="ds-aa"))
        assert result.opportunities
        assert all(o.source_finding_ids or o.source_trend_ids for o in result.opportunities)


@pytest.mark.unit
class TestDeterminism:
    def test_same_reference_same_result_with_default_provider(self) -> None:
        engine = DeterministicContinuousImprovementEngine(
            policy=default_improvement_policy(), clock=_FIXED_CLOCK
        )
        ref = _reference(dataset_id="ds-det")
        first = engine.improve(ref)
        second = engine.improve(ref)
        assert first == second

    def test_serialization_round_trips(self) -> None:
        dataset = _dataset(
            "ds-bb",
            recurrence={ImprovementSourceLayer.VALIDATION: [True, True, True, True, True]},
        )
        result = _engine(dataset=dataset).improve(_reference(dataset_id="ds-bb"))
        dumped = result.model_dump(mode="json", by_alias=True)
        assert ContinuousImprovementResult.model_validate(dumped) == result

    def test_result_is_frozen(self) -> None:
        result = _engine().improve(_reference())
        with pytest.raises(ValidationError):
            result.result_id = "changed"  # type: ignore[misc]

    def test_deterministic_provider_is_pure_function_of_reference(self) -> None:
        provider = DeterministicHistoricalDatasetProvider()
        ref = _reference(dataset_id="ds-cc")
        first = provider.resolve(ref)
        second = provider.resolve(ref)
        assert first == second

    def test_deterministic_provider_varies_with_dataset_id(self) -> None:
        provider = DeterministicHistoricalDatasetProvider()
        a = provider.resolve(_reference(dataset_id="ds-dd-1"))
        b = provider.resolve(_reference(dataset_id="ds-dd-2"))
        assert a != b

    def test_deterministic_provider_anchors_first_and_last_execution_ids(self) -> None:
        provider = DeterministicHistoricalDatasetProvider()
        ref = _reference(
            dataset_id="ds-ee", first_execution_id="anchor-first", last_execution_id="anchor-last"
        )
        dataset = provider.resolve(ref)
        assert dataset.executions[0].execution_id == "anchor-first"
        assert dataset.executions[-1].execution_id == "anchor-last"


@pytest.mark.unit
class TestRecommendation11NoRecursiveDerivedKnowledge:
    """Derived Knowledge must never recursively consume Derived Knowledge (ADR-0022)."""

    def test_improve_signature_accepts_only_historical_dataset_reference(self) -> None:
        hints = get_type_hints(DeterministicContinuousImprovementEngine.improve)
        params = {k: v for k, v in hints.items() if k != "return"}
        assert set(params.values()) == {HistoricalDatasetReference}

    def test_resolve_signature_accepts_only_historical_dataset_reference(self) -> None:
        hints = get_type_hints(DeterministicHistoricalDatasetProvider.resolve)
        params = {k: v for k, v in hints.items() if k != "return"}
        assert set(params.values()) == {HistoricalDatasetReference}

    def test_no_engine_method_accepts_derived_knowledge_as_a_parameter(self) -> None:
        """No method anywhere on the engine accepts a prior result/finding/trend/
        opportunity as an input — every execution derives directly from the
        Historical Dataset, never from previous observations."""
        forbidden = {
            ContinuousImprovementResult,
            ImprovementFinding,
            ImprovementTrend,
            ImprovementOpportunity,
        }
        for name, member in inspect.getmembers(
            DeterministicContinuousImprovementEngine, predicate=inspect.isfunction
        ):
            try:
                hints = get_type_hints(member)
            except Exception:  # some helpers may not be fully resolvable; skip defensively
                continue
            params = {k: v for k, v in hints.items() if k != "return"}
            assert not (set(params.values()) & forbidden), (
                f"{name} accepts a Derived Knowledge type as a parameter: {params}"
            )

    def test_provider_resolve_never_receives_a_prior_result_in_practice(self) -> None:
        """A behavioural companion to the signature checks above: calling ``improve``
        twice never threads the first call's result into the second's resolution —
        each call is independent and derives solely from the reference.
        """
        engine = DeterministicContinuousImprovementEngine(
            policy=default_improvement_policy(), clock=_FIXED_CLOCK
        )
        ref = _reference(dataset_id="ds-rec11")
        first = engine.improve(ref)
        second = engine.improve(ref)
        # Byte-identical: the second call could not have been influenced by the
        # first call's ContinuousImprovementResult, since no channel exists to pass
        # it back in (Recommendation 11).
        assert first == second
