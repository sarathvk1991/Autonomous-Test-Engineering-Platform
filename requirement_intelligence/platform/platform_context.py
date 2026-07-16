"""Platform Context — centralized construction of platform components.

:class:`PlatformContext` is a pure dependency factory. The CLI (and any other
caller) asks it for the components it needs instead of importing and
instantiating each platform class directly. This keeps wiring in one place and
keeps callers thin.

PlatformContext contains **no business logic** — every method only constructs
and returns a platform object.
"""

from __future__ import annotations

from functools import cached_property

from requirement_intelligence.analysis.analysis_configuration import (
    AnalysisConfiguration,
)
from requirement_intelligence.analysis.requirement_analysis_service import (
    RequirementAnalysisService,
)
from requirement_intelligence.consolidation.consolidation_engine import (
    ConsolidationEngine,
)
from requirement_intelligence.context_orchestration import (
    DefaultOrchestrationPolicy,
    EngineeringContextBuilder,
    EngineeringContextOrchestrator,
    LegacySelectionPolicy,
    OrchestrationPolicy,
)
from requirement_intelligence.continuous_improvement.continuous_improvement_service import (
    ContinuousImprovementService,
    DeterministicContinuousImprovementService,
)
from requirement_intelligence.continuous_improvement.policy import (
    ImprovementPolicy,
    default_improvement_policy,
)
from requirement_intelligence.continuous_improvement.rules import (
    ImprovementRuleCatalog,
    default_improvement_rule_catalog,
)
from requirement_intelligence.cp1.response import (
    CP1Service,
    ValidationToCP1Handoff,
    build_cp1_service,
)
from requirement_intelligence.enhancement.policy import (
    EnhancementPolicy,
    default_enhancement_policy,
)
from requirement_intelligence.enhancement.requirement_enhancement_service import (
    DeterministicRequirementEnhancementService,
    RequirementEnhancementService,
)
from requirement_intelligence.enhancement.rules import (
    EnhancementRuleCatalog,
    default_enhancement_rule_catalog,
)
from requirement_intelligence.grounding.builders import (
    GroundedRequirementBuilder,
    MatchingContextBuilder,
)
from requirement_intelligence.grounding.builders.grounding_assessment_builder import (
    GroundingAssessmentBuilder,
)
from requirement_intelligence.grounding.builders.grounding_result_builder import (
    GroundingResultBuilder,
)
from requirement_intelligence.grounding.classification import (
    ClassificationPolicy,
    ClassificationPolicyBuilder,
    SupportClassificationEngine,
)
from requirement_intelligence.grounding.confidence import (
    ConfidenceCalculator,
    ConfidencePolicy,
    ConfidencePolicyBuilder,
    DeterministicConfidenceCalculator,
)
from requirement_intelligence.grounding.config import (
    GroundingConfiguration,
    default_grounding_configuration,
)
from requirement_intelligence.grounding.grounding_service import (
    DefaultGroundingService,
    GroundingService,
)
from requirement_intelligence.grounding.matching import (
    MatchingPolicy,
    MatchingPolicyBuilder,
)
from requirement_intelligence.grounding.metrics_builder import GroundingMetricsBuilder
from requirement_intelligence.grounding.normalization import (
    DefaultMatchingNormalizer,
    MatchingNormalizer,
)
from requirement_intelligence.grounding.pipeline import GroundingPipeline
from requirement_intelligence.grounding.strategies import DeterministicTextMatchingStrategy
from requirement_intelligence.knowledge_graph.knowledge_graph_service import (
    DeterministicKnowledgeGraphService,
    KnowledgeGraphService,
)
from requirement_intelligence.knowledge_graph.policy import (
    KnowledgeGraphPolicy,
    default_knowledge_graph_policy,
)
from requirement_intelligence.knowledge_graph.rules import (
    KnowledgeGraphRuleCatalog,
    default_knowledge_graph_rule_catalog,
)
from requirement_intelligence.learning.learning_service import (
    DormantLearningService,
    LearningService,
)
from requirement_intelligence.learning.policy import LearningPolicy, default_learning_policy
from requirement_intelligence.llm.llm_factory import create_provider as _create_provider
from requirement_intelligence.llm.providers.base_provider import LLMProvider
from requirement_intelligence.organizational_memory.organizational_memory_service import (
    DeterministicOrganizationalMemoryService,
    OrganizationalMemoryService,
)
from requirement_intelligence.organizational_memory.policy import (
    OrganizationalMemoryPolicy,
    default_organizational_memory_policy,
)
from requirement_intelligence.prompts.framework.composition import build_prompt_registry
from requirement_intelligence.prompts.framework.prompt_registry import PromptRegistry
from requirement_intelligence.prompts.requirement_prompt_builder import (
    RequirementPromptBuilder,
)
from requirement_intelligence.quality_governance.assessment import (
    AssessmentPolicy,
    DeterministicQualityAssessmentEngine,
    QualityAssessmentEngine,
    default_assessment_policy,
)
from requirement_intelligence.quality_governance.builder import QualityGovernanceResultBuilder
from requirement_intelligence.quality_governance.decision import (
    DecisionPolicy,
    DeterministicQualityDecisionEngine,
    QualityDecisionEngine,
    default_decision_policy,
)
from requirement_intelligence.quality_governance.evaluation import (
    DeterministicQualityRuleEvaluator,
    QualityRuleEvaluator,
)
from requirement_intelligence.quality_governance.pipeline import QualityGovernancePipeline
from requirement_intelligence.quality_governance.policy import (
    QualityPolicy,
    default_quality_policy,
)
from requirement_intelligence.quality_governance.quality_governance_service import (
    DefaultQualityGovernanceService,
    QualityGovernanceService,
)
from requirement_intelligence.quality_governance.rules import (
    QualityRuleCatalog,
    default_quality_rule_catalog,
)
from requirement_intelligence.recommendation.policy import (
    RecommendationPolicy,
    default_recommendation_policy,
)
from requirement_intelligence.recommendation.recommendation_service import (
    DeterministicRecommendationService,
    RecommendationService,
)
from requirement_intelligence.recommendation.rules import (
    RecommendationRuleCatalog,
    default_recommendation_rule_catalog,
)
from requirement_intelligence.registry.connector_registry import ConnectorRegistry
from requirement_intelligence.validation.profiles import (
    ValidationProfileDefinition,
    ValidationProfileRegistry,
)
from requirement_intelligence.validation.response import (
    ResponseValidator,
    build_response_validator,
    build_response_validator_for_profile,
)


