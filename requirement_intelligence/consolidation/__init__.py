"""Consolidation Engine module.

Groups ``List[SourceArtifact]`` into ``List[ConsolidatedArtifact]`` using
deterministic, explainable heuristics — no AI, no I/O, no source-specific code.
"""

from requirement_intelligence.consolidation.consolidation_engine import (
    ConsolidationEngine,
)
from requirement_intelligence.consolidation.consolidation_exceptions import (
    ConsolidationError,
    ConsolidationInputError,
)
from requirement_intelligence.consolidation.consolidation_rules import (
    GroupingDimension,
    GroupingKey,
)

__all__ = [
    "ConsolidationEngine",
    "ConsolidationError",
    "ConsolidationInputError",
    "GroupingDimension",
    "GroupingKey",
]
