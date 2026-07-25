"""Cross-layer boundary contracts.

Distinct from ``shared/contracts/`` (the ``Schema`` base class and other shared
infrastructure every layer's models build on) and from any single layer's own
internal models (e.g. ``requirement_intelligence/analysis/analysis_models.py`` —
Layer-1-internal, never a boundary artifact, ADR-0034). This package holds the
contracts that actually cross a layer boundary, starting with
:mod:`contracts.testable_requirement` (the Layer 1 -> Layer 2 contract, ADR-0034 /
ADR-0042). Its checked-in JSON Schema lives under ``contracts/schemas/``
(ADR-0042 Decision 6).
"""

from __future__ import annotations

from contracts.testable_requirement import (
    CONTRACT_VERSION,
    AcceptanceCriterion,
    AcceptanceCriterionInput,
    Category,
    PolarityHint,
    Priority,
    RequirementQualityGovernanceDecision,
    Risk,
    RiskInput,
    SourceRef,
    TestableRequirement,
    TestableRequirementSet,
    TestableRequirementSetProvenance,
    build_risk,
    build_testable_requirement,
)

__all__ = [
    "CONTRACT_VERSION",
    "AcceptanceCriterion",
    "AcceptanceCriterionInput",
    "Category",
    "PolarityHint",
    "Priority",
    "RequirementQualityGovernanceDecision",
    "Risk",
    "RiskInput",
    "SourceRef",
    "TestableRequirement",
    "TestableRequirementSet",
    "TestableRequirementSetProvenance",
    "build_risk",
    "build_testable_requirement",
]
