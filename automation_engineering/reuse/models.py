"""The reuse-decision domain shapes (ADR-0044 D4).

This module defines the data the reuse-safety model reads and produces --
nothing else. It carries no matching logic (:mod:`.matcher`) and no
three-check decision logic (:mod:`.engine`); those consume these shapes.

Two boundary concepts, kept deliberately distinct:

* :class:`GherkinStepNeed` -- the asset-need being satisfied: a Gherkin step
  a (future, not-built-here) generator would otherwise have to write code
  for, unless a reuse binding can be trusted instead. ``captures`` is this
  step's own required capture shape (count, order, type) -- the same values
  a bound step definition would receive AND, in turn, would pass through to
  whichever page-object/utility method it calls. This one shape now backs
  BOTH of check (c)'s two realizations (:mod:`.engine`): against a
  catalogued step definition's own recorded ``SignatureAlignment.captures``
  (:mod:`automation_engineering.catalog.alignment`) for SIGNATURE-FIT, and
  against a catalogued page-object's/utility's own recorded ``.methods``
  parameter shapes for METHOD-FIT. Deriving this shape from raw
  natural-language step text is a generation-time concern, out of scope for
  this task (the future generator); this engine takes it as an
  already-known input, the same way it takes the catalog as an input.
* :class:`MatchCandidate` -- one :class:`~automation_engineering.reuse.matcher.SemanticMatcher`
  result: an ``asset_id`` plus a confidence score, PLUS the ``content_hash``
  the match was computed against (whatever the catalog said at match time).
  That third field is what makes ADR-0044 D4(b)'s content-hash check
  possible at all -- without it, there is nothing to compare a fresh catalog
  lookup's current hash against.

The three-check engine's own output vocabulary (ADR-0044 D4's "TRUSTED_REUSE
| ESCALATE | NO_MATCH") is modeled as a closed union,
:data:`ReuseDecision` -- exhaustive, so a caller (or ``mypy``, via
structural matching) cannot silently drop a case.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from automation_engineering.catalog.models import CatalogAsset, StepCapture


@dataclass(frozen=True, slots=True)
class GherkinStepNeed:
    """One Gherkin step the reuse engine is deciding whether to satisfy via
    reuse (a trusted catalog binding) or generation (the future generator,
    out of scope here).

    ``text`` is the step's own literal text (no ``Given``/``When``/``Then``
    keyword) -- the semantic-match input (:mod:`.matcher`). ``captures`` is
    this step's own required capture shape, already derived by the caller
    (see module docstring) -- ``()`` for a step needing no parameters.
    """

    text: str
    step_type: str
    captures: tuple[StepCapture, ...] = ()


@dataclass(frozen=True, slots=True)
class MatchCandidate:
    """One semantic-match result (:mod:`.matcher`) for one
    :class:`GherkinStepNeed` -- the ONLY nondeterministic input the
    three-check engine (:mod:`.engine`) ever consumes.

    ``content_hash`` is the catalogued asset's content-hash *as observed by
    the matcher at match time* -- not necessarily its current value. The
    engine's content-hash check (ADR-0044 D4(b)) re-looks-up the asset by
    ``asset_id`` in a fresh catalog and compares; this field is the "what
    the match was computed against" side of that comparison.
    """

    asset_id: str
    confidence: float
    content_hash: str


class EscalationCheck(StrEnum):
    """Which of ADR-0044 D4's three checks caused an escalation. Exactly one
    value per :class:`Escalation` -- the first check to fail is reported;
    the checks are evaluated in the ADR's own (a) -> (b) -> (c) order, so a
    candidate failing multiple checks at once is still reported for the
    earliest one, never silently for a later one instead.

    Check (c) -- "structural fit" -- has two realizations, one per catalog
    asset shape (see the ADR-0044 clarification note added to D4 alongside
    this change): :attr:`SIGNATURE_FIT` for a
    :class:`~automation_engineering.catalog.models.StepDefinitionAsset`
    (unchanged, the ADR's own literal example) and :attr:`METHOD_FIT` for a
    :class:`~automation_engineering.catalog.models.PageObjectAsset`/
    :class:`~automation_engineering.catalog.models.UtilityAsset` candidate
    (:mod:`.engine`'s ``_check_method_fit``). Both close the SAME gap check
    (c) exists for -- a confident, current-hash match whose STRUCTURE
    doesn't fit the binding -- just measured against a different structural
    dimension (Gherkin-annotation captures vs. class methods). Unlike
    signature-fit, method-fit is COARSE at decision time (:mod:`.engine`'s
    own docstring) -- it is a class-level compatibility screen, not proof
    the specific method the binding needs exists.
    """

    CONFIDENCE = "confidence"
    CONTENT_HASH = "content_hash"
    SIGNATURE_FIT = "signature_fit"
    METHOD_FIT = "method_fit"


@dataclass(frozen=True, slots=True)
class TrustedReuse:
    """ADR-0044 D4's ``TRUSTED_REUSE(asset)`` outcome -- all three checks
    passed. ``asset`` is the fresh catalog entry the binding actually
    resolves to (not merely the candidate's ``asset_id``), so a caller never
    has to re-look it up.

    For a page-object/utility asset, METHOD-FIT (:mod:`.engine`) is a
    COARSE, decision-time class-compatibility screen only -- it proves
    *some* method with a fitting shape exists on the class, never that the
    class provides the SPECIFIC method a not-yet-written step definition
    will actually call. ``asset.methods`` (the full method inventory,
    names included) is exposed here precisely so the future generator --
    the only place the specific call target is chosen, and the only place
    that information exists -- can perform the PRECISE check this engine
    structurally cannot: **the generator MUST, before binding a step to a
    reused page object/utility, verify the SPECIFIC method it is about to
    call is actually present on ``asset.methods``, and escalate/regenerate
    if it is not.** This is the decision/generation split's own contract:
    this engine hands over the data that check needs (this field); it does
    not, and cannot, perform the check itself.
    """

    asset: CatalogAsset
    candidate: MatchCandidate


@dataclass(frozen=True, slots=True)
class Escalation:
    """ADR-0044 D4's ``ESCALATE(reason, candidate)`` outcome -- routes to the
    same human-in-the-loop discipline every other layer already uses
    (``escalated``/``escalation_reason`` on a stage record, e.g.
    :class:`feature_engineering.stage.models.FeatureRecord`) -- no new queue
    is built here (see :mod:`.engine` module docstring).

    Carries enough for a human to decide without re-running the match:
    which check failed (``check``), the failing candidate in full
    (``candidate`` -- ``None`` only when the match itself never happened,
    which this engine never produces: an escalation always has a candidate,
    by construction, since check (a) is the first check and a candidate
    failing to `exist` at all is :class:`NoMatch`, never an escalation), the
    confidence the match carried, and a human-readable ``detail`` of the
    specific mismatch (e.g. which capture index/type disagreed, or the
    stale vs. current hash values).
    """

    need: GherkinStepNeed
    check: EscalationCheck
    candidate: MatchCandidate
    detail: str


@dataclass(frozen=True, slots=True)
class NoMatch:
    """ADR-0044 D3's reuse-or-generate boundary's "generate" side: no
    candidate was found at all (an empty catalog, or nothing the matcher
    considers even remotely similar) -- never an error, and never an
    escalation (there is no candidate for a human to review). The
    generator (a future, not-built-here task) is the caller that acts on
    this by generating the asset from scratch."""

    need: GherkinStepNeed


#: ADR-0044 D4's exhaustive reuse-decision vocabulary. A caller (or a
#: `match`-style exhaustiveness check) handles all three; there is no
#: fourth case.
ReuseDecision = TrustedReuse | Escalation | NoMatch

__all__ = [
    "Escalation",
    "EscalationCheck",
    "GherkinStepNeed",
    "MatchCandidate",
    "NoMatch",
    "ReuseDecision",
    "TrustedReuse",
]
