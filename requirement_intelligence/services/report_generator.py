"""Report Generator.

Renders the layer's outputs (consolidated/classified/analyzed requirements and
the CP1 validation result) into human-readable reports using templates in
``requirement_intelligence/reports``. Logic deferred.
"""

from __future__ import annotations

from requirement_intelligence.cp1.models import CP1Result
from requirement_intelligence.models.canonical_requirement import CanonicalRequirement


class ReportGenerator:
    """Generates requirement-intelligence reports from pipeline outputs."""

    def generate(
        self,
        requirements: list[CanonicalRequirement],
        cp1_result: CP1Result,
    ) -> str:
        """Render and return the report (path or serialised content)."""
        raise NotImplementedError
