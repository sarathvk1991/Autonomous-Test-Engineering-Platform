"""Layer 3's step-definition generator (ADR-0044 D3/D4/D5, D8).

Generates Java step definitions for Gherkin steps the reuse engine
(:mod:`automation_engineering.reuse`) returned NO_MATCH for, binds
TRUSTED_REUSE steps to existing catalog assets without regenerating them,
and surfaces ESCALATION steps for human review -- never silently generating
or reusing a step whose binding the reuse engine itself would not trust.

Builds ONLY the step-definition generator: not page objects, utilities,
test-data classes, CP3, CP4, or promotion (this build's own scope boundary,
ADR-0044 D1).

Public surface
--------------
StepDefinitionGenerator            -- the generation seam (Protocol)
StepDefinitionGenerationContext    -- the seam's own input contract
StubStepDefinitionGenerator        -- deterministic test/dev stand-in + spy
LiveStepDefinitionGenerator        -- the live, provider-backed peer
LiveGenerationError                -- the live generator's own boundary error
GeneratedStepDefinition            -- NO_MATCH outcome
BoundStepDefinition                -- TRUSTED_REUSE outcome
EscalatedStepNeed                  -- ESCALATION outcome
StepDefinitionOutcome              -- the closed union of the three
orchestrate_step_definition        -- reuse-first orchestration, one step-need
generate_step_definitions          -- reuse-first orchestration, a full feature
DEFAULT_TARGET_PACKAGE             -- com.automation.steps
DEFAULT_CUSTOMQA_STEP_DEFINITION_CONSTRAINTS -- the customqa:* constraints injected at generation
"""

from __future__ import annotations

from automation_engineering.generation.live_step_definition_generator import (
    LiveGenerationError,
    LiveStepDefinitionGenerator,
)
from automation_engineering.generation.models import (
    BoundStepDefinition,
    EscalatedStepNeed,
    GeneratedStepDefinition,
    StepDefinitionOutcome,
)
from automation_engineering.generation.orchestrator import (
    DEFAULT_CUSTOMQA_STEP_DEFINITION_CONSTRAINTS,
    DEFAULT_TARGET_PACKAGE,
    generate_step_definitions,
    orchestrate_step_definition,
)
from automation_engineering.generation.step_definition_generator import (
    StepDefinitionGenerationContext,
    StepDefinitionGenerator,
    StubStepDefinitionGenerator,
)

__all__ = [
    "DEFAULT_CUSTOMQA_STEP_DEFINITION_CONSTRAINTS",
    "DEFAULT_TARGET_PACKAGE",
    "BoundStepDefinition",
    "EscalatedStepNeed",
    "GeneratedStepDefinition",
    "LiveGenerationError",
    "LiveStepDefinitionGenerator",
    "StepDefinitionGenerationContext",
    "StepDefinitionGenerator",
    "StepDefinitionOutcome",
    "StubStepDefinitionGenerator",
    "generate_step_definitions",
    "orchestrate_step_definition",
]
