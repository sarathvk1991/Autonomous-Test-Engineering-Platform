"""Engineering Context Orchestration — the canonical orchestration subsystem.

Sits between Consolidation and Analysis:

    list[ConsolidatedArtifact]  ->  Engineering Context Orchestrator  ->  EngineeringContext

Consolidation owns *grouping*: which records share an attribute. This subsystem
owns *orchestration*: which evidence a reasoning session receives, under a
governed :class:`OrchestrationPolicy`. See ADR-0015.

Scope at CAP-076C
-----------------
The subsystem is **live**. :class:`EngineeringContextOrchestrator` is the
runtime's single orchestration point: the CLI hands it every consolidation
group, it executes :class:`LegacySelectionPolicy`, and the resulting
``EngineeringContext`` flows to the prompt builder, the analysis service, and
the execution package.

:class:`LegacySelectionPolicy` is the **active** policy and reproduces the
pre-CAP-076 selection rule exactly, so runtime behaviour is unchanged.
:class:`DefaultOrchestrationPolicy` — the policy that repairs the CAP-074B
defect — remains constructed but **inactive**; activating it is CAP-076D.

A note on the word "orchestration"
----------------------------------
ADR-0002, ADR-0003 and ADR-0011 use *orchestration boundary* for components that
sequence collaborators and own **no** policy (``ResponseNormalizer``,
``ResponseValidator``, ``CP1Service``, ``RequirementAnalysisService``).
Engineering Context Orchestration is the opposite: owning policy is its purpose.
Always use the full term (CAP-076A §0.1).
"""

from __future__ import annotations

from requirement_intelligence.context_orchestration.context_exceptions import (
    ContextBudgetExceededError,
    ContextConstructionError,
    ContextOrchestrationError,
    PolicyCompatibilityError,
)
from requirement_intelligence.context_orchestration.engineering_context_builder import (
    SUPPORTED_POLICY_MAJOR,
    EngineeringContextBuilder,
)
from requirement_intelligence.context_orchestration.engineering_context_orchestrator import (
    ContextOrchestrationResult,
    EngineeringContextOrchestrator,
)
from requirement_intelligence.context_orchestration.models import (
    ENGINEERING_CONTEXT_VERSION,
    ContextContribution,
    ContextCorrelation,
    ContextDependencies,
    ContextEvidence,
    ContextMetadata,
    ContextProvenance,
    ContextSubject,
    ContextSubjectBasis,
    EngineeringContext,
    EngineeringContextId,
    OrchestrationMetadata,
    OrchestrationPolicyId,
    PolicyVersion,
)
from requirement_intelligence.context_orchestration.policy import (
    CoverageMode,
    CoverageRule,
    DefaultOrchestrationPolicy,
    EvidenceBudget,
    EvidenceOrdering,
    LegacySelectionPolicy,
    OrchestrationPolicy,
    RankingKey,
    RankingRule,
    SelectionStrategy,
    TieBreaker,
)

__all__ = [
    "ENGINEERING_CONTEXT_VERSION",
    "SUPPORTED_POLICY_MAJOR",
    "ContextBudgetExceededError",
    "ContextConstructionError",
    "ContextContribution",
    "ContextCorrelation",
    "ContextDependencies",
    "ContextEvidence",
    "ContextMetadata",
    "ContextOrchestrationError",
    "ContextOrchestrationResult",
    "ContextProvenance",
    "ContextSubject",
    "ContextSubjectBasis",
    "CoverageMode",
    "CoverageRule",
    "DefaultOrchestrationPolicy",
    "EngineeringContext",
    "EngineeringContextBuilder",
    "EngineeringContextId",
    "EngineeringContextOrchestrator",
    "EvidenceBudget",
    "EvidenceOrdering",
    "LegacySelectionPolicy",
    "OrchestrationMetadata",
    "OrchestrationPolicy",
    "OrchestrationPolicyId",
    "PolicyCompatibilityError",
    "PolicyVersion",
    "RankingKey",
    "RankingRule",
    "SelectionStrategy",
    "TieBreaker",
]
