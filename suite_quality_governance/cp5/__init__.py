"""Layer 4's CP5 -- suite-integration governance (ADR-0040 Decision 3,
ADR-0046).

Four components (ADR-0046 D2-D5): orphaned-glue detection, the cross-suite
near-duplicate sweep, promotion-wrapping, and aggregate-release cohesion.
**This package currently builds components 1, 2, and 4**: orphaned-glue
detection (`.orphaned_glue`, gating, ADR-0046 D2), the cross-suite
near-duplicate sweep (`.near_duplicate_sweep`, advisory, ADR-0046 D3), and
aggregate-release cohesion (`.cohesion`/`.compile_check`, gating, ADR-0046
D5) -- promotion-wrapping (ADR-0046 D4, the capstone that composes all
four detectors atop ADR-0045's per-asset promotion) is the remaining
future task.

CP5's own deterministic/advisory composition rule (ADR-0046 D6): gates on
deterministic evidence only; any embedding/semantic-similarity-derived
signal is advisory, flagged for human review, never itself gating.
Components 1 and 4's deterministic checks contribute to CP5's own
PASS/FAIL; component 2's near-dup sweep never does
(`Cp5NearDuplicateSweepResult` carries no `overall_verdict` at all -- see
`.models`'s own module docstring).

**Package location, per ADR-0033.** CP5 is Layer 4's own control point
(ADR-0040 Decision 3, ADR-0044), so it lives under `suite_quality_governance/`
-- ADR-0033's own disambiguated Layer 4 package (its Recommendation 1:
"All future ADRs, tickets, and specs use the disambiguated names... never
the old, colliding names") -- not under `automation_engineering/`, Layer
3's own package. It imports Layer 3's catalog/reuse/embedding modules
directly (ADR-0046 D7's "reuses, does not rebuild"), the same cross-layer
consumption ADR-0044 D1 already describes for the Validated Automation
Package hand-off.
"""

from __future__ import annotations

from suite_quality_governance.cp5.cohesion import evaluate_cohesion
from suite_quality_governance.cp5.compile_check import (
    CompileChecker,
    CompileError,
    LiveCompileChecker,
    StubCompileChecker,
    run_compile_check,
)
from suite_quality_governance.cp5.models import (
    CP5_COHESION_CRITERIA,
    CRITERION_COMPILES,
    CRITERION_NO_AMBIGUOUS_GLUE,
    CRITERION_ORPHANED_GLUE,
    FINDING_SOURCE_NEAR_DUPLICATE_SWEEP,
    CompileResult,
    Cp5CohesionCriterionResult,
    Cp5CohesionResult,
    Cp5NearDuplicateSweepResult,
    Cp5OrphanedGlueResult,
    NearDuplicateAssetRef,
    NearDuplicateClusterFinding,
    NearDuplicatePairScore,
    OrphanedAssetFinding,
    SemanticOrphanHint,
)
from suite_quality_governance.cp5.near_duplicate_sweep import (
    DEFAULT_NEAR_DUPLICATE_THRESHOLD,
    sweep_near_duplicates,
)
from suite_quality_governance.cp5.orphaned_glue import (
    DEFAULT_SEMANTIC_HINT_FLOOR,
    detect_orphaned_glue,
)
from suite_quality_governance.cp5.pattern_matching import pattern_matches_text

__all__ = [
    "CP5_COHESION_CRITERIA",
    "CRITERION_COMPILES",
    "CRITERION_NO_AMBIGUOUS_GLUE",
    "CRITERION_ORPHANED_GLUE",
    "DEFAULT_NEAR_DUPLICATE_THRESHOLD",
    "DEFAULT_SEMANTIC_HINT_FLOOR",
    "FINDING_SOURCE_NEAR_DUPLICATE_SWEEP",
    "CompileChecker",
    "CompileError",
    "CompileResult",
    "Cp5CohesionCriterionResult",
    "Cp5CohesionResult",
    "Cp5NearDuplicateSweepResult",
    "Cp5OrphanedGlueResult",
    "LiveCompileChecker",
    "NearDuplicateAssetRef",
    "NearDuplicateClusterFinding",
    "NearDuplicatePairScore",
    "OrphanedAssetFinding",
    "SemanticOrphanHint",
    "StubCompileChecker",
    "detect_orphaned_glue",
    "evaluate_cohesion",
    "pattern_matches_text",
    "run_compile_check",
    "sweep_near_duplicates",
]
