"""Fixture-driven proof for all 17 ported gherkin-lint rules (ADR-0043 D3).

Each rule gets a dedicated violation fixture under
`tests/unit/fixtures/gherkin_lint/` that must fire *exactly* that rule (and
no other), plus a shared `clean.feature` that must stay silent under every
rule. Two rules are corpus-scoped (`no-dupe-feature-names`,
`no-dupe-scenario-names`) and are proved separately, against their own
multi-file fixtures, since a single-file fixture cannot exercise them.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from feature_engineering.gherkin_lint import load_config
from feature_engineering.gherkin_lint.linter import lint_corpus, lint_file, lint_source
from feature_engineering.gherkin_lint.source import parse_source_text

CONFIG = load_config(Path("docs/reference/automation-poc/.gherkin-lintrc"))
FIXTURES = Path("tests/unit/fixtures/gherkin_lint")

# rule name -> its dedicated single-file violation fixture. `no-empty-file`
# is annotated separately below: on a genuinely empty file, the real
# gherkin-lint tool fires it *together with* `no-unnamed-features` (both
# check `!feature` first) -- verified directly against upstream source, not
# a defect in this port.
PER_FILE_RULE_FIXTURES: dict[str, str] = {
    "no-unnamed-features": "no_unnamed_features_violation.feature",
    "no-unnamed-scenarios": "no_unnamed_scenarios_violation.feature",
    "no-files-without-scenarios": "no_files_without_scenarios_violation.feature",
    "no-duplicate-tags": "no_duplicate_tags_violation.feature",
    "no-homogenous-tags": "no_homogenous_tags_violation.feature",
    "no-scenario-outlines-without-examples": (
        "no_scenario_outlines_without_examples_violation.feature"
    ),
    "no-examples-in-scenarios": "no_examples_in_scenarios_violation.feature",
    "no-partially-commented-tag-lines": "no_partially_commented_tag_lines_violation.feature",
    "no-trailing-spaces": "no_trailing_spaces_violation.feature",
    "no-multiple-empty-lines": "no_multiple_empty_lines_violation.feature",
    "new-line-at-eof": "new_line_at_eof_violation.feature",
    "indentation": "indentation_violation.feature",
    "name-length": "name_length_violation.feature",
    "scenario-size": "scenario_size_violation.feature",
    "no-dupe-scenario-names": "scenario_dupe_in_feature_violation.feature",
}

RAW_SOURCE_RULES = {"no-trailing-spaces", "no-multiple-empty-lines", "new-line-at-eof"}


@pytest.mark.parametrize("rule,fixture_name", sorted(PER_FILE_RULE_FIXTURES.items()))
def test_rule_fires_on_its_violation_fixture(rule: str, fixture_name: str) -> None:
    result = lint_file(FIXTURES / fixture_name, CONFIG)
    fired = {v.rule for v in result.violations}
    assert fired == {rule}, f"expected only {rule!r} to fire on {fixture_name}, got {fired}"


@pytest.mark.parametrize("rule", sorted(PER_FILE_RULE_FIXTURES))
def test_rule_is_silent_on_clean_fixture(rule: str) -> None:
    result = lint_file(FIXTURES / "clean.feature", CONFIG)
    assert result.is_clean, (
        f"clean.feature must be silent under every rule, got {result.violations}"
    )


def test_clean_feature_is_silent_end_to_end() -> None:
    result = lint_file(FIXTURES / "clean.feature", CONFIG)
    assert result.violations == ()


def test_no_empty_file_fires_and_also_fires_no_unnamed_features() -> None:
    """A genuinely empty file trips two rules in the real gherkin-lint tool.

    Both `no-empty-file` and `no-unnamed-features` check `!feature` before
    anything else, so an empty file (no `Feature:` line at all) fires both.
    This is upstream behaviour, re-verified directly against
    `src/rules/no-empty-file.js` and `src/rules/no-unnamed-features.js`; the
    port preserves it rather than "fixing" it.
    """
    result = lint_file(FIXTURES / "no_empty_file_violation.feature", CONFIG)
    fired = {v.rule for v in result.violations}
    assert fired == {"no-empty-file", "no-unnamed-features"}


class TestRawSourceRulesCatchWhatAstAloneMisses:
    """The 3 rules that upstream's own source (`src/rules/*.js`) reads
    `file.lines` for: `no-trailing-spaces`, `no-multiple-empty-lines`,
    `new-line-at-eof`. (ADR-0043 D3 also names `indentation` and
    `no-partially-commented-tag-lines` as raw-source rules; re-reading
    upstream's actual source shows both operate purely on AST
    fields -- see the discrepancy note in the task report.)
    """

    @pytest.mark.parametrize("rule", sorted(RAW_SOURCE_RULES))
    def test_fires_via_raw_lines(self, rule: str) -> None:
        fixture = PER_FILE_RULE_FIXTURES[rule]
        result = lint_file(FIXTURES / fixture, CONFIG)
        assert {v.rule for v in result.violations} == {rule}


def test_no_dupe_feature_names_is_silent_within_a_single_file() -> None:
    result = lint_file(FIXTURES / "dupe_feature_names_a.feature", CONFIG)
    assert result.for_rule("no-dupe-feature-names") == ()


def test_no_dupe_feature_names_fires_across_a_two_file_corpus() -> None:
    result = lint_corpus(
        [FIXTURES / "dupe_feature_names_a.feature", FIXTURES / "dupe_feature_names_b.feature"],
        CONFIG,
    )
    dupes = result.for_rule("no-dupe-feature-names")
    assert len(dupes) == 1
    assert dupes[0].file == str(FIXTURES / "dupe_feature_names_b.feature")


def test_no_dupe_scenario_names_fires_in_feature() -> None:
    result = lint_file(FIXTURES / "scenario_dupe_in_feature_violation.feature", CONFIG)
    assert len(result.for_rule("no-dupe-scenario-names")) == 1


def test_no_dupe_scenario_names_does_not_cross_files_under_in_feature_scope() -> None:
    """The committed config scopes this rule `in-feature` (ADR-0043 D3): two
    different files sharing a scenario name must NOT be flagged as dupes."""
    result = lint_corpus(
        [
            FIXTURES / "scenario_same_name_across_files_a.feature",
            FIXTURES / "scenario_same_name_across_files_b.feature",
        ],
        CONFIG,
    )
    assert result.violations == ()


def test_smoke_feature_baseline_is_clean() -> None:
    """The one committed tracked-tier fixture (ADR-0037) lints clean."""
    result = lint_file(
        "test-suite-baseline/src/test/resources/features/smoke.feature", CONFIG
    )
    assert result.violations == (), result.violations


def test_lint_source_validates_in_memory_content_with_no_disk_io() -> None:
    """For a caller that assembles content in memory (e.g. the Layer 2
    generation core validating a file before ever writing it) -- proves
    `lint_source` agrees exactly with `lint_file` for the same bytes."""
    path = FIXTURES / "clean.feature"
    in_memory_source = parse_source_text(path.read_text(encoding="utf-8"), path=str(path))

    from_memory = lint_source(in_memory_source, CONFIG)
    from_disk = lint_file(path, CONFIG)

    assert from_memory.violations == from_disk.violations
    assert from_memory.is_clean


def test_lint_source_catches_a_violation_with_no_disk_io() -> None:
    path = FIXTURES / "no_trailing_spaces_violation.feature"
    in_memory_source = parse_source_text(path.read_text(encoding="utf-8"), path=str(path))

    result = lint_source(in_memory_source, CONFIG)

    assert {v.rule for v in result.violations} == {"no-trailing-spaces"}
