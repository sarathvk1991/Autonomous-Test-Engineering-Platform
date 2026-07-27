"""D5's bounded remediation loop -- structured result contract.

Two future, NOT-built-here consumers read this shape:

* Run-state (ADR-0036 stage 14) reads ``status`` to record CP2/remediation
  as the pipeline stage's outcome, and ``final_content`` to know what (if
  anything) to persist.
* A future human-in-the-loop mechanism (ADR-0043 D5 / LLD §17) reads
  ``escalation_reason`` and the last attempt's ``cp2_result`` (per-criterion
  failures) to decide what to show a reviewer -- never built here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from feature_engineering.cp2.models import CP2Result

#: ADR-0043 D5: "Two rules are non-remediable: no-empty-file,
#: no-files-without-scenarios... A violation of either means generation
#: itself failed -- there is no content to remediate -- so these escalate
#: directly to human-in-the-loop rather than entering the 2-attempt loop."
#: Neither the linter nor CP2 special-cases these rule names themselves
#: (both treat every lint violation uniformly) -- this loop is the one
#: place that reads for them, by name, to route around the loop entirely.
NON_REMEDIABLE_RULES: frozenset[str] = frozenset({"no-empty-file", "no-files-without-scenarios"})

#: ADR-0040 Decision 1 / ADR-0043 D5, binding, not a tunable parameter:
#: "Repair loops are bounded at a maximum of 2 LLM remediation attempts;
#: on exhaustion, escalate to human-in-the-loop."
MAX_LLM_REMEDIATION_ATTEMPTS = 2


class RemediationStatus(StrEnum):
    """The loop's own outcome -- distinct from CP2's PASS/FAIL/WARN
    vocabulary (:class:`~shared.enums.base.ValidationVerdict`), which
    describes one gate evaluation, not a bounded, possibly-multi-attempt
    process. ``ESCALATED`` has no CP2 analogue: CP2 alone never "gives up",
    only this loop does, and only after exhausting
    :data:`MAX_LLM_REMEDIATION_ATTEMPTS` or hitting a non-remediable
    violation.
    """

    PASSED = "passed"
    ESCALATED = "escalated"


@dataclass(frozen=True, slots=True)
class RemediationAttempt:
    """One Tier-2 (LLM) remediation attempt's own record.

    ``attempt_number`` is 1-based and never exceeds
    :data:`MAX_LLM_REMEDIATION_ATTEMPTS`. ``cp2_result`` is the re-gate
    outcome for `content_after` -- computed by the SAME, unmodified CP2
    evaluator every other caller uses; this loop never re-implements or
    relaxes any CP2 criterion.
    """

    attempt_number: int
    content_before: str
    content_after: str
    cp2_result: CP2Result


@dataclass(frozen=True, slots=True)
class RemediationResult:
    """The single output of one D5 remediation run over one dirty feature.

    ``attempts`` holds only Tier-2 (LLM) attempts -- Tier 1 (the
    deterministic formatter) runs at most once, unconditionally, before any
    LLM call, and its own before/after is recorded via `tier1_formatted`
    rather than as an "attempt" (it is never bounded, never escalates on
    its own, and costs no LLM call). ``final_content`` is:

    * the Tier-1-formatted content, if that alone reached PASS;
    * the last successful attempt's `content_after`, if PASSED via Tier 2;
    * the last attempt's `content_after`, or the pre-Tier-2 content if no
      attempt ran at all, if ESCALATED.

    ``final_cp2_result`` is always the CP2 evaluation of `final_content` --
    the same object a caller would get by calling `evaluate_cp2` on it
    directly. This result never claims a feature passed when
    `final_cp2_result.passed` is `False`; the two are structurally kept in
    sync by construction (see :mod:`.loop`), not merely by convention.
    """

    status: RemediationStatus
    requirement_id: str
    tier1_formatted: bool
    attempts: tuple[RemediationAttempt, ...]
    final_content: str
    final_cp2_result: CP2Result
    escalation_reason: str | None = None

    @property
    def llm_attempt_count(self) -> int:
        return len(self.attempts)


__all__ = [
    "MAX_LLM_REMEDIATION_ATTEMPTS",
    "NON_REMEDIABLE_RULES",
    "RemediationAttempt",
    "RemediationResult",
    "RemediationStatus",
]
