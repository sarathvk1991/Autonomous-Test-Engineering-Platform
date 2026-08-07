r"""CP8, `junit-platform.properties` structural validity (ADR-0047 D7's
own third bullet, structural half): present, parses, `cucumber.glue`
declared and non-empty, `cucumber.plugin`'s own declared entries
syntactically well-formed.

**Deliberately NOT the semantic half.** Whether a `cucumber.glue` package
NAME actually corresponds to a real package in the assembled suite is
`suite_quality_governance.cp8.glue_resolution`'s own job (D7's own
semantic half, D8's own distinctive value) -- this module only checks the
properties FILE's own shape, never the catalog.

**A minimal, real-file-shaped parser, not a general-purpose
`java.util.Properties` clone.** This platform's own real
`junit-platform.properties` uses exactly three conventions: `#`-prefixed
comments, `key=value` pairs, and `\`-terminated line continuation
(`cucumber.plugin`'s own multi-line value) -- this module parses exactly
those, nothing more (no `:`-as-separator support, no Unicode escapes;
Java's own `.properties` spec supports both, this platform's own tracked
file uses neither).
"""

from __future__ import annotations

from pathlib import Path

from shared.enums.base import ValidationVerdict
from suite_quality_governance.cp8.models import (
    CRITERION_JUNIT_PLATFORM_PROPERTIES_VALID,
    Cp8CriterionResult,
)

JUNIT_PLATFORM_PROPERTIES_RELATIVE_PATH = Path("src/test/resources/junit-platform.properties")

CUCUMBER_GLUE_KEY = "cucumber.glue"
CUCUMBER_PLUGIN_KEY = "cucumber.plugin"


def _join_continuations(text: str) -> list[str]:
    r"""Collapse every `\`-terminated line into its own following line,
    the same continuation rule `java.util.Properties` applies -- the
    trailing backslash and the newline it precedes are both removed; the
    continuation line's own leading whitespace is stripped (matching this
    platform's own real file's indented continuation lines)."""
    logical_lines: list[str] = []
    buffer = ""
    for raw_line in text.splitlines():
        line = raw_line.lstrip() if buffer else raw_line
        if line.endswith("\\"):
            buffer += line[:-1]
            continue
        logical_lines.append(buffer + line)
        buffer = ""
    if buffer:
        logical_lines.append(buffer)
    return logical_lines


def parse_java_properties(text: str) -> dict[str, str]:
    """`key=value` pairs, comments and continuations already resolved
    (module docstring). A line with no `=` (and not a comment) is simply
    skipped -- contributing no key is how a caller downstream discovers
    the property it needed is genuinely absent."""
    properties: dict[str, str] = {}
    for line in _join_continuations(text):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("!"):
            continue
        if "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        properties[key.strip()] = value.strip()
    return properties


def _plugin_entry_messages(plugin_value: str) -> list[str]:
    """Each comma-separated `cucumber.plugin` entry must be a
    `name:path`-shaped pair, both halves non-empty -- the real shape this
    platform's own file uses (`message:target/cucumber-reports/
    messages.ndjson`, ...). A malformed entry (no `:`, an empty name, or
    an empty path) would fail Cucumber's own plugin-string parser at
    runtime before a single scenario executes."""
    messages: list[str] = []
    for entry in (e.strip() for e in plugin_value.split(",") if e.strip()):
        if ":" not in entry:
            messages.append(f"cucumber.plugin entry {entry!r} is not name:path-shaped")
            continue
        name, _, path = entry.partition(":")
        if not name.strip() or not path.strip():
            messages.append(f"cucumber.plugin entry {entry!r} has an empty name or path")
    return messages


def check_junit_platform_properties_valid(baseline_root: Path) -> Cp8CriterionResult:
    """Present, parses, `cucumber.glue` declared and non-empty,
    `cucumber.plugin`'s own entries well-formed (module docstring)."""
    properties_path = baseline_root / JUNIT_PLATFORM_PROPERTIES_RELATIVE_PATH
    if not properties_path.is_file():
        return Cp8CriterionResult(
            criterion=CRITERION_JUNIT_PLATFORM_PROPERTIES_VALID,
            verdict=ValidationVerdict.FAIL,
            messages=(f"no junit-platform.properties found at {properties_path}",),
        )
    properties = parse_java_properties(properties_path.read_text(encoding="utf-8"))

    messages: list[str] = []
    glue_value = properties.get(CUCUMBER_GLUE_KEY, "")
    if not glue_value.strip():
        messages.append(f"{CUCUMBER_GLUE_KEY} is missing or empty in {properties_path}")

    plugin_value = properties.get(CUCUMBER_PLUGIN_KEY, "")
    if plugin_value.strip():
        messages.extend(_plugin_entry_messages(plugin_value))

    if messages:
        return Cp8CriterionResult(
            criterion=CRITERION_JUNIT_PLATFORM_PROPERTIES_VALID,
            verdict=ValidationVerdict.FAIL,
            messages=tuple(messages),
        )
    return Cp8CriterionResult(
        criterion=CRITERION_JUNIT_PLATFORM_PROPERTIES_VALID, verdict=ValidationVerdict.PASS
    )


__all__ = [
    "CUCUMBER_GLUE_KEY",
    "CUCUMBER_PLUGIN_KEY",
    "JUNIT_PLATFORM_PROPERTIES_RELATIVE_PATH",
    "check_junit_platform_properties_valid",
    "parse_java_properties",
]
