"""Loads ``.gherkin-lintrc`` verbatim as the linter's config contract.

Same 17 rule names, same config shapes as the committed
``docs/reference/automation-poc/.gherkin-lintrc`` (ADR-0043 D3) — that file
drops into this loader unchanged. A rule name outside the closed 17-rule set
is rejected: extending the set requires a future ADR (D3, Recommendation 4).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

#: The 17 rule names ADR-0043 D3 locks. This set is closed, not "currently" 17.
KNOWN_RULES: frozenset[str] = frozenset(
    {
        "no-unnamed-features",
        "no-unnamed-scenarios",
        "no-empty-file",
        "no-files-without-scenarios",
        "no-dupe-feature-names",
        "no-dupe-scenario-names",
        "no-duplicate-tags",
        "no-homogenous-tags",
        "no-scenario-outlines-without-examples",
        "no-examples-in-scenarios",
        "no-partially-commented-tag-lines",
        "no-trailing-spaces",
        "no-multiple-empty-lines",
        "new-line-at-eof",
        "indentation",
        "name-length",
        "scenario-size",
    }
)


class GherkinLintConfigError(ValueError):
    """Raised when a ``.gherkin-lintrc`` file names a rule outside KNOWN_RULES."""


def is_rule_enabled(rule_config: Any) -> bool:
    """Mirror gherkin-lint's ``isRuleEnabled``: ``"on"`` or ``["on", ...]``."""
    if isinstance(rule_config, list):
        return bool(rule_config) and rule_config[0] == "on"
    return bool(rule_config == "on")


def rule_option(rule_config: Any) -> Any:
    """The rule's own config value: ``rule_config[1]`` if a pair, else ``{}``.

    Mirrors ``runAllEnabledRules``'s ``ruleConfig`` extraction in gherkin-lint's
    ``rules.js``.
    """
    if isinstance(rule_config, list) and len(rule_config) > 1:
        return rule_config[1]
    return {}


def load_config(path: str | Path) -> dict[str, Any]:
    """Load a ``.gherkin-lintrc`` file, rejecting any rule name outside KNOWN_RULES."""
    raw: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    unknown = set(raw) - KNOWN_RULES
    if unknown:
        raise GherkinLintConfigError(
            "Unknown Gherkin lint rule(s) in config, outside the ADR-0043 D3 "
            f"17-rule set: {sorted(unknown)}"
        )
    return raw


def enabled_rules(config: dict[str, Any]) -> dict[str, Any]:
    """Map of enabled rule name -> its option value, for rules ``"on"`` in config."""
    return {
        name: rule_option(value) for name, value in config.items() if is_rule_enabled(value)
    }
