"""Layer 3's CP3 -- the deterministic coverage gate plus the hard
SonarQube quality gate (ADR-0044 D5, ADR-0040 Decision 1/2).

Two independently testable halves, combined by :func:`.gate.evaluate_cp3`:

* :mod:`.coverage` -- static, infra-free: step coverage, scenario
  coverage, unmapped steps, duplicate steps (D5's own four verbatim
  criteria), plus a reuse-percentage REPORT that never gates.
* :mod:`.sonar` -- the SonarQube adapter seam (submit/poll/parse, behind a
  ``Protocol``) and the fifth, hard-gating criterion: CP3 does not pass
  unless a live SonarQube server's own quality gate passes (D5, locking
  ADR-0040 Decision 1's CP3/SonarQube assignment).
* :mod:`.architecture` -- a sixth, hard-gating criterion, added 2026-08-04
  (ADR-0044 D5 revision, the F4 discovery's Path A): a static,
  ``javalang``-based, class-role-aware check for ``customqa:
  direct-webdriver-action``, the half of ``customqa:*`` SonarQube cannot
  natively express (no per-call network/subprocess dependency, unlike
  ``.sonar``).

CP3's own verdict is ``PASS`` iff ALL THREE halves pass -- a coverage
failure, a Sonar failure, or a static-architecture failure each
independently fail CP3 (see :mod:`.gate`).

This module builds ONLY CP3. It does not build CP4 (static locator health,
ADR-0044 D6) or promotion (workspace -> tracked baseline, ADR-0045) --
both out of scope here.
"""

from __future__ import annotations

from automation_engineering.cp3.architecture import (
    CRITERION_DIRECT_WEBDRIVER_ACTION,
    STEP_DEFINITION_PACKAGE,
    Cp3GeneratedClassInput,
    evaluate_direct_webdriver_action,
)
from automation_engineering.cp3.coverage import evaluate_coverage
from automation_engineering.cp3.gate import Cp3SonarInput, evaluate_cp3
from automation_engineering.cp3.models import (
    CP3_CRITERIA,
    CRITERION_DUPLICATE_STEPS,
    CRITERION_SCENARIO_COVERAGE,
    CRITERION_SONAR_QUALITY_GATE,
    CRITERION_STEP_COVERAGE,
    CRITERION_UNMAPPED_STEPS,
    Cp3CoverageInput,
    Cp3CriterionResult,
    Cp3FeatureInput,
    Cp3Result,
    Cp3ReuseReport,
)

__all__ = [
    "CP3_CRITERIA",
    "CRITERION_DIRECT_WEBDRIVER_ACTION",
    "CRITERION_DUPLICATE_STEPS",
    "CRITERION_SCENARIO_COVERAGE",
    "CRITERION_SONAR_QUALITY_GATE",
    "CRITERION_STEP_COVERAGE",
    "CRITERION_UNMAPPED_STEPS",
    "STEP_DEFINITION_PACKAGE",
    "Cp3CoverageInput",
    "Cp3CriterionResult",
    "Cp3FeatureInput",
    "Cp3GeneratedClassInput",
    "Cp3Result",
    "Cp3ReuseReport",
    "Cp3SonarInput",
    "evaluate_coverage",
    "evaluate_cp3",
    "evaluate_direct_webdriver_action",
]
