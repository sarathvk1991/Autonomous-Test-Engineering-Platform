"""D5 — Layer 2's bounded remediation loop (ADR-0043 D5, ADR-0040 Decision 1).

Two tiers: `formatter.py` (Tier 1, deterministic, zero LLM cost) and
`remediator.py`/`live_remediator.py` (Tier 2 seam, LLM-backed -- the stub and
the live, `llm_factory`-backed peer). `loop.py` is the loop control binding
both to CP2 (`feature_engineering.cp2`) without ever weakening its verdict.
See `models.py` for the result shape and its future consumers (run-state, a
future human-in-the-loop trigger) -- neither built here.
"""

from __future__ import annotations

from feature_engineering.remediation.formatter import format_feature_content
from feature_engineering.remediation.live_remediator import (
    LiveFeatureRemediator,
    LiveRemediationError,
)
from feature_engineering.remediation.loop import rebuild_generated_feature, run_cp2_remediation
from feature_engineering.remediation.models import (
    MAX_LLM_REMEDIATION_ATTEMPTS,
    NON_REMEDIABLE_RULES,
    RemediationAttempt,
    RemediationResult,
    RemediationStatus,
)
from feature_engineering.remediation.remediator import FeatureRemediator, StubFeatureRemediator

__all__ = [
    "MAX_LLM_REMEDIATION_ATTEMPTS",
    "NON_REMEDIABLE_RULES",
    "FeatureRemediator",
    "LiveFeatureRemediator",
    "LiveRemediationError",
    "RemediationAttempt",
    "RemediationResult",
    "RemediationStatus",
    "StubFeatureRemediator",
    "format_feature_content",
    "rebuild_generated_feature",
    "run_cp2_remediation",
]
