"""Canonical version constants for the Organizational Memory Framework.

Kept in the organizational_memory package (not ``platform_metadata``) so
registering the framework changes no existing platform catalogue or manifest
field, and the Architecture Version stays 1.2.0 — mirroring
``continuous_improvement/version.py`` (ADR-0022) and
``knowledge_graph/version.py`` (ADR-0023).
"""

from __future__ import annotations

from requirement_intelligence.organizational_memory.identity import (
    OrganizationalMemoryFrameworkVersion,
    OrganizationalMemoryPolicyVersion,
)

#: Version of the Organizational Memory Framework code/contract. 1.0.0 is the
#: CAP-085A foundation: canonical models, typed identities, enumerations, the
#: governed policy and its builder, and the dormant Organizational Memory
#: service contract.
ORGANIZATIONAL_MEMORY_FRAMEWORK_VERSION = OrganizationalMemoryFrameworkVersion(1, 0, 0)

#: Version of the governed default organizational memory policy. 1.0.0 is the
#: CAP-085A foundation policy (capability switches and deterministic
#: thresholds as data only, no capability exercised — the deterministic
#: engine switch is reserved off until a future CAP-085B).
ORGANIZATIONAL_MEMORY_POLICY_VERSION = OrganizationalMemoryPolicyVersion(1, 0, 0)
