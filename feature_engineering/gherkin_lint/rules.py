"""The 17 ported gherkin-lint rules (ADR-0043 D3).

Each rule here is a faithful port of the corresponding rule in the npm
``gherkin-lint`` package (github.com/gherkin-lint/gherkin-lint,
``src/rules/*.js``, re-read directly for this port) — same firing
conditions, same message text, same config shape. Nothing here reimagines a
rule's behaviour, and no 18th rule is added; see ``config.KNOWN_RULES``.

Fifteen rules are **per-file**: they see one :class:`~.source.SourceFile`
(its raw lines and its parsed AST) and return ``(line, message)`` pairs.
Two rules are **corpus-scoped** and see the whole workspace at once:

* ``no-dupe-feature-names`` — cross-file by definition (a duplicate feature
  *name* can only be found by comparing every file).
* ``no-dupe-scenario-names`` — scoped by its own ``availableConfigs``
  (``anywhere`` or ``in-feature``); the committed ``.gherkin-lintrc`` sets
  ``in-feature``, so in practice this rule's state resets per file.

Both corpus rules return ``(file, line, message)`` triples since a single
call spans files.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from typing import Any

from .dialect import dialect_key, node_type
from .source import SourceFile

PerFileRule = Callable[[SourceFile, Any], list[tuple[int, str]]]
CorpusRule = Callable[[Sequence[SourceFile], Any], list[tuple[str, int, str]]]


def _tag_names(node: dict[str, Any]) -> list[str]:
    return [tag["name"] for tag in node.get("tags", [])]


# ---------------------------------------------------------------------------
# Structural rules operating on the AST's `feature` node.
# ---------------------------------------------------------------------------


def no_unnamed_features(source: SourceFile, option: Any) -> list[tuple[int, str]]:
    feature = source.feature
    if not feature or not feature.get("name"):
        line = feature["location"]["line"] if feature else 0
        return [(line, "Missing Feature name")]
    return []


def no_unnamed_scenarios(source: SourceFile, option: Any) -> list[tuple[int, str]]:
    feature = source.feature
    if not feature:
        return []
    errors: list[tuple[int, str]] = []
    for child in feature.get("children", []):
        scenario = child.get("scenario")
        if scenario and not scenario.get("name"):
            errors.append((scenario["location"]["line"], "Missing Scenario name"))
    return errors


def no_empty_file(source: SourceFile, option: Any) -> list[tuple[int, str]]:
    if not source.feature:
        return [(1, "Empty feature files are disallowed")]
    return []


def _has_scenario(child: dict[str, Any]) -> bool:
    if child.get("scenario") is not None:
        return True
    rule = child.get("rule")
    if rule is None:
        return False
    return any(_has_scenario(c) for c in rule.get("children", []))


def no_files_without_scenarios(source: SourceFile, option: Any) -> list[tuple[int, str]]:
    feature = source.feature
    if not feature:
        return []
    if not any(_has_scenario(c) for c in feature.get("children", [])):
        return [(1, "Feature file does not have any Scenarios")]
    return []


def no_duplicate_tags(source: SourceFile, option: Any) -> list[tuple[int, str]]:
    feature = source.feature
    if not feature:
        return []
    errors: list[tuple[int, str]] = []

    def verify(node: dict[str, Any]) -> None:
        failed: set[str] = set()
        unique: set[str] = set()
        for tag in node.get("tags", []):
            name = tag["name"]
            if name in failed:
                continue
            if name in unique:
                errors.append((tag["location"]["line"], f"Duplicate tags are not allowed: {name}"))
                failed.add(name)
            else:
                unique.add(name)

    verify(feature)
    for child in feature.get("children", []):
        scenario = child.get("scenario")
        if scenario:
            verify(scenario)
            for example in scenario.get("examples", []):
                verify(example)
    return errors


def _lodash_intersection(arrays: list[list[str]]) -> list[str]:
    """Port of lodash's ``_.intersection`` semantics used by no-homogenous-tags.

    With zero arrays, returns ``[]``. With one array, returns its unique
    values (there is nothing else to intersect against) — this is the
    lodash behaviour the upstream rule relies on, not a simplification.
    """
    if not arrays:
        return []
    first, others = arrays[0], arrays[1:]
    seen: set[str] = set()
    result: list[str] = []
    for item in first:
        if item in seen:
            continue
        if all(item in arr for arr in others):
            result.append(item)
            seen.add(item)
    return result


def no_homogenous_tags(source: SourceFile, option: Any) -> list[tuple[int, str]]:
    feature = source.feature
    if not feature:
        return []
    errors: list[tuple[int, str]] = []
    children_tags: list[list[str]] = []

    for child in feature.get("children", []):
        scenario = child.get("scenario")
        if not scenario:
            continue
        children_tags.append(_tag_names(scenario))

        example_tags = [_tag_names(example) for example in scenario.get("examples", [])]
        homogenous_example_tags = _lodash_intersection(example_tags)
        if homogenous_example_tags:
            errors.append(
                (
                    scenario["location"]["line"],
                    "All Examples of a Scenario Outline have the same tag(s), they should be "
                    "defined on the Scenario Outline instead: "
                    + ", ".join(homogenous_example_tags),
                )
            )

    homogenous_tags = _lodash_intersection(children_tags)
    if homogenous_tags:
        errors.append(
            (
                feature["location"]["line"],
                "All Scenarios on this Feature have the same tag(s), they should be defined "
                "on the Feature instead: " + ", ".join(homogenous_tags),
            )
        )
    return errors


def _first_with_table_body(examples: list[dict[str, Any]]) -> dict[str, Any] | None:
    for example in examples:
        if example.get("tableBody") is not None:
            return example
    return None


def no_scenario_outlines_without_examples(source: SourceFile, option: Any) -> list[tuple[int, str]]:
    feature = source.feature
    if not feature:
        return []
    errors: list[tuple[int, str]] = []
    for child in feature.get("children", []):
        scenario = child.get("scenario")
        if not scenario:
            continue
        if node_type(scenario, feature["language"]) != "Scenario Outline":
            continue
        first = _first_with_table_body(scenario.get("examples", []))
        if first is None or not first.get("tableBody"):
            errors.append(
                (scenario["location"]["line"], "Scenario Outline does not have any Examples")
            )
    return errors


def no_examples_in_scenarios(source: SourceFile, option: Any) -> list[tuple[int, str]]:
    feature = source.feature
    if not feature:
        return []
    errors: list[tuple[int, str]] = []
    for child in feature.get("children", []):
        scenario = child.get("scenario")
        if not scenario:
            continue
        if node_type(scenario, feature["language"]) == "Scenario" and scenario.get("examples"):
            errors.append(
                (
                    scenario["location"]["line"],
                    'Cannot use "Examples" in a "Scenario", use a "Scenario Outline" instead',
                )
            )
    return errors


def _check_tags_partial_comment(node: dict[str, Any], errors: list[tuple[int, str]]) -> None:
    for tag in node.get("tags", []):
        name = tag["name"]
        if name.find("#") > 0:
            errors.append((tag["location"]["line"], "Partially commented tag lines not allowed"))


def no_partially_commented_tag_lines(source: SourceFile, option: Any) -> list[tuple[int, str]]:
    feature = source.feature
    if not feature:
        return []
    errors: list[tuple[int, str]] = []
    _check_tags_partial_comment(feature, errors)
    for child in feature.get("children", []):
        scenario = child.get("scenario")
        if scenario:
            _check_tags_partial_comment(scenario, errors)
            for example in scenario.get("examples", []):
                _check_tags_partial_comment(example, errors)
    return errors


# ---------------------------------------------------------------------------
# Raw-source-text rules (ADR-0043 D3): the AST discards this information.
# ---------------------------------------------------------------------------

_TRAILING_WHITESPACE = re.compile(r"[\t ]+$")


def no_trailing_spaces(source: SourceFile, option: Any) -> list[tuple[int, str]]:
    errors: list[tuple[int, str]] = []
    for line_no, line in enumerate(source.lines, start=1):
        if _TRAILING_WHITESPACE.search(line):
            errors.append((line_no, "Trailing spaces are not allowed"))
    return errors


def no_multiple_empty_lines(source: SourceFile, option: Any) -> list[tuple[int, str]]:
    errors: list[tuple[int, str]] = []
    lines = source.lines
    for i in range(len(lines) - 1):
        if lines[i].strip() == "" and lines[i + 1].strip() == "":
            errors.append((i + 2, "Multiple empty lines are not allowed"))
    return errors


def new_line_at_eof(source: SourceFile, option: Any) -> list[tuple[int, str]]:
    configuration = option if isinstance(option, str) else "yes"
    has_newline_at_eof = bool(source.lines) and source.lines[-1] == ""

    message = ""
    if has_newline_at_eof and configuration == "no":
        message = "New line at EOF(end of file) is not allowed"
    elif not has_newline_at_eof and configuration == "yes":
        message = "New line at EOF(end of file) is required"

    if message:
        return [(len(source.lines), message)]
    return []


# ---------------------------------------------------------------------------
# Structural rules with their own config shape.
# ---------------------------------------------------------------------------

_DEFAULT_INDENTATION = {
    "Feature": 0,
    "Background": 0,
    "Rule": 0,
    "Scenario": 0,
    "Step": 2,
    "Examples": 0,
    "example": 2,
    "given": 2,
    "when": 2,
    "then": 2,
    "and": 2,
    "but": 2,
}


def indentation(source: SourceFile, option: Any) -> list[tuple[int, str]]:
    feature = source.feature
    if not feature:
        return []

    raw_config: dict[str, Any] = option if isinstance(option, dict) else {}
    merged = dict(_DEFAULT_INDENTATION)
    merged.update(raw_config)
    merged.setdefault("feature tag", merged["Feature"])
    merged.setdefault("scenario tag", merged["Scenario"])

    errors: list[tuple[int, str]] = []

    def test(location: dict[str, int], node_key: str) -> None:
        expected = merged.get(node_key)
        if expected is None:
            return
        actual = location["column"] - 1
        if actual != expected:
            errors.append(
                (
                    location["line"],
                    f'Wrong indentation for "{node_key}", expected indentation level of '
                    f"{expected}, but got {actual}",
                )
            )

    def test_step(step: dict[str, Any]) -> None:
        key = dialect_key(step, feature["language"])
        step_type = key if key in raw_config else "Step"
        test(step["location"], step_type)

    def test_tags(tags: list[dict[str, Any]], node_key: str) -> None:
        by_line: dict[int, list[dict[str, Any]]] = {}
        for tag in tags:
            by_line.setdefault(tag["location"]["line"], []).append(tag)
        for line in sorted(by_line):
            first_tag = min(by_line[line], key=lambda t: t["location"]["column"])
            test(first_tag["location"], node_key)

    test(feature["location"], "Feature")
    test_tags(feature.get("tags", []), "feature tag")

    for child in feature.get("children", []):
        if child.get("rule"):
            test(child["rule"]["location"], "Rule")
        elif child.get("background"):
            background = child["background"]
            test(background["location"], "Background")
            for step in background.get("steps", []):
                test_step(step)
        else:
            scenario = child["scenario"]
            test(scenario["location"], "Scenario")
            test_tags(scenario.get("tags", []), "scenario tag")
            for step in scenario.get("steps", []):
                test_step(step)
            for example in scenario.get("examples", []):
                test(example["location"], "Examples")
                header = example.get("tableHeader")
                if header:
                    test(header["location"], "example")
                    for row in example.get("tableBody", []):
                        test(row["location"], "example")

    return errors


_DEFAULT_NAME_LENGTH = {"Feature": 70, "Rule": 70, "Step": 70, "Scenario": 70}


def name_length(source: SourceFile, option: Any) -> list[tuple[int, str]]:
    feature = source.feature
    if not feature:
        return []

    config = dict(_DEFAULT_NAME_LENGTH)
    if isinstance(option, dict):
        config.update(option)

    errors: list[tuple[int, str]] = []

    def test(name: str | None, location: dict[str, int], node_key: str) -> None:
        if name and len(name) > config[node_key]:
            errors.append(
                (
                    location["line"],
                    f"{node_key} name is too long. Length of {len(name)} is longer than the "
                    f"maximum allowed: {config[node_key]}",
                )
            )

    def test_steps(node: dict[str, Any]) -> None:
        for step in node.get("steps", []):
            test(step.get("text"), step["location"], "Step")

    test(feature.get("name"), feature["location"], "Feature")
    for child in feature.get("children", []):
        if child.get("rule"):
            test(child["rule"].get("name"), child["rule"]["location"], "Rule")
        elif child.get("background"):
            test_steps(child["background"])
        else:
            scenario = child["scenario"]
            test(scenario.get("name"), scenario["location"], "Scenario")
            test_steps(scenario)

    return errors


_DEFAULT_SCENARIO_SIZE = {"steps-length": {"Rule": 15, "Background": 15, "Scenario": 15}}


def scenario_size(source: SourceFile, option: Any) -> list[tuple[int, str]]:
    feature = source.feature
    if not feature:
        return []

    config = option if option else _DEFAULT_SCENARIO_SIZE
    steps_length = config.get("steps-length", {})

    errors: list[tuple[int, str]] = []
    for child in feature.get("children", []):
        if child.get("rule"):
            node, config_key = child["rule"], "Rule"
        elif child.get("background"):
            node, config_key = child["background"], "Background"
        else:
            node, config_key = child["scenario"], "Scenario"

        max_size = steps_length.get(config_key)
        steps = node.get("steps", [])
        if max_size and len(steps) > max_size:
            kind = node_type(node, feature["language"])
            errors.append(
                (
                    node["location"]["line"],
                    f"Element {kind} too long: actual {len(steps)}, expected {max_size}",
                )
            )

    return errors


# ---------------------------------------------------------------------------
# Corpus-scoped rules.
# ---------------------------------------------------------------------------


def no_dupe_feature_names(corpus: Sequence[SourceFile], option: Any) -> list[tuple[str, int, str]]:
    seen: dict[str, list[str]] = {}
    errors: list[tuple[str, int, str]] = []
    for source in corpus:
        feature = source.feature
        if not feature:
            continue
        name = feature.get("name", "")
        if name in seen:
            dupes = ", ".join(seen[name])
            message = f"Feature name is already used in: {dupes}"
            errors.append((source.path, feature["location"]["line"], message))
            seen[name].append(source.path)
        else:
            seen[name] = [source.path]
    return errors


def no_dupe_scenario_names(corpus: Sequence[SourceFile], option: Any) -> list[tuple[str, int, str]]:
    mode = option if option in ("anywhere", "in-feature") else "anywhere"
    seen: dict[str, list[tuple[str, int]]] = {}
    errors: list[tuple[str, int, str]] = []

    for source in corpus:
        feature = source.feature
        if not feature:
            continue
        if mode == "in-feature":
            seen = {}
        for child in feature.get("children", []):
            scenario = child.get("scenario")
            if not scenario:
                continue
            name = scenario.get("name", "")
            line = scenario["location"]["line"]
            if name in seen:
                dupes = ", ".join(f"{dupe_file}:{dupe_line}" for dupe_file, dupe_line in seen[name])
                errors.append((source.path, line, f"Scenario name is already used in: {dupes}"))
                seen[name].append((source.path, line))
            else:
                seen[name] = [(source.path, line)]

    return errors


PER_FILE_RULES: dict[str, PerFileRule] = {
    "no-unnamed-features": no_unnamed_features,
    "no-unnamed-scenarios": no_unnamed_scenarios,
    "no-empty-file": no_empty_file,
    "no-files-without-scenarios": no_files_without_scenarios,
    "no-duplicate-tags": no_duplicate_tags,
    "no-homogenous-tags": no_homogenous_tags,
    "no-scenario-outlines-without-examples": no_scenario_outlines_without_examples,
    "no-examples-in-scenarios": no_examples_in_scenarios,
    "no-partially-commented-tag-lines": no_partially_commented_tag_lines,
    "no-trailing-spaces": no_trailing_spaces,
    "no-multiple-empty-lines": no_multiple_empty_lines,
    "new-line-at-eof": new_line_at_eof,
    "indentation": indentation,
    "name-length": name_length,
    "scenario-size": scenario_size,
}

CORPUS_RULES: dict[str, CorpusRule] = {
    "no-dupe-feature-names": no_dupe_feature_names,
    "no-dupe-scenario-names": no_dupe_scenario_names,
}
