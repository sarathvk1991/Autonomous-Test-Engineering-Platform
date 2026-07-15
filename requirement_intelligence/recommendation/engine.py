"""The :class:`DeterministicRecommendationEngine` — the first real engine behind the
frozen CAP-082A boundary (CAP-082B).

Consumes only the five completed upstream runtime contracts —
``RequirementEnhancementResult``, ``GroundingResult``, ``ValidationResult``,
``CP1Result``, ``QualityGovernanceResult`` — the governed ``RecommendationPolicy``,
and the governed ``RecommendationRuleCatalog``. Produces only a
``RecommendationResult``. It never performs enhancement, grounding, validation,
CP1, or quality governance, and never imports an upstream *implementation* class
(Recommendation 1).

Internal execution order (frozen for this engine)::

    1. Candidate collection   (one candidate per governed piece of upstream evidence,
                               matched to a RecommendationRule by category — Recommendation 2)
    2. Confidence surfacing   (drop candidates below the governed confidence floor)
    3. Priority resolution    (policy-derived only — Recommendation 9)
    4. Recommendation assembly (references, never copies — Recommendation 4)
    5. Grouping               (ordering/categorization only — Recommendation 6)
    6. Metrics                (computed exactly once — Recommendation 5 of this stage)
    7. Summary                (pure assembly, exactly once)
    8. RecommendationResult

Rule catalogue, not embedded rules (frozen, mirrors ADR-0017 §D25)
    The engine iterates the governed :class:`RecommendationRuleCatalog` — it
    hard-codes no priority, no effort, and no confidence. Each rule *names* the
    category of evidence it covers, the action it suggests, and the governed hints a
    matching recommendation carries. The engine owns exactly one generic mechanism —
    classifying a piece of upstream evidence into a :class:`RecommendationRuleCategory`
    — invoked per candidate; it contains no per-recommendation priority decision.
    Adding a rule is a catalogue change, never an engine change.

Policy-derived priority only (frozen, Recommendation 9)
    A recommendation's final ``priority`` is always the matched rule's
    ``priority_hint``, optionally clamped and capped by the governed
    ``PrioritizationRules`` (``enabled_priorities``, ``max_recommendations_per_priority``).
    The engine never branches on ``recommendation_source`` or ``recommendation_type``
    to decide a priority — a Quality Governance recommendation is not automatically
    HIGH, and neither is a Grounding recommendation.

Explainability (frozen, Recommendation 7)
    Every :class:`Recommendation` carries exactly one :class:`RecommendationReference`
    naming the upstream evidence it was derived from — an id and a contract version,
    never a copy of the evidence's content (Recommendation 2/4). ``title`` and
    ``description`` come entirely from the matched rule's governed metadata
    (``rule_name`` / ``guidance``); ``rationale`` names only the reference id, never
    the evidence's message text.

Consumer only (frozen, Recommendation 1)
    ``recommend`` consumes only the five completed upstream results — never
    re-running Requirement Enhancement, Grounding, Validation, CP1, or Quality
    Governance, and never importing an upstream implementation class.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from requirement_intelligence.cp1.models.cp1_finding import CP1Finding
from requirement_intelligence.cp1.models.cp1_result import CP1Result
from requirement_intelligence.enhancement.models.enums import (
    EnhancementSeverity,
    ObservationCategory,
)
from requirement_intelligence.enhancement.models.observations import EnhancementFinding
from requirement_intelligence.enhancement.models.result import RequirementEnhancementResult
from requirement_intelligence.grounding.models.assessment import GroundingResult
from requirement_intelligence.grounding.models.enums import SupportClassification
from requirement_intelligence.grounding.models.findings import GroundingFinding
from requirement_intelligence.quality_governance.models.enums import (
    QualityDecision,
    QualitySeverity,
)
from requirement_intelligence.quality_governance.models.findings import QualityFinding
from requirement_intelligence.quality_governance.models.result import QualityGovernanceResult
from requirement_intelligence.recommendation.identity.recommendation_identity import (
    RecommendationGroupId,
    RecommendationId,
    RecommendationResultId,
)
from requirement_intelligence.recommendation.models.enums import (
    RecommendationPriority,
    RecommendationSource,
    RecommendationType,
)
from requirement_intelligence.recommendation.models.group import RecommendationGroup
from requirement_intelligence.recommendation.models.recommendation import (
    Recommendation,
    RecommendationReference,
)
from requirement_intelligence.recommendation.models.result import (
    RecommendationInputReference,
    RecommendationResult,
)
from requirement_intelligence.recommendation.models.summary import (
    RecommendationMetrics,
    RecommendationPriorityCount,
    RecommendationSummary,
)
from requirement_intelligence.recommendation.policy.recommendation_policy import (
    RecommendationPolicy,
)
from requirement_intelligence.recommendation.rules.recommendation_rule import (
    RecommendationRule,
    RecommendationRuleCategory,
)
from requirement_intelligence.recommendation.rules.recommendation_rule_builder import (
    default_recommendation_rule_catalog,
)
from requirement_intelligence.recommendation.rules.recommendation_rule_catalog import (
    RecommendationRuleCatalog,
)
from requirement_intelligence.recommendation.version import RECOMMENDATION_FRAMEWORK_VERSION
from requirement_intelligence.validation.models.validation_enums import ValidationSeverity
from requirement_intelligence.validation.models.validation_issue import ValidationIssue
from requirement_intelligence.validation.models.validation_result import ValidationResult
from shared.enums.base import ValidationVerdict as CP1Verdict

#: The governed dispatch order every candidate stream is collected in — a fixed,
#: documented order (never a source-conditioned priority), so recommendation ids are
#: a pure, reproducible function of the execution id and a candidate's position.
_PRIORITY_ORDER: tuple[RecommendationPriority, ...] = (
    RecommendationPriority.LOW,
    RecommendationPriority.MEDIUM,
    RecommendationPriority.HIGH,
    RecommendationPriority.CRITICAL,
)

#: A deterministic, governed label for each recommendation type's group — descriptive
#: data only, never computed or AI-generated.
_GROUP_LABELS: dict[RecommendationType, str] = {
    RecommendationType.ADD_REQUIREMENT: "Add Missing Requirements",
    RecommendationType.CLARIFY_REQUIREMENT: "Clarify Requirements",
    RecommendationType.RESOLVE_DUPLICATE: "Resolve Duplicates",
    RecommendationType.RESOLVE_DEPENDENCY: "Resolve Dependencies",
    RecommendationType.RESOLVE_CONFLICT: "Resolve Conflicts",
    RecommendationType.STRENGTHEN_EVIDENCE: "Strengthen Evidence",
    RecommendationType.ADDRESS_VALIDATION_ISSUE: "Address Validation Issues",
    RecommendationType.ADDRESS_ENGINEERING_GAP: "Address Engineering Gaps",
    RecommendationType.IMPROVE_QUALITY_SCORE: "Improve Quality Score",
}


@dataclass(frozen=True)
class _Candidate:
    """One piece of upstream evidence matched to a governed rule. Internal only."""

    ordinal: int
    rule: RecommendationRule
    source: RecommendationSource
    referenced_id: str
    referenced_version: str


class DeterministicRecommendationEngine:
    """The first deterministic implementation behind ``RecommendationService``.

    Consumes only the five completed upstream results, the governed
    ``RecommendationPolicy``, and the governed ``RecommendationRuleCatalog``. Every
    method below owns exactly one responsibility so a future statistical, ML, or
    LLM-based engine can reuse the same decomposition without changing the public
    ``recommend`` contract.
    """

    def __init__(
        self,
        *,
        policy: RecommendationPolicy,
        rule_catalog: RecommendationRuleCatalog | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        """Store the governed collaborators this engine reads. Construction only."""
        self._policy = policy
        self._catalog = (
            rule_catalog if rule_catalog is not None else default_recommendation_rule_catalog()
        )
        self._clock = clock or (lambda: datetime.now(UTC))

    def recommend(
        self,
        enhancement_result: RequirementEnhancementResult,
        grounding_result: GroundingResult,
        validation_result: ValidationResult,
        cp1_result: CP1Result,
        quality_governance_result: QualityGovernanceResult,
    ) -> RecommendationResult:
        """Recommend actions from the five completed upstream results. Deterministic."""
        started_at = self._clock()
        execution_id = enhancement_result.execution_id
        analysis_id = enhancement_result.analysis_id
        result_id = RecommendationResultId.for_execution(execution_id)
        consumed_inputs = self._consumed_inputs(
            enhancement_result,
            grounding_result,
            validation_result,
            cp1_result,
            quality_governance_result,
        )

        if not self._policy.capability_switches.enable_deterministic_engine:
            return self._empty_result(
                result_id=result_id,
                analysis_id=analysis_id,
                execution_id=execution_id,
                consumed_inputs=consumed_inputs,
                started_at=started_at,
                completed_at=self._clock(),
                headline=(
                    "Recommendation generation is disabled by policy "
                    "(enable_deterministic_engine=False)."
                ),
            )

        candidates = self._collect_candidates(
            enhancement_result,
            grounding_result,
            validation_result,
            cp1_result,
            quality_governance_result,
        )
        surfaced = self._apply_confidence(candidates)
        if not surfaced:
            return self._empty_result(
                result_id=result_id,
                analysis_id=analysis_id,
                execution_id=execution_id,
                consumed_inputs=consumed_inputs,
                started_at=started_at,
                completed_at=self._clock(),
                headline="No recommendation cleared the governed confidence floor.",
            )

        priorities = self._resolve_priorities(surfaced)
        recommendations = self._build_recommendations(execution_id, surfaced, priorities)
        groups = self._build_groups(execution_id, recommendations)
        metrics = self._compute_metrics(recommendations, groups)
        summary = self._build_summary(recommendations, groups)
        completed_at = self._clock()

        return RecommendationResult(
            result_id=result_id,
            analysis_id=analysis_id,
            execution_id=execution_id,
            recommendations=recommendations,
            groups=groups,
            summary=summary,
            metrics=metrics,
            consumed_inputs=consumed_inputs,
            policy_id=self._policy.policy_id,
            policy_version=self._policy.policy_version,
            framework_version=RECOMMENDATION_FRAMEWORK_VERSION,
            started_at=started_at,
            completed_at=completed_at,
        )

    # -- 1. candidate collection (evidence matched to a rule by category only) ---------

    def _collect_candidates(
        self,
        enhancement_result: RequirementEnhancementResult,
        grounding_result: GroundingResult,
        validation_result: ValidationResult,
        cp1_result: CP1Result,
        quality_governance_result: QualityGovernanceResult,
    ) -> list[_Candidate]:
        """Collect one candidate per piece of governed upstream evidence, in fixed order."""
        candidates: list[_Candidate] = []
        ordinal = 0

        def add(
            category: RecommendationRuleCategory | None,
            source: RecommendationSource,
            referenced_id: str,
            referenced_version: str,
        ) -> None:
            nonlocal ordinal
            if category is None:
                return
            rule = self._catalog.rule_for_category(category)
            if rule is None:
                return
            candidates.append(
                _Candidate(
                    ordinal=ordinal,
                    rule=rule,
                    source=source,
                    referenced_id=referenced_id,
                    referenced_version=referenced_version,
                )
            )
            ordinal += 1

        enhancement_version = str(enhancement_result.result_version)
        for finding in enhancement_result.findings:
            add(
                self._enhancement_category(finding),
                RecommendationSource.ENHANCEMENT,
                finding.finding_id,
                enhancement_version,
            )

        grounding_version = str(grounding_result.result_version)
        for finding in grounding_result.assessment.findings:
            add(
                self._grounding_category(finding),
                RecommendationSource.GROUNDING,
                finding.finding_id,
                grounding_version,
            )

        validation_version = validation_result.validation_framework_metadata.framework_version
        for issue in validation_result.validation_issues:
            add(
                self._validation_category(issue),
                RecommendationSource.VALIDATION,
                issue.issue_id,
                validation_version,
            )

        cp1_version = cp1_result.cp1_result_version
        for finding in cp1_result.findings:
            add(
                self._cp1_category(finding),
                RecommendationSource.CP1,
                finding.finding_id,
                cp1_version,
            )

        quality_version = str(quality_governance_result.result_version)
        assessment = quality_governance_result.assessment
        for finding in assessment.findings:
            add(
                self._quality_finding_category(finding),
                RecommendationSource.QUALITY_GOVERNANCE,
                finding.finding_id,
                quality_version,
            )
        add(
            self._quality_decision_category(assessment.decision),
            RecommendationSource.QUALITY_GOVERNANCE,
            str(assessment.assessment_id),
            quality_version,
        )

        return candidates

    @staticmethod
    def _enhancement_category(finding: EnhancementFinding) -> RecommendationRuleCategory | None:
        """Classify one surfaced enhancement finding — dispatch only, no priority decided."""
        category = ObservationCategory(finding.category)
        if category == ObservationCategory.DEPENDENCY:
            return RecommendationRuleCategory.ENHANCEMENT_DEPENDENCY_GAP
        if category == ObservationCategory.DUPLICATION:
            return RecommendationRuleCategory.ENHANCEMENT_DUPLICATE_REQUIREMENT
        if category == ObservationCategory.CONSISTENCY:
            severity = EnhancementSeverity(finding.severity)
            if severity == EnhancementSeverity.CRITICAL:
                return RecommendationRuleCategory.ENHANCEMENT_CONSISTENCY_CRITICAL
            return RecommendationRuleCategory.ENHANCEMENT_CONSISTENCY_WARNING
        if category == ObservationCategory.TRACEABILITY:
            return RecommendationRuleCategory.ENHANCEMENT_TRACEABILITY_GAP
        return None  # COMPLETENESS / ADVISORY: no governed rule covers these yet.

    @staticmethod
    def _grounding_category(finding: GroundingFinding) -> RecommendationRuleCategory | None:
        """Classify one grounding finding — dispatch only, no priority decided."""
        classification = SupportClassification(finding.classification)
        if classification == SupportClassification.UNSUPPORTED:
            return RecommendationRuleCategory.GROUNDING_UNSUPPORTED
        if classification == SupportClassification.CONTRADICTED:
            return RecommendationRuleCategory.GROUNDING_CONTRADICTED
        return None

    @staticmethod
    def _validation_category(issue: ValidationIssue) -> RecommendationRuleCategory:
        """Classify one validation issue by its governed severity — dispatch only."""
        severity = ValidationSeverity(issue.severity)
        return {
            ValidationSeverity.INFO: RecommendationRuleCategory.VALIDATION_ISSUE_INFO,
            ValidationSeverity.WARNING: RecommendationRuleCategory.VALIDATION_ISSUE_WARNING,
            ValidationSeverity.ERROR: RecommendationRuleCategory.VALIDATION_ISSUE_ERROR,
            ValidationSeverity.CRITICAL: RecommendationRuleCategory.VALIDATION_ISSUE_CRITICAL,
        }[severity]

    @staticmethod
    def _cp1_category(finding: CP1Finding) -> RecommendationRuleCategory | None:
        """Classify one CP1 finding by its verdict contribution — dispatch only."""
        verdict = CP1Verdict(finding.verdict_contribution)
        if verdict == CP1Verdict.FAIL:
            return RecommendationRuleCategory.CP1_FINDING_FAIL
        if verdict == CP1Verdict.WARN:
            return RecommendationRuleCategory.CP1_FINDING_WARN
        return None  # A PASS contribution needs no recommendation.

    @staticmethod
    def _quality_finding_category(finding: QualityFinding) -> RecommendationRuleCategory:
        """Classify one quality finding by its governed severity — dispatch only."""
        severity = QualitySeverity(finding.severity)
        return {
            QualitySeverity.INFO: RecommendationRuleCategory.QUALITY_FINDING_INFO,
            QualitySeverity.WARNING: RecommendationRuleCategory.QUALITY_FINDING_WARNING,
            QualitySeverity.FAILURE: RecommendationRuleCategory.QUALITY_FINDING_FAILURE,
        }[severity]

    @staticmethod
    def _quality_decision_category(decision: QualityDecision) -> RecommendationRuleCategory | None:
        """Classify the release decision itself — dispatch only, a PASS needs no action."""
        resolved = QualityDecision(decision)
        if resolved == QualityDecision.FAIL:
            return RecommendationRuleCategory.QUALITY_DECISION_FAIL
        if resolved == QualityDecision.PASS_WITH_WARNINGS:
            return RecommendationRuleCategory.QUALITY_DECISION_PASS_WITH_WARNINGS
        return None  # PASS: no release-affecting recommendation is warranted.

    # -- 2. confidence surfacing (governed floor only, Recommendation 9 precedent) -----

    def _apply_confidence(self, candidates: list[_Candidate]) -> list[_Candidate]:
        """Drop candidates below the governed confidence floor. No score is computed."""
        if not self._policy.capability_switches.enable_confidence_scoring:
            return candidates
        floor = self._policy.confidence_rules.minimum_confidence_to_surface
        return [c for c in candidates if c.rule.confidence_hint >= floor]

    # -- 3. priority resolution (policy-derived only, Recommendation 9) ----------------

    def _resolve_priorities(self, candidates: list[_Candidate]) -> list[RecommendationPriority]:
        """Resolve each candidate's final priority from its rule hint and governed policy.

        Never branches on ``recommendation_source`` or ``recommendation_type`` — the
        only inputs are the matched rule's ``priority_hint`` (data, not a per-item
        decision) and the governed ``PrioritizationRules`` (``enabled_priorities``,
        ``max_recommendations_per_priority``).
        """
        hints = [candidate.rule.priority_hint for candidate in candidates]
        if not self._policy.capability_switches.enable_prioritization:
            return [RecommendationPriority(hint) for hint in hints]

        rules = self._policy.prioritization_rules
        enabled = tuple(p for p in _PRIORITY_ORDER if p in rules.enabled_priorities)
        if not enabled:
            enabled = _PRIORITY_ORDER

        clamped = [self._clamp_priority(RecommendationPriority(hint), enabled) for hint in hints]

        cap = rules.max_recommendations_per_priority
        counts: dict[RecommendationPriority, int] = dict.fromkeys(enabled, 0)
        resolved: list[RecommendationPriority] = []
        for priority in clamped:
            index = enabled.index(priority)
            while counts[enabled[index]] >= cap and index > 0:
                index -= 1
            settled = enabled[index]
            counts[settled] += 1
            resolved.append(settled)
        return resolved

    @staticmethod
    def _clamp_priority(
        priority: RecommendationPriority, enabled: tuple[RecommendationPriority, ...]
    ) -> RecommendationPriority:
        """Clamp *priority* to the nearest enabled priority at or below it."""
        if priority in enabled:
            return priority
        index = _PRIORITY_ORDER.index(priority)
        for candidate_index in range(index, -1, -1):
            if _PRIORITY_ORDER[candidate_index] in enabled:
                return _PRIORITY_ORDER[candidate_index]
        return enabled[0]

    # -- 4. recommendation assembly (references, never copies, Recommendation 4) ------

    @staticmethod
    def _build_recommendations(
        execution_id: str,
        candidates: list[_Candidate],
        priorities: list[RecommendationPriority],
    ) -> tuple[Recommendation, ...]:
        """Assemble one Recommendation per candidate. Title/description are rule-owned."""
        recommendations: list[Recommendation] = []
        for candidate, priority in zip(candidates, priorities, strict=True):
            rule = candidate.rule
            reference = RecommendationReference(
                source=candidate.source,
                referenced_id=candidate.referenced_id,
                referenced_version=candidate.referenced_version,
            )
            recommendations.append(
                Recommendation(
                    recommendation_id=RecommendationId.for_ordinal(execution_id, candidate.ordinal),
                    title=rule.rule_name,
                    description=rule.guidance,
                    rationale=(
                        f"{rule.rule_name}: triggered by {candidate.source.value} evidence "
                        f"'{candidate.referenced_id}'."
                    ),
                    recommendation_type=rule.recommendation_type,
                    priority=priority,
                    effort=rule.effort_hint,
                    confidence=rule.confidence_hint,
                    recommendation_source=candidate.source,
                    references=(reference,),
                )
            )
        return tuple(recommendations)

    # -- 5. grouping (ordering/categorization only, Recommendation 6) -----------------

    def _build_groups(
        self, execution_id: str, recommendations: tuple[Recommendation, ...]
    ) -> tuple[RecommendationGroup, ...]:
        """Form one group per populated, governed recommendation type. No content owned."""
        if not self._policy.capability_switches.enable_grouping:
            return ()
        rules = self._policy.grouping_rules
        groups: list[RecommendationGroup] = []
        ordinal = 0
        for recommendation_type in RecommendationType:
            if recommendation_type not in rules.enabled_categories:
                continue
            members = tuple(
                recommendation.recommendation_id
                for recommendation in recommendations
                if recommendation.recommendation_type == recommendation_type
            )
            if not members:
                continue
            groups.append(
                RecommendationGroup(
                    group_id=RecommendationGroupId.for_ordinal(execution_id, ordinal),
                    category=recommendation_type,
                    label=_GROUP_LABELS[RecommendationType(recommendation_type)],
                    recommendation_ids=members[: rules.max_recommendations_per_group],
                )
            )
            ordinal += 1
        return tuple(groups)

    # -- 6. metrics (computed exactly once) --------------------------------------------

    @staticmethod
    def _compute_metrics(
        recommendations: tuple[Recommendation, ...], groups: tuple[RecommendationGroup, ...]
    ) -> RecommendationMetrics:
        """Deterministic numeric roll-ups — recorded, never derived elsewhere."""
        total = len(recommendations)
        density = (total / len(groups)) if groups else 0.0
        average_confidence = (
            sum(recommendation.confidence for recommendation in recommendations) / total
            if total
            else 0.0
        )
        high_priority = sum(
            1
            for recommendation in recommendations
            if RecommendationPriority(recommendation.priority)
            in (RecommendationPriority.HIGH, RecommendationPriority.CRITICAL)
        )
        high_priority_ratio = (high_priority / total) if total else 0.0
        return RecommendationMetrics(
            recommendation_density=density,
            average_confidence=average_confidence,
            high_priority_ratio=high_priority_ratio,
        )

    # -- 7. summary (pure assembly, exactly once) --------------------------------------

    def _build_summary(
        self, recommendations: tuple[Recommendation, ...], groups: tuple[RecommendationGroup, ...]
    ) -> RecommendationSummary:
        """The deterministic headline for this run."""
        counts: Counter[RecommendationPriority] = Counter(
            RecommendationPriority(recommendation.priority) for recommendation in recommendations
        )
        distribution = tuple(
            RecommendationPriorityCount(priority=priority, count=counts[priority])
            for priority in RecommendationPriority
            if counts.get(priority, 0) > 0
        )
        headline = f"{len(recommendations)} recommendation(s) across {len(groups)} group(s)."
        return RecommendationSummary(
            policy_id=self._policy.policy_id,
            policy_version=self._policy.policy_version,
            total_recommendations=len(recommendations),
            total_groups=len(groups),
            priority_distribution=distribution,
            headline=headline,
        )

    # -- provenance ---------------------------------------------------------------------

    @staticmethod
    def _consumed_inputs(
        enhancement_result: RequirementEnhancementResult,
        grounding_result: GroundingResult,
        validation_result: ValidationResult,
        cp1_result: CP1Result,
        quality_governance_result: QualityGovernanceResult,
    ) -> tuple[RecommendationInputReference, ...]:
        """Record the identity and contract version of each consumed input (provenance)."""
        return (
            RecommendationInputReference(
                source=RecommendationSource.ENHANCEMENT,
                input_id=str(enhancement_result.result_id),
                input_version=str(enhancement_result.result_version),
            ),
            RecommendationInputReference(
                source=RecommendationSource.GROUNDING,
                input_id=str(grounding_result.assessment.assessment_id),
                input_version=str(grounding_result.result_version),
            ),
            RecommendationInputReference(
                source=RecommendationSource.VALIDATION,
                input_id=validation_result.validation_id,
                input_version=validation_result.validation_framework_metadata.framework_version,
            ),
            RecommendationInputReference(
                source=RecommendationSource.CP1,
                input_id=cp1_result.cp1_id,
                input_version=cp1_result.cp1_result_version,
            ),
            RecommendationInputReference(
                source=RecommendationSource.QUALITY_GOVERNANCE,
                input_id=str(quality_governance_result.result_id),
                input_version=str(quality_governance_result.result_version),
            ),
        )

    # -- empty result (policy-disabled, or nothing cleared the confidence floor) -------

    def _empty_result(
        self,
        *,
        result_id: RecommendationResultId,
        analysis_id: str,
        execution_id: str,
        consumed_inputs: tuple[RecommendationInputReference, ...],
        started_at: datetime,
        completed_at: datetime,
        headline: str,
    ) -> RecommendationResult:
        """A well-defined, empty-but-valid result."""
        summary = RecommendationSummary(
            policy_id=self._policy.policy_id,
            policy_version=self._policy.policy_version,
            total_recommendations=0,
            total_groups=0,
            headline=headline,
        )
        metrics = RecommendationMetrics(
            recommendation_density=0.0, average_confidence=0.0, high_priority_ratio=0.0
        )
        return RecommendationResult(
            result_id=result_id,
            analysis_id=analysis_id,
            execution_id=execution_id,
            summary=summary,
            metrics=metrics,
            consumed_inputs=consumed_inputs,
            policy_id=self._policy.policy_id,
            policy_version=self._policy.policy_version,
            framework_version=RECOMMENDATION_FRAMEWORK_VERSION,
            started_at=started_at,
            completed_at=completed_at,
        )
