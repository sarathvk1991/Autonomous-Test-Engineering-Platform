"""CP1 engine framework (CAP-063).

The reusable, **behaviour-free** infrastructure of the CP1 engine, governed by the
``Criterion → Registry → Pipeline`` pattern of **ADR-0011 §D7** and mirroring the
frozen Response Validation Framework.

The framework knows **how to run criteria deterministically**; it knows **nothing
about engineering readiness**.  Only future criteria (governed by the Engineering
Readiness Criteria Catalog / ADR-0012 — currently empty) know engineering readiness,
and only the future CP1 engine aggregates findings into a verdict (ADR-0012 §8).

Public surface
--------------
* :class:`CP1Criterion` · :class:`CP1CriterionMetadata` — the criterion contract.
* :class:`CP1CriterionRegistry` · :class:`CP1RegistryState` — the deterministic,
  sealable registry.
* :class:`CP1CriterionPipeline` · :class:`CP1PipelineState` — the orchestrator that
  collects findings (it derives **no** verdict).
* :class:`CP1FrameworkMetadata` + version constants — framework provenance.
* :class:`CP1FrameworkError` and its subtypes — framework-level failures.
* :func:`build_cp1_criterion_registry` · :func:`build_cp1_criterion_pipeline` —
  composition helpers (register no criteria).
"""

from __future__ import annotations

from requirement_intelligence.cp1.framework.composition import (
    build_cp1_criterion_pipeline,
    build_cp1_criterion_registry,
)
from requirement_intelligence.cp1.framework.criterion import CP1Criterion
from requirement_intelligence.cp1.framework.criterion_metadata import (
    DEFAULT_CRITERION_VERSION,
    CP1CriterionMetadata,
)
from requirement_intelligence.cp1.framework.criterion_pipeline import (
    CP1CriterionPipeline,
    CP1PipelineState,
)
from requirement_intelligence.cp1.framework.criterion_registry import (
    CP1CriterionRegistry,
    CP1RegistryState,
)
from requirement_intelligence.cp1.framework.framework_exceptions import (
    CP1CriterionError,
    CP1FrameworkError,
    CP1PipelineError,
    CP1RegistryError,
)
from requirement_intelligence.cp1.framework.framework_metadata import (
    CP1_FRAMEWORK_VERSION,
    CP1_PIPELINE_VERSION,
    CP1_REGISTRY_VERSION,
    DEFAULT_CP1_CRITERIA_CONTRACT_VERSION,
    CP1FrameworkMetadata,
)

__all__ = [
    "CP1_FRAMEWORK_VERSION",
    "CP1_PIPELINE_VERSION",
    "CP1_REGISTRY_VERSION",
    "DEFAULT_CP1_CRITERIA_CONTRACT_VERSION",
    "DEFAULT_CRITERION_VERSION",
    "CP1Criterion",
    "CP1CriterionError",
    "CP1CriterionMetadata",
    "CP1CriterionPipeline",
    "CP1CriterionRegistry",
    "CP1FrameworkError",
    "CP1FrameworkMetadata",
    "CP1PipelineError",
    "CP1PipelineState",
    "CP1RegistryError",
    "CP1RegistryState",
    "build_cp1_criterion_pipeline",
    "build_cp1_criterion_registry",
]
