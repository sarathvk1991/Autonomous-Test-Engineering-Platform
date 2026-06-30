"""Concrete validation rule implementations, grouped by layer.

Every rule here conforms to ``docs/architecture/validation-rule-catalog.md`` and
is implemented per ``docs/development/validation-rule-development-guide.md``:
one rule per file, files grouped by validation layer.

Rules are discovered by **registration**, never by import side effects.  Each
layer package exposes a ``register_<layer>_rules`` helper that registers its
rules with a :class:`~requirement_intelligence.validation.validation_registry.ValidationRegistry`
using the framework's existing registration mechanism.
"""

from __future__ import annotations
