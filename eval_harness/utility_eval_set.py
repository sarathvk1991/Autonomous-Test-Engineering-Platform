"""ADR-0051 D5's fifth-generator curated eval set: `LiveUtilityGenerator`.

Same discipline as `page_object_eval_set.py`/`test_data_eval_set.py`, applied
to a FIFTH artifact type -- a stateless, static Java utility class (no
locators, no `BasePage`, no requirement traceability), not a page object, a
Cucumber step, or a SUT-bound test-data class.

**A HYBRID seed, reported honestly, not silently presented as uniform
provenance.** Unlike page-object (three cases, all seeded from a real,
currently-tracked 33-class catalog), utility has exactly ONE real, currently-
tracked, currently-compiling utility class on this platform --
`ConfigReader` (`test-suite-baseline/src/test/java/com/automation/base/
ConfigReader.java`) -- and no committed class lives in `com.automation.utils`
(`DEFAULT_UTILITY_TARGET_PACKAGE`) at all
(`utility_orchestrator.py`'s own module docstring: "even though no COMMITTED
utility class lives there yet"). This set therefore mixes two real,
distinguishable provenances rather than forcing a third real-tracked case
that does not exist:

1. **Two cases seeded directly from `ConfigReader`'s own two real,
   currently-tracked, currently-compiling methods** (`env`/`data`) --
   mirroring page-object's own "supply the real tracked name directly"
   precedent (`page_object_eval_set.py`'s own module docstring) exactly:
   `class_name="ConfigReader"` is supplied directly, not derived via
   `derive_utility_class_name` (which would not reproduce it -- that
   function has no knowledge of an already-existing class). `target_package`
   is likewise supplied as `ConfigReader`'s own REAL package
   (`"com.automation.base"`), honestly NOT `DEFAULT_UTILITY_TARGET_PACKAGE`
   (`"com.automation.utils"`) -- `ConfigReader` predates that convention, a
   fact stated directly in `utility_orchestrator.py`'s own module docstring,
   not papered over here.
2. **One case built the way `orchestrate_utility_method`'s own `NoMatch`
   branch actually constructs a `UtilityGenerationContext` for a brand-new
   need TODAY** -- `target_package=DEFAULT_UTILITY_TARGET_PACKAGE`,
   `class_name=derive_utility_class_name(action_text)` computed via the real,
   live orchestrator function (never hardcoded here, so this case cannot
   silently drift from what that function actually returns). This is the
   honest, CURRENT production shape a fresh GENERATE call takes -- not an
   invented fixture, since no second real tracked utility exists to seed a
   third real-corpus case from.
"""

from __future__ import annotations

from dataclasses import dataclass

from automation_engineering.catalog.models import StepCapture
from automation_engineering.generation.utility_generator import UtilityGenerationContext
from automation_engineering.generation.utility_orchestrator import (
    DEFAULT_CUSTOMQA_UTILITY_CONSTRAINTS,
    DEFAULT_UTILITY_TARGET_PACKAGE,
    derive_utility_class_name,
)
from automation_engineering.reuse.models import GherkinStepNeed

#: Independent from `GenerationIdentity`/the prompt version (ADR-0051 D2) --
#: this is the CURATED SET's own version, advanced when cases are added,
#: removed, or re-labeled, never when the generator or prompt changes.
UTILITY_EVAL_SET_VERSION = "1.0.0"

#: `ConfigReader`'s own real, currently-tracked package -- deliberately NOT
#: `DEFAULT_UTILITY_TARGET_PACKAGE` (see module docstring).
_CONFIG_READER_PACKAGE = "com.automation.base"

#: The fresh, constructed case's own action text -- feeds
#: `derive_utility_class_name` directly (computed, not hardcoded) below.
_FRESH_ACTION_TEXT = "format a date for display"


@dataclass(frozen=True, slots=True)
class EvalCase:
    """One curated eval case: an id (for diagnosis) plus the real
    `UtilityGenerationContext` a `UtilityGenerator` would be called with."""

    case_id: str
    context: UtilityGenerationContext


def _context(
    *, action_text: str, step_type: str, class_name: str, target_package: str
) -> UtilityGenerationContext:
    """Builds one real `UtilityGenerationContext` -- a single string capture
    (`key`), the shape both `ConfigReader.env(String)`/`ConfigReader.
    data(String)` and the prompt's own `action_text` example ("read a
    test-data value by key") share."""
    return UtilityGenerationContext(
        need=GherkinStepNeed(
            text=action_text,
            step_type=step_type,
            captures=(StepCapture(index=0, style="call_site", expression_type="string"),),
        ),
        class_name=class_name,
        target_package=target_package,
        customqa_constraints=DEFAULT_CUSTOMQA_UTILITY_CONSTRAINTS,
    )


#: Two cases seeded from `ConfigReader`'s own two real methods, one
#: constructed in the real, current production NoMatch shape (module
#: docstring, above, explains the hybrid provenance).
UTILITY_EVAL_SET: tuple[EvalCase, ...] = (
    EvalCase(
        case_id="config_reader_env",
        context=_context(
            action_text="read an environment/SUT-binding config value by key",
            step_type="Given",
            class_name="ConfigReader",
            target_package=_CONFIG_READER_PACKAGE,
        ),
    ),
    EvalCase(
        case_id="config_reader_data",
        context=_context(
            action_text="read a test-data value by key",
            step_type="Given",
            class_name="ConfigReader",
            target_package=_CONFIG_READER_PACKAGE,
        ),
    ),
    EvalCase(
        case_id="fresh_date_formatting_utility",
        context=_context(
            action_text=_FRESH_ACTION_TEXT,
            step_type="When",
            class_name=derive_utility_class_name(_FRESH_ACTION_TEXT),
            target_package=DEFAULT_UTILITY_TARGET_PACKAGE,
        ),
    ),
)


__all__ = ["UTILITY_EVAL_SET", "UTILITY_EVAL_SET_VERSION", "EvalCase"]