class PlatformContext:
    """Factory for platform components. Construction only — no business logic."""

    def create_connector_registry(self) -> ConnectorRegistry:
        """Return a new connector registry (Connectors + Mappers orchestrator)."""
        return ConnectorRegistry()

    def create_consolidation_engine(self) -> ConsolidationEngine:
        """Return a new consolidation engine."""
        return ConsolidationEngine()

    def create_orchestration_policy(self) -> OrchestrationPolicy:
        """Return the **active** governed :class:`OrchestrationPolicy` (CAP-076D).

        :class:`DefaultOrchestrationPolicy` — coverage-guaranteed, risk-ranked,
        domain-budgeted — is what
        :meth:`create_engineering_context_orchestrator` binds, and therefore what
        every runtime execution now applies. It is the policy that repairs the
        CAP-074B defect: functional, security and quality evidence all reach the
        reasoner whenever the repository holds them.
        """
        return DefaultOrchestrationPolicy()

    def create_legacy_selection_policy(self) -> OrchestrationPolicy:
        """Return the behaviour-preserving :class:`LegacySelectionPolicy` (CAP-076C).

        No longer the runtime policy, and deliberately retained. It restates the
        pre-CAP-076 selection rule declaratively — largest group by artifact
        count, ties broken by ``consolidated_id`` ascending — and exists as the
        **control arm**: running it against the active policy over the same
        candidates is what demonstrates that a change in a reasoner's evidence
        came from the policy rather than from the code that executes it.

        Pass it to :meth:`create_engineering_context_orchestrator` to use it.
        """
        return LegacySelectionPolicy()

    def create_engineering_context_builder(self) -> EngineeringContextBuilder:
        """Return a new :class:`EngineeringContextBuilder` (CAP-076B).

        Construction only. It owns construction of an immutable
        ``EngineeringContext`` from already-selected consolidation groups; it
        performs no ranking, coverage, budgeting, or orchestration. The
        orchestrator is its only runtime caller.
        """
        return EngineeringContextBuilder()

    def create_engineering_context_orchestrator(
        self, policy: OrchestrationPolicy | None = None
    ) -> EngineeringContextOrchestrator:
        """Return the runtime's :class:`EngineeringContextOrchestrator` (CAP-076D).

        The single orchestration point between Consolidation and Analysis. When
        *policy* is omitted the orchestrator is bound to
        :meth:`create_orchestration_policy` — the active
        :class:`DefaultOrchestrationPolicy`. The parameter exists so a caller can
        exercise a different governed policy (notably
        :meth:`create_legacy_selection_policy`, for comparison) without
        constructing the orchestrator itself.
        """
        return EngineeringContextOrchestrator(
            policy=policy if policy is not None else self.create_orchestration_policy(),
            builder=self.create_engineering_context_builder(),
        )

    def create_grounding_configuration(self) -> GroundingConfiguration:
        """Return the governed :class:`GroundingConfiguration` (CAP-077A, ADR-0016).

        Construction only, and **not yet consumed by any runtime path**. CAP-077A
        registers the Grounding Framework's versioned configuration here so future
        milestones can obtain it from the same seam every other component uses; the
        configuration is weightless today (matching and confidence land later). No
        pipeline stage calls this method, so runtime behaviour is unchanged.
        """
        return default_grounding_configuration()

    def create_grounding_service(self) -> GroundingService:
        """Return the fully wired :class:`GroundingService` (CAP-077E, ADR-0016).

        The single runtime entry point into the Grounding subsystem. This is the
        composition root for grounding: it constructs the private ``GroundingPipeline``
        from the governed components (matching context builder, deterministic strategy,
        classification engine, confidence calculator, builders) and injects it into the
        service, which delegates ``assess`` to it. The pipeline is an internal detail —
        it is not exposed as a public factory. **Still unwired into the execution
        pipeline**: nothing calls ``assess`` at runtime, so behaviour is byte-identical.
        """
        pipeline = GroundingPipeline(
            matching_context_builder=self.create_matching_context_builder(),
            strategy=self.create_deterministic_text_matching_strategy(),
            classification_engine=self.create_support_classification_engine(),
            confidence_calculator=self.create_confidence_calculator(),
            grounded_requirement_builder=GroundedRequirementBuilder(),
            metrics_builder=GroundingMetricsBuilder(),
            assessment_builder=GroundingAssessmentBuilder(),
            result_builder=GroundingResultBuilder(),
            configuration=self.create_grounding_configuration(),
        )
        return DefaultGroundingService(pipeline)

    def create_matching_context_builder(self) -> MatchingContextBuilder:
        """Return the :class:`MatchingContextBuilder` (CAP-077A.2, ADR-0016).

        The construction-only translator from runtime models (``EngineeringContext``
        + ``AnalysisResult``) to the canonical ``MatchingContext`` every grounding
        strategy consumes. **Not yet wired**: no pipeline stage calls it, so runtime
        behaviour is unchanged. It is registered here so the future
        :class:`GroundingService` can obtain it from the same seam.
        """
        return MatchingContextBuilder()

    def create_matching_normalizer(self) -> MatchingNormalizer:
        """Return the :class:`MatchingNormalizer` preprocessing boundary (CAP-077A.4).

        The canonical text-normalization seam every grounding strategy will share.
        Returns the minimal :class:`DefaultMatchingNormalizer` (lowercase + whitespace);
        the full normalizer lands with the first strategy (CAP-077B). **Not yet wired**:
        no pipeline stage calls it, so runtime behaviour is unchanged.
        """
        return DefaultMatchingNormalizer()

    def create_matching_policy(self) -> MatchingPolicy:
        """Return the governed default :class:`MatchingPolicy` (CAP-077A.5, ADR-0016).

        The governed decision rules for *what constitutes a match* — thresholds,
        weights, permitted relations, ranking, tie-breaking. A ``GroundingStrategy``
        reads it; it contains no logic. **Not yet wired**: no pipeline stage calls it,
        so runtime behaviour is unchanged.
        """
        return MatchingPolicyBuilder().build()

    def create_deterministic_text_matching_strategy(self) -> DeterministicTextMatchingStrategy:
        """Return Strategy V1 — the deterministic text matcher (CAP-077B, ADR-0016).

        Built from the governed matching normalizer and matching policy. It owns
        comparison only. **Not yet wired**: no pipeline stage or ``GroundingService``
        calls it, so runtime behaviour is unchanged.
        """
        return DeterministicTextMatchingStrategy(
            normalizer=self.create_matching_normalizer(),
            policy=self.create_matching_policy(),
        )

    def create_classification_policy(self) -> ClassificationPolicy:
        """Return the governed default :class:`ClassificationPolicy` (CAP-077C, ADR-0016).

        The governed decision rules for *what constitutes support* — score thresholds,
        relation-to-role mapping, precedence, conflict and unknown handling. A
        ``SupportClassificationEngine`` reads it; it contains no logic. **Not yet
        wired**: no pipeline stage calls it, so runtime behaviour is unchanged.
        """
        return ClassificationPolicyBuilder().build()

    def create_support_classification_engine(self) -> SupportClassificationEngine:
        """Return the :class:`SupportClassificationEngine` (CAP-077C, ADR-0016).

        Classifies a ``MatchResult`` into a ``ClassificationResult`` under the governed
        classification policy. It consumes only a ``MatchResult``. **Not yet wired**:
        no pipeline stage calls it, so runtime behaviour is unchanged.
        """
        return SupportClassificationEngine(policy=self.create_classification_policy())

    def create_confidence_policy(self) -> ConfidencePolicy:
        """Return the governed default :class:`ConfidencePolicy` (CAP-077C.1, ADR-0016).

        The governed decision rules for confidence — base scores per verdict, bonuses,
        penalties, ceiling, band thresholds. A ``ConfidenceCalculator`` reads it; it
        contains no logic. **Not yet wired**: no pipeline stage calls it, so runtime
        behaviour is unchanged.
        """
        return ConfidencePolicyBuilder().build()

    def create_confidence_calculator(self) -> ConfidenceCalculator:
        """Return the :class:`DeterministicConfidenceCalculator` (CAP-077D, ADR-0016).

        The first production confidence calculator, bound to the governed confidence
        policy. It scores deterministically from the policy and a ``ClassificationResult``.
        **Not yet wired**: no pipeline stage or ``GroundingService`` calls it, so runtime
        behaviour is unchanged.
        """
        return DeterministicConfidenceCalculator(policy=self.create_confidence_policy())

    def create_quality_policy(self) -> QualityPolicy:
        """Return the governed default :class:`QualityPolicy` (CAP-080A, ADR-0017).

        The governed decision rules for *what constitutes acceptable release quality*
        — the failure/warning numeric bars, per-source severity budgets, and mandatory
        release rules. A future decision engine reads it; it contains no logic. **Not
        yet wired**: no runtime path calls it, so runtime behaviour is unchanged.
        """
        return default_quality_policy()

    def create_quality_governance_service(self) -> QualityGovernanceService:
        """Return the :class:`DefaultQualityGovernanceService` (CAP-080C, ADR-0017 §D29).

        The single runtime entry point into Quality Governance, and the **composition
        root** for the whole subsystem: it constructs the rule evaluator, assessment
        engine, decision engine, and result builder, injects them (with the governed
        :meth:`create_quality_policy`) into the private
        :class:`QualityGovernancePipeline`, and delegates the thin service to it. The
        service and pipeline own only orchestration/sequencing; every stage is a governed
        collaborator. **Not yet wired into the execution pipeline** (nothing calls
        ``evaluate`` at runtime), so runtime behaviour is byte-identical and the golden
        baseline is unchanged; CLI and execution-package integration land in CAP-080D.
        """
        pipeline = QualityGovernancePipeline(
            policy=self.create_quality_policy(),
            rule_evaluator=self.create_quality_rule_evaluator(),
            assessment_engine=self.create_quality_assessment_engine(),
            decision_engine=self.create_quality_decision_engine(),
            result_builder=QualityGovernanceResultBuilder(),
        )
        return DefaultQualityGovernanceService(pipeline=pipeline)

    def create_quality_rule_catalog(self) -> QualityRuleCatalog:
        """Return the governed default :class:`QualityRuleCatalog` (CAP-080B, ADR-0017 §D25).

        The metadata-only declaration of *which* quality rules the framework governs —
        ordering, lookup, and grouping over the governed rules. The deterministic
        evaluator iterates it; it evaluates nothing itself. **Not yet wired**: no runtime
        path calls it, so runtime behaviour is unchanged.
        """
        return default_quality_rule_catalog()

    def create_quality_rule_evaluator(self) -> QualityRuleEvaluator:
        """Return the :class:`DeterministicQualityRuleEvaluator` (CAP-080B, ADR-0017 §D25).

        The single owner of governance rule evaluation. It is the composition root for
        evaluation: constructed with the governed :meth:`create_quality_policy` (the
        source of every threshold) and :meth:`create_quality_rule_catalog` (the source of
        every rule). CAP-080B replaces the dormant CAP-080A.1 evaluator with this real,
        deterministic one, but it remains **unwired** — no runtime path consumes it, so
        runtime behaviour is byte-identical and the golden baseline is unchanged. The
        governance service consumes it in a later CAP-080 milestone.
        """
        return DeterministicQualityRuleEvaluator(
            policy=self.create_quality_policy(),
            catalog=self.create_quality_rule_catalog(),
        )

    def create_assessment_policy(self) -> AssessmentPolicy:
        """Return the governed default :class:`AssessmentPolicy` (CAP-080A.2, ADR-0017).

        The governed rules for *how a rule evaluation is interpreted* — precedence,
        conflict handling, blocking semantics, weighting, recommendation behaviour. The
        future assessment engine reads it; it contains no logic and carries no release
        decision. **Not yet wired**: no runtime path calls it, so runtime is unchanged.
        """
        return default_assessment_policy()

    def create_quality_assessment_engine(self) -> QualityAssessmentEngine:
        """Return the :class:`DeterministicQualityAssessmentEngine` (CAP-080B.1, ADR-0017 §D26).

        The single owner of quality assessment — interpreting a ``RuleEvaluationResult``
        into a ``QualityAssessmentResult`` of observations. It is the composition root for
        assessment: constructed with the governed :meth:`create_assessment_policy` (its
        only dependency). CAP-080B.1 replaces the dormant CAP-080A.2 engine with this
        real, deterministic one, but it remains **unwired** — no runtime path consumes it,
        so runtime behaviour is byte-identical and the golden baseline is unchanged. The
        governance service consumes it in a later CAP-080 milestone.
        """
        return DeterministicQualityAssessmentEngine(policy=self.create_assessment_policy())

    def create_decision_policy(self) -> DecisionPolicy:
        """Return the governed default :class:`DecisionPolicy` (CAP-080A.3, ADR-0017).

        The governed rules for *how an assessment becomes a release decision* — the base
        ``AssessmentLevel`` → ``QualityDecision`` mapping plus the mandatory gates that
        can force ``FAIL``. The future decision engine reads it; it contains no logic.
        **Not yet wired**: no runtime path calls it, so runtime is unchanged.
        """
        return default_decision_policy()

    def create_quality_decision_engine(self) -> QualityDecisionEngine:
        """Return the :class:`DeterministicQualityDecisionEngine` (CAP-080B.2, ADR-0017 §D28).

        The single owner of the release decision — deriving ``PASS`` /
        ``PASS_WITH_WARNINGS`` / ``FAIL`` from a ``QualityAssessmentResult`` under the
        governed :meth:`create_decision_policy` (its only dependency). CAP-080B.2 replaces
        the dormant CAP-080A.3 engine with this real, deterministic one, but it remains
        **unwired** — no runtime path consumes it, so runtime behaviour is byte-identical
        and the golden baseline is unchanged. The governance service consumes it in a later
        CAP-080 milestone.
        """
        return DeterministicQualityDecisionEngine(policy=self.create_decision_policy())

    def create_enhancement_policy(self) -> EnhancementPolicy:
        """Return the governed default :class:`EnhancementPolicy` (CAP-081A, ADR-0018).

        The governed capability switches and deterministic configuration for
        Requirement Intelligence Enhancement — which capabilities are enabled, and the
        bounds a future engine must respect. A future enrichment/relationship/
        observation engine reads it; it contains no logic. **Not yet wired**: no
        runtime path calls it, so runtime behaviour is unchanged.
        """
        return default_enhancement_policy()

    def create_enhancement_rule_catalog(self) -> EnhancementRuleCatalog:
        """Return the governed default :class:`EnhancementRuleCatalog` (CAP-081B, ADR-0018).

        The metadata-only declaration of *which* deterministic enhancement mechanisms
        the framework governs — ordering, lookup, and grouping over the governed
        rules. The deterministic engine iterates it; it evaluates nothing itself.
        **Not yet wired**: no runtime path calls it, so runtime behaviour is unchanged.
        """
        return default_enhancement_rule_catalog()

    def create_requirement_enhancement_service(self) -> RequirementEnhancementService:
        """Return the :class:`DeterministicRequirementEnhancementService` (CAP-081B, ADR-0018).

        The single runtime entry point into Requirement Intelligence Enhancement, and
        the **composition root** for the subsystem: it constructs the deterministic
        engine, injecting the governed :meth:`create_enhancement_policy` and
        :meth:`create_enhancement_rule_catalog`. CAP-081B replaces the dormant CAP-081A
        service with this real, deterministic one, but it remains **unwired into the
        execution pipeline** — nothing calls ``enhance`` at runtime, so runtime
        behaviour is byte-identical and the golden baseline is unchanged.
        """
        return DeterministicRequirementEnhancementService(
            policy=self.create_enhancement_policy(),
            rule_catalog=self.create_enhancement_rule_catalog(),
        )

    def create_recommendation_policy(self) -> RecommendationPolicy:
        """Return the governed default :class:`RecommendationPolicy` (CAP-082A, ADR-0019).

        The governed capability switches and deterministic configuration for the
        Recommendation Framework — which capabilities are enabled, and the bounds a
        future engine must respect. A future deterministic/ML/LLM recommendation
        engine reads it; it contains no logic. **Not yet wired**: no runtime path
        calls it, so runtime behaviour is unchanged.
        """
        return default_recommendation_policy()

    def create_recommendation_rule_catalog(self) -> RecommendationRuleCatalog:
        """Return the governed default :class:`RecommendationRuleCatalog` (CAP-082B, ADR-0019).

        The metadata-only declaration of *which* deterministic recommendation rules
        the framework governs — ordering, lookup, and grouping over the governed
        rules. The deterministic engine iterates it; it generates no recommendation
        itself. **Not yet wired**: no runtime path calls it, so runtime behaviour is
        unchanged.
        """
        return default_recommendation_rule_catalog()

    def create_recommendation_service(self) -> RecommendationService:
        """Return the :class:`DeterministicRecommendationService` (CAP-082B, ADR-0019).

        The single runtime entry point into the Recommendation Framework, and the
        **composition root** for the subsystem: it constructs the deterministic
        engine, injecting the governed :meth:`create_recommendation_policy` and
        :meth:`create_recommendation_rule_catalog`. CAP-082B replaces the dormant
        CAP-082A service with this real, deterministic one, but it remains
        **unwired into the execution pipeline** — nothing calls ``recommend`` at
        runtime, so runtime behaviour is byte-identical and the golden baseline is
        unchanged.
        """
        return DeterministicRecommendationService(
            policy=self.create_recommendation_policy(),
            rule_catalog=self.create_recommendation_rule_catalog(),
        )

    def create_improvement_policy(self) -> ImprovementPolicy:
        """Return the governed default :class:`ImprovementPolicy` (CAP-083A, ADR-0022).

        The governed capability switches and deterministic thresholds for the
        Continuous Improvement Framework — which capabilities are enabled, and
        the bounds a future engine must respect. A future deterministic/ML/LLM
        Continuous Improvement engine reads it; it contains no logic. **Not yet
        wired**: no runtime path calls it, so runtime behaviour is unchanged.
        """
        return default_improvement_policy()

    def create_improvement_rule_catalog(self) -> ImprovementRuleCatalog:
        """Return the governed default :class:`ImprovementRuleCatalog` (CAP-083B, ADR-0022).

        The metadata-only declaration of *which* deterministic recurrence/trend/
        opportunity rules the framework governs — ordering, lookup, and grouping
        over the governed rules. The deterministic engine iterates it; it
        observes nothing itself. **Not yet wired**: no runtime path calls it, so
        runtime behaviour is unchanged.
        """
        return default_improvement_rule_catalog()

    def create_continuous_improvement_service(self) -> ContinuousImprovementService:
        """Return the :class:`DeterministicContinuousImprovementService` (CAP-083B, ADR-0022).

        The single runtime entry point into the Continuous Improvement
        Framework — the first Layer 2 capability (ADR-0020) — and the
        **composition root** for the subsystem: it constructs the deterministic
        engine, injecting the governed :meth:`create_improvement_policy` and
        :meth:`create_improvement_rule_catalog`. CAP-083B replaces the dormant
        CAP-083A service with this real, deterministic one, but it remains
        **unwired into any execution pipeline** — nothing calls ``improve`` at
        runtime, so runtime behaviour is byte-identical and the golden baseline
        is unchanged.
        """
        return DeterministicContinuousImprovementService(
            policy=self.create_improvement_policy(),
            rule_catalog=self.create_improvement_rule_catalog(),
        )

    def create_knowledge_graph_policy(self) -> KnowledgeGraphPolicy:
        """Return the governed default :class:`KnowledgeGraphPolicy` (CAP-084A, ADR-0023).

        The governed capability switches and deterministic thresholds for the
        Knowledge Graph Framework — which capabilities are enabled, and the
        bounds the engine must respect. The deterministic Knowledge Graph
        engine reads it; it contains no logic. **Not yet wired**: no runtime
        path calls it, so runtime behaviour is unchanged.
        """
        return default_knowledge_graph_policy()

    def create_knowledge_graph_rule_catalog(self) -> KnowledgeGraphRuleCatalog:
        """Return the governed default :class:`KnowledgeGraphRuleCatalog` (CAP-084B, ADR-0023).

        The metadata-only declaration of *which* deterministic node, edge, and
        structural rules the framework governs — ordering, lookup, and grouping
        over the governed rules. The deterministic engine's projectors and
        analyzers iterate it; it generates no node, edge, observation, or
        finding itself. **Not yet wired**: no runtime path calls it, so runtime
        behaviour is unchanged.
        """
        return default_knowledge_graph_rule_catalog()

    def create_knowledge_graph_service(self) -> KnowledgeGraphService:
        """Return the :class:`DeterministicKnowledgeGraphService` (CAP-084B, ADR-0023).

        The single runtime entry point into the Knowledge Graph Framework — the
        second Layer 2 capability (ADR-0020) — and the **composition root** for
        the subsystem: it constructs the deterministic engine, injecting the
        governed :meth:`create_knowledge_graph_policy` and
        :meth:`create_knowledge_graph_rule_catalog`. CAP-084B replaces the
        dormant CAP-084A service with this real, deterministic one, but it
        remains **unwired into any execution pipeline** — nothing calls
        ``build`` at runtime, so runtime behaviour is byte-identical and the
        golden baseline is unchanged.
        """
        return DeterministicKnowledgeGraphService(
            policy=self.create_knowledge_graph_policy(),
            rule_catalog=self.create_knowledge_graph_rule_catalog(),
        )

    def create_organizational_memory_policy(self) -> OrganizationalMemoryPolicy:
        """Return the governed default :class:`OrganizationalMemoryPolicy` (CAP-085A, ADR-0027).

        The governed capability switches and deterministic thresholds for the
        Organizational Memory Framework — which capabilities are enabled, and
        the bounds the engine must respect. **Not yet wired**: no runtime
        path calls it, so runtime behaviour is unchanged.
        """
        return default_organizational_memory_policy()

    def create_organizational_memory_service(self) -> OrganizationalMemoryService:
        """Return the :class:`DeterministicOrganizationalMemoryService` (CAP-085B, ADR-0027).

        The single runtime entry point into the Organizational Memory
        Framework — the third Layer 2 capability (ADR-0020) — and the
        **composition root** for the subsystem: it constructs the
        deterministic engine, injecting the governed
        :meth:`create_organizational_memory_policy`. CAP-085B replaces the
        dormant CAP-085A service with this real, deterministic one, but it
        remains **unwired into any execution pipeline** — nothing calls
        ``build`` at runtime, so runtime behaviour is byte-identical and the
        golden baseline is unchanged.
        """
        return DeterministicOrganizationalMemoryService(
            policy=self.create_organizational_memory_policy()
        )

    def create_learning_policy(self) -> LearningPolicy:
        """Return the governed default :class:`LearningPolicy` (CAP-086A, ADR-0029).

        The governed capability switches and deterministic thresholds for
        the Learning Framework — which capabilities are enabled, and the
        bounds a future engine must respect. **Not yet wired**: no runtime
        path calls it, so runtime behaviour is unchanged.
        """
        return default_learning_policy()

    def create_learning_service(self) -> LearningService:
        """Return the :class:`DormantLearningService` (CAP-086A, ADR-0029).

        The single runtime entry point into the Learning Framework — the
        fourth and final Layer 2 capability (ADR-0020), and the
        **composition root** for the subsystem. CAP-086A registers only the
        dormant implementation: no engine exists yet, so every call to
        ``build`` raises ``NotImplementedError``. The framework remains
        **unwired into any execution pipeline** — nothing calls ``build`` at
        runtime, so runtime behaviour is byte-identical and the golden
        baseline is unchanged.
        """
        return DormantLearningService()

    @cached_property
    def prompt_registry(self) -> PromptRegistry:
        """The single sealed :class:`PromptRegistry` owned by this context (CAP-075).

        Built **once**, exclusively through the Prompt Governance composition root
        :func:`~requirement_intelligence.prompts.framework.composition.build_prompt_registry`,
        and reused for every prompt builder this context creates. Composing it
        loads and SHA-verifies every governed template, so the cost is paid once
        per context rather than once per builder.
        """
        return build_prompt_registry()

    def create_prompt_builder(self) -> RequirementPromptBuilder:
        """Return a new requirement prompt builder bound to this context's registry."""
        return RequirementPromptBuilder(registry=self.prompt_registry)

    def create_provider(self, provider_name: str, model: str | None = None) -> LLMProvider:
        """Return a provider instance via the platform factory.

        Parameters
        ----------
        provider_name:
            Provider id (e.g. ``"gemini"``).
        model:
            Optional model override; when *None* the provider reads its
            environment-configured model.
        """
        return _create_provider(provider_name, model_name=model)

    def create_analysis_configuration(
        self, reasoning_contract_version: str
    ) -> AnalysisConfiguration:
        """Return an execution configuration carrying the reasoning version."""
        return AnalysisConfiguration(
            reasoning_contract_version=reasoning_contract_version,
        )

    def create_requirement_analysis_service(
        self,
        prompt_builder: RequirementPromptBuilder,
        provider: LLMProvider,
        configuration: AnalysisConfiguration,
    ) -> RequirementAnalysisService:
        """Return the requirement analysis service wired with its collaborators."""
        return RequirementAnalysisService(
            prompt_builder=prompt_builder,
            provider=provider,
            configuration=configuration,
        )

    def create_response_validator(self) -> ResponseValidator:
        """Return a fully wired :class:`ResponseValidator` over every implemented rule.

        Pure composition: delegates to the validation subsystem's composition root
        :func:`~requirement_intelligence.validation.response.build_response_validator`,
        which assembles the registry, pipeline, and validator. This method owns only
        dependency composition — it introduces no validation logic, no caching, and
        no configuration of its own.
        """
        return build_response_validator()

    def get_validation_profile(self, name: str | None = None) -> ValidationProfileDefinition:
        """Return the governed Validation Profile for *name* (default when ``None``).

        Delegates to the :class:`ValidationProfileRegistry`, the sole owner of the
        immutable governed profile definitions. This method owns only selection — it
        never defines profiles, constructs validators, or executes validation.
        """
        return ValidationProfileRegistry().get(name)

    def create_response_validator_for_profile(
        self, profile: ValidationProfileDefinition
    ) -> ResponseValidator:
        """Return a :class:`ResponseValidator` wired for *profile*.

        Pure composition: delegates to the Validation Factory
        (:func:`~requirement_intelligence.validation.response.build_response_validator_for_profile`),
        which builds a registry containing exactly the profile's implemented rules
        and the validator over it. Rule ordering remains governed by ``LAYER_ORDER``;
        the profile only narrows the rule set. This method owns only composition.
        """
        return build_response_validator_for_profile(profile)

    @cached_property
    def cp1_service(self) -> CP1Service:
        """The single :class:`CP1Service` owned by this context (CAP-067B).

        Built **once**, exclusively through the CP1 composition root
        :func:`~requirement_intelligence.cp1.response.build_cp1_service`, and reused for
        every CP1 run. This context constructs **no** registry, pipeline, criterion, or
        engine of its own — the composition root owns that assembly (CAP-066); this
        property owns only the single-instance ownership. ``CP1Service`` holds only
        immutable wiring (a sealed registry + the stateless engine) and builds a fresh
        pipeline per :meth:`~CP1Service.run` call, so a single shared instance is
        deterministic and safe to reuse across runs.
        """
        return build_cp1_service()

    def create_validation_to_cp1_handoff(self) -> ValidationToCP1Handoff:
        """Return the Validation → CP1 handoff seam (CAP-064, ADR-0011 §D4/§D5).

        Pure construction of the stateless seam that gates on the Validation verdict
        and binds a single ``CP1Input``. This method owns only construction — the seam
        owns the gate/bind orchestration; this context invents no gating policy and
        builds no ``CP1Input`` itself.
        """
        return ValidationToCP1Handoff()
