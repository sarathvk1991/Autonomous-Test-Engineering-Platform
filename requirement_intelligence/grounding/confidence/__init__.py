"""Confidence framework (CAP-077C.1).

Owns confidence only — turning a ``ClassificationResult`` into a
``ConfidenceAssessment`` under a governed ``ConfidencePolicy``. It performs no matching,
normalization, classification, metrics, or execution-artifact writing. A
``ConfidenceCalculator`` reads only a ``ClassificationResult``.

**Architecture only:** the calculator contract is abstract and its default is dormant;
deterministic scoring lands in CAP-077D.
"""

from __future__ import annotations

from requirement_intelligence.grounding.confidence.calculator import (
    ConfidenceCalculator,
    DormantConfidenceCalculator,
)
from requirement_intelligence.grounding.confidence.confidence_policy import (
    CONFIDENCE_POLICY_VERSION,
    DEFAULT_CONFIDENCE_POLICY_ID,
    ConfidenceBandThresholds,
    ConfidenceBaseScores,
    ConfidenceBonuses,
    ConfidencePenalties,
    ConfidencePolicy,
    ConfidencePolicyBuilder,
    default_confidence_policy,
)
from requirement_intelligence.grounding.confidence.deterministic_calculator import (
    DeterministicConfidenceCalculator,
)
from requirement_intelligence.grounding.confidence.models import (
    CONFIDENCE_VERSION,
    ConfidenceAssessment,
    ConfidenceExplanation,
)

__all__ = [
    "CONFIDENCE_POLICY_VERSION",
    "CONFIDENCE_VERSION",
    "DEFAULT_CONFIDENCE_POLICY_ID",
    "ConfidenceAssessment",
    "ConfidenceBandThresholds",
    "ConfidenceBaseScores",
    "ConfidenceBonuses",
    "ConfidenceCalculator",
    "ConfidenceExplanation",
    "ConfidencePenalties",
    "ConfidencePolicy",
    "ConfidencePolicyBuilder",
    "DeterministicConfidenceCalculator",
    "DormantConfidenceCalculator",
    "default_confidence_policy",
]
