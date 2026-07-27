"""CP2's structured result contract (ADR-0040 Decision 1/2, ADR-0043 D5).

Two future, NOT-built-here consumers read this shape:

* The bounded remediation loop (D5, max 2 attempts) reads ``criteria`` to
  decide what to hand an LLM for a fix-and-relint attempt -- a criterion
  whose ``verdict`` is ``FAIL`` names exactly which check failed and why
  (``messages``). It also reads which specific rules fired inside the
  ``lint`` criterion to decide the two non-remediable cases (D5:
  ``no-empty-file``, ``no-files-without-scenarios``) that must escalate
  directly to human-in-the-loop instead of entering the loop.
* Run-state (ADR-0036 stage 14) reads ``overall_verdict`` to record CP2's
  stage outcome.

Neither consumer is built here. ``advisory`` is a third, human-in-the-loop
consumer (ADR-0043 D5 / LLD §17): a future LLM-judged check
("Feature generation confidence low," "Generated feature changes business
intent," etc.) would read/write it to decide when to escalate a
CP2-``PASS``ing feature for human review anyway -- again, not built here.
"""

from __future__ import annotations

from dataclasses import dataclass

from shared.enums.base import ValidationVerdict

#: The four criteria ADR-0043 D5 names, verbatim: "lint result;
#: acceptance-criteria coverage...; tag presence...; duplicate detection...".
CRITERION_LINT = "lint"
CRITERION_AC_COVERAGE = "acceptance_criteria_coverage"
CRITERION_TAG_PRESENCE = "tag_presence"
CRITERION_DUPLICATE_DETECTION = "duplicate_detection"

CP2_CRITERIA: tuple[str, ...] = (
    CRITERION_LINT,
    CRITERION_AC_COVERAGE,
    CRITERION_TAG_PRESENCE,
    CRITERION_DUPLICATE_DETECTION,
)


@dataclass(frozen=True, slots=True)
class CP2CriterionResult:
    """One CP2 gate criterion's own deterministic verdict.

    ``verdict`` is always ``PASS`` or ``FAIL`` -- every CP2 criterion is an
    exact, countable computation (ADR-0040 Decision 2), never a score.
    ``WARN`` is representable by the shared :class:`ValidationVerdict` type
    (mirroring CP1's own vocabulary, ADR-0011) but no CP2 criterion below
    ever produces it: D5 defines only pass/fail-shaped floors ("zero
    violations", "every AC-* has >=1 mapped SCN-*", "all present", "no
    duplicates"), none with WARN semantics.

    ``messages`` carries zero or more human-readable specifics -- empty on a
    clean ``PASS``, one entry per distinct problem on a ``FAIL`` (e.g. one
    line per lint violation, one line per uncovered AC, one line per missing
    tag). This is what lets a failure "say exactly which criterion failed
    and why," per this task's own requirement, without inventing a second
    per-item severity/blocking model duplicating what ``LintResult``
    already carries for the lint criterion specifically.
    """

    criterion: str
    verdict: ValidationVerdict
    messages: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CP2AdvisorySignals:
    """RESERVED, non-gating LLM-judged signals (ADR-0040 Decision 2's
    deterministic/advisory boundary, made structural).

    Layer 2's generator does not produce these today -- there is no live
    equivalent of ``validate-generated-feature.md``'s "Business readability"
    / "Step reusability" checks wired into this pipeline. This slot exists
    so a *future* caller has somewhere to attach that judgement without
    touching :class:`CP2Result`'s shape, and so that attaching it is
    structurally incapable of influencing :attr:`CP2Result.overall_verdict`:
    no code in this package ever reads ``advisory`` when computing a
    verdict, and no field on this class participates in
    :func:`~.evaluator.evaluate_cp2`'s pass/fail computation. A future
    human-in-the-loop trigger (ADR-0043 D5 / LLD §17) reads this field
    directly -- never built here.

    Every field is free text: a negative value (e.g. "low confidence") is a
    review prompt, never a gate input.
    """

    business_readability: str | None = None
    step_reusability: str | None = None


@dataclass(frozen=True, slots=True)
class CP2Result:
    """The single output of one CP2 evaluation over one ``GeneratedFeature``.

    ``overall_verdict`` is derived from ``criteria`` alone (``PASS`` iff
    every criterion's own verdict is ``PASS``) -- never from ``advisory``,
    which is fixed at construction and read by nothing in this package.
    """

    requirement_id: str
    overall_verdict: ValidationVerdict
    criteria: tuple[CP2CriterionResult, ...]
    advisory: CP2AdvisorySignals | None = None

    def criterion(self, name: str) -> CP2CriterionResult:
        """Return the named criterion's result.

        Raises
        ------
        KeyError
            If no criterion with this name was evaluated.
        """
        for c in self.criteria:
            if c.criterion == name:
                return c
        raise KeyError(f"No CP2 criterion named {name!r} in this result.")

    @property
    def passed(self) -> bool:
        return self.overall_verdict == ValidationVerdict.PASS


__all__ = [
    "CP2_CRITERIA",
    "CRITERION_AC_COVERAGE",
    "CRITERION_DUPLICATE_DETECTION",
    "CRITERION_LINT",
    "CRITERION_TAG_PRESENCE",
    "CP2AdvisorySignals",
    "CP2CriterionResult",
    "CP2Result",
]
