"""ADR-0051 D2's deterministic property/assertion checks for one generated
utility artifact (`LiveUtilityGenerator`'s raw output).

**Composed, not invented (ADR-0051 D1, the reframe) -- and CONTRACT-grounded,
not incident-grounded, checked directly rather than assumed.** Utility is the
FIFTH artifact type this harness covers. Unlike page-object (THREE real,
measured defects from the 2026-08-10 live regeneration run,
`[[cap-page-object-live-regen-findings]]`), utility generation has never once
run live: `LiveUtilityGenerator` exists, but utility generation is not wired
into stage 15 at all (`CachingUtilityGenerator`'s own module docstring,
2026-08-21 -- `run_automation_engineering_stage` accepts no
`utility_matcher`/`utility_generator` parameters) and was never part of the
one measured live corpus (`docs/architecture/mentor-feedback-scoping.md`'s own
20-call distribution). **There is no real utility INCIDENT to replay -- every
check below is grounded in the governed `generate_utilities` v1.0.0 prompt's
own explicit OUTPUT CONTRACT/CONSTRAINTS text
(`automation_engineering/prompts/versions/generate_utilities_v1.0.0.txt`),
the same grounding basis feature-content/test-data used, not step-def/
page-object's incident-replay basis.**

**Five checks, the honest count -- not forced to match any other
increment's own number.** `UtilityGenerationContext` (`utility_generator.py`)
carries no `method_name` field the way `PageObjectGenerationContext` does (no
caller-supplied method name to check verbatim presence of, the way page-
object's `check_method_names_present` does) -- a method-name-fidelity check
was considered and is NOT built here for that reason, not merely skipped
(see "Considered and NOT built," below):

1. **`check_no_markdown_fence`** -- the prompt's own OUTPUT CONTRACT: "No
   markdown code fence, no explanation, no commentary before or after the
   code." Mirrors `test_data_properties.check_no_markdown_fence` exactly,
   ported to a different artifact type's own contract text.
2. **`check_class_name_matches`** -- the prompt's own OUTPUT CONTRACT: "Use
   class_name verbatim as the class name." Mirrors
   `test_data_properties.check_class_name_matches` exactly.
3. **`check_static_utility_shape`** -- utility's OWN, most distinctive
   contract clause, held by no other artifact type this harness covers: "The
   class must be declared final with exactly one private, no-argument
   constructor, and every method must be static... no instance state, no
   instance methods" (the prompt's own CONSTRAINTS text, mirroring the
   tracked baseline's own real `ConfigReader` shape,
   `test-suite-baseline/src/test/java/com/automation/base/ConfigReader.java`
   -- verified directly against a real `javalang` parse of that file: a
   `final` class, one `{'private'}`-modifier no-arg constructor, and every
   method (`load`/`env`/`data`/`require`) carrying `'static'`). A genuinely
   NEW structural check, not a port of an existing CP3/CP4 criterion -- no
   existing gate checks "is this class a stateless static-utility shape."
   Parses via the same `javalang`/`parse_java_file` primitive CP3 uses,
   degrading to `NOT_APPLICABLE` (not a false `FAILED`) on unparseable Java
   or on text declaring no class under `context.class_name` at all --
   mirroring CP3's own `(JavaSyntaxError, LexerError)` degrade pattern.
4. **`check_no_selenium_or_basepage_reference`** -- the prompt's own
   CONSTRAINTS text: "Never import or reference
   org.openqa.selenium.WebDriver, WebElement, By, or any other Selenium
   type, and never extend BasePage or any page-object class." A stricter
   cousin of `test_data_properties.check_no_webdriver_reference` (which only
   forbids `WebDriver`/`org.openqa.selenium`) -- utility's own contract
   additionally forbids extending `BasePage`, so this check adds that
   proscription rather than reusing test-data's pattern unchanged. Bare `By`
   is deliberately NOT regex-matched on its own (a common English word,
   false-positive-prone) -- any real `By` usage is still caught, since it is
   either imported (`org.openqa.selenium.By`, caught by the import-prefix
   match) or fully qualified in source (`org.openqa.selenium.By.id(...)`,
   same match) -- there is no real way to reference Selenium's `By` type in
   generated Java without one of those two shapes appearing.
5. **`check_no_long_method`** -- calls CP3's real, PUBLIC
   `evaluate_long_method` (`automation_engineering.cp3.architecture`)
   DIRECTLY, no port needed -- `customqa:long-method` applies to "ANY
   generated class... no class-role restriction" (that module's own
   docstring), utility included, mirroring
   `test_data_properties.check_no_long_method` exactly.

**Considered and NOT built, reported honestly.** A check verifying the
generated method's parameter count/order matches `context.need.captures`
(the INPUT CONTRACT's own "your method's own parameters must correspond to
these, in order" clause) was considered. Unlike page-object (which carries
an explicit, caller-supplied `method_name` to anchor a "this exact method's
parameters" check against), `UtilityGenerationContext` names no specific
method at all -- a freshly generated utility class may declare one or
several methods, and nothing in the context says which one is "the" method
the captures bind to. A check here would have to guess which declared
method the captures apply to, which is not a deterministic property check,
it is a heuristic with no real anchor -- left out on that basis, not merely
skipped for scope (the same "don't force a check with no real anchor"
discipline `test_data_properties`'s own field-variant-coverage finding
already established for a different artifact type).

Every check is a pure function of ``(generated_text, context)`` -- no LLM
call, no filesystem access, no subprocess. Each returns
:class:`~eval_harness.models.PropertyCheckOutcome.NOT_APPLICABLE` rather than
a vacuous PASS when nothing in the content gives the check anything to
evaluate -- ``NOT_APPLICABLE`` results are excluded from the eval score's
pass-rate denominator (:mod:`.scoring`), never silently counted as evidence
of quality.
"""

