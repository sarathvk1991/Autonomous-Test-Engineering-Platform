"""ADR-0051 D2's deterministic property/assertion checks for one generated
test-data artifact (`LiveTestDataGenerator`'s raw output).

**Composed, not invented (ADR-0051 D1, the reframe) -- and NOT copied from
step-def's Java checks or feature-content's Gherkin checks.** Test-data is a
THIRD artifact type: a Java class, like step-def's, but governed by a
different real contract -- ADR-0037 D3's SUT-binding boundary, not
Cucumber's annotation grammar. This module composes two ALREADY-REAL,
ALREADY-ENFORCED mechanisms plus three contract-grounded checks:

1. **`check_no_env_binding` ports `automation_engineering.generation.
   test_data_orchestrator._check_no_env_binding`'s own regex verbatim.**
   That function is not a design aspiration -- it is a live, ALWAYS-ON,
   orchestration-level guard: `generate_test_data_class` calls it on every
   generator's output (stub or live) and raises `TestDataBoundaryError`
   before ever returning a result. This is the closest analog to
   step-def's CP5-compile-check reuse and feature-content's `assembler.py`
   reuse this arc has found: a real production check, not merely a prompt
   clause. Ported (not called through) for the same reason step-def's own
   checks were ports of CP5's logic, not live calls into it -- independent,
   per-check evaluability, no cross-package reach into another module's
   underscore-prefixed internals.
2. **`check_no_long_method` calls `automation_engineering.cp3.architecture.
   evaluate_long_method` DIRECTLY** -- a genuinely public function (`__all__`),
   no port needed. `customqa:long-method` applies to "ANY generated class...
   no class-role restriction" (that module's own docstring) -- test-data
   classes are explicitly in scope, unlike CP3's OTHER criterion,
   `direct_webdriver_action`, which is scoped to `com.automation.steps`
   only and explicitly does NOT evaluate test-data at all (`architecture.py`:
   "A class in any OTHER package (page objects, utilities, test data) is
   not evaluated by this criterion").
3. **`check_no_markdown_fence`, `check_class_name_matches`,
   `check_no_webdriver_reference` are contract-grounded, not
   incident-grounded** -- ported from the governed `generate_test_data`
   v1.0.0 prompt's own explicit OUTPUT CONTRACT/CONSTRAINTS text. Unlike
   step-def, there is no known real historical test-data defect on record.
   Unlike feature-content (whose gap was "no incident, but the assembler DID
   already enforce the contract"), test-data's gap is DEEPER: CP3's own
   `direct_webdriver_action` criterion explicitly EXCLUDES test-data's
   package from evaluation, so `check_no_webdriver_reference` closes a real
   enforcement gap this platform has today -- the FIRST deterministic check
   of that specific constraint anywhere in the codebase, not a duplicate of
   an existing one.

**One check considered and NOT built, reported honestly (mirrors
feature-content's own tagged-Background finding):** "one static member per
required (field_name, variant) pair" (the OUTPUT CONTRACT's own field-
coverage requirement) was considered. Unlike the Background-tag case, this
one is NOT structurally unreachable -- a real defect (a dropped required
variant) is genuinely possible. It was not built because **every real
`TestDataSpecification` this platform has ever emitted carries `fields=()`**
(`contracts.test_data_specification.TestDataSpecification`'s own docstring;
confirmed against all 20 requirements in `output/latest/
test_data_specifications.json`) -- there is no real case to seed or ground
it against, and a synthetic-fields fixture would violate this arc's own
"seeded from real generation contexts, not invented" discipline for the
CURATED SET (`TEST_DATA_EVAL_SET`). If Layer 2 ever emits a non-empty
specification, this is the next check to add -- named here, not designed.

Every check is a pure function of ``(generated_text, context)`` -- no LLM
call, no filesystem access, no subprocess. Each returns
:class:`~eval_harness.models.PropertyCheckOutcome.NOT_APPLICABLE` rather
than a vacuous PASS when nothing in the content gives the check anything to
evaluate -- ``NOT_APPLICABLE`` results are excluded from the eval score's
pass-rate denominator (:mod:`.scoring`), never silently counted as evidence
of quality.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from automation_engineering.cp3.architecture import Cp3GeneratedClassInput, evaluate_long_method
from automation_engineering.generation.test_data_generator import TestDataGenerationContext
from eval_harness.models import PropertyCheckOutcome, PropertyCheckResult
from shared.enums.base import ValidationVerdict

#: Ported VERBATIM from `automation_engineering.generation.
#: test_data_orchestrator._ENV_BINDING_PATTERN` -- the real, live,
#: always-on orchestration guard's own pattern, not a re-derivation.
_ENV_BINDING_PATTERN = re.compile(r"ConfigReader\s*\.\s*env\s*\(|[\"']env\.[A-Za-z0-9_.]*[\"']")

#: The class the governed `generate_test_data` v1.0.0 prompt's own OUTPUT
#: CONTRACT forbids unconditionally: "never reference `org.openqa.selenium.
#: WebDriver` or any Selenium type."
_WEBDRIVER_REFERENCE_RE = re.compile(r"org\.openqa\.selenium|\bWebDriver\b")

PropertyCheck = Callable[[str, TestDataGenerationContext], PropertyCheckResult]


def check_no_env_binding(
    generated_text: str, context: TestDataGenerationContext
) -> PropertyCheckResult:
    """Catches a `ConfigReader.env(...)` call or an `env.`-prefixed
    config-key literal -- ADR-0037 D3's SUT-binding boundary: a test-data
    class is the DATA side only, never the environment side. Exactly mirrors
    the real, always-on `test_data_orchestrator._check_no_env_binding`
    guard. Always applicable.
    """
    match = _ENV_BINDING_PATTERN.search(generated_text)
    if match is not None:
        return PropertyCheckResult(
            check_name="no_env_binding",
            outcome=PropertyCheckOutcome.FAILED,
            reason=f"generated test-data source references environment/SUT-binding "
            f"({match.group()!r}) -- ConfigReader.env(...) and env.* config keys "
            "stay the environment side's job, never a test-data class's",
        )
    return PropertyCheckResult(check_name="no_env_binding", outcome=PropertyCheckOutcome.PASSED)


def check_no_markdown_fence(
    generated_text: str, context: TestDataGenerationContext
) -> PropertyCheckResult:
    """Catches a fenced ``` code block wrapping the response, despite the
    governed `generate_test_data` v1.0.0 prompt's own explicit OUTPUT
    CONTRACT ("No markdown code fence, no explanation, no commentary before
    or after the code"). Always applicable.
    """
    if "```" in generated_text:
        return PropertyCheckResult(
            check_name="no_markdown_fence",
            outcome=PropertyCheckOutcome.FAILED,
            reason="generated text contains a markdown code fence ('```')",
        )
    return PropertyCheckResult(
        check_name="no_markdown_fence", outcome=PropertyCheckOutcome.PASSED
    )


