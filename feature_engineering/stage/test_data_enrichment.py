"""Post-hoc test-data field/variant derivation from a finalized acceptance
criterion's own ``statement`` text -- the #3 Option B STOPGAP (mentor
scoping doc; ADR-0043 D10), never Option A.

**This is honestly the LOWER-FIDELITY fix.** `feature_engineering.stage.
test_data_spec`'s own module docstring already established the real gap:
`AcceptanceCriterion.data_fields[]`/`.polarity_hints[]` (ADR-0042, real,
committed fields on the frozen `TestableRequirement` contract) are never
populated by the real Layer 1 emitter (`requirement_intelligence.
testable_requirement.emitter`), so every specification Layer 2 has ever
derived from real output is empty. The RIGHT fix (Option A) is teaching
Layer 1's analysis to elicit these fields AT ANALYSIS TIME, when the model
still has the raw source evidence in context -- but that is new Layer 1
judgement logic, and ADR-0032 freezes new Layer 1 capability until a
separate, future, ARB-approved lifting ADR names it. This module is the
freeze-clean STOPGAP available in the meantime: it infers the SAME two
signals post-hoc, from the requirement's own already-finalized TEXT alone,
after Layer 1 has already finished and moved on. Post-hoc text inference
is structurally weaker than analysis-time elicitation -- it can only see
what the finalized statement happens to say, never the source evidence
behind it -- and this module's own docstrings below say so at every
derivation site, not just here.

**Deterministic, not an LLM pass -- a deliberate choice, not a shortcut.**
Given Option B is already the acknowledged lower-fidelity stopgap, adding a
governed LLM call (a new prompt, ADR-0014 registration, rate-limit
exposure, real per-run cost) to reach for MORE fidelity would blur the line
between "the honest stopgap" and "a second, uncommitted attempt at Option
A's own territory." A small, deterministic vocabulary — cheap, freeze-clean
feeling, and honestly bounded — is the right-sized choice for a fix
explicitly framed as good-enough-for-now, not as-good-as-the-real-fix.

**The vocabulary, complete and closed, not open-ended.** Two independent
tables:

* :data:`_FIELD_VOCABULARY` -- LITERAL field-referent phrases (e.g.
  "postal code", "username") that name a field directly, wherever they
  appear in a statement's own text.
* :data:`_LOGIN_DOMAIN_TRIGGER_WORDS`/:data:`_LOGIN_DOMAIN_CONTEXT_WORDS`/
  :data:`_LOGIN_DOMAIN_EXCLUSION_WORDS` -- ONE domain pattern (not a
  generic NLP rule): a login-flow statement implies ``username``/
  ``password`` fields even when neither literal word appears (e.g. "invalid
  credentials", "successful ... authentication"), deliberately excluding a
  session/logout/timeout context to avoid a real false-positive this
  module's own tests catch directly (a requirement about a session timeout
  redirecting to "the login page" is NOT a requirement about SUBMITTING
  credentials -- see :mod:`tests.unit.
  test_feature_engineering_stage_test_data_enrichment` for the exact real
  statement this exclusion exists for).

**Honest miss, by design, not an oversight.** Any statement naming neither
a literal field phrase nor the login-domain pattern derives NOTHING --
never a guessed field. Measured directly against the real, live 15 SUT
requirements (post ADR-0043 D9's own SUT/framework-SAST split): most of
them (cart, inventory sort, checkout abort/finish, session/logout) are
behavioral, not data-driven, and correctly derive empty. Only the
login-flow and postal-code-format requirements carry recoverable data
signal in their own finalized text -- this module recovers exactly those,
nothing more, and the module's own tests report the real count, not an
inflated one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from contracts.testable_requirement import PolarityHint


def _stem_pattern(stem: str, *, whole_word: bool = False) -> re.Pattern[str]:
    """A left-word-boundary pattern for `stem` (so "credential" also
    matches "credentials", "account" also matches "accounts") --
    `whole_word=True` additionally requires a RIGHT boundary too, for the
    one real case that needs it: "valid" must never match inside "invalid"
    (a real false-polarity bug this module's own tests caught directly
    against the real corpus -- `REQ-c64bb0f7`'s "invalid credentials"
    wrongly produced BOTH ``NEGATIVE`` and ``POSITIVE`` before this fix,
    since a bare substring check treats "valid" as present inside
    "invalid")."""
    suffix = r"\b" if whole_word else ""
    return re.compile(r"\b" + re.escape(stem) + suffix)


#: LITERAL field-referent phrases -> the canonical field name they imply.
#: Multi-word phrases (a literal space inside the pattern) are inherently
#: safe from the "valid"/"invalid" class of collision; single words use
#: :func:`_stem_pattern`'s own left-boundary stemming. Order matters only
#: for iteration determinism, never for correctness -- every phrase is
#: checked independently.
_FIELD_VOCABULARY: tuple[tuple[re.Pattern[str], str], ...] = (
    (_stem_pattern("postal code"), "postalCode"),
    (_stem_pattern("zip code"), "postalCode"),
    (_stem_pattern("first name"), "firstName"),
    (_stem_pattern("last name"), "lastName"),
    (_stem_pattern("user name"), "username"),
    (_stem_pattern("username"), "username"),
    (_stem_pattern("password"), "password"),
    (_stem_pattern("email"), "email"),
)

#: Polarity CUE words -> the `PolarityHint` they imply. A statement naming
#: more than one cue accumulates every one it names (the union, mirroring
#: `test_data_spec.py`'s own per-field variant-union rule one level up).
#: ``valid`` is ``whole_word=True`` specifically so it never matches inside
#: ``invalid`` (see :func:`_stem_pattern`'s own docstring for the real bug
#: this guards).
_POLARITY_CUES: tuple[tuple[re.Pattern[str], PolarityHint], ...] = (
    (_stem_pattern("invalid"), PolarityHint.NEGATIVE),
    (_stem_pattern("deny"), PolarityHint.NEGATIVE),
    (_stem_pattern("denied"), PolarityHint.NEGATIVE),
    (_stem_pattern("locked"), PolarityHint.NEGATIVE),
    (_stem_pattern("valid", whole_word=True), PolarityHint.POSITIVE),
    (_stem_pattern("success"), PolarityHint.POSITIVE),
    (_stem_pattern("boundary"), PolarityHint.BOUNDARY),
    (_stem_pattern("format"), PolarityHint.BOUNDARY),
    (_stem_pattern("maximum"), PolarityHint.BOUNDARY),
    (_stem_pattern("minimum"), PolarityHint.BOUNDARY),
)

#: The ONE domain pattern this module recognizes beyond literal nouns: a
#: login-flow statement implies `username`/`password` even when neither
#: word appears verbatim (e.g. "invalid credentials"). Requires a TRIGGER
#: word AND a CONTEXT word, both present, AND no EXCLUSION word present --
#: three independent guards, not one broad keyword match, specifically to
#: avoid the real false positive a bare "login" match would produce (a
#: session-timeout requirement that merely redirects to "the login page").
_LOGIN_DOMAIN_TRIGGER_PATTERNS: tuple[re.Pattern[str], ...] = (
    _stem_pattern("login"),
    _stem_pattern("authenticat"),
)
_LOGIN_DOMAIN_CONTEXT_PATTERNS: tuple[re.Pattern[str], ...] = (
    _stem_pattern("credential"),
    _stem_pattern("authenticat"),
    _stem_pattern("account"),
    _stem_pattern("password"),
)
_LOGIN_DOMAIN_EXCLUSION_PATTERNS: tuple[re.Pattern[str], ...] = (
    _stem_pattern("session"),
    _stem_pattern("logout"),
    _stem_pattern("timeout"),
)
_LOGIN_DOMAIN_FIELDS: tuple[str, ...] = ("username", "password")


@dataclass(frozen=True, slots=True)
class DerivedDataHints:
    """One acceptance criterion's own post-hoc-derived data-field/polarity
    hints -- the SAME two shapes `AcceptanceCriterion.data_fields`/
    `.polarity_hints` (ADR-0042) already carry, never written back onto
    that frozen model (this module never constructs or mutates a
    `TestableRequirement`/`AcceptanceCriterion` -- see module docstring:
    Layer 1's own emitted contract, and its content-hash, are untouched).
    Empty on an honest miss -- never fabricated."""

    data_fields: tuple[str, ...] = ()
    polarity_hints: tuple[PolarityHint, ...] = ()


def _literal_field_matches(lowered_statement: str) -> tuple[str, ...]:
    fields: list[str] = []
    for pattern, field_name in _FIELD_VOCABULARY:
        if pattern.search(lowered_statement) is not None and field_name not in fields:
            fields.append(field_name)
    return tuple(fields)


def _login_domain_matches(lowered_statement: str) -> tuple[str, ...]:
    has_trigger = any(p.search(lowered_statement) for p in _LOGIN_DOMAIN_TRIGGER_PATTERNS)
    has_context = any(p.search(lowered_statement) for p in _LOGIN_DOMAIN_CONTEXT_PATTERNS)
    has_exclusion = any(p.search(lowered_statement) for p in _LOGIN_DOMAIN_EXCLUSION_PATTERNS)
    if has_trigger and has_context and not has_exclusion:
        return _LOGIN_DOMAIN_FIELDS
    return ()


def _polarity_cues(lowered_statement: str) -> tuple[PolarityHint, ...]:
    hints: list[PolarityHint] = []
    for pattern, hint in _POLARITY_CUES:
        if pattern.search(lowered_statement) is not None and hint not in hints:
            hints.append(hint)
    return tuple(hints)


def derive_data_hints_from_statement(statement: str) -> DerivedDataHints:
    """Derive `(data_fields, polarity_hints)` from one acceptance
    criterion's own ``statement`` text alone -- pure, deterministic, no LLM
    call, no I/O. Returns an honestly empty :class:`DerivedDataHints` when
    the statement names neither a literal field phrase nor the login-domain
    pattern (module docstring's own "honest miss" account) -- NEVER a
    guessed field.

    When at least one field is derived but the statement names no polarity
    cue, defaults to :data:`~contracts.testable_requirement.PolarityHint.POSITIVE`
    alone -- a documented default (the "expected/successful case needs data
    at minimum" assumption), not a claimed inference from the text.
    """
    lowered = statement.lower()

    fields: list[str] = list(_literal_field_matches(lowered))
    for field_name in _login_domain_matches(lowered):
        if field_name not in fields:
            fields.append(field_name)

    if not fields:
        return DerivedDataHints()

    polarity_hints = _polarity_cues(lowered)
    if not polarity_hints:
        polarity_hints = (PolarityHint.POSITIVE,)

    return DerivedDataHints(data_fields=tuple(fields), polarity_hints=polarity_hints)


__all__ = ["DerivedDataHints", "derive_data_hints_from_statement"]
