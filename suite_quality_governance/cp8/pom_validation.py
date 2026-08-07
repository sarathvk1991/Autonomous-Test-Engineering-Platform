"""CP8, `pom.xml` structural validity (ADR-0047 D7's own second bullet):
present, well-formed XML, and every `<dependency>`/`<plugin>` declaration
it actually contains is internally consistent.

**Never against a hardcoded expected-dependency list (D7's own explicit
rejection).** `pom.xml` is this platform's own single source of truth for
what the suite depends on; this module validates that whatever IS
declared is well-formed, never that some particular set of artifact ids
is present. An empty `<dependencies>` section is not, by itself, a defect
this module flags -- "declares zero dependencies" and "declares the WRONG
dependencies" are both questions this module deliberately does not
answer, per D7's own reasoning (a hardcoded parallel list "would drift
the moment a real dependency changes and would duplicate, not validate,
the POM's own authority").

**No Maven property resolution.** A `<version>${some.property}</version>`
is treated as a normal, non-empty declared version -- this module never
resolves `${...}` placeholders against `<properties>`; doing so would be
real, new Maven-semantics logic, not a structural XML check, and is not
needed to catch D7's own named defect class (a MISSING/empty field, not
an unresolved one).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from shared.enums.base import ValidationVerdict
from suite_quality_governance.cp8.models import CRITERION_POM_WELL_FORMED, Cp8CriterionResult

POM_RELATIVE_PATH = Path("pom.xml")


def _declaration_messages(root: ET.Element, tag: str, label: str) -> list[str]:
    """One message per structurally-defective `<dependency>`/`<plugin>`
    element: a missing/empty `<artifactId>`, a missing/empty `<groupId>`,
    or a `<version>` present but empty (D7's own "malformed version
    coordinate" example). A `<version>` element ABSENT entirely is never
    flagged -- normal, valid Maven practice for a BOM-managed dependency
    (this platform's own real `pom.xml` relies on exactly this for five
    of its six dependencies)."""
    messages: list[str] = []
    for element in root.findall(f".//{{*}}{tag}"):
        group_id = element.findtext("{*}groupId")
        artifact_id = element.findtext("{*}artifactId")
        version = element.findtext("{*}version")
        identity = f"{group_id or '?'}:{artifact_id or '?'}"
        if not artifact_id or not artifact_id.strip():
            messages.append(f"a <{tag}> is missing a non-empty <artifactId> ({label}, {identity})")
        if not group_id or not group_id.strip():
            messages.append(f"a <{tag}> is missing a non-empty <groupId> ({label}, {identity})")
        if version is not None and not version.strip():
            messages.append(f"a <{tag}> declares an empty <version> ({label}, {identity})")
    return messages


def check_pom_well_formed(baseline_root: Path) -> Cp8CriterionResult:
    """`pom.xml` present, well-formed XML, and every declared dependency/
    plugin structurally consistent (module docstring)."""
    pom_path = baseline_root / POM_RELATIVE_PATH
    if not pom_path.is_file():
        return Cp8CriterionResult(
            criterion=CRITERION_POM_WELL_FORMED,
            verdict=ValidationVerdict.FAIL,
            messages=(f"no pom.xml found at {pom_path}",),
        )
    try:
        root = ET.fromstring(pom_path.read_text(encoding="utf-8"))  # noqa: S314 - tracked baseline's own committed file, not untrusted input
    except ET.ParseError as exc:
        return Cp8CriterionResult(
            criterion=CRITERION_POM_WELL_FORMED,
            verdict=ValidationVerdict.FAIL,
            messages=(f"{pom_path} is not well-formed XML: {exc}",),
        )
    messages = (
        *_declaration_messages(root, "dependency", "dependency"),
        *_declaration_messages(root, "plugin", "plugin"),
    )
    if messages:
        return Cp8CriterionResult(
            criterion=CRITERION_POM_WELL_FORMED,
            verdict=ValidationVerdict.FAIL,
            messages=tuple(messages),
        )
    return Cp8CriterionResult(criterion=CRITERION_POM_WELL_FORMED, verdict=ValidationVerdict.PASS)


__all__ = ["POM_RELATIVE_PATH", "check_pom_well_formed"]
