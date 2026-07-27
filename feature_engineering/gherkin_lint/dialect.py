"""Port of gherkin-lint's ``rules/utils/gherkin.js`` node-type resolution.

A ``Scenario`` and a ``Scenario Outline`` share the same AST node shape —
they differ only in which dialect keyword the parser matched. Several rules
(``no-examples-in-scenarios``, ``no-scenario-outlines-without-examples``,
``scenario-size``, ``indentation``) need that distinction, so it is resolved
here the same way the npm tool resolves it: by looking up the node's
``keyword`` string in the active language's dialect table.
"""

from __future__ import annotations

from typing import Any

from gherkin.dialect import Dialect

_STEP_KEYS = {"given", "when", "then", "and", "but"}

_NODE_TYPE_BY_KEY = {
    "feature": "Feature",
    "rule": "Rule",
    "background": "Background",
    "scenario": "Scenario",
    "scenariooutline": "Scenario Outline",
    "examples": "Examples",
}


def dialect_key(node: dict[str, Any], language: str) -> str | None:
    """The dialect table key (e.g. ``"given"``, ``"scenarioOutline"``) whose
    keyword list contains ``node["keyword"]``.

    Mirrors ``getLanguageInsitiveKeyword`` (sic, upstream's spelling) in
    gherkin-lint's source.
    """
    dialect = Dialect.for_name(language) or Dialect.for_name("en")
    assert dialect is not None
    keyword = node.get("keyword")
    for key, keywords in dialect.spec.items():
        if isinstance(keywords, list) and keyword in keywords:
            return str(key)
    return None


def node_type(node: dict[str, Any], language: str) -> str:
    """One of Feature/Rule/Background/Scenario/Scenario Outline/Examples/Step/""."

    Mirrors ``getNodeType`` in gherkin-lint's source.
    """
    key = dialect_key(node, language)
    if key is None:
        return ""
    lowered = key.lower()
    if lowered in _STEP_KEYS:
        return "Step"
    return _NODE_TYPE_BY_KEY.get(lowered, "")