from __future__ import annotations

import re
from collections.abc import Callable

import javalang

from automation_engineering.catalog.java_source import parse_java_file
from automation_engineering.cp3.architecture import Cp3GeneratedClassInput, evaluate_long_method
from automation_engineering.generation.utility_generator import UtilityGenerationContext
from eval_harness.models import PropertyCheckOutcome, PropertyCheckResult
from shared.enums.base import ValidationVerdict

#: `generate_utilities` v1.0.0's own CONSTRAINTS text, verbatim: "Never
#: import or reference org.openqa.selenium.WebDriver, WebElement, By, or any
#: other Selenium type... a utility that needs WebDriver access is a page
#: object, not a utility." Bare `By` is deliberately excluded (see module
#: docstring) -- any real usage still matches via the import prefix or a
#: fully-qualified reference.
_SELENIUM_REFERENCE_RE = re.compile(r"org\.openqa\.selenium|\bWebDriver\b|\bWebElement\b")

#: The prompt's own second CONSTRAINTS proscription: "never extend BasePage
#: or any page-object class."
_EXTENDS_BASEPAGE_RE = re.compile(r"\bextends\s+BasePage\b")

PropertyCheck = Callable[[str, UtilityGenerationContext], PropertyCheckResult]


def check_no_markdown_fence(
    generated_text: str, context: UtilityGenerationContext
) -> PropertyCheckResult:
    """Catches a fenced ``` code block wrapping the response, despite the
    governed `generate_utilities` v1.0.0 prompt's own explicit OUTPUT
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
    generated_text: str, context: UtilityGenerationContext
) -> PropertyCheckResult:
    """Catches a generated class declared under any name other than
    ``context.class_name`` -- the governed prompt's own explicit OUTPUT
    CONTRACT: "Use class_name verbatim as the class name -- already derived
    by the platform, never renamed." Always applicable.
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


def check_static_utility_shape(
    generated_text: str, context: UtilityGenerationContext
) -> PropertyCheckResult:
    """Guards utility's own most distinctive contract clause: "The class
    must be declared final with exactly one private, no-argument
    constructor, and every method must be static... no instance state, no
    instance methods" (`generate_utilities` v1.0.0's own CONSTRAINTS text,
    mirroring the tracked baseline's own real `ConfigReader` shape).

    ``NOT_APPLICABLE`` when `generated_text` is not parseable Java, or
    declares no class under `context.class_name` at all -- mirroring CP3's
    own `(JavaSyntaxError, LexerError)` degrade pattern
    (`automation_engineering.cp3.architecture`): a parse failure means
    "nothing here to evaluate the shape of," not "zero real shape defects
    were found."
    """
    try:
        parsed = parse_java_file(context.class_name, generated_text)
    except (javalang.parser.JavaSyntaxError, javalang.tokenizer.LexerError) as exc:
        return PropertyCheckResult(
            check_name="static_utility_shape",
            outcome=PropertyCheckOutcome.NOT_APPLICABLE,
            reason=f"generated text is not parseable Java -- no class shape to evaluate ({exc})",
        )

    class_decls = [
        node
        for _, node in parsed.tree.filter(javalang.tree.ClassDeclaration)
        if node.name == context.class_name
    ]
    if not class_decls:
        return PropertyCheckResult(
            check_name="static_utility_shape",
            outcome=PropertyCheckOutcome.NOT_APPLICABLE,
            reason=f"no class named {context.class_name!r} declared in the generated text -- "
            "no shape to evaluate",
        )
    class_decl = class_decls[0]

    issues: list[str] = []
    if "final" not in class_decl.modifiers:
        issues.append(f"{context.class_name} is not declared final")

    constructors = [
        node
        for _, node in parsed.tree.filter(javalang.tree.ConstructorDeclaration)
        if node.name == context.class_name
    ]
    if len(constructors) != 1:
        issues.append(
            f"expected exactly one constructor declared on {context.class_name}, "
            f"found {len(constructors)}"
        )
    else:
        constructor = constructors[0]
        if "private" not in constructor.modifiers:
            issues.append(f"{context.class_name}'s constructor is not private")
        if constructor.parameters:
            issues.append(f"{context.class_name}'s constructor is not no-argument")

    non_static_methods = [
        node.name
        for _, node in parsed.tree.filter(javalang.tree.MethodDeclaration)
        if "static" not in node.modifiers
    ]
    if non_static_methods:
        issues.append(f"non-static method(s) declared: {non_static_methods!r}")

    if issues:
        return PropertyCheckResult(
            check_name="static_utility_shape",
            outcome=PropertyCheckOutcome.FAILED,
            reason="; ".join(issues),
        )
    return PropertyCheckResult(
        check_name="static_utility_shape", outcome=PropertyCheckOutcome.PASSED
    )


