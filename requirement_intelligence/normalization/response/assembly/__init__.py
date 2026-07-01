"""Internal normalization-stage layer of the ``ResponseNormalizer``.

This package realises the **internal collaboration** governed by the Normalization
Assembly Contract (``docs/architecture/normalization-assembly-contract.md``): the
five stages ``NORMALIZATION-0001 … 0005`` and the transient ``AssemblyState``
through which they exchange intermediate facts.

Per **ADR-0002**, everything here lives **inside the ``ResponseNormalizer``
boundary** and is **not** part of the generic Response Normalization Framework:
the framework is unaware of the Assembly State, the stage collaboration, and the
``ParsedResponse`` assembly.

Phase status
------------
``NORMALIZATION-0001`` (Recover Canonical Structure) is implemented as the
reference pattern; ``0002 … 0005`` follow the same
:class:`~requirement_intelligence.normalization.response.assembly.normalization_stage.NormalizationStage`
shape.  Wiring the stages into the ``ResponseNormalizer``'s execution flow is a
subsequent task (it is not wired here, so no existing component is modified).
"""

from __future__ import annotations

from requirement_intelligence.normalization.response.assembly.assembly_state import (
    AssemblyState,
)
from requirement_intelligence.normalization.response.assembly.canonical_structure_recoverer import (
    CanonicalStructureRecoverer,
)
from requirement_intelligence.normalization.response.assembly.normalization_stage import (
    NormalizationStage,
)
from requirement_intelligence.normalization.response.assembly.normalization_stage_metadata import (
    DEFAULT_STAGE_ORDER,
    DEFAULT_STAGE_VERSION,
    NormalizationStageMetadata,
)
from requirement_intelligence.normalization.response.assembly.recover_canonical_structure import (
    RecoverCanonicalStructure,
)
from requirement_intelligence.normalization.response.assembly.stage_coordinator import (
    NormalizationStageCoordinator,
)
from requirement_intelligence.normalization.response.assembly.stage_exceptions import (
    AssemblyStateError,
    NormalizationStageError,
    StageCoordinationError,
    StructureRecoveryError,
)

__all__ = [
    "DEFAULT_STAGE_ORDER",
    "DEFAULT_STAGE_VERSION",
    "AssemblyState",
    "AssemblyStateError",
    "CanonicalStructureRecoverer",
    "NormalizationStage",
    "NormalizationStageCoordinator",
    "NormalizationStageError",
    "NormalizationStageMetadata",
    "RecoverCanonicalStructure",
    "StageCoordinationError",
    "StructureRecoveryError",
]
