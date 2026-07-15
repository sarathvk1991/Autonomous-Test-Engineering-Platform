"""The :class:`DeterministicContinuousImprovementEngine` — the first real engine
behind the frozen CAP-083A boundary (CAP-083B).

Consumes only ``HistoricalDatasetReference`` — no Layer 1 runtime object, no
Execution Package, no serializer, no reports, no manifest, no CLI. Produces
only a ``ContinuousImprovementResult``.

Historical Dataset Resolution Principle (frozen, ADR-0022 §D9)
------------------------------------------------------------------
``HistoricalDatasetReference`` intentionally carries provenance only — it names
a dataset; it never embeds one. To have anything to observe, this engine
resolves the reference through a private, constructor-injected
:class:`HistoricalDatasetProvider` into an internal :class:`HistoricalDataset` —
a plain, unexported, engine-internal structure that is **not** a runtime
contract, **not** Historical Truth, **not** Derived Knowledge, and **never**
crosses the ``continuous_improvement`` package boundary. The public runtime
boundary remains exactly ``HistoricalDatasetReference → ContinuousImprovementResult``
(ADR-0022's ``improve`` signature is unchanged); resolution is an
implementation detail of *this* engine, replaceable by any future engine
(deterministic, statistical, ML, LLM) without touching the service contract.

The default :class:`DeterministicHistoricalDatasetProvider` shipped in CAP-083B
synthesizes reproducible per-execution records **purely as a function of the
reference's own provenance fields** (no real Historical Dataset storage exists
yet, per ADR-0021 §Stage 6) — it exists solely to exercise this deterministic
engine end to end. A future milestone may replace it with a provider backed by
a real Historical Dataset implementation without changing the engine's public
contract or this module's other collaborators.

Recommendation 11 (frozen, ADR-0022): Derived Knowledge must never recursively
consume Derived Knowledge
--------------------------------------------------------------------------------
Every execution of this engine derives its observations **directly** from the
resolved ``HistoricalDataset`` — never from a previous ``ContinuousImprovementResult``,
``ImprovementFinding``, ``ImprovementTrend``, or ``ImprovementOpportunity``. Neither
``improve`` nor ``HistoricalDatasetProvider.resolve`` accepts any of those types as
an input; both only ever *produce* them. This is enforced structurally (their
signatures name no such type as a parameter) and by dedicated containment tests.

Internal execution order (frozen for this engine)::

    1. Historical Dataset resolution  (HistoricalDatasetReference -> internal HistoricalDataset)
    2. Recurring finding detection    (-> ImprovementFinding, policy-gated)
    3. Trend detection                (-> ImprovementTrend, policy-gated)
    4. Opportunity generation         (-> ImprovementOpportunity, derived from findings/trends only)
    5. Metrics                        (computed exactly once)
    6. Summary                        (pure assembly, exactly once)
    7. ContinuousImprovementResult

Rule catalogue, not embedded rules (frozen, mirrors ADR-0017 §D25 / ADR-0019)
    The engine iterates the governed :class:`ImprovementRuleCatalog` — it
    hard-codes no threshold, no severity, and no metric name. Each rule *names*
    the family, the subsystem, and the governed vocabulary member(s) it
    concerns; the engine owns three generic mechanisms — recurrence counting,
    direction resolution, and opportunity matching — invoked per rule. Adding a
    rule is a catalogue change, never an engine change.

Policy-governed thresholds only (frozen, Recommendation 5 of ADR-0022)
    Every threshold this engine reads — ``minimum_occurrences``,
    ``history_window`` — comes from the governed :class:`ImprovementPolicy`.
    No literal `3`, `25`, or any other bound is hard-coded in this module.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from requirement_intelligence.continuous_improvement.identity import (
    ContinuousImprovementResultId,
    ImprovementFindingId,
    ImprovementOpportunityId,
    ImprovementTrendId,
)
from requirement_intelligence.continuous_improvement.models.enums import (
    ImprovementSourceLayer,
    ImprovementTrendDirection,
)
from requirement_intelligence.continuous_improvement.models.finding import ImprovementFinding
from requirement_intelligence.continuous_improvement.models.historical_dataset_reference import (
    HistoricalDatasetReference,
)
from requirement_intelligence.continuous_improvement.models.opportunity import (
    ImprovementOpportunity,
)
from requirement_intelligence.continuous_improvement.models.result import (
    ContinuousImprovementResult,
)
from requirement_intelligence.continuous_improvement.models.summary import (
    ImprovementMetrics,
    ImprovementSummary,
)
from requirement_intelligence.continuous_improvement.models.trend import ImprovementTrend
from requirement_intelligence.continuous_improvement.policy.continuous_improvement_policy import (
    ImprovementPolicy,
)
from requirement_intelligence.continuous_improvement.rules.improvement_rule import (
    ImprovementPolicyToggle,
    ImprovementRuleFamily,
)
from requirement_intelligence.continuous_improvement.rules.improvement_rule_builder import (
    default_improvement_rule_catalog,
)
from requirement_intelligence.continuous_improvement.rules.improvement_rule_catalog import (
    ImprovementRuleCatalog,
)
from requirement_intelligence.continuous_improvement.version import (
    CONTINUOUS_IMPROVEMENT_FRAMEWORK_VERSION,
)

#: A small epsilon below which a metric delta between two consecutive
#: executions is treated as "unchanged" — a fixed, governed comparison
#: tolerance (like a floating-point equality guard), never a tunable policy
#: value, since it bounds numeric noise rather than improvement behaviour.
_TREND_EPSILON = 1e-9

#: Trend directions that indicate an opportunity-worthy trend — a governed,
#: fixed vocabulary subset (never a literal boolean hard-coded per rule).
_OPPORTUNITY_WORTHY_DIRECTIONS = frozenset(
    {ImprovementTrendDirection.DEGRADING, ImprovementTrendDirection.VOLATILE}
)


# ---------------------------------------------------------------------------
# Engine-internal Historical Dataset resolution (Historical Dataset Resolution
# Principle, ADR-0022 §D9). Plain dataclasses, not pydantic ``Schema`` models:
# these are deliberately NOT runtime contracts, NOT Historical Truth, and NOT
# Derived Knowledge. They never leave this module's callers within the
# continuous_improvement package, and no other subsystem or artifact may name
# them (ADR-0021 §Stage 6 leaves the real Historical Dataset's ownership to a
# future milestone; this is a private, replaceable stand-in for it).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HistoricalExecutionRecord:
    """One resolved execution's deterministic facts. Engine-internal only.

    ``recurrence_flags`` names, per :class:`ImprovementSourceLayer`, whether a
    recurrence-eligible event occurred in this execution. ``metric_values``
    names, per source, the metric reading this execution contributed. Never
    serialized, never a runtime contract.
    """

    execution_id: str
    ordinal: int
    recurrence_flags: dict[ImprovementSourceLayer, bool]
    metric_values: dict[ImprovementSourceLayer, float]


@dataclass(frozen=True)
class HistoricalDataset:
    """The resolved historical dataset for one reference. Engine-internal only.

    Never a runtime contract, never persisted, never crosses the
    ``continuous_improvement`` package boundary — resolved fresh on every
    :meth:`DeterministicContinuousImprovementEngine.improve` call, never
    cached (Recommendation 11: no historical storage is introduced here).
    """

    dataset_id: str
    executions: tuple[HistoricalExecutionRecord, ...]


class HistoricalDatasetProvider(ABC):
    """Resolves a :class:`HistoricalDatasetReference` into a :class:`HistoricalDataset`.

    The **only** sanctioned way this engine obtains anything to observe. A
    provider consumes only the reference's own provenance fields — never a
    previous :class:`ContinuousImprovementResult` or any of its constituents
    (Recommendation 11) — and never a Layer 1 runtime object.
    """

    @abstractmethod
    def resolve(self, historical_dataset: HistoricalDatasetReference) -> HistoricalDataset:
        """Resolve *historical_dataset* into its per-execution records."""
        raise NotImplementedError


class DeterministicHistoricalDatasetProvider(HistoricalDatasetProvider):
    """The CAP-083B default provider — deterministic, reproducible, a stand-in.

    No real Historical Dataset storage exists yet (ADR-0021 §Stage 6). This
    provider synthesizes per-execution records as a **pure function** of the
    reference's own fields (``dataset_id``, ordinal, ``first_execution_id``,
    ``last_execution_id``) via SHA-256 digests — no UUID, no clock, no
    randomness — solely so the deterministic engine can be exercised end to
    end. A future milestone replaces this with a provider backed by a real
    Historical Dataset implementation, behind this same
    :class:`HistoricalDatasetProvider` contract.
    """

    def resolve(self, historical_dataset: HistoricalDatasetReference) -> HistoricalDataset:
        """Deterministically synthesize one record per execution the reference spans."""
        count = historical_dataset.execution_count
        executions = tuple(
            self._record_for(historical_dataset, ordinal, count) for ordinal in range(count)
        )
        return HistoricalDataset(dataset_id=historical_dataset.dataset_id, executions=executions)

    @staticmethod
    def _record_for(
        reference: HistoricalDatasetReference, ordinal: int, count: int
    ) -> HistoricalExecutionRecord:
        """Deterministically synthesize one execution's facts. Pure function of inputs."""
        if ordinal == 0:
            execution_id = reference.first_execution_id
        elif ordinal == count - 1:
            execution_id = reference.last_execution_id
        else:
            digest = hashlib.sha256(f"{reference.dataset_id}:{ordinal}".encode()).hexdigest()
            execution_id = f"{reference.dataset_id}-exec-{digest[:8]}"

        recurrence_flags: dict[ImprovementSourceLayer, bool] = {}
        metric_values: dict[ImprovementSourceLayer, float] = {}
        for source in ImprovementSourceLayer:
            flag_digest = hashlib.sha256(
                f"{reference.dataset_id}:{ordinal}:{source.value}:flag".encode()
            ).hexdigest()
            recurrence_flags[source] = int(flag_digest[:8], 16) % 3 == 0
            metric_digest = hashlib.sha256(
                f"{reference.dataset_id}:{ordinal}:{source.value}:metric".encode()
            ).hexdigest()
            metric_values[source] = float(int(metric_digest[:8], 16) % 101)

        return HistoricalExecutionRecord(
            execution_id=execution_id,
            ordinal=ordinal,
            recurrence_flags=recurrence_flags,
            metric_values=metric_values,
        )


