"""Per-asset decomposition of CP3's whole-batch result (ADR-0044 D5 additive
note, ADR-0045 D2 additive note, 2026-08-06): CP3 evaluates seven criteria
once per RUN, not once per candidate (`automation_engineering.cp3.gate.
evaluate_cp3`, called once in `stage/runner.py`) -- this module reinterprets
that SAME already-computed `Cp3Result` (no re-parsing, no re-scan, no new
validation surface, per ADR-0045 D2's own "no new validation surface is
introduced") to answer "does THIS candidate's own promotion depend on THIS
criterion," criterion by criterion, rather than treating one FAIL anywhere
in the batch as blocking every candidate.

**Three criteria genuinely decompose per-asset**, because the underlying
computation already IS per-class/per-asset, only its verdict was previously
collapsed into one shared pass/fail across the whole batch:

* `direct_webdriver_action` / `long_method` -- `cp3/architecture.py`'s own
  `_evaluate_one_class`/`_long_method_messages` already loop class by class,
  one message per offending CLASS (`f"{class_name}: ..."` /
  `f"{class_name}.{method}: ..."`). This module filters those SAME messages
  by whether THIS candidate's own `class_name` is the one named.
* `duplicate_steps` -- `cp3/coverage.py`'s own `_find_duplicate_patterns`
  already reports one message per colliding PATTERN, naming every asset_id
  in the collision (`f"...bound by N step-definition assets: {asset_id}
  (...), ..."`). This module filters by whether THIS candidate's own
  `asset_id` appears in a collision message. NOTE this is a DIFFERENT check
  from ADR-0045 D2(b)'s own duplicate check (`promotion/gate.py`'s
  content-hash lookup against the TRACKED baseline catalog) -- CP3's
  `duplicate_steps` instead scans the post-generation WORKSPACE catalog for
  Cucumber-ambiguous-glue WITHIN this one run's own output. The two are
  independent checks over different catalogs; this module decomposes only
  the former, D2(b) already being per-candidate by construction.

**`sonar_quality_gate` does not decompose.** `SonarQualityGateResult`
(`cp3/sonar/models.py`) carries no file/class attribution -- the server's
own `/api/qualitygates/project_status` reports ONE verdict for the whole
scanned Maven project, never per class (`SonarQualityGateCondition` is
`metric_key`/`status`/`actual_value`/`error_threshold` only). A whole-
project Sonar FAIL is therefore applied UNIFORMLY to every candidate in the
batch -- honest given the real machinery, not a downgrade of the per-asset
design (ADR-0044 D5's additive note, this same date).

**`step_coverage`/`scenario_coverage`/`unmapped_steps` are excluded from
the per-asset gate entirely, not merely filtered.** A candidate reaching
this module's own caller (`promotion.gate.evaluate_promotion`) is, by
construction, resolved (`promotion/outcomes.py::promote_outcome` routes
only `Generated*`/`Bound*` outcomes there -- an `Escalated*` outcome never
becomes a `PromotionCandidate` at all, D3). Its own Gherkin step therefore
already has a mapped outcome; these three criteria can only fail because of
a DIFFERENT, unresolved need elsewhere in the batch. Excluding them is
equivalent to recomputing coverage over the resolved-needs-only subset and
finding this one need already inside it (ADR-0044 D5's additive note) -- it
is the same check, correctly scoped to what it can actually be true or
false ABOUT for one candidate, not a weaker one.
"""

from __future__ import annotations

from dataclasses import dataclass

from automation_engineering.cp3.models import (
    CRITERION_DIRECT_WEBDRIVER_ACTION,
    CRITERION_DUPLICATE_STEPS,
    CRITERION_LONG_METHOD,
    CRITERION_SONAR_QUALITY_GATE,
    Cp3Result,
)
from shared.enums.base import ValidationVerdict


@dataclass(frozen=True, slots=True)
class Cp3AssetVerdict:
    """One candidate's own CP3 promotion-eligibility verdict, decomposed
    from the batch's `Cp3Result` -- never a fresh evaluation, never a
    re-parse or re-scan."""

    verdict: ValidationVerdict
    messages: tuple[str, ...]


def _class_implicated(messages: tuple[str, ...], class_name: str) -> tuple[str, ...]:
    """Messages naming `class_name` specifically -- `architecture.py`'s own
    message shape is always `"{class_name}: ..."` (an import violation) or
    `"{class_name}.{method}: ..."` (a call/long-method violation), so a
    prefix check cannot false-match a different class whose name happens to
    share a substring."""
    return tuple(
        message
        for message in messages
        if message.startswith(f"{class_name}:") or message.startswith(f"{class_name}.")
    )


def _asset_implicated(messages: tuple[str, ...], asset_id: str) -> tuple[str, ...]:
    """Messages naming `asset_id` specifically -- `_find_duplicate_patterns`
    always includes every colliding asset's own stable `asset_id` in its
    message text (`coverage.py`'s own `_find_duplicate_patterns`)."""
    return tuple(message for message in messages if asset_id in message)


def decompose_for_asset(result: Cp3Result, *, class_name: str, asset_id: str) -> Cp3AssetVerdict:
    """This candidate's own CP3 verdict: FAIL iff the batch's own Sonar
    quality gate failed (whole-project, applies to every candidate alike)
    OR a per-class/per-asset criterion's own messages name THIS class/asset
    specifically -- never because some OTHER need in the batch escalated,
    or some OTHER class/asset failed its own check.
    """
    messages: list[str] = []

    sonar = result.criterion(CRITERION_SONAR_QUALITY_GATE)
    if sonar.verdict != ValidationVerdict.PASS:
        messages.extend(
            sonar.messages
            or (f"{CRITERION_SONAR_QUALITY_GATE}: whole-project Sonar quality gate failed",)
        )

    webdriver = result.criterion(CRITERION_DIRECT_WEBDRIVER_ACTION)
    messages.extend(_class_implicated(webdriver.messages, class_name))

    long_method = result.criterion(CRITERION_LONG_METHOD)
    messages.extend(_class_implicated(long_method.messages, class_name))

    duplicate = result.criterion(CRITERION_DUPLICATE_STEPS)
    messages.extend(_asset_implicated(duplicate.messages, asset_id))

    verdict = ValidationVerdict.FAIL if messages else ValidationVerdict.PASS
    return Cp3AssetVerdict(verdict=verdict, messages=tuple(messages))


__all__ = ["Cp3AssetVerdict", "decompose_for_asset"]
