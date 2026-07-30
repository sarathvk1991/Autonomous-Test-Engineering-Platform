"""Capture-to-parameter correlation for step definitions (ADR-0044 D4(c)).

The catalog's javalang-based parameter extraction is sound (confirmed by
direct inspection: parameter count, order, and Java type -- including the
boxed-vs-primitive distinction -- all extract correctly against every
plain/built-in parameter shape). What the catalog did not yet record is
the ALIGNMENT between a step definition's own Gherkin-annotation captures
(``{string}``, a regex capture group, ...) and its Java parameters --
exactly the data ADR-0044 D4(c) needs to judge "does this step
definition's parameter shape fit the Gherkin step it would bind to: count,
order, and type."

This module only RECORDS that alignment for a step definition's own
annotation-plus-method (both already known, both already sound). It does
not compare one step definition against a *different* Gherkin step from a
future generated feature -- that comparison is D4's own reuse-safety job,
not built here. Recording a step definition's self-consistency (does its
own pattern's captures fit its own parameters) is a meaningful, useful
signal on its own -- a step definition whose own captures and parameters
don't line up is a red flag regardless of what it might later be matched
against -- and it is exactly the shape of data D4 will need to reuse when
comparing against a *different* Gherkin step's own capture list.
"""

from __future__ import annotations

import re

from automation_engineering.catalog.models import (
    JavaParameter,
    ParameterCorrelation,
    SignatureAlignment,
    StepCapture,
)

#: Cucumber Expressions' built-in parameter types (cucumber-expressions
#: library, `io.cucumber.java.en.*`) mapped to the Java type(s) each one
#: legitimately binds to -- both the primitive and its boxed form, since
#: Cucumber-JVM accepts either.
CUCUMBER_EXPRESSION_TYPES: dict[str, frozenset[str]] = {
    "string": frozenset({"String"}),
    "word": frozenset({"String"}),
    "int": frozenset({"int", "Integer"}),
    "float": frozenset({"float", "Float"}),
    "double": frozenset({"double", "Double"}),
    "long": frozenset({"long", "Long"}),
    "short": frozenset({"short", "Short"}),
    "byte": frozenset({"byte", "Byte"}),
    "biginteger": frozenset({"BigInteger"}),
    "bigdecimal": frozenset({"BigDecimal"}),
}

#: Trailing parameter types Cucumber-JVM binds AFTER all step-text captures
#: -- never corresponding to a placeholder/capture group. Recognized here
#: by exact, unambiguous type name only: ``DataTable`` is structurally
#: distinct from anything a capture could produce. A docstring-bound
#: parameter is deliberately NOT included -- Cucumber conventionally binds
#: it as a plain ``String``, which is indistinguishable, from the step
#: definition's Java signature alone, from a genuinely miscounted extra
#: ``String`` parameter (the actual presence of a docstring is a property
#: of a step's *invocation* in a `.feature` file, not of the step
#: definition's own declared annotation+method -- outside what a
#: definition-only scan can see). Treating an unrecognized trailing
#: ``String`` as a real arity concern, rather than assuming it is a
#: docstring, is the conservative, correct default for a signature-fit
#: check: D4's whole discipline is escalating the ambiguous case, never
#: silently assuming the benign explanation (ADR-0044 D4's own "any one
#: failing routes to human review, never a silent fallback").
NON_CAPTURE_TRAILING_TYPES = frozenset({"DataTable"})

_CUCUMBER_EXPRESSION_CAPTURE_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def parse_captures(pattern: str) -> tuple[StepCapture, ...]:
    """Ordered captures from a step-definition annotation's pattern text --
    Cucumber Expression placeholders if any are present, else regex
    capturing groups if the pattern looks like a regex, else none (a plain
    phrase with no placeholders binds zero captures either way)."""
    if _CUCUMBER_EXPRESSION_CAPTURE_RE.search(pattern):
        return _parse_cucumber_expression_captures(pattern)
    if _looks_like_regex(pattern):
        return _parse_regex_captures(pattern)
    return ()


def _looks_like_regex(pattern: str) -> bool:
    return bool(re.search(r"(?<!\\)\(", pattern))


