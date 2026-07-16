"""Canonical version constants for the Learning Framework.

Kept in the learning package (not ``platform_metadata``) so registering the
framework changes no existing platform catalogue or manifest field, and the
Architecture Version stays 1.2.0 — mirroring
``continuous_improvement/version.py`` (ADR-0022),
``knowledge_graph/version.py`` (ADR-0023), and
``organizational_memory/version.py`` (ADR-0027).
"""

from __future__ import annotations

from requirement_intelligence.learning.identity import (
    LearningFrameworkVersion,
    LearningPolicyVersion,
)

#: Version of the Learning Framework code/contract. 1.0.0 is the CAP-086A
#: foundation: canonical models, typed identities, enumerations, the
#: governed policy and its builder, and the dormant Learning service
#: contract.
LEARNING_FRAMEWORK_VERSION = LearningFrameworkVersion(1, 0, 0)

#: Version of the governed default learning policy. 1.0.0 is the CAP-086A
#: foundation policy (capability switches and deterministic thresholds as
#: data only, no capability exercised — the deterministic engine switch is
#: reserved off until a future CAP-086B).
LEARNING_POLICY_VERSION = LearningPolicyVersion(1, 0, 0)
