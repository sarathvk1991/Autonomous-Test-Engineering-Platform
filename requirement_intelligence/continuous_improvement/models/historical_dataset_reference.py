"""The :class:`HistoricalDatasetReference` — provenance, never the dataset itself.

ADR-0021 §Stage 6 defines the **Historical Dataset** as the canonical owner of
historical executions — ordering, lineage, retention, indexing, search,
organization. CAP-083A introduces no Historical Dataset implementation: no
storage, no schema, no query surface. What it freezes instead is the shape of the
**reference** a future Continuous Improvement engine will receive in place of the
dataset itself — the same "reference, never copy" discipline every prior
subsystem's input/consumed-input models already apply (ADR-0018
``EnhancementInputReference``, ADR-0019 ``RecommendationInputReference``), lifted
here to a dataset instead of a single upstream result.

``HistoricalDatasetReference`` is **not** the Historical Dataset. It names one:
which dataset, which version of it, what range of executions it spans, what
history window the governed policy bounded it to, and when the reference was
minted. A future Historical Dataset implementation (Layer 2, reserved) is free to
carry as much internal structure as it needs; nothing about it leaks into this
reference beyond these five provenance fields.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from shared.contracts.base import Schema


class HistoricalDatasetReference(Schema):
    """Provenance naming one Historical Dataset — never its content.

    Carries the dataset identity/version, the execution range it spans (by id,
    never by embedding the executions themselves), the governed history window
    the reference was bounded to, and when the reference was minted. It computes
    nothing and stores nothing beyond this provenance.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    dataset_id: str = Field(..., min_length=1, description="Identity of the historical dataset.")
    dataset_version: str = Field(
        ..., min_length=1, description="Version of the historical dataset's schema/organization."
    )
    first_execution_id: str = Field(
        ..., min_length=1, description="The earliest execution id spanned by this reference."
    )
    last_execution_id: str = Field(
        ..., min_length=1, description="The most recent execution id spanned by this reference."
    )
    execution_count: int = Field(
        ..., ge=1, description="Number of executions spanned by this reference."
    )
    history_window: int = Field(
        ...,
        ge=1,
        description="The governed history window (executions) this reference was bounded to.",
    )
    generated_at: datetime = Field(..., description="When this reference was minted.")

    @model_validator(mode="after")
    def _validate_reference(self) -> HistoricalDatasetReference:
        """The execution count must not exceed the governed history window."""
        if self.execution_count > self.history_window:
            raise ValueError(
                f"execution_count ({self.execution_count}) must not exceed the governed "
                f"history_window ({self.history_window})."
            )
        return self
