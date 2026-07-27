"""Prompt semantic version value object and governed lifecycle enumeration.

This module defines two governing concepts:

* :class:`PromptVersion` — an immutable, comparable semantic version
  (``MAJOR.MINOR.PATCH``) for prompt contracts.
* :class:`PromptLifecycle` — the ordered, one-directional lifecycle a prompt
  advances through before it can be retired.

Why a dedicated value object?
------------------------------
The platform stores most versions as plain strings (``"1.0.0"``).  A plain
string is opaque; it cannot be compared semantically, and it cannot be bumped
safely.  :class:`PromptVersion` provides:

1. **Validated parsing** — the constructor rejects malformed strings.
2. **Semantic comparison** — ``<``, ``<=``, ``>``, ``>=``, ``==`` are
   well-defined across major/minor/patch components.
3. **Governed bumping** — :meth:`bump_patch`, :meth:`bump_minor`,
   :meth:`bump_major` enforce the versioning rules documented below.
4. **String round-trip** — ``str(v)`` always returns the canonical
   ``"MAJOR.MINOR.PATCH"`` form.

Versioning Rules (Phase 9)
--------------------------
These rules govern when each component is incremented:

PATCH  (``1.0.0 → 1.0.1``)
    Wording clarification, punctuation fix, or editorial improvement that
    does not alter the semantic meaning of any section.  Output schema
    compatibility is **preserved**.  No compatibility metadata change required.

MINOR  (``1.0.0 → 1.1.0``)
    Addition of a new section or instruction block that does not remove or
    restructure an existing section.  Output schema compatibility is
    **preserved**.  Compatibility metadata **may** need updating when the
    new content requires a newer downstream contract version.

MAJOR  (``1.x.x → 2.0.0``)
    Removal, restructuring, or replacement of a section that changes the
    output schema contract.  Output schema compatibility is **broken**.
    Compatibility metadata **must** be updated.  Every consumer of the
    previous major version must migrate before using the new version.

These rules mirror the semantic-versioning discipline already applied to the
governed normalization, validation, and CP1 frameworks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

# ---------------------------------------------------------------------------
# Governed lifecycle states
# ---------------------------------------------------------------------------


class PromptLifecycle(StrEnum):
    """Ordered, one-directional lifecycle of a governed prompt.

    Members
    -------
    DRAFT
        The prompt is being authored.  It is not stable and must not be used
        in a production pipeline.  A draft prompt may change without a version
        increment.
    EXPERIMENTAL
        The prompt is under active evaluation.  It may be used in non-production
        pipelines.  A version increment is required for any wording change.
    APPROVED
        The prompt has passed review and is authorised for production use.
        Wording changes require a version increment **and** re-approval.
    PRODUCTION
        The prompt is in active production use and is the current canonical
        version.  Only one version of a given prompt should hold this state.
    DEPRECATED
        The prompt has been superseded by a newer version.  Existing consumers
        should migrate; no new usage is permitted.
    ARCHIVED
        The prompt is retired.  It is retained for historical traceability only
        and must not be used.
    """

    DRAFT = "draft"
    EXPERIMENTAL = "experimental"
    APPROVED = "approved"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


# ---------------------------------------------------------------------------
# Semantic version value object
# ---------------------------------------------------------------------------

_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


@dataclass(frozen=True, order=True)
class PromptVersion:
    """Immutable, comparable semantic version for a prompt contract.

    Fields
    ------
    major:
        Major component.  Incremented on breaking output-schema changes.
    minor:
        Minor component.  Incremented on backwards-compatible additions.
    patch:
        Patch component.  Incremented on backwards-compatible clarifications.

    Construction
    ------------
    Use :meth:`parse` to construct from a version string.

    >>> v = PromptVersion.parse("1.0.0")
    >>> v.major, v.minor, v.patch
    (1, 0, 0)
    >>> str(v)
    '1.0.0'
    """

    major: int
    minor: int
    patch: int

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def parse(cls, version_string: str) -> PromptVersion:
        """Parse a semantic version string into a :class:`PromptVersion`.

        Parameters
        ----------
        version_string:
            Must be in ``MAJOR.MINOR.PATCH`` form with non-negative integer
            components (e.g. ``"1.0.0"``).

        Raises
        ------
        ValueError
            If *version_string* does not conform to the expected format.
        """
        match = _SEMVER_RE.match(version_string.strip())
        if not match:
            raise ValueError(
                f"Invalid prompt version string {version_string!r}. "
                f"Expected MAJOR.MINOR.PATCH with non-negative integers "
                f"(e.g. '1.0.0')."
            )
        return cls(
            major=int(match.group(1)),
            minor=int(match.group(2)),
            patch=int(match.group(3)),
        )

    # ------------------------------------------------------------------
    # String representation
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        """Return the canonical ``MAJOR.MINOR.PATCH`` string form."""
        return f"{self.major}.{self.minor}.{self.patch}"

    # ------------------------------------------------------------------
    # Governed bumping (Phase 9 rules)
    # ------------------------------------------------------------------

    def bump_patch(self) -> PromptVersion:
        """Return a new version with the patch component incremented.

        Use for wording clarifications that preserve output schema
        compatibility (see module-level versioning rules).
        """
        return PromptVersion(self.major, self.minor, self.patch + 1)

    def bump_minor(self) -> PromptVersion:
        """Return a new version with the minor component incremented and patch reset.

        Use for additive section additions that preserve output schema
        compatibility (see module-level versioning rules).
        """
        return PromptVersion(self.major, self.minor + 1, 0)

    def bump_major(self) -> PromptVersion:
        """Return a new version with the major component incremented and minor/patch reset.

        Use for changes that break output schema compatibility (see
        module-level versioning rules).
        """
        return PromptVersion(self.major + 1, 0, 0)

    # ------------------------------------------------------------------
    # Compatibility query
    # ------------------------------------------------------------------

    def is_compatible_with(self, other: PromptVersion) -> bool:
        """Return ``True`` when this version is backwards-compatible with *other*.

        Two versions are considered backwards-compatible when their major
        components are equal.  Minor and patch increments are always
        backwards-compatible; a major increment is not.

        Parameters
        ----------
        other:
            The reference version to compare against (typically the version
            a downstream consumer was built against).
        """
        return self.major == other.major
