---
title: ACT-001 Governance Designation Record
document: GDR-ACT-001
version: 1.0
status: Adopted — Effective Date Pending Signature
owner: Architecture Review Board
approval-authority: Architecture Review Board
related-action: ACT-001
related-decision: ARB-DEC-001
effective-date:
---

# ACT-001 Governance Designation Record

**Note on location.** This record is filed at `docs/architecture/ACT-001-Governance-Designation-Record.md`, alongside the other ACT-001 artifacts, rather than at the `docs/governance/actions/ACT-001/` path suggested in the preparation instructions. The repository governance directory reorganization that path assumes is a separate, unapproved proposal and has not been executed. This record uses the repository's current, actual file organization.

---

## Document Information

| Field | Value |
|---|---|
| Title | ACT-001 Governance Designation Record |
| Document ID | GDR-ACT-001 |
| Version | 1.0 |
| Status | Adopted — Effective Date Pending Signature |
| Owner | Architecture Review Board |
| Approval Authority | Architecture Review Board |
| Related Action | ACT-001 — Resolve shared capability identifier collision |
| Related Decision | ACT-001 Architecture Review Board Decision Record (ARB-DEC-001) |
| Effective Date | |

---

## 1. Purpose

This record exists to implement the designation the Architecture Review Board already approved in ARB-DEC-001. It is the governance action contemplated by the second disjunct of the ACT-001 Exit Criteria: a record that "formally designates one definition as authoritative."

This document does not create governance. It does not exercise discretion over which resolution applies, and it does not revisit whether Decision Option 3 was the correct choice. That decision has already been made by the Architecture Review Board and is recorded in ARB-DEC-001. This record implements it.

---

## 2. Authority

This record derives its authority from the following governance artifacts, each cited for the specific role it plays:

- **Architecture Governance Guide** — establishes that a governance conflict discovered during execution is resolved through the exception workflow (Execution Report → Decision Review Package → Board Decision → revised Execution Record), and that the Board's decision, once recorded, authorizes a defined implementation step. This record is that implementation step.
- **Repository Architecture Assessment Report (RAAR-001)** — the originating source of the finding this action resolves: a shared capability identifier, `CAP-001`, naming two unrelated capabilities without cross-reference (RAAR-001 §4, Repository Identity; §11, Architectural Debt).
- **Architecture Action Register** — the record of the Board's approval of ACT-001 and its Exit Criteria, which this designation satisfies under the "formally designates one definition as authoritative" disjunct.
- **ACT-001 Architecture Action Execution Record, Version 2.0** — the confirmed implementation plan under which this record is Step 4's required output.
- **ACT-001 Architecture Review Board Decision Record (ARB-DEC-001)** — the governing authority for this designation's content. ARB-DEC-001 §3 records the Board's decision in full; this record implements that decision without reinterpretation.

The relationship among these artifacts is sequential: RAAR-001 identified the ambiguity; the Architecture Action Register authorized action on it; the Execution Record planned implementation; ARB-DEC-001 resolved the conflict discovered during that implementation; this record carries out ARB-DEC-001's resulting instruction.

---

## 3. Background

RAAR-001 identified that the identifier `CAP-001` is independently assigned to two unrelated capabilities: "Connector Framework & Registry" (Track A), defined in the platform capability matrix, and "Requirements Intelligence" (Track B), defined in the Engineering Intelligence Operating System target-architecture lineage. Neither definition referenced the other. The Architecture Review Board approved ACT-001 to resolve this collision.

The ACT-001 Architecture Action Execution Record, Version 1.0, proposed resolving the collision by reassigning the Track A identifier. Execution of that plan was paused when `docs/governance/platform-capability-matrix.md` was found to state, in two places, that assigned capability identifiers are immutable and may never be renumbered — a rule the proposed reassignment would have violated.

This conflict was documented and referred to the Architecture Review Board through the ACT-001 Decision Review Package, which presented three resolution options. The Board reviewed the Package and adopted Decision Option 3 in ARB-DEC-001: formally designate the Track B definition as authoritative for citation, without reassigning either capability's identifier and without granting an exception to the identifier-permanence rule. The ACT-001 Architecture Action Execution Record, Version 2.0, revised the implementation plan accordingly, with Step 4 directing that this designation be drafted and adopted.

---

## 4. Formal Designation

The Architecture Review Board, having adopted Decision Option 3 in ARB-DEC-001, formally designates as follows:

1. **Requirements Intelligence** (Track B), as defined in `docs/product/CAP-001-requirements-intelligence.md`, remains `CAP-001`.
2. This designation is authoritative for repository citation wherever ambiguity between the two existing `CAP-001` definitions would otherwise exist.
3. No identifier is renumbered as a result of this designation.
4. No identifier is reassigned as a result of this designation.
5. Identifier immutability, as stated in `docs/governance/platform-capability-matrix.md` §3.1 and §8, remains unchanged and unexcepted.
6. **Connector Framework & Registry** (Track A), as defined in `docs/governance/platform-capability-matrix.md` §5.1, remains historically valid under its existing identifier and record.
7. This designation resolves the repository ambiguity identified in RAAR-001 §4 through governance action, not through identifier reassignment.

