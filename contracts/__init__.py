"""Cross-layer boundary contracts.

Distinct from ``shared/contracts/`` (the ``Schema`` base class and other shared
infrastructure every layer's models build on) and from any single layer's own
internal models (e.g. ``requirement_intelligence/analysis/analysis_models.py`` —
Layer-1-internal, never a boundary artifact, ADR-0034). This package holds the
contracts that actually cross a layer boundary: :mod:`contracts.testable_requirement`
(the Layer 1 -> Layer 2 contract, ADR-0034 / ADR-0042) and
:mod:`contracts.test_data_specification` (the Layer 2 -> Layer 3 contract,
ADR-0043 D7 / ADR-0044 D7). ``contracts.testable_requirement``'s checked-in
JSON Schema lives under ``contracts/schemas/`` (ADR-0042 Decision 6).

Each boundary contract module owns its own ``CONTRACT_VERSION`` constant
(independently versioned — a shape change to one boundary never bumps the
other's). Only :mod:`contracts.testable_requirement`'s is re-exported at
this package's own top level, unqualified, for backward compatibility with
every existing `from contracts import CONTRACT_VERSION` call site; a second,
same-named constant from a different module would shadow it, not
coexist with it, so :mod:`contracts.test_data_specification`'s own version
is available only via its own module, never re-exported here bare.
"""

from __future__ import annotations

from contracts.test_data_specification import TestDataFieldSpec, TestDataSpecification
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
    "TestDataFieldSpec",
    "TestDataSpecification",
    "TestableRequirement",
    "TestableRequirementSet",
    "TestableRequirementSetProvenance",
    "build_risk",
    "build_testable_requirement",
]
