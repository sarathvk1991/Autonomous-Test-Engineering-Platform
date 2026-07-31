"""Layer 3's four generators: step definitions, page objects, utilities,
and test data (ADR-0044 D1/D3/D4/D5/D7/D8).

Generates Java code for needs the reuse engine
(:mod:`automation_engineering.reuse`) returned NO_MATCH for, binds
TRUSTED_REUSE needs to existing catalog assets without regenerating them,
and surfaces ESCALATION needs for human review -- never silently generating
or reusing a binding the reuse engine itself would not trust. That
discipline governs THREE of the four generators here (step definitions,
page objects, utilities); the fourth (test data) deliberately breaks it --
see :mod:`.test_data_orchestrator`'s own module docstring for the
investigation that resolved test-data is SPEC-DRIVEN, not reuse-first, and
why.

The precise method-fit obligation ADR-0044 D4's clarification note recorded
(before a page-object/utility binding is trusted, verify the SPECIFIC
method a step definition is about to call actually exists) is DISCHARGED
for BOTH page objects and utilities (:mod:`.method_fit`, wired into
:mod:`.orchestrator`'s own NO_MATCH branch).

All three catalog asset kinds (D3) are legitimately handled; there is no
fourth, still-deferred asset kind AMONG THOSE THREE. Test data is not a
reuse-catalog asset kind at all (see :mod:`.test_data_orchestrator`).

Builds test-data generation from Layer 2's own specification (ADR-0044
D7); NOT CP3, CP4, or promotion (this build's own scope boundary). Records
an honest gap this build found: Layer 2 does not implement emission of the
D7 specification today -- this generator is built and proven against the
CONTRACT that specification defines, not a real emission (none exists).

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

TestDataGenerator                   -- the test-data generation seam (Protocol)
TestDataGenerationContext           -- the seam's own input contract
StubTestDataGenerator               -- deterministic test/dev stand-in + spy
LiveTestDataGenerator               -- the live, provider-backed peer
TestDataLiveGenerationError         -- the test-data live generator's own boundary error
GeneratedTestDataClass              -- the ONLY outcome (no reuse decision -- see module docstring)
TestDataBoundaryError               -- raised on an env/data boundary violation (ADR-0037 D3)
generate_test_data_class            -- always-generate orchestration, one specification
generate_test_data_classes          -- always-generate orchestration, a full set of specifications
derive_test_data_class_name         -- deterministic UpperCamelCase + "TestData" derivation
DEFAULT_TEST_DATA_TARGET_PACKAGE    -- com.automation.utils
DEFAULT_CUSTOMQA_TEST_DATA_CONSTRAINTS -- customqa:* constraints for test-data generation

TestDataFieldSpec/TestDataSpecification -- the Layer 2 -> Layer 3 boundary
                                        contract itself now lives in
                                        `contracts.test_data_specification`,
                                        not re-exported from this package
                                        (import it from `contracts` directly).
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
from automation_engineering.generation.live_test_data_generator import (
    LiveGenerationError as TestDataLiveGenerationError,
)
from automation_engineering.generation.live_test_data_generator import (
    LiveTestDataGenerator,
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
    GeneratedTestDataClass,
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
from automation_engineering.generation.test_data_generator import (
    StubTestDataGenerator,
    TestDataGenerationContext,
    TestDataGenerator,
)
from automation_engineering.generation.test_data_orchestrator import (
    DEFAULT_CUSTOMQA_TEST_DATA_CONSTRAINTS,
    DEFAULT_TEST_DATA_TARGET_PACKAGE,
    TestDataBoundaryError,
    derive_test_data_class_name,
    generate_test_data_class,
    generate_test_data_classes,
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
    "DEFAULT_CUSTOMQA_TEST_DATA_CONSTRAINTS",
    "DEFAULT_CUSTOMQA_UTILITY_CONSTRAINTS",
    "DEFAULT_PAGE_OBJECT_TARGET_PACKAGE",
    "DEFAULT_TARGET_PACKAGE",
    "DEFAULT_TEST_DATA_TARGET_PACKAGE",
    "DEFAULT_UTILITY_TARGET_PACKAGE",
    "BoundPageObjectMethod",
    "BoundStepDefinition",
    "BoundUtilityMethod",
    "EscalatedPageObjectMethodNeed",
    "EscalatedStepNeed",
    "EscalatedUtilityMethodNeed",
    "GeneratedPageObject",
    "GeneratedStepDefinition",
    "GeneratedTestDataClass",
    "GeneratedUtility",
    "LivePageObjectGenerator",
    "LiveStepDefinitionGenerator",
    "LiveTestDataGenerator",
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
    "StubTestDataGenerator",
    "StubUtilityGenerator",
    "TestDataBoundaryError",
    "TestDataGenerationContext",
    "TestDataGenerator",
    "TestDataLiveGenerationError",
    "UtilityBindingRequest",
    "UtilityGenerationContext",
    "UtilityGenerator",
    "UtilityLiveGenerationError",
    "UtilityMethodNeed",
    "UtilityMethodOutcome",
    "derive_page_object_class_name",
    "derive_test_data_class_name",
    "derive_utility_class_name",
    "generate_page_object_methods",
    "generate_step_definitions",
    "generate_test_data_class",
    "generate_test_data_classes",
    "generate_utility_methods",
    "orchestrate_page_object_method",
    "orchestrate_step_definition",
    "orchestrate_utility_method",
    "verify_specific_method_fit",
]
