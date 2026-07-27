"""Config-loading tests for the Gherkin linter (ADR-0043 D3).

Proves the committed POC `.gherkin-lintrc` drops into the loader verbatim
(same 17 rule names, same config shapes) and that a rule name outside the
closed 17-rule set is rejected rather than silently accepted.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from feature_engineering.gherkin_lint.config import (
    KNOWN_RULES,
    GherkinLintConfigError,
    enabled_rules,
    is_rule_enabled,
    load_config,
    rule_option,
)

POC_LINTRC = Path("docs/reference/automation-poc/.gherkin-lintrc")


def test_known_rules_has_exactly_seventeen_entries() -> None:
    assert len(KNOWN_RULES) == 17


def test_poc_lintrc_loads_verbatim() -> None:
    config = load_config(POC_LINTRC)
    raw = json.loads(POC_LINTRC.read_text(encoding="utf-8"))

    assert config == raw
    assert set(config) == KNOWN_RULES, (
        "committed .gherkin-lintrc must configure exactly the 17 known rules"
    )


def test_poc_lintrc_every_rule_is_on() -> None:
    config = load_config(POC_LINTRC)
    for name, value in config.items():
        assert is_rule_enabled(value), f"{name} is expected 'on' in the committed POC config"


def test_poc_lintrc_config_shapes_are_honored() -> None:
    config = load_config(POC_LINTRC)
    enabled = enabled_rules(config)

    assert rule_option(config["no-dupe-scenario-names"]) == "in-feature"
    assert rule_option(config["new-line-at-eof"]) == "yes"
    assert rule_option(config["indentation"]) == {
        "Feature": 0,
        "Background": 2,
        "Scenario": 2,
        "Step": 4,
        "Examples": 4,
        "example": 6,
        "given": 4,
        "when": 4,
        "then": 4,
        "and": 4,
        "but": 4,
    }
    assert rule_option(config["name-length"]) == {"Feature": 70, "Scenario": 90, "Step": 120}
    assert rule_option(config["scenario-size"]) == {
        "steps-length": {"Background": 12, "Scenario": 12}
    }
    # Plain "on" rules carry no extra option.
    assert enabled["no-unnamed-features"] == {}
    assert enabled["no-empty-file"] == {}


def test_unknown_rule_is_rejected(tmp_path: Path) -> None:
    bad_config = tmp_path / ".gherkin-lintrc"
    bad_config.write_text(json.dumps({"no-unnamed-features": "on", "no-eighteenth-rule": "on"}))

    with pytest.raises(GherkinLintConfigError):
        load_config(bad_config)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("on", True),
        ("off", False),
        (["on", "in-feature"], True),
        (["off", "in-feature"], False),
        ([], False),
    ],
)
def test_is_rule_enabled(value: object, expected: bool) -> None:
    assert is_rule_enabled(value) is expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("on", {}),
        (["on", "in-feature"], "in-feature"),
        (["on", {"a": 1}], {"a": 1}),
    ],
)
def test_rule_option(value: object, expected: object) -> None:
    assert rule_option(value) == expected
