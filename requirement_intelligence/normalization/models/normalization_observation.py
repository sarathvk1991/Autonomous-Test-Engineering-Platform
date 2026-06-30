"""NormalizationObservation — one recorded, un-judged fact about a response.

:class:`NormalizationObservation` is the conceptual realisation of the
Normalization Observation concept in
``docs/architecture/response-normalization-contract.md`` (§8, §10).  It records
exactly **one** objective fact the Response Normalization Layer noticed while
recovering structure — a fact a later consumer may *interpret*, but which
normalization itself never *judges*.

Facts, not judgments
--------------------
An observation is a **fact**.  Per the frozen Normalization-Validation boundary
(Response Normalization Contract §10) it therefore carries:

* **no severity** — severity is a validation concept;
* **no verdict** — verdicts are a validation concept;
* **no recommendation** and **no blocking indicator** — those are judgments.

A validation rule (a separate subsystem) may *read* an observation and *decide*
to raise a :class:`~requirement_intelligence.validation.models.validation_issue.ValidationIssue`
— but that decision belongs entirely to validation.  A NormalizationObservation
is **never itself** a ValidationIssue.

This is the deliberate counterpart to the validation subsystem's
``ValidationIssue``: structurally similar (an atomic, immutable, located record)
but semantically a *fact* rather than a *judgment* — see the framework README for
the full list of deviations from the Validation Framework.

Format independence
-------------------
``observation_type`` is a free string, not a closed enumeration, so the catalog
of observations can grow additively (Response Normalization Contract §15) without
binding the model to any one serialization format.  The well-known values are
published as module constants for convenience; new values are admitted by an ADR
that advances the Normalization Contract Version.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from shared.contracts.base import Schema

#: Well-known ``observation_type`` values (Response Normalization Contract §8).
#: This set is **open**: new observation types are additive and governed by the
#: Normalization Contract Version.  It is published as constants — never a closed
#: enum — to keep the model format-neutral and extensible.
OBSERVATION_DUPLICATE_IDENTIFIER = "duplicate_identifier"
OBSERVATION_MALFORMED_REPRESENTATION = "malformed_representation"
OBSERVATION_ENCODING = "encoding_observation"


class NormalizationObservation(Schema):
    """One atomic, immutable, **un-judged** fact recorded during normalization.

    Field names serialise as ``camelCase`` (``observationId``,
    ``observationType``, ``correlationId``, …); Python attributes stay
    ``snake_case``.  The model is immutable and strictly validated (inherited
    from :class:`~shared.contracts.base.Schema`).

    The model deliberately carries **no severity, no verdict, no recommendation,
    and no blocking indicator** — those are validation judgments, not
    normalization facts (Response Normalization Contract §10).

    Fields
    ------
    observation_id:
        Stable handle that uniquely references this observation.
    observation_type:
        The kind of fact recorded.  An open string (well-known values are
        published as module constants such as
        :data:`OBSERVATION_DUPLICATE_IDENTIFIER`); new types are additive.
    detail:
        Human-readable statement of *what was observed* — a fact, never a
        judgement about whether it matters.
    location:
        Where in the response the fact occurs, when applicable.  Optional.
    evidence:
        The observed value or condition that substantiates the fact.  Optional —
        some observations (e.g. a structural absence) have no evidence value.
    correlation_id:
        Trace key linking the observation to its originating normalization run.
        Optional.
    created_at:
        When the observation was recorded.
    metadata:
        Free-form metadata associated with the observation.  Preserved verbatim.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    observation_id: str
    observation_type: str
    detail: str
    location: str | None = None
    evidence: str | None = None
    correlation_id: str | None = None
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
