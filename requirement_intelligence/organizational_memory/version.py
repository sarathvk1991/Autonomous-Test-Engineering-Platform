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

#: Version of the governed default organizational memory policy. 1.0.0 was
#: the CAP-085A foundation policy (capability switches and deterministic
#: thresholds as data only, no capability exercised). 1.1.0 is the CAP-085B
#: tuning: the governed ``enable_deterministic_engine`` switch flips to
#: ``True`` now that ``DeterministicOrganizationalMemoryEngine`` exists — a
#: versioned policy *value* change, never a policy *shape* change and never
#: an engine code change (mirrors ADR-0022 Recommendation 5, ADR-0023
#: Recommendation 5).
ORGANIZATIONAL_MEMORY_POLICY_VERSION = OrganizationalMemoryPolicyVersion(1, 1, 0)
