"""CP1 engine composition (reserved).

Reserved home for the assembled, runnable CP1 engine — the composition of the
framework contract, registry, and pipeline that executes the governed criteria and
produces a ``CP1Result`` (**ADR-0011 §D7**), analogous to the Validation subsystem's
composition root (``validator_factory``).

Intentionally **empty**: this package establishes the subsystem layout only.  No
engine, composition root, or other implementation exists yet — that is a later
milestone.  The exact placement of components across ``framework``/``engine``/
``response`` is finalized by the implementing milestone; this task fixes only the
layout.
"""

from __future__ import annotations
