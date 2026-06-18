"""Azure OpenAI Requirement Analyzer.

The AI-powered component of the layer: enriches/assesses requirements using
Azure OpenAI (e.g. quality scoring, gap detection, testability assessment,
ambiguity flagging). Obtains its client from the reusable
``infrastructure.azure_openai`` factory and its prompts from
``requirement_intelligence/prompts``. Logic deferred.
"""

from __future__ import annotations

from requirement_intelligence.models.canonical_requirement import CanonicalRequirement


class RequirementAnalyzer:
    """Analyzes requirements with Azure OpenAI."""

    def analyze(
        self, requirements: list[CanonicalRequirement]
    ) -> list[CanonicalRequirement]:
        """Return requirements enriched with AI-derived analysis."""
        raise NotImplementedError
