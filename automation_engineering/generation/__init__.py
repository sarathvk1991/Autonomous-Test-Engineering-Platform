"""Layer 3's step-definition and page-object generators (ADR-0044 D3/D4/D5, D8).

Generates Java step definitions AND page objects for needs the reuse engine
(:mod:`automation_engineering.reuse`) returned NO_MATCH for, binds
TRUSTED_REUSE needs to existing catalog assets without regenerating them,
and surfaces ESCALATION needs for human review -- never silently generating
or reusing a binding the reuse engine itself would not trust.

The precise method-fit obligation ADR-0044 D4's clarification note recorded
(before a page-object binding is trusted, verify the SPECIFIC method a step
definition is about to call actually exists) is now DISCHARGED
(:mod:`.method_fit`, wired into :mod:`.orchestrator`'s own NO_MATCH branch)
-- carried forward, undischarged, by the step-definition build that first
wrote this package; closed by the page-object build that added
:mod:`.page_object_generator`, :mod:`.page_object_orchestrator`, and
:mod:`.method_fit`.

Builds page objects + the method-fit discharge; NOT utilities, test-data
classes, CP3, CP4, or promotion (this build's own scope boundary).

Public surface
--------------
StepDefinitionGenerator            -- the step-def generation seam (Protocol)
StepDefinitionGenerationContext    -- the seam's own input contract
StubStepDefinitionGenerator        -- deterministic test/dev stand-in + spy
LiveStepDefinitionGenerator        -- the live, provider-backed peer
StepDefinitionLiveGenerationError  -- the step-def live generator's own boundary error
GeneratedStepDefinition            -- NO_MATCH outcome
BoundStepDefinition                -- TRUSTED_REUSE outcome
EscalatedStepNeed                  -- ESCALATION outcome
StepDefinitionOutcome              -- the closed union of the three
orchestrate_step_definition        -- reuse-first orchestration, one step-need
generate_step_definitions          -- reuse-first orchestration, a full feature
DEFAULT_TARGET_PACKAGE             -- com.automation.steps
DEFAULT_CUSTOMQA_STEP_DEFINITION_CONSTRAINTS -- customqa:* constraints for step-def generation

PageObjectGenerator                 -- the page-object generation seam (Protocol)
PageObjectGenerationContext         -- the seam's own input contract
StubPageObjectGenerator             -- deterministic test/dev stand-in + spy
LivePageObjectGenerator             -- the live, provider-backed peer
PageObjectLiveGenerationError       -- the page-object live generator's own boundary error
PageObjectMethodNeed                -- the page-object action + specific method a step calls
GeneratedPageObject                 -- NO_MATCH outcome
BoundPageObjectMethod               -- TRUSTED_REUSE outcome, precise method-fit verified
EscalatedPageObjectMethodNeed       -- ESCALATION outcome (reuse-engine OR precise method-fit)
PageObjectMethodOutcome             -- the closed union of the three
PageObjectBindingRequest            -- wires page-object resolution into the step-def orchestrator
orchestrate_page_object_method      -- reuse-first orchestration, one method-need
generate_page_object_methods        -- reuse-first orchestration, a full set of method-needs
derive_page_object_class_name       -- deterministic UpperCamelCase + "Page" derivation
verify_specific_method_fit          -- THE precise method-fit discharge
DEFAULT_PAGE_OBJECT_TARGET_PACKAGE  -- com.automation.pages
DEFAULT_CUSTOMQA_PAGE_OBJECT_CONSTRAINTS -- customqa:* constraints for page-object generation
"""

from __future__ import annotations

from automation_engineering.generation.live_page_object_generator import (
    LiveGenerationError as PageObjectLiveGenerationError,
)
from automation_engineering.generation.live_page_object_generator import (
    LivePageObjectGenerator,
)
from automation_engineering.generation.live_step_definition_generator import (
    LiveGenerationError as StepDefinitionLiveGenerationError,
)
from automation_engineering.generation.live_step_definition_generator import (
    LiveStepDefinitionGenerator,
)
from automation_engineering.generation.method_fit import verify_specific_method_fit
from automation_engineering.generation.models import (
    BoundPageObjectMethod,
    BoundStepDefinition,
    EscalatedPageObjectMethodNeed,
    EscalatedStepNeed,
    GeneratedPageObject,
    GeneratedStepDefinition,
    PageObjectMethodNeed,
    PageObjectMethodOutcome,
    StepDefinitionOutcome,
)
from automation_engineering.generation.orchestrator import (
    DEFAULT_CUSTOMQA_STEP_DEFINITION_CONSTRAINTS,
    DEFAULT_TARGET_PACKAGE,
    generate_step_definitions,
    orchestrate_step_definition,
)
from automation_engineering.generation.page_object_generator import (
    PageObjectGenerationContext,
    PageObjectGenerator,
    StubPageObjectGenerator,
)
from automation_engineering.generation.page_object_orchestrator import (
    DEFAULT_CUSTOMQA_PAGE_OBJECT_CONSTRAINTS,
    DEFAULT_PAGE_OBJECT_TARGET_PACKAGE,
    PageObjectBindingRequest,
    derive_page_object_class_name,
    generate_page_object_methods,
    orchestrate_page_object_method,
)
from automation_engineering.generation.step_definition_generator import (
    StepDefinitionGenerationContext,
    StepDefinitionGenerator,
    StubStepDefinitionGenerator,
)

__all__ = [
    "DEFAULT_CUSTOMQA_PAGE_OBJECT_CONSTRAINTS",
    "DEFAULT_CUSTOMQA_STEP_DEFINITION_CONSTRAINTS",
    "DEFAULT_PAGE_OBJECT_TARGET_PACKAGE",
    "DEFAULT_TARGET_PACKAGE",
    "BoundPageObjectMethod",
    "BoundStepDefinition",
    "EscalatedPageObjectMethodNeed",
    "EscalatedStepNeed",
    "GeneratedPageObject",
    "GeneratedStepDefinition",
    "LivePageObjectGenerator",
    "LiveStepDefinitionGenerator",
    "PageObjectBindingRequest",
    "PageObjectGenerationContext",
    "PageObjectGenerator",
    "PageObjectLiveGenerationError",
    "PageObjectMethodNeed",
    "PageObjectMethodOutcome",
    "StepDefinitionGenerationContext",
    "StepDefinitionGenerator",
    "StepDefinitionLiveGenerationError",
    "StepDefinitionOutcome",
    "StubPageObjectGenerator",
    "StubStepDefinitionGenerator",
    "derive_page_object_class_name",
    "generate_page_object_methods",
    "generate_step_definitions",
    "orchestrate_page_object_method",
    "orchestrate_step_definition",
    "verify_specific_method_fit",
]
