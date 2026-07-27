"""CP2 — Layer 2's deterministic feature-governance gate (ADR-0040, ADR-0043 D5).

One `GeneratedFeature` in, one `CP2Result` out. Pure evaluation: no disk
I/O, no network call, no LLM provider. See `evaluator.py` for the four
gate criteria and `models.py` for the result shape and its future
consumers (the D5 remediation loop, run-state, and a future
human-in-the-loop trigger) -- none of which are built here.
"""

from __future__ import annotations

from feature_engineering.cp2.evaluator import evaluate_cp2
from feature_engineering.cp2.models import (
    CP2_CRITERIA,
    CRITERION_AC_COVERAGE,
    CRITERION_DUPLICATE_DETECTION,
    CRITERION_LINT,
    CRITERION_TAG_PRESENCE,
    CP2AdvisorySignals,
    CP2CriterionResult,
    CP2Result,
)

__all__ = [
    "CP2_CRITERIA",
    "CRITERION_AC_COVERAGE",
    "CRITERION_DUPLICATE_DETECTION",
    "CRITERION_LINT",
    "CRITERION_TAG_PRESENCE",
    "CP2AdvisorySignals",
    "CP2CriterionResult",
    "CP2Result",
    "evaluate_cp2",
]