def check_no_selenium_or_basepage_reference(
    generated_text: str, context: UtilityGenerationContext
) -> PropertyCheckResult:
    """Catches a reference to `org.openqa.selenium.*`/`WebDriver`/
    `WebElement`, or an `extends BasePage` declaration -- `generate_utilities`
    v1.0.0's own CONSTRAINTS text: "Never import or reference
    org.openqa.selenium.WebDriver, WebElement, By, or any other Selenium
    type, and never extend BasePage or any page-object class -- a utility
    that needs WebDriver access is a page object, not a utility." Always
    applicable.
    """
    reasons: list[str] = []
    selenium_match = _SELENIUM_REFERENCE_RE.search(generated_text)
    if selenium_match is not None:
        reasons.append(
            f"references {selenium_match.group()!r} -- a utility must never touch WebDriver, "
            "WebElement, or any other Selenium type"
        )
    if _EXTENDS_BASEPAGE_RE.search(generated_text):
        reasons.append(
            "extends BasePage -- a utility that needs WebDriver access is a page object, "
            "not a utility"
        )
    if reasons:
        return PropertyCheckResult(
            check_name="no_selenium_or_basepage_reference",
            outcome=PropertyCheckOutcome.FAILED,
            reason="; ".join(reasons),
        )
    return PropertyCheckResult(
        check_name="no_selenium_or_basepage_reference", outcome=PropertyCheckOutcome.PASSED
    )


def check_no_long_method(
    generated_text: str, context: UtilityGenerationContext
) -> PropertyCheckResult:
    """Catches a generated method exceeding `customqa:long-method`'s own
    40-line threshold -- DIRECTLY calls CP3's real, public
    `evaluate_long_method` (not a port; `customqa:long-method` applies to
    "ANY generated class... no class-role restriction," utility included).
    Unparseable content is that criterion's own, already-established
    degrade-to-empty behaviour (never raises, reports no message it cannot
    parse) -- surfaced here as PASSED, mirroring
    `test_data_properties.check_no_long_method`'s own identical discipline.
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


#: ADR-0051 D2/D5's utility check set -- the honest FIVE real, contract-
#: grounded checks (no known incident to ground against; see module
#: docstring), one of which (`check_static_utility_shape`) is a genuinely new
#: structural check no existing CP3/CP4 criterion already covers, one of
#: which (`check_no_long_method`) directly composes CP3's real, already-live
#: `evaluate_long_method`. Ordered deterministically; a caller wanting a
#: different or extended set composes its own tuple rather than mutating
#: this one.
UTILITY_PROPERTY_CHECKS: tuple[PropertyCheck, ...] = (
    check_no_markdown_fence,
    check_class_name_matches,
    check_static_utility_shape,
    check_no_selenium_or_basepage_reference,
    check_no_long_method,
)


def run_property_checks(
    generated_text: str,
    context: UtilityGenerationContext,
    checks: tuple[PropertyCheck, ...] = UTILITY_PROPERTY_CHECKS,
) -> tuple[PropertyCheckResult, ...]:
    """Run every check in ``checks`` against one generated artifact,
    deterministically, in order -- no LLM call, no I/O."""
    return tuple(check(generated_text, context) for check in checks)


__all__ = [
    "UTILITY_PROPERTY_CHECKS",
    "PropertyCheck",
    "check_class_name_matches",
    "check_no_long_method",
    "check_no_markdown_fence",
    "check_no_selenium_or_basepage_reference",
    "check_static_utility_shape",
    "run_property_checks",
]
