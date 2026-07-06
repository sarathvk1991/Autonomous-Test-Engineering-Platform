"""CP1 engineering-readiness criteria (CAP-067A).

Concrete criteria governed by the **Engineering Readiness Criteria Catalog** (ADR-0012)
— the CP1 analogue of the Validation ``rules/`` package.

* **CP1-0001** — :class:`EngineeringInputAvailabilityCriterion` (ADR-0013): the
  validated response must provide **at least one** requirement to engineer from
  (Engineering Input Availability).  The catalog's first and only criterion.
"""

from __future__ import annotations

from requirement_intelligence.cp1.criteria.engineering_input_availability import (
    EngineeringInputAvailabilityCriterion,
)

__all__ = ["EngineeringInputAvailabilityCriterion"]
