"""Gherkin -> step-need derivation for stage 15 (ADR-0044 D1/D3).

The reuse engine and every generator consume :class:`~automation_engineering.
reuse.models.GherkinStepNeed`, but nothing anywhere in this platform derives
that shape from a real, already-generated ``.feature`` file's own text --
:class:`GherkinStepNeed`'s own docstring calls this "a generation-time
concern, out of scope for this task (the future generator)." Stage 15 is
that generator's own orchestration layer, so this module performs exactly
that derivation -- minimal, and built on the SAME Gherkin parser CP2/CP3
already use (:func:`feature_engineering.gherkin_lint.parse_source_text`),
never a second one.

``captures`` stays ``()`` on every derived need, deliberately. Inferring a
step's own required capture SHAPE (count/order/type) from literal step text
(e.g. recognizing a quoted string or a bare integer as a Cucumber-Expression-
shaped placeholder) is itself real, new inferential logic that feeds
directly into ADR-0044 D4's reuse-safety TRUST decision -- exactly the kind
of judgment this platform's own discipline never builds as an unreviewed
side effect of an orchestration/wiring task. Every D4 check that consumes
``captures`` fails CLOSED when it is empty: :func:`automation_engineering.
reuse.engine._check_signature_fit`/``_check_method_fit`` escalate rather
than silently trusting a structurally-unverified binding, so this is a safe
default, not an unsafe shortcut -- it costs REUSE RATE for any step that
genuinely has a parameter (it escalates instead of reusing a
perfectly-matching candidate), never trust correctness. Building real
capture derivation is a deliberate, reviewed follow-up task, the same
posture this platform already takes for the page-object/utility "which
specific method does this step need" binding-request derivation (this
module never derives that either, for the identical reason).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from automation_engineering.reuse.models import GherkinStepNeed
from feature_engineering.gherkin_lint import parse_source_text

#: The official Gherkin AST's own ``keywordType`` values (``Context``/
#: ``Action``/``Outcome``/``Conjunction``/``Unknown``) mapped to the
#: effective Given/When/Then vocabulary this platform's
#: ``GherkinStepNeed.step_type`` already uses elsewhere (e.g.
#: `automation_engineering/cp3/gate.py`'s own test fixtures). ``Conjunction``
#: (``And``/``But``) and ``Unknown`` are deliberately absent -- a
#: conjunction step inherits whichever of Given/When/Then precedes it in the
#: same scenario (real Gherkin semantics), tracked below rather than mapped
#: here.
_KEYWORD_TYPE_TO_STEP_TYPE = {
    "Context": "Given",
    "Action": "When",
    "Outcome": "Then",
}

_DEFAULT_STEP_TYPE = "Given"


@dataclass(frozen=True, slots=True)
class FeatureStepNeeds:
    """One ``.feature`` file's own ordered step needs, duplicates preserved
    within the file (a feature legitimately repeats the same step text
    across scenarios, e.g. a shared login precondition) -- deduping across
    an entire run's feature set is :func:`derive_unique_step_needs`'s own,
    separate job.
    """

    file_path: Path
    content: str
    needs: tuple[GherkinStepNeed, ...]


def _resolve_step_type(keyword_type: str, last_resolved: str) -> str:
    return _KEYWORD_TYPE_TO_STEP_TYPE.get(keyword_type, last_resolved)


def derive_feature_step_needs(content: str, *, file_path: Path) -> FeatureStepNeeds:
    """Parse one already-in-memory ``.feature`` file's text into its own
    ordered :class:`GherkinStepNeed` tuple, one per step (background steps
    included, in document order), via the same parser CP2/CP3 already use.

    A feature with no ``Feature:`` line (or that fails to parse) yields an
    empty needs tuple, never an exception -- CP2 has already gated every
    feature this stage is handed (only non-escalated ``FeatureRecord``s
    reach this function, ``.runner``'s own filtering), so a genuinely
    malformed file here would itself be a finding worth surfacing loudly,
    not silently working around; this function stays honest about "no
    steps found" either way.
    """
    source = parse_source_text(content, path=str(file_path))
    feature = source.feature
    if not feature:
        return FeatureStepNeeds(file_path=file_path, content=content, needs=())

    needs: list[GherkinStepNeed] = []
    for child in feature.get("children", []):
        scenario = child.get("scenario")
        if scenario is None:
            continue
        last_type = _DEFAULT_STEP_TYPE
        for step in scenario.get("steps", []):
            last_type = _resolve_step_type(step.get("keywordType", ""), last_type)
            needs.append(GherkinStepNeed(text=step.get("text", ""), step_type=last_type))
    return FeatureStepNeeds(file_path=file_path, content=content, needs=tuple(needs))


def derive_unique_step_needs(
    per_feature: tuple[FeatureStepNeeds, ...],
) -> tuple[GherkinStepNeed, ...]:
    """One :class:`GherkinStepNeed` per unique step TEXT across every
    feature in ``per_feature``, first-seen order.

    This is the batch-level dedup the reuse engine and every generator
    actually consume: reuse-deciding or generating the identical step text
    twice (once per feature that happens to reuse it) would be wasted work
    and, for a live, non-deterministic generator, could produce two
    different Java implementations of what Cucumber itself treats as one
    glue binding. ``step_type`` for a step text seen in more than one
    feature is whichever feature saw it first -- informational only (no
    reuse-safety check reads it, see module docstring), never
    identity-bearing.
    """
    seen: dict[str, GherkinStepNeed] = {}
    for feature_needs in per_feature:
        for need in feature_needs.needs:
            seen.setdefault(need.text, need)
    return tuple(seen.values())


__all__ = ["FeatureStepNeeds", "derive_feature_step_needs", "derive_unique_step_needs"]
