"""The step-definition orchestration's own output shapes.

Mirrors :mod:`automation_engineering.reuse.models`'s own discipline exactly:
a closed union, :data:`StepDefinitionOutcome`, one variant per reuse-engine
decision this task's orchestration (:mod:`.orchestrator`) acts on --
:class:`GeneratedStepDefinition` for NO_MATCH,
:class:`BoundStepDefinition` for TRUSTED_REUSE,
:class:`EscalatedStepNeed` for ESCALATION -- exhaustive, so a caller (or
``mypy``, via structural matching) cannot silently drop a case.
"""

from __future__ import annotations

from dataclasses import dataclass

from automation_engineering.catalog.models import CatalogAsset
from automation_engineering.reuse.models import Escalation, GherkinStepNeed


@dataclass(frozen=True, slots=True)
class GeneratedStepDefinition:
    """ADR-0044 D3's reuse-or-generate boundary's "generate" side, realized:
    one Gherkin step the reuse engine found NO_MATCH for, satisfied by a
    freshly generated Java step-definition (:mod:`.step_definition_generator`'s
    own seam, never regeneration of an existing asset).
    """

    need: GherkinStepNeed
    java_source: str
    target_package: str


@dataclass(frozen=True, slots=True)
class BoundStepDefinition:
    """A Gherkin step whose reuse binding was trusted (ADR-0044 D4) --
    bound to an existing catalog asset, never regenerated. ``asset`` is the
    same :class:`~automation_engineering.reuse.models.TrustedReuse.asset`
    the reuse engine resolved -- always a
    :class:`~automation_engineering.catalog.models.StepDefinitionAsset` in
    this task's own orchestration, since the matcher this task wires in
    (:class:`~automation_engineering.reuse.matcher.SemanticMatcher`) only
    ever matches a step-need against catalogued step definitions (see
    :mod:`automation_engineering.reuse.live_matcher`'s own docstring: "Only
    step definitions are matched").
    """

    need: GherkinStepNeed
    asset: CatalogAsset


@dataclass(frozen=True, slots=True)
class EscalatedStepNeed:
    """A Gherkin step whose reuse candidate failed one of ADR-0044 D4's three
    checks -- neither generated nor bound, surfaced for human review via the
    same plain-record discipline every other layer's escalation already uses
    (:mod:`automation_engineering.reuse.engine`'s own module docstring:
    "no new queue, no new mechanism, built here"). ``escalation`` is the
    reuse engine's own :class:`~automation_engineering.reuse.models.Escalation`
    record, unedited -- this variant only re-homes it under this
    orchestration's own result vocabulary, it does not re-decide anything.
    """

    need: GherkinStepNeed
    escalation: Escalation


#: ADR-0044 D3's reuse-or-generate-or-escalate vocabulary, realized for the
#: step-definition generator specifically. A caller handles all three; there
#: is no fourth case.
StepDefinitionOutcome = GeneratedStepDefinition | BoundStepDefinition | EscalatedStepNeed

__all__ = [
    "BoundStepDefinition",
    "EscalatedStepNeed",
    "GeneratedStepDefinition",
    "StepDefinitionOutcome",
]