---

## 5. Scope

**This designation applies to:**

- Repository documentation citing `CAP-001` for the purpose of identifying which capability — Track A or Track B — is meant, wherever that citation would otherwise be ambiguous.
- Architecture governance records that reference `CAP-001` in a context requiring disambiguation between the two tracks.
- Repository cross-references from any document to either `CAP-001` definition.
- Capability citation practice going forward, for any reader or document needing to resolve `CAP-001` unambiguously.

**This designation does not:**

- Redefine the functionality, scope, or content of either Track A or Track B's capability.
- Renumber, reassign, or otherwise change either capability's identifier.
- Alter any historical governance record, including the ACT-001 Architecture Action Execution Record Version 1.0, the ACT-001 Decision Review Package, or ARB-DEC-001, all of which remain as adopted.
- Authorize repository restructuring of any kind. The repository governance reorganization described in a separate proposal remains unapproved and unrelated to this designation.

---

## 6. Repository Impact

| Item | Change Required |
|---|---|
| Repository renumbering | None. No capability is renumbered. |
| Identifier reassignment | None. Neither `CAP-001` instance is reassigned. |
| Repository restructuring | None. This designation does not authorize or perform any directory reorganization. |
| Cross references | None required. Both existing `CAP-001` citations remain valid within their respective tracks; this designation supplies the disambiguation rule rather than requiring citation edits. |
| Governance history | Unaffected. The ACT-001 Execution Record Version 1.0, the Decision Review Package, and ARB-DEC-001 remain unaltered and retained in full. |
| Platform Capability Matrix (`docs/governance/platform-capability-matrix.md`) | None. Its Track A `CAP-001` entry is unchanged in identifier and content. |
| Requirements Intelligence document (`docs/product/CAP-001-requirements-intelligence.md`) | None. Its Track B `CAP-001` designation and content are unchanged. |

---

## 7. Implementation Status

**Completed by this record:**

- The formal designation required by the ACT-001 Exit Criteria's second disjunct is now recorded (Section 4 above).
- Whether an optional supplementary note is added to `HB-001` §20.4, as contemplated in the Execution Record Version 2.0, is a discretionary matter separate from this designation and does not affect its adoption or effect.

**Remaining before ACT-001 may be closed:**

- **Verification Evidence.** The repository-wide search for `CAP-001` specified in the Execution Record Version 2.0, Section 7, Step 6, confirming every reference is attributable to a specific track, must be performed and recorded.
- **Action Register update.** The Architecture Action Register must be updated to reflect that ACT-001's Exit Criteria are satisfied under the "formally designates one definition as authoritative" disjunct, citing this record as the governance action.
- **Action closure.** The Architecture Review Board must record ACT-001's closure in the Architecture Action Register, with this record and the search evidence populated as Verification Evidence, consistent with the Register's own Governance Rules.

---

## 8. References

- Repository Architecture Assessment Report (RAAR-001)
- Architecture Action Register
- ACT-001 Architecture Action Execution Record, Version 1.0
- ACT-001 Architecture Action Execution Record, Version 2.0
- ACT-001 Decision Review Package
- ACT-001 Architecture Review Board Decision Record (ARB-DEC-001)
- Architecture Governance Guide
- `docs/governance/platform-capability-matrix.md`
- `docs/product/CAP-001-requirements-intelligence.md`

---

## 9. Architecture Review Board Confirmation

**Architecture Review Board Chair:** _________________________

**Architecture Review Board Secretary:** _________________________

**Effective Date:** _________________________

---

## Appendix A — Affected Repository Artifacts

| Artifact | Affected | Reason | Implementation Required |
|---|---|---|---|
| `docs/governance/platform-capability-matrix.md` | No | Track A identifier and content unchanged | None |
| `docs/governance/architecture-coverage-dashboard.md` | No | Mirrors the unchanged Capability Matrix entry | None |
| `docs/product/CAP-001-requirements-intelligence.md` | No | Track B identifier and content unchanged | None |
| Thirteen further Track B lineage documents (per ACT-001 Execution Record, Section 3) | No | Cite the unchanged Track B definition | None |
| `docs/handbook/HB-001-platform-engineering-handbook.md` §20.4 | Optional | May receive a discretionary supplementary note disclosing its grandfather clause's scope | Optional; not required for ACT-001 closure |
| `docs/releases/v1.1.0-requirement-intelligence.md` | No | Cites the unchanged Track A identifier | None |
| Architecture Action Register | Yes | Must record ACT-001's status against this designation | Register update, pending as a follow-up action |
| This record (`ACT-001 Governance Designation Record`) | Yes | Newly created governance artifact implementing ARB-DEC-001 | Complete upon Board Confirmation (Section 9) |

---

## Appendix B — Traceability

```
Repository Assessment
    ↓
Action Register
    ↓
Execution Record
    ↓
Execution Report
    ↓
Decision Review
    ↓
Board Decision
    ↓
Governance Designation Record
    ↓
Verification Evidence
    ↓
Action Register Updated
    ↓
Action Closed
```