def _parse_cucumber_expression_captures(pattern: str) -> tuple[StepCapture, ...]:
    matches = list(_CUCUMBER_EXPRESSION_CAPTURE_RE.finditer(pattern))
    return tuple(
        StepCapture(index=i, style="cucumber_expression", expression_type=m.group(1).lower())
        for i, m in enumerate(matches)
    )


def _parse_regex_captures(pattern: str) -> tuple[StepCapture, ...]:
    count = _count_regex_capturing_groups(pattern)
    return tuple(StepCapture(index=i, style="regex", expression_type=None) for i in range(count))


def _count_regex_capturing_groups(pattern: str) -> int:
    """The number of CAPTURING groups in a regex-style annotation pattern --
    delegated to Python's own ``re`` engine (real, well-tested group
    accounting: non-capturing ``(?:...)``, lookaround, and named groups are
    all handled correctly by the engine itself, not by a hand-rolled
    counter) wherever the pattern is valid Python regex syntax. Falls back
    to a narrow bracket scan only for the rare pattern Python's ``re``
    cannot compile (e.g. a Java-only regex construct) -- the fallback is
    intentionally conservative, not a full Java-regex-dialect parser."""
    try:
        return re.compile(pattern).groups
    except re.error:
        return _count_regex_capturing_groups_fallback(pattern)


def _count_regex_capturing_groups_fallback(pattern: str) -> int:
    count = 0
    index = 0
    escaped = False
    while index < len(pattern):
        char = pattern[index]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == "(":
            if pattern[index + 1 : index + 2] != "?":
                count += 1
            elif pattern[index + 2 : index + 3] == "<" and pattern[index + 3 : index + 4] not in {
                "=",
                "!",
            }:
                count += 1  # a Java named group, "(?<name>...)" -- capturing
        index += 1
    return count


def _type_compatible(capture: StepCapture, parameter_type: str) -> bool:
    if capture.expression_type is None:
        return True  # regex capture: no independently declared type to disagree with
    accepted = CUCUMBER_EXPRESSION_TYPES.get(capture.expression_type)
    if accepted is None:
        return True  # a custom/unrecognized expression type -- not determinable, not a mismatch
    return parameter_type in accepted


def correlate(pattern: str, parameters: tuple[JavaParameter, ...]) -> SignatureAlignment:
    """Record a step definition's own capture <-> parameter alignment.

    Positional correlation (capture *i* <-> parameter *i*), exactly
    Cucumber-JVM's own binding rule. A single trailing parameter beyond
    the capture count is recognized as a legitimate non-capture parameter
    only when its type is one of :data:`NON_CAPTURE_TRAILING_TYPES`
    (``DataTable``) -- anything else with a count mismatch is recorded as
    an arity mismatch, never silently assumed benign.
    """
    captures = parse_captures(pattern)
    non_capture_parameters: tuple[JavaParameter, ...] = ()
    correlatable = parameters
    if (
        len(parameters) == len(captures) + 1
        and parameters[-1].java_type in NON_CAPTURE_TRAILING_TYPES
    ):
        non_capture_parameters = (parameters[-1],)
        correlatable = parameters[:-1]

    if len(correlatable) != len(captures):
        return SignatureAlignment(
            captures=captures,
            correlations=(),
            non_capture_parameters=non_capture_parameters,
            is_aligned=False,
            mismatch_reason="arity",
        )

    correlations = tuple(
        ParameterCorrelation(
            capture=capture,
            parameter=parameter,
            type_compatible=_type_compatible(capture, parameter.java_type),
        )
        for capture, parameter in zip(captures, correlatable, strict=True)
    )
    is_aligned = all(c.type_compatible for c in correlations)
    return SignatureAlignment(
        captures=captures,
        correlations=correlations,
        non_capture_parameters=non_capture_parameters,
        is_aligned=is_aligned,
        mismatch_reason=None if is_aligned else "type",
    )


__all__ = [
    "CUCUMBER_EXPRESSION_TYPES",
    "NON_CAPTURE_TRAILING_TYPES",
    "correlate",
    "parse_captures",
]
