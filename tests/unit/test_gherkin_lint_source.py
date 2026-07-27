"""Raw-source-vs-AST tests for the Gherkin linter (ADR-0043 D3).

Proves the specific structural claim that motivates keeping raw lines
alongside the AST: the parsed AST does not retain trailing whitespace on a
step line, so a rule with access only to the AST has no way to detect it.
`SourceFile` keeps both representations precisely so a rule can look past
the AST when it needs to.
"""

from __future__ import annotations

from pathlib import Path

from feature_engineering.gherkin_lint.source import read_source

FIXTURES = Path("tests/unit/fixtures/gherkin_lint")


def test_source_file_keeps_raw_lines_and_ast_side_by_side() -> None:
    source = read_source(FIXTURES / "no_trailing_spaces_violation.feature")

    assert source.feature is not None
    assert source.lines[3] == "    Given a precondition  "  # raw: trailing spaces intact


def test_ast_step_text_discards_the_trailing_whitespace_the_raw_line_keeps() -> None:
    """The AST alone cannot see what `no-trailing-spaces` must catch."""
    source = read_source(FIXTURES / "no_trailing_spaces_violation.feature")

    assert source.feature is not None
    step = source.feature["children"][0]["scenario"]["steps"][0]
    assert step["text"] == "a precondition"  # AST: whitespace already gone
    assert source.lines[3].endswith("  ")  # raw: still there


def test_ast_gives_no_signal_for_a_double_blank_line() -> None:
    """`no-multiple-empty-lines` has nothing to key off of in the AST."""
    source = read_source(FIXTURES / "no_multiple_empty_lines_violation.feature")

    assert source.feature is not None
    assert source.feature.get("name")  # the feature parses as entirely unremarkable
    assert source.lines[1] == ""
    assert source.lines[2] == ""


def test_ast_gives_no_signal_for_missing_eof_newline() -> None:
    """`new-line-at-eof` has nothing to key off of in the AST."""
    source = read_source(FIXTURES / "new_line_at_eof_violation.feature")

    assert source.feature is not None
    assert source.lines[-1] != ""  # raw: no trailing newline
    # The AST has no notion of "did the file end with a newline" at all --
    # there is no field to assert is absent; the information simply isn't there.


def test_empty_file_has_no_feature_node() -> None:
    source = read_source(FIXTURES / "no_empty_file_violation.feature")

    assert source.feature is None
    assert source.lines == ("",)


def test_feature_without_scenario_still_parses_a_feature_node() -> None:
    source = read_source(FIXTURES / "no_files_without_scenarios_violation.feature")

    assert source.feature is not None
    assert source.feature["name"] == "A feature with no scenarios"