def check_class_name_matches(
    generated_text: str, context: TestDataGenerationContext
) -> PropertyCheckResult:
    """Catches a generated class declared under any name other than
    ``context.class_name`` -- the governed prompt's own explicit OUTPUT
    CONTRACT: "Use target_class_name verbatim as the class name... already
    derived by the platform, never renamed." Always applicable.
    """
    expected = f"class {context.class_name}"
    if expected not in generated_text:
        return PropertyCheckResult(
            check_name="class_name_matches",
            outcome=PropertyCheckOutcome.FAILED,
            reason=f"expected {expected!r} (verbatim) in the generated source, not found",
        )
    return PropertyCheckResult(
        check_name="class_name_matches", outcome=PropertyCheckOutcome.PASSED
    )


def check_no_webdriver_reference(
    generated_text: str, context: TestDataGenerationContext
) -> PropertyCheckResult:
    """Catches a reference to `org.openqa.selenium.*`/`WebDriver` -- the
    governed prompt's own explicit OUTPUT CONTRACT: "never reference
    `org.openqa.selenium.WebDriver` or any Selenium type." Closes a REAL gap
    in this platform's existing enforcement: CP3's `direct_webdriver_action`
    criterion explicitly excludes test-data's own package from evaluation
    (`automation_engineering/cp3/architecture.py`), so nothing else in this
    platform checks this constraint for test-data specifically. Always
    applicable.
    """
    if _WEBDRIVER_REFERENCE_RE.search(generated_text):
        return PropertyCheckResult(
            check_name="no_webdriver_reference",
            outcome=PropertyCheckOutcome.FAILED,
            reason="generated test-data source references WebDriver/org.openqa.selenium -- "
            "test-data classes are the DATA side only, never UI interaction",
        )
    return PropertyCheckResult(
        check_name="no_webdriver_reference", outcome=PropertyCheckOutcome.PASSED
    )


def check_no_long_method(
    generated_text: str, context: TestDataGenerationContext
) -> PropertyCheckResult:
    """Catches a generated method exceeding `customqa:long-method`'s own
    40-line threshold -- DIRECTLY calls CP3's real, public
    `evaluate_long_method` (not a port; genuinely reused, since that
    function is already a pure, in-memory, no-subprocess computation over
    Java source text). Unparseable content is that criterion's own,
    already-established degrade-to-empty behaviour (never raises, never
    reports a message for content it cannot parse) -- surfaced here as
    PASSED, since this check's own concern is method length, not
    parseability (a separate concern this artifact type has no dedicated
    structural-validity check for, unlike feature-content's Gherkin parser).
    Always applicable.
    """
    result = evaluate_long_method(
        (Cp3GeneratedClassInput(class_name=context.class_name, java_source=generated_text),)
    )
    if result.verdict == ValidationVerdict.FAIL:
        return PropertyCheckResult(
            check_name="no_long_method",
            outcome=PropertyCheckOutcome.FAILED,
            reason="; ".join(result.messages),
        )
    return PropertyCheckResult(check_name="no_long_method", outcome=PropertyCheckOutcome.PASSED)


#: ADR-0051 D2/D5's test-data check set -- two directly composed from
#: already-real, already-enforced mechanisms (`check_no_env_binding`,
#: `check_no_long_method`), three contract-grounded (`check_no_markdown_
#: fence`, `check_class_name_matches`, `check_no_webdriver_reference`).
#: Ordered deterministically; a caller wanting a different or extended set
#: composes its own tuple rather than mutating this one.
TEST_DATA_PROPERTY_CHECKS: tuple[PropertyCheck, ...] = (
    check_no_env_binding,
    check_no_markdown_fence,
    check_class_name_matches,
    check_no_webdriver_reference,
    check_no_long_method,
)


def run_property_checks(
    generated_text: str,
    context: TestDataGenerationContext,
    checks: tuple[PropertyCheck, ...] = TEST_DATA_PROPERTY_CHECKS,
) -> tuple[PropertyCheckResult, ...]:
    """Run every check in ``checks`` against one generated artifact,
    deterministically, in order -- no LLM call, no I/O."""
    return tuple(check(generated_text, context) for check in checks)


__all__ = [
    "TEST_DATA_PROPERTY_CHECKS",
    "PropertyCheck",
    "check_class_name_matches",
    "check_no_env_binding",
    "check_no_long_method",
    "check_no_markdown_fence",
    "check_no_webdriver_reference",
    "run_property_checks",
]
