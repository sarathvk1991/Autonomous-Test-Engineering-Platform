"""CP3's `direct_webdriver_action` criterion (ADR-0044 D5 revision,
2026-08-04 -- the F4 discovery's Path A, build task 2 of 2): a static,
`javalang`-based, class-role-aware check for the half of `customqa:*`
SonarQube cannot natively express.

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

Static, no SUT, no browser, no Sonar, no network call: a pure function of
already-in-memory Java source text, mirroring ADR-0044 D6/CP4's own
"static, no live dependency" posture for locator health. Feeds CP3's
composite gate as a sixth criterion (`CP3_CRITERIA`), alongside the four
coverage criteria and the Sonar quality gate -- `evaluate_cp3` composes it
exactly like the other five, `overall_verdict` unchanged as "PASS iff every
named criterion is PASS."
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import javalang

from automation_engineering.catalog.java_source import parse_java_file
from automation_engineering.cp3.models import Cp3CriterionResult
from shared.enums.base import ValidationVerdict

CRITERION_DIRECT_WEBDRIVER_ACTION = "direct_webdriver_action"

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


__all__ = [
    "CRITERION_DIRECT_WEBDRIVER_ACTION",
    "STEP_DEFINITION_PACKAGE",
    "Cp3GeneratedClassInput",
    "evaluate_direct_webdriver_action",
]
