"""Requirement Classification Engine.

Assigns classification attributes (type, priority, tags) to each canonical
requirement. May apply deterministic rules and/or delegate to the AI analyzer
for ambiguous cases. Logic deferred.
"""

from __future__ import annotations

from requirement_intelligence.models.canonical_requirement import CanonicalRequirement


class ClassificationEngine:
    """Classifies canonical requirements by type, priority, and tags."""

    def classify(
        self, requirements: list[CanonicalRequirement]
    ) -> list[CanonicalRequirement]:
        """Return requirements enriched with classification attributes."""
        raise NotImplementedError
