"""Requirement Intelligence pipeline orchestration.

Wires the layer's components into the end-to-end flow. The workflow owns
*sequencing*; each step's logic lives in its own service. This is the single
place that defines the order of operations for the layer.

Flow:
    1. Source Registry        -> resolve active connectors
    2. Connectors             -> fetch raw records per source
    3. Parsers                -> raw records  -> CanonicalRequirement[]
    4. Consolidation Engine   -> merge/de-duplicate across sources
    5. Classification Engine  -> assign type/priority/tags
    6. Requirement Analyzer   -> Azure OpenAI enrichment
    7. CP1 Validator          -> quality gate (pass/fail + findings)
    8. Report Generator       -> human-readable report

Logic deferred.
"""

from __future__ import annotations

from shared.enums.base import SourceSystem


class RequirementPipeline:
    """Orchestrates the Requirement Intelligence end-to-end flow."""

    def run(
        self,
        sources: list[SourceSystem],
        project_key: str | None = None,
    ) -> str:
        """Execute the full pipeline and return the generated report reference."""
        raise NotImplementedError
