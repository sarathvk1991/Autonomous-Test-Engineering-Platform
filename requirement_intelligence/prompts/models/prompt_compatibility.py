"""Prompt compatibility declarations.

Every governed prompt explicitly declares the downstream subsystem versions it
is compatible with.  Compatibility is **metadata only** — it carries no runtime
behaviour and triggers no enforcement.  It is an architectural record that
allows dependency auditing, regression planning, and impact analysis when any
referenced subsystem version advances.

Compatibility contract
-----------------------
A prompt author updates :class:`PromptCompatibility` when a downstream
subsystem advances its governed version *and* the prompt must be verified
against the new version.  The update is part of the normal version bump
process:

* PATCH bump: compatibility metadata unchanged (wording-only fix).
* MINOR bump: compatibility metadata **may** need updating.
* MAJOR bump: compatibility metadata **must** be updated.

Governed dimensions (Phase 7)
------------------------------
normalization_version
    The ``NORMALIZATION_CONTRACT_VERSION`` the prompt was validated against.
    Governed by ``docs/architecture/response-normalization-contract.md``.

validation_version
    The ``DEFAULT_VALIDATION_CONTRACT_VERSION`` the prompt was validated
    against.  Governed by ``docs/architecture/ai-response-validation.md``.

cp1_version
    The ``DEFAULT_CP1_CRITERIA_CONTRACT_VERSION`` the prompt was validated
    against.  Governed by the Engineering Readiness Criteria Catalog (ADR-0012).

golden_dataset_version
    The ``GOLDEN_DATASET_VERSION`` the prompt was regression-tested against.
    Governed by ``docs/productization/golden-baseline.md``.

output_schema_version
    The version of the governed JSON response schema the prompt targets.
    The schema is defined by the prompt's own ``JSON_RESPONSE_REQUIREMENTS``
    constant and advances when new top-level keys are added or removed.
"""

from __future__ import annotations

from shared.contracts.base import Schema


class PromptCompatibility(Schema):
    """Explicit compatibility declarations for one versioned prompt.

    All fields are plain strings that mirror the governing version constants
    defined in each referenced subsystem.  No imports from those subsystems;
    no coupling; information only.

    Fields
    ------
    normalization_version:
        Normalization contract version the prompt is verified against
        (e.g. ``"1.0"``).
    validation_version:
        Validation contract version the prompt is verified against
        (e.g. ``"1.0"``).
    cp1_version:
        CP1 criteria contract version the prompt is verified against
        (e.g. ``"1.0"``).
    golden_dataset_version:
        Golden dataset version the prompt's regression suite used
        (e.g. ``"1.0.0"``).
    output_schema_version:
        Governed JSON response schema version this prompt targets
        (e.g. ``"1.0.0"``).
    """

    normalization_version: str
    validation_version: str
    cp1_version: str
    golden_dataset_version: str
    output_schema_version: str
