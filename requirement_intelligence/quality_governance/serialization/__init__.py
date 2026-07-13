"""Quality Governance serialization — pure projections of a ``QualityGovernanceResult`` (CAP-080D).

Renders the runtime contract into execution artifacts. It computes nothing; it never
re-enters the Quality Governance runtime. See ADR-0017 §D30.
"""

from __future__ import annotations

from requirement_intelligence.quality_governance.serialization.quality_governance_serializer import (  # noqa: E501
    QualityGovernanceSerializer,
)

__all__ = ["QualityGovernanceSerializer"]
