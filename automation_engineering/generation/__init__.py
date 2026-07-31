"""Layer 3's three Gherkin-derived generators: step definitions, page
objects, and utilities (ADR-0044 D3/D4/D5, D8).

Generates Java code for needs the reuse engine
(:mod:`automation_engineering.reuse`) returned NO_MATCH for, binds
TRUSTED_REUSE needs to existing catalog assets without regenerating them,
and surfaces ESCALATION needs for human review -- never silently generating
or reusing a binding the reuse engine itself would not trust.

The precise method-fit obligation ADR-0044 D4's clarification note recorded
(before a page-object/utility binding is trusted, verify the SPECIFIC
method a step definition is about to call actually exists) is now
DISCHARGED for BOTH page objects and utilities (:mod:`.method_fit`, wired
into :mod:`.orchestrator`'s own NO_MATCH branch) -- carried forward,
undischarged, by the step-definition build that first wrote this package;
discharged for page objects by that build's successor; discharged for
utilities by this build, after investigating (not assuming) that utilities
carry the identical risk -- see :mod:`.utility_orchestrator`'s own module
docstring for the investigation.

All three catalog asset kinds (D3) are now legitimately handled. There is
no fourth, still-deferred asset kind.

Builds utilities + the utility method-fit resolution; NOT test-data
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
DEFAULT_PAGE_OBJECT_TARGET_PACKAGE  -- com.automation.pages
DEFAULT_CUSTOMQA_PAGE_OBJECT_CONSTRAINTS -- customqa:* constraints for page-object generation

UtilityGenerator                    -- the utility generation seam (Protocol)
UtilityGenerationContext            -- the seam's own input contract
StubUtilityGenerator                -- deterministic test/dev stand-in + spy
LiveUtilityGenerator                -- the live, provider-backed peer
UtilityLiveGenerationError          -- the utility live generator's own boundary error
UtilityMethodNeed                   -- the utility action + specific method a step calls
GeneratedUtility                    -- NO_MATCH outcome
BoundUtilityMethod                  -- TRUSTED_REUSE outcome, precise method-fit verified
EscalatedUtilityMethodNeed          -- ESCALATION outcome (reuse-engine OR precise method-fit)
UtilityMethodOutcome                -- the closed union of the three
UtilityBindingRequest               -- wires utility resolution into the step-def orchestrator
orchestrate_utility_method          -- reuse-first orchestration, one method-need
generate_utility_methods            -- reuse-first orchestration, a full set of method-needs
derive_utility_class_name           -- deterministic UpperCamelCase derivation
DEFAULT_UTILITY_TARGET_PACKAGE      -- com.automation.utils
DEFAULT_CUSTOMQA_UTILITY_CONSTRAINTS -- customqa:* constraints for utility generation

verify_specific_method_fit          -- THE precise method-fit discharge
                                        (shared: page objects + utilities)
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
from automation_engineering.generation.live_utility_generator import (
    LiveGenerationError as UtilityLiveGenerationError,
)
from automation_engineering.generation.live_utility_generator import (
    LiveUtilityGenerator,
)
from automation_engineering.generation.method_fit import verify_specific_method_fit
from automation_engineering.generation.models import (
    BoundPageObjectMethod,
    BoundStepDefinition,
    BoundUtilityMethod,
    EscalatedPageObjectMethodNeed,
    EscalatedStepNeed,
    EscalatedUtilityMethodNeed,
    GeneratedPageObject,
    GeneratedStepDefinition,
    GeneratedUtility,
    PageObjectMethodNeed,
    PageObjectMethodOutcome,
    StepDefinitionOutcome,
    UtilityMethodNeed,
    UtilityMethodOutcome,
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
from automation_engineering.generation.utility_generator import (
    StubUtilityGenerator,
    UtilityGenerationContext,
    UtilityGenerator,
)
from automation_engineering.generation.utility_orchestrator import (
    DEFAULT_CUSTOMQA_UTILITY_CONSTRAINTS,
    DEFAULT_UTILITY_TARGET_PACKAGE,
    UtilityBindingRequest,
    derive_utility_class_name,
    generate_utility_methods,
    orchestrate_utility_method,
)

__all__ = [
    "DEFAULT_CUSTOMQA_PAGE_OBJECT_CONSTRAINTS",
    "DEFAULT_CUSTOMQA_STEP_DEFINITION_CONSTRAINTS",
    "DEFAULT_CUSTOMQA_UTILITY_CONSTRAINTS",
    "DEFAULT_PAGE_OBJECT_TARGET_PACKAGE",
    "DEFAULT_TARGET_PACKAGE",
    "DEFAULT_UTILITY_TARGET_PACKAGE",
    "BoundPageObjectMethod",
    "BoundStepDefinition",
    "BoundUtilityMethod",
    "EscalatedPageObjectMethodNeed",
    "EscalatedStepNeed",
    "EscalatedUtilityMethodNeed",
    "GeneratedPageObject",
    "GeneratedStepDefinition",
    "GeneratedUtility",
    "LivePageObjectGenerator",
    "LiveStepDefinitionGenerator",
    "LiveUtilityGenerator",
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
    "StubUtilityGenerator",
    "UtilityBindingRequest",
    "UtilityGenerationContext",
    "UtilityGenerator",
    "UtilityLiveGenerationError",
    "UtilityMethodNeed",
    "UtilityMethodOutcome",
    "derive_page_object_class_name",
    "derive_utility_class_name",
    "generate_page_object_methods",
    "generate_step_definitions",
    "generate_utility_methods",
    "orchestrate_page_object_method",
    "orchestrate_step_definition",
    "orchestrate_utility_method",
    "verify_specific_method_fit",
]
