"""CP3's `direct_webdriver_action` and `long_method` criteria: two static,
`javalang`-based checks for BOTH halves of `customqa:*` -- neither is
Sonar-gated (ADR-0044 D5's revisions, 2026-08-04 and 2026-08-05).

`customqa:direct-webdriver-action`'s own rule text (the generation prompts,
`automation_engineering/generation/orchestrator.py`'s own
`DEFAULT_CUSTOMQA_STEP_DEFINITION_CONSTRAINTS`): "never call a WebDriver
method (findElement, click, sendKeys, get, etc.) or import
`org.openqa.selenium.WebDriver` directly in a step definition; every UI
interaction must go through a page-object method." The mirror, stated in
the page-object generation prompt: WebDriver calls are exactly where they
BELONG in a page object. This is a constraint about a call's CALLER-CLASS-
ROLE, not about the call site in isolation -- the reason F4's discovery
found no SonarQube rule (built-in or template-composed) can express it
precisely: Sonar's only native path, a disallowed-method template rule
plus a project-level path exclusion, approximates class role by FILE PATH
convention, drifts if that convention changes, and lives in project
settings rather than versioned code. This module inspects the REAL,
PARSED package declaration of each class it is handed -- the actual
semantic signal Java itself uses for a class's identity -- which is more
precise than a path glob and requires no server-side configuration at all.

`customqa:long-method`'s own rule text (the generation prompts): "keep every
generated method under 40 lines." This was originally meant to be verified
by SonarQube's own built-in `java:S138` ("Methods should not have too many
lines") -- cheap and real as a MECHANISM (`test-suite-baseline/sonar/
README.md`'s own live proof: a 47-line method flagged, a short one not) --
but a Sonar-config discovery (2026-08-05) found it structurally cannot
reach this platform's real generated code: `java:S138` is permanently
`scope:"MAIN"` (a rule-catalog property, not something a profile's
activation can override), while every class Layer 3 generates or promotes
lives under `src/test/java` (`automation_engineering/catalog/scanner.py`'s
own `JAVA_SOURCE_SUBPATH`, ADR-0037 Path A) -- `MAIN`-scope rules never
evaluate `testSourceDirectory` content, on any project, on any server. The
only Sonar-side workaround found (repointing `sonar.sources` to include the
test tree) would apply EVERY `MAIN`-scope rule in the active profile to
test code, not just S138 -- roughly 400 additional rules never intended for
this tree, a correctness hazard disguised as a config tweak, not a targeted
fix. `long-method` is therefore verified the same way
`direct-webdriver-action` already is: a static check against the real
parsed source, unconditioned on Sonar's own source/test classification.

**Line-span measurement.** A method's line count is `end_line - start_line
+ 1`, both 1-indexed, via
`automation_engineering.catalog.java_source.declaration_line_span` -- the
SAME start/end anchors `extract_declaration_span` already uses for the
catalog's own content-hash (annotations/modifiers through the closing brace
or terminating semicolon), as line numbers rather than a substring. This is
a PHYSICAL line count (every line in the span, including blank lines and
comments) -- matching the INTENT of `java:S138` ("too many lines") and
calibrated directly against its own live proof (`README.md`: a method
declared at line 12, flagged at "47 lines," consistent with an inclusive
declaration-line-through-closing-brace count). It may differ from
SonarJava's own exact internal counting by a line or two in edge cases
(e.g. whether a preceding `@Given(...)` annotation line is itself counted)
-- the same "heuristic, not byte-exact" honesty
`_webdriver_typed_names`/its own call-detection loop already states for its
own limitation, above.

**Scope: every generated class, not step-definition-only.** Unlike
`direct-webdriver-action` (a caller-CLASS-ROLE rule, scoped to step
definitions by its own text), `long-method` is a per-method size rule with
no class-role restriction -- a 41-line method is a violation in a step
definition, a page object, or a utility class alike. This function applies
no package filter at all, unlike `_evaluate_one_class` above.

Static, no SUT, no browser, no Sonar, no network call: a pure function of
already-in-memory Java source text, mirroring ADR-0044 D6/CP4's own
"static, no live dependency" posture for locator health. Both checks feed
CP3's composite gate (`CP3_CRITERIA`, now seven criteria), alongside the
four coverage criteria and the Sonar quality gate (generic Java quality
only, as of this same revision) -- `evaluate_cp3` composes them exactly
like the others, `overall_verdict` unchanged as "PASS iff every named
criterion is PASS."
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import javalang

from automation_engineering.catalog.java_source import declaration_line_span, parse_java_file
from automation_engineering.cp3.models import Cp3CriterionResult
from shared.enums.base import ValidationVerdict

CRITERION_DIRECT_WEBDRIVER_ACTION = "direct_webdriver_action"
CRITERION_LONG_METHOD = "long_method"

#: `customqa:long-method`'s own threshold ("keep every generated method
#: under 40 lines") -- the same value the (Sonar-inert) `customqa-profile
#: .xml` activates `java:S138` at, so the two artifacts state one number,
#: not two that could drift apart.
MAX_METHOD_LINES = 40

#: The generated suite's own step-definition package (the same default
#: `automation_engineering.generation.orchestrator.orchestrate_step_definition`
#: targets) -- this criterion's own scope, matching the rule's own text
#: ("never call... in a step definition"). A class in any OTHER package
#: (page objects, utilities, test data) is not evaluated by this criterion
#: at all -- neither passed nor failed, simply out of scope, exactly as
#: WebDriver usage is legitimate there.
STEP_DEFINITION_PACKAGE = "com.automation.steps"

_FORBIDDEN_IMPORT = "org.openqa.selenium.WebDriver"


@dataclass(frozen=True, slots=True)
class Cp3GeneratedClassInput:
    """One generated class's own real Java source -- ANY generated class
    (a step definition, a page object, a utility), never pre-filtered by
    the caller. Unlike :class:`~automation_engineering.cp4.models.
    Cp4PageObjectInput` (which trusts the caller's own "this is a page
    object" classification), this criterion determines class role itself,
    from the class's own parsed ``package`` declaration -- the precise
    signal a file-path convention can only approximate.
    """

    class_name: str
    java_source: str


def _is_step_definition_package(package_name: str) -> bool:
    return package_name == STEP_DEFINITION_PACKAGE or package_name.startswith(
        STEP_DEFINITION_PACKAGE + "."
    )


def _webdriver_typed_names(tree: javalang.tree.CompilationUnit) -> frozenset[str]:
    """Every field, parameter, and local-variable name declared with type
    ``WebDriver`` anywhere in the compilation unit -- the set a direct
    method-call check matches invocation qualifiers against."""
    names: set[str] = set()
    for _, field in tree.filter(javalang.tree.FieldDeclaration):
        if isinstance(field.type, javalang.tree.ReferenceType) and field.type.name == "WebDriver":
            names.update(d.name for d in field.declarators)
    for _, param in tree.filter(javalang.tree.FormalParameter):
        if isinstance(param.type, javalang.tree.ReferenceType) and param.type.name == "WebDriver":
            names.add(param.name)
    for _, local in tree.filter(javalang.tree.LocalVariableDeclaration):
        if isinstance(local.type, javalang.tree.ReferenceType) and local.type.name == "WebDriver":
            names.update(d.name for d in local.declarators)
    return frozenset(names)


def _evaluate_one_class(candidate: Cp3GeneratedClassInput) -> tuple[str, ...]:
    try:
        parsed = parse_java_file(candidate.class_name, candidate.java_source)
    except (javalang.parser.JavaSyntaxError, javalang.tokenizer.LexerError):
        # Unparsable content is a different criterion's concern (coverage's
        # own duplicate/unmapped checks already re-parse feature/step text
        # independently) -- this criterion has nothing to say about it.
        return ()
    if not _is_step_definition_package(parsed.package):
        return ()

    messages: list[str] = []

    # Import-based detection: the rule's own first proscription.
    if any(imp.path == _FORBIDDEN_IMPORT for imp in parsed.tree.imports):
        messages.append(
            f"{candidate.class_name}: imports {_FORBIDDEN_IMPORT} directly -- "
            "WebDriver must never be referenced in a step-definition class; "
            "route every UI interaction through a page-object method"
        )

    # Call-based detection: the rule's own second proscription. Matches a
    # MethodInvocation's own qualifier against every WebDriver-typed name
    # declared in the class -- direct, unchained calls (`driver.click()`),
    # the shape a generation violation would realistically take. A deeply
    # chained expression (`driver.findElement(...).click()`) is a known,
    # documented gap: javalang's own AST does not reliably preserve a
    # qualifier chain through nested invocations (verified directly against
    # this parser, not assumed) -- the same "heuristic, not exhaustive"
    # honesty CP4's own dynamic-XPath detection already states for its
    # equivalent limitation. The import-based check above still catches
    # such a class regardless, since the WebDriver type must be imported
    # to be referenced at all.
    webdriver_names = _webdriver_typed_names(parsed.tree)
    if webdriver_names:
        for _, invocation in parsed.tree.filter(javalang.tree.MethodInvocation):
            if invocation.qualifier in webdriver_names:
                messages.append(
                    f"{candidate.class_name}: calls "
                    f"{invocation.qualifier}.{invocation.member}(...) directly -- "
                    "a WebDriver method call in a step-definition class; route "
                    "through a page-object method instead"
                )

    return tuple(messages)


def evaluate_direct_webdriver_action(
    classes: Sequence[Cp3GeneratedClassInput],
) -> Cp3CriterionResult:
    """Evaluate `customqa:direct-webdriver-action` over every generated
    class in `classes`. Only classes whose own parsed package is (or is
    nested under) :data:`STEP_DEFINITION_PACKAGE` are evaluated; anything
    else (a page object, most concretely) never contributes a message here,
    regardless of what it imports or calls -- WebDriver usage there is
    correct, not merely unpenalized.

    Pure and deterministic: no network call, no subprocess, no live
    infrastructure of any kind. The same input always yields the same
    result.
    """
    messages = tuple(
        message for candidate in classes for message in _evaluate_one_class(candidate)
    )
    verdict = ValidationVerdict.FAIL if messages else ValidationVerdict.PASS
    return Cp3CriterionResult(
        criterion=CRITERION_DIRECT_WEBDRIVER_ACTION, verdict=verdict, messages=messages
    )


def _long_method_messages(candidate: Cp3GeneratedClassInput) -> tuple[str, ...]:
    try:
        parsed = parse_java_file(candidate.class_name, candidate.java_source)
    except (javalang.parser.JavaSyntaxError, javalang.tokenizer.LexerError):
        # Unparsable content is a different criterion's concern, mirroring
        # _evaluate_one_class above.
        return ()

    messages: list[str] = []
    for _, method in parsed.tree.filter(javalang.tree.MethodDeclaration):
        start_line, end_line = declaration_line_span(parsed, method)
        line_count = end_line - start_line + 1
        if line_count > MAX_METHOD_LINES:
            messages.append(
                f"{candidate.class_name}.{method.name}: this method has {line_count} lines, "
                f"which is greater than the {MAX_METHOD_LINES} lines authorized. Split it "
                "into smaller methods."
            )
    return tuple(messages)


def evaluate_long_method(classes: Sequence[Cp3GeneratedClassInput]) -> Cp3CriterionResult:
    """Evaluate `customqa:long-method` over every generated class in
    `classes` -- ALL of them, no class-role/package filter (unlike
    :func:`evaluate_direct_webdriver_action`, above): a method whose own
    declaration-line-through-closing-brace span exceeds
    :data:`MAX_METHOD_LINES` lines is a violation regardless of whether it
    lives in a step definition, a page object, or a utility class.

    Scoped to `MethodDeclaration` nodes only -- constructors are excluded,
    matching the rule's own text ("every generated method"), not
    `java:S138`'s exact scope (which SonarJava's own implementation applies
    to constructors too); this platform's generated constructors are
    presently small (a dependency-injecting one-liner in every generated
    step-definition class today), so this is a documented, deliberate
    narrowing, not an oversight.

    Pure and deterministic: no network call, no subprocess, no live
    infrastructure of any kind. The same input always yields the same
    result.
    """
    messages = tuple(
        message for candidate in classes for message in _long_method_messages(candidate)
    )
    verdict = ValidationVerdict.FAIL if messages else ValidationVerdict.PASS
    return Cp3CriterionResult(criterion=CRITERION_LONG_METHOD, verdict=verdict, messages=messages)


__all__ = [
    "CRITERION_DIRECT_WEBDRIVER_ACTION",
    "CRITERION_LONG_METHOD",
    "MAX_METHOD_LINES",
    "STEP_DEFINITION_PACKAGE",
    "Cp3GeneratedClassInput",
    "evaluate_direct_webdriver_action",
    "evaluate_long_method",
]
