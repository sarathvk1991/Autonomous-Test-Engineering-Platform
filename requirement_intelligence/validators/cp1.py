"""Legacy CP1 entry-point placeholder.

Historical note
---------------
This module predates the CP1 subsystem (**ADR-0011**, **ADR-0012**) and the CP1
canonical models (**CAP-062**).  It formerly defined its own ``CP1Result`` and
``CP1Finding`` models and consumed an obsolete ``list[CanonicalRequirement]`` input.
Those have been **reconciled away** (CAP-063A):

* The canonical CP1 models live **only** in
  :mod:`requirement_intelligence.cp1.models` (``CP1Input``, ``CP1Result``,
  ``CP1Finding``, ``CP1FrameworkMetadata``).
* The reusable engine infrastructure lives in
  :mod:`requirement_intelligence.cp1.framework`.

Current role
------------
This file retains **only** a legacy placeholder for the future CP1 entry point
(:class:`CP1Validator`), per **ADR-0011 §D9**, which retains the ``validators/``
location and the ``CAP-060`` allocation.  It owns **no** canonical models, no
framework metadata, no verdict logic, no readiness logic, and no criteria.

The concrete CP1 engine — verdict aggregation over criterion findings and
``CP1Result`` assembly — is a **future milestone** (CAP-064+) and belongs to the CP1
subsystem (:mod:`requirement_intelligence.cp1.engine`), **not** here.  The CAP-063A
report recommends retiring this placeholder in favour of ``cp1/engine/`` once an
ADR-0011 §D9 amendment authorises relocating the retained ``validators/`` location.
"""

from __future__ import annotations

from requirement_intelligence.cp1.models import CP1Input, CP1Result


class CP1Validator:
    """Legacy placeholder for the future CP1 engine entry point (ADR-0011 §D9).

    Owns no models and no logic.  The reconciled input is the canonical
    :class:`~requirement_intelligence.cp1.models.cp1_input.CP1Input` (ADR-0011 §D3),
    superseding the obsolete ``list[CanonicalRequirement]`` signature; the output is
    the canonical
    :class:`~requirement_intelligence.cp1.models.cp1_result.CP1Result`.  The concrete
    implementation (verdict aggregation + result assembly) is deferred to the CP1
    engine milestone and lives in :mod:`requirement_intelligence.cp1.engine`.
    """

    def validate(self, cp1_input: CP1Input) -> CP1Result:
        """Evaluate the CP1 gate over *cp1_input* and return the ``CP1Result``.

        Not implemented — the concrete CP1 engine is a future milestone (CAP-064+).
        """
        raise NotImplementedError
