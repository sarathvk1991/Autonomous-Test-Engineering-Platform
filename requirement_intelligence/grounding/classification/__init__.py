"""Support Classification framework (CAP-077C).

Owns support classification only — turning a ``MatchResult`` into a governed
``ClassificationResult``. It performs no matching, normalization, confidence,
metrics, explanation rendering, or execution-artifact writing. A
``SupportClassificationEngine`` reads only a ``MatchResult`` under a governed
``ClassificationPolicy``.
"""

from __future__ import annotations

from requirement_intelligence.grounding.classification.classification_policy import (
    CLASSIFICATION_POLICY_VERSION,
    DEFAULT_CLASSIFICATION_POLICY_ID,
    ClassificationPolicy,
    ClassificationPolicyBuilder,
    ClassificationThresholds,
    default_classification_policy,
)
from requirement_intelligence.grounding.classification.engine import SupportClassificationEngine
from requirement_intelligence.grounding.classification.models import (
    CLASSIFICATION_VERSION,
    ClassificationResult,
)

__all__ = [
    "CLASSIFICATION_POLICY_VERSION",
    "CLASSIFICATION_VERSION",
    "DEFAULT_CLASSIFICATION_POLICY_ID",
    "ClassificationPolicy",
    "ClassificationPolicyBuilder",
    "ClassificationResult",
    "ClassificationThresholds",
    "SupportClassificationEngine",
    "default_classification_policy",
]
