"""Deterministic Cucumber-pattern-vs-literal-step-text matching (ADR-0046
D2/D6).

This did **not** already exist anywhere in this codebase before this
module. The catalog (`automation_engineering.catalog.alignment`) parses a
step definition's own pattern into its own CAPTURES (`parse_captures`) --
that is a different question ("what does this pattern's own shape look
like") from the one this module answers ("does this literal step TEXT
actually match this pattern"). The reuse engine's own matching
(`automation_engineering.reuse.matcher`/`.live_matcher`) is SEMANTIC
(embedding cosine similarity) -- a fuzzy "how similar in intent" question,
never a "does Cucumber's own runtime binding actually fire" question. This
module is the missing third piece: it reproduces Cucumber-JVM's own literal
binding rule, deterministically, with no embedding or live call involved.

**Why deterministic matching matters here, not semantic matching.**
Cucumber itself resolves glue at runtime by matching a step's literal text
against a step-definition's own pattern (a Cucumber Expression or a regex)
-- never by semantic similarity. A step definition that is a *semantic*
near-match to some current need but whose pattern never actually matches
that need's literal text will genuinely never fire at execution time,
regardless of how similar its intent reads. Using this deterministic
matcher (not the embedding matcher) as CP5's own orphan GATE keeps that gate
a genuine, deterministic contributor to CP5's PASS/FAIL, per ADR-0040
Decision 2 ("control-point gates evaluate only deterministic evidence...
never [an] LLM-generated assessment") and ADR-0046 D6's own composition
table.

**Reuses, does not re-derive, the catalog's own pattern classification.**
`CUCUMBER_EXPRESSION_CAPTURE_RE`/`looks_like_regex`
(`automation_engineering.catalog.alignment`, promoted to public for exactly
this reuse, ADR-0046 D7) are the SAME heuristics `parse_captures` already
uses to decide whether a pattern is a Cucumber Expression, a regex, or a
plain literal phrase. This module classifies a pattern identically, so a
pattern is never interpreted one way for capture-parsing and a different
way for text-matching.

**Layer 4 depending on Layer 3's own machinery.** This module -- and this
whole `cp5` package -- lives under `suite_quality_governance/`, ADR-0033's
own Layer 4 package (not `automation_engineering/`, Layer 3's), but
imports `automation_engineering.catalog.alignment` directly: CP5 consumes
the catalog Layer 3 already built, exactly the "Validated Automation
Package" hand-off ADR-0044 D1 describes, not a second, parallel
pattern-classification mechanism.
"""

from __future__ import annotations

import re

from automation_engineering.catalog.alignment import (
    CUCUMBER_EXPRESSION_CAPTURE_RE,
    looks_like_regex,
)

#: Cucumber Expressions' built-in parameter types, mapped to the regex
#: fragment that matches what that placeholder actually accepts in step
#: text -- mirrors `automation_engineering.catalog.alignment.
#: CUCUMBER_EXPRESSION_TYPES`'s own type roster (the Java-type side of the
#: same placeholders), kept as a distinct mapping here because this side
#: maps a placeholder to a TEXT pattern, not a Java type.
_CAPTURE_TEXT_PATTERN: dict[str, str] = {
    "string": r'(?:"[^"]*"|\'[^\']*\')',
    "word": r"\S+",
    "int": r"-?\d+",
    "float": r"-?\d+(?:\.\d+)?",
    "double": r"-?\d+(?:\.\d+)?",
    "long": r"-?\d+",
    "short": r"-?\d+",
    "byte": r"-?\d+",
    "biginteger": r"-?\d+",
    "bigdecimal": r"-?\d+(?:\.\d+)?",
}

#: A custom/unrecognized Cucumber Expression placeholder's own matching
#: shape is not knowable from the type name alone -- a permissive,
#: non-empty-token fallback, never a guess narrow enough to falsely reject
#: a real match.
_DEFAULT_CAPTURE_TEXT_PATTERN = r".+?"


def _cucumber_expression_to_regex(pattern: str) -> re.Pattern[str]:
    """Compile a Cucumber Expression pattern into the regex that matches
    exactly the step text it would bind, full-string (Cucumber requires the
    ENTIRE step text to match, not a substring)."""
    pieces: list[str] = []
    last_end = 0
    for placeholder in CUCUMBER_EXPRESSION_CAPTURE_RE.finditer(pattern):
        pieces.append(re.escape(pattern[last_end : placeholder.start()]))
        expression_type = placeholder.group(1).lower()
        pieces.append(_CAPTURE_TEXT_PATTERN.get(expression_type, _DEFAULT_CAPTURE_TEXT_PATTERN))
        last_end = placeholder.end()
    pieces.append(re.escape(pattern[last_end:]))
    return re.compile("".join(pieces))


def pattern_matches_text(pattern: str, text: str) -> bool:
    """Does `text` (one Gherkin step's own literal text, no keyword) match
    `pattern` (one step definition's own Cucumber-annotation pattern) --
    the same literal-binding question Cucumber-JVM answers at runtime,
    reproduced deterministically, no live call.

    Three cases, matching `automation_engineering.catalog.alignment.
    parse_captures`'s own three-way classification of a pattern exactly:

    1. **Cucumber Expression** (contains a ``{placeholder}``) -- compiled to
       a full-string regex (literal segments escaped, each placeholder
       replaced by the text shape its own type accepts) and matched against
       `text` in full.
    2. **Regex-style** (`looks_like_regex`, an unescaped ``(`` group) --
       `pattern` IS itself the regex; matched against `text` in full
       (`re.fullmatch`), mirroring Cucumber-JVM's own regex-annotation
       binding. A pattern using Java-only regex syntax Python's `re` cannot
       compile falls back to exact literal comparison -- conservative (a
       real match is more likely missed than falsely reported), the same
       posture `automation_engineering.catalog.alignment.
       _count_regex_capturing_groups_fallback` already takes for the
       identical "can't compile this as Python regex" case.
    3. **Plain literal phrase** (neither of the above) -- exact string
       equality, Cucumber-JVM's own literal-step-text binding rule.
    """
    if CUCUMBER_EXPRESSION_CAPTURE_RE.search(pattern):
        return _cucumber_expression_to_regex(pattern).fullmatch(text) is not None
    if looks_like_regex(pattern):
        try:
            compiled = re.compile(pattern)
        except re.error:
            return pattern == text
        return compiled.fullmatch(text) is not None
    return pattern == text


__all__ = ["pattern_matches_text"]
