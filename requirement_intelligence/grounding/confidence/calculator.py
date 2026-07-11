"""The :class:`ConfidenceCalculator` contract — the permanent confidence boundary.

A ``ConfidenceCalculator`` consumes a :class:`ClassificationResult` and returns a
:class:`ConfidenceAssessment`, under a governed :class:`ConfidencePolicy`. It owns
confidence **only**: no matching, normalization, classification, metrics, or execution
artifacts. It consumes **only** a ``ClassificationResult`` — never the ``MatchResult``
directly, the strategy, the normalizer, or a matching policy.

CAP-077C.1 establishes the boundary only. ``calculate`` is abstract, and the registered
default raises :class:`NotImplementedError`: no scoring, no heuristics, no runtime
integration. The deterministic implementation lands in CAP-077D; statistical and hybrid
calculators may follow behind the same contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from requirement_intelligence.grounding.classification.models import ClassificationResult
from requirement_intelligence.grounding.confidence.confidence_policy import ConfidencePolicy
from requirement_intelligence.grounding.confidence.models import ConfidenceAssessment


class ConfidenceCalculator(ABC):
    """The permanent contract: a ``ClassificationResult`` in, a ``ConfidenceAssessment`` out."""

    @abstractmethod
    def calculate(self, classification_result: ClassificationResult) -> ConfidenceAssessment:
        """Return the confidence assessment for *classification_result*.

        Implementations must be deterministic: identical input yields an equal
        assessment. They consume only the classification result — never matching.
        """
        raise NotImplementedError


class DormantConfidenceCalculator(ConfidenceCalculator):
    """The registered, construction-only calculator. ``calculate`` is not implemented.

    Holds the governed :class:`ConfidencePolicy` so a future implementation can read it;
    ``calculate`` deliberately raises :class:`NotImplementedError` until CAP-077D. The
    boundary is live, the behaviour is not.
    """

    def __init__(self, policy: ConfidencePolicy) -> None:
        """Store the governed confidence policy this calculator will apply."""
        self._policy = policy

    @property
    def policy(self) -> ConfidencePolicy:
        """The governed confidence policy this calculator was built with."""
        return self._policy

    def calculate(self, classification_result: ClassificationResult) -> ConfidenceAssessment:
        """Not yet implemented — deterministic confidence lands in CAP-077D."""
        raise NotImplementedError(
            "ConfidenceCalculator.calculate is not implemented in CAP-077C.1. The Confidence "
            "subsystem exposes its boundary here; deterministic scoring lands in CAP-077D."
        )