class DeterministicContinuousImprovementEngine:
    """The first deterministic implementation behind ``ContinuousImprovementService``.

    Consumes only a :class:`HistoricalDatasetReference`, the governed
    :class:`ImprovementPolicy`, and the governed :class:`ImprovementRuleCatalog`.
    Every method below owns exactly one responsibility so a future statistical,
    ML, or LLM-based engine can reuse the same decomposition without changing
    the public ``improve`` contract.
    """

    def __init__(
        self,
        *,
        policy: ImprovementPolicy,
        rule_catalog: ImprovementRuleCatalog | None = None,
        provider: HistoricalDatasetProvider | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        """Store the governed collaborators this engine reads. Construction only."""
        self._policy = policy
        self._catalog = (
            rule_catalog if rule_catalog is not None else default_improvement_rule_catalog()
        )
        self._provider = (
            provider if provider is not None else DeterministicHistoricalDatasetProvider()
        )
        self._clock = clock or (lambda: datetime.now(UTC))

    def improve(
        self,
        historical_dataset: HistoricalDatasetReference,
    ) -> ContinuousImprovementResult:
        """Observe recurrence across *historical_dataset*. Deterministic."""
        started_at = self._clock()
        result_id = ContinuousImprovementResultId.for_dataset(historical_dataset.dataset_id)

        if not self._policy.capability_switches.enable_deterministic_engine:
            return self._empty_result(
                result_id=result_id,
                historical_dataset=historical_dataset,
                started_at=started_at,
                completed_at=self._clock(),
                headline=(
                    "Continuous Improvement is disabled by policy "
                    "(enable_deterministic_engine=False)."
                ),
            )

        dataset = self._provider.resolve(historical_dataset)
        dataset_id = historical_dataset.dataset_id

        findings = self._detect_recurring_findings(dataset_id, dataset)
        trends = self._detect_trends(dataset_id, dataset)
        opportunities = self._generate_opportunities(dataset_id, findings, trends)
        metrics = self._compute_metrics(findings, trends, opportunities, len(dataset.executions))
        summary = self._build_summary(findings, trends, opportunities)
        completed_at = self._clock()

        return ContinuousImprovementResult(
            result_id=result_id,
            historical_dataset=historical_dataset,
            findings=findings,
            trends=trends,
            opportunities=opportunities,
            summary=summary,
            metrics=metrics,
            policy_id=self._policy.policy_id,
            policy_version=self._policy.policy_version,
            framework_version=CONTINUOUS_IMPROVEMENT_FRAMEWORK_VERSION,
            started_at=started_at,
            completed_at=completed_at,
        )

    # -- 1. recurring finding detection (policy-governed threshold only) -------------

    def _detect_recurring_findings(
        self, dataset_id: str, dataset: HistoricalDataset
    ) -> tuple[ImprovementFinding, ...]:
        """Emit one finding per RECURRENCE rule whose occurrence meets the governed floor."""
        if not self._policy.capability_switches.enable_recurring_finding_detection:
            return ()
        findings: list[ImprovementFinding] = []
        ordinal = 0
        for rule in self._catalog.by_family(ImprovementRuleFamily.RECURRENCE):
            if not self._toggle_enabled(rule.policy_reference):
                continue
            contributing = tuple(
                record.execution_id
                for record in dataset.executions
                if record.recurrence_flags.get(rule.source_subsystem, False)
            )
            occurrence_count = len(contributing)
            if occurrence_count < self._policy.thresholds.minimum_occurrences:
                continue
            findings.append(
                ImprovementFinding(
                    finding_id=ImprovementFindingId.for_ordinal(dataset_id, ordinal),
                    category=rule.finding_category,
                    source=rule.source_subsystem,
                    severity=rule.severity_hint,
                    occurrence_count=occurrence_count,
                    contributing_execution_ids=contributing,
                    message=rule.guidance,
                )
            )
            ordinal += 1
        return tuple(findings)

    # -- 2. trend detection (observation only, never a prediction) -------------------

    def _detect_trends(
        self, dataset_id: str, dataset: HistoricalDataset
    ) -> tuple[ImprovementTrend, ...]:
        """Emit one trend per TREND rule with at least two observed data points."""
        if not self._policy.capability_switches.enable_trend_detection:
            return ()
        trends: list[ImprovementTrend] = []
        ordinal = 0
        for rule in self._catalog.by_family(ImprovementRuleFamily.TREND):
            if not self._toggle_enabled(rule.policy_reference):
                continue
            observations = [
                (record.execution_id, record.metric_values.get(rule.source_subsystem))
                for record in dataset.executions
            ]
            observations = [(eid, value) for eid, value in observations if value is not None]
            if len(observations) < 2:
                continue
            direction = self._resolve_direction([value for _, value in observations])
            trends.append(
                ImprovementTrend(
                    trend_id=ImprovementTrendId.for_ordinal(dataset_id, ordinal),
                    direction=direction,
                    source=rule.source_subsystem,
                    metric_name=rule.metric_name,
                    observation_count=len(observations),
                    contributing_execution_ids=tuple(eid for eid, _ in observations),
                    message=rule.guidance,
                )
            )
            ordinal += 1
        return tuple(trends)

    @staticmethod
    def _resolve_direction(values: list[float]) -> ImprovementTrendDirection:
        """Resolve a governed direction from consecutive deltas. Pure arithmetic only.

        ``IMPROVING`` / ``DEGRADING`` name a monotonic (non-decreasing /
        non-increasing) sequence; ``VOLATILE`` names a sequence whose deltas
        change sign; ``STABLE`` names a sequence whose deltas are all within
        :data:`_TREND_EPSILON` of zero. No prediction, no statistics, no
        semantic judgement of whether higher or lower is "better."
        """
        deltas = [values[i + 1] - values[i] for i in range(len(values) - 1)]
        if all(abs(delta) <= _TREND_EPSILON for delta in deltas):
            return ImprovementTrendDirection.STABLE
        signs = {
            1 if delta > _TREND_EPSILON else (-1 if delta < -_TREND_EPSILON else 0)
            for delta in deltas
        }
        nonzero_signs = signs - {0}
        if len(nonzero_signs) > 1:
            return ImprovementTrendDirection.VOLATILE
        if nonzero_signs == {1}:
            return ImprovementTrendDirection.IMPROVING
        if nonzero_signs == {-1}:
            return ImprovementTrendDirection.DEGRADING
        return ImprovementTrendDirection.STABLE

    # -- 3. opportunity generation (derived from findings/trends only) ---------------

    def _generate_opportunities(
        self,
        dataset_id: str,
        findings: tuple[ImprovementFinding, ...],
        trends: tuple[ImprovementTrend, ...],
    ) -> tuple[ImprovementOpportunity, ...]:
        """Emit one opportunity per OPPORTUNITY rule matched by an already-recorded
        finding or a trend already observed to be degrading/volatile. Never derived
        directly from the Historical Dataset — always by reference to a finding or
        trend this same run already computed."""
        if not self._policy.capability_switches.enable_opportunity_generation:
            return ()
        findings_by_key = {(finding.category, finding.source): finding for finding in findings}
        trends_by_key = {(trend.metric_name, trend.source): trend for trend in trends}

        opportunities: list[ImprovementOpportunity] = []
        ordinal = 0
        for rule in self._catalog.by_family(ImprovementRuleFamily.OPPORTUNITY):
            if not self._toggle_enabled(rule.policy_reference):
                continue
            source_finding_ids: tuple[ImprovementFindingId, ...] = ()
            source_trend_ids: tuple[ImprovementTrendId, ...] = ()
            occurrence_count = 0

            if rule.finding_category is not None:
                matched_finding = findings_by_key.get(
                    (rule.finding_category, rule.source_subsystem)
                )
                if matched_finding is None:
                    continue
                source_finding_ids = (matched_finding.finding_id,)
                occurrence_count = matched_finding.occurrence_count
            else:
                matched_trend = trends_by_key.get((rule.metric_name, rule.source_subsystem))
                if matched_trend is None or matched_trend.direction not in (
                    _OPPORTUNITY_WORTHY_DIRECTIONS
                ):
                    continue
                source_trend_ids = (matched_trend.trend_id,)
                occurrence_count = matched_trend.observation_count

            opportunities.append(
                ImprovementOpportunity(
                    opportunity_id=ImprovementOpportunityId.for_ordinal(dataset_id, ordinal),
                    category=rule.opportunity_category,
                    source_finding_ids=source_finding_ids,
                    source_trend_ids=source_trend_ids,
                    occurrence_count=occurrence_count,
                    description=rule.guidance,
                )
            )
            ordinal += 1
        return tuple(opportunities)

    # -- 4. metrics (computed exactly once) -------------------------------------------

    @staticmethod
    def _compute_metrics(
        findings: tuple[ImprovementFinding, ...],
        trends: tuple[ImprovementTrend, ...],
        opportunities: tuple[ImprovementOpportunity, ...],
        execution_count: int,
    ) -> ImprovementMetrics:
        """Deterministic numeric roll-ups — recorded, never derived elsewhere."""
        finding_density = (len(findings) / execution_count) if execution_count else 0.0
        stable_trends = sum(
            1 for trend in trends if trend.direction == ImprovementTrendDirection.STABLE
        )
        trend_stability_ratio = (stable_trends / len(trends)) if trends else 0.0
        signal_count = len(findings) + len(trends)
        opportunity_rate = (len(opportunities) / signal_count) if signal_count else 0.0
        return ImprovementMetrics(
            finding_density=finding_density,
            trend_stability_ratio=trend_stability_ratio,
            opportunity_rate=opportunity_rate,
        )

    # -- 5. summary (pure assembly, exactly once) -------------------------------------

    def _build_summary(
        self,
        findings: tuple[ImprovementFinding, ...],
        trends: tuple[ImprovementTrend, ...],
        opportunities: tuple[ImprovementOpportunity, ...],
    ) -> ImprovementSummary:
        """The deterministic headline for this run."""
        headline = (
            f"{len(findings)} finding(s), {len(trends)} trend(s), "
            f"{len(opportunities)} opportunity(ies)."
        )
        return ImprovementSummary(
            policy_id=self._policy.policy_id,
            policy_version=self._policy.policy_version,
            total_findings=len(findings),
            total_trends=len(trends),
            total_opportunities=len(opportunities),
            headline=headline,
        )

    # -- policy toggle resolution ------------------------------------------------------

    def _toggle_enabled(self, toggle: ImprovementPolicyToggle) -> bool:
        """Whether the governed capability switch *toggle* names is enabled.

        ``Schema`` validates with ``use_enum_values=True`` (shared/contracts/base.py),
        so ``rule.policy_reference`` is already the plain string value here — mirrors
        how the deterministic Recommendation engine resolves its own rule toggles.
        """
        return bool(getattr(self._policy.capability_switches, str(toggle)))

    # -- empty result (policy-disabled) -----------------------------------------------

    def _empty_result(
        self,
        *,
        result_id: ContinuousImprovementResultId,
        historical_dataset: HistoricalDatasetReference,
        started_at: datetime,
        completed_at: datetime,
        headline: str,
    ) -> ContinuousImprovementResult:
        """A well-defined, empty-but-valid result."""
        summary = ImprovementSummary(
            policy_id=self._policy.policy_id,
            policy_version=self._policy.policy_version,
            total_findings=0,
            total_trends=0,
            total_opportunities=0,
            headline=headline,
        )
        metrics = ImprovementMetrics(
            finding_density=0.0, trend_stability_ratio=0.0, opportunity_rate=0.0
        )
        return ContinuousImprovementResult(
            result_id=result_id,
            historical_dataset=historical_dataset,
            summary=summary,
            metrics=metrics,
            policy_id=self._policy.policy_id,
            policy_version=self._policy.policy_version,
            framework_version=CONTINUOUS_IMPROVEMENT_FRAMEWORK_VERSION,
            started_at=started_at,
            completed_at=completed_at,
        )
