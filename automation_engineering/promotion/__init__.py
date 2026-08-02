"""Layer 3's promotion capstone (ADR-0045) -- the workspace -> tracked-
baseline transition that closes the reuse loop.

**Scope (D1): promotion only.** This package builds ONLY what ADR-0045
locks -- the promotable gate (D2), the review model (D3), and the copy/stage
mechanism (D5). It deliberately does NOT build any of Layer 4's broader
suite-level integration governance (ADR-0040 Decision 3): orphaned-glue
detection, the suite-wide near-duplicate sweep, or the aggregate release
gate. Those remain Layer 4's, unchanged, and nothing here anticipates their
shape.

Why promotion exists at all: the reuse catalog (ADR-0044 D3,
:mod:`automation_engineering.catalog`) is reconciled from the tracked
baseline's own committed Java at the start of every run -- a generated asset
that only ever lands in a run's untracked workspace
(:mod:`automation_engineering.catalog.scanner`'s own ``JAVA_SOURCE_SUBPATH``,
ADR-0037 Path A) is invisible to the next run's reconciliation unless this
package moves it into the tracked baseline first. Promotion is what makes
reuse accumulate across runs at all -- run N's promotion is run N+1's
catalog content.

Package layout:

* :mod:`.models` -- the decision vocabulary (``Promoted`` / ``NotPromotable``
  / ``PromotionEscalated``), a closed union mirroring
  :mod:`automation_engineering.reuse.models`'s own discipline.
* :mod:`.identity` -- resolves a freshly generated asset's own identity
  (content-hash, class name, destination path) via the SAME scan the
  catalog itself uses (:func:`automation_engineering.catalog.scanner.
  reconcile`) -- never a second, hand-rolled hashing mechanism.
* :mod:`.gate` -- the pure D2/D3 decision: given a resolved candidate, its
  gate outcomes, and the reconciled baseline catalog, decide
  promote/block/escalate.
* :mod:`.outcomes` -- the glue mapping generation's own outcome unions
  (:mod:`automation_engineering.generation.models`) onto this package's
  gate inputs.
* :mod:`.mechanism` -- D5's copy-then-stage mechanism: writes a promoted
  candidate's Java into the tracked baseline and ``git add``s it (stages
  for review; never auto-commits -- see the module docstring for the
  resolved TBD and its rationale).
"""

from __future__ import annotations
