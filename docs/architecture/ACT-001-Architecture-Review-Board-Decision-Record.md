# Architecture Review Board Decision Record — ACT-001

This is the official governance record of the Architecture Review Board's decision on the ACT-001 Decision Review Package. It is not an architecture assessment, an implementation plan, or an execution artifact. It records the Board's decision and authorizes the next stage of execution only.

---

## 1. Decision Summary

| Field | Value |
|---|---|
| Decision ID | ARB-DEC-001 |
| Related Action | ACT-001 — Resolve shared capability identifier collision |
| Decision Date | |
| Decision Authority | Architecture Review Board |
| Status | Approved |

---

## 2. Background

The Repository Architecture Assessment Report (RAAR-001) identified that the identifier `CAP-001` is independently assigned to two unrelated capabilities: "Connector Framework & Registry," a real, implemented capability defined in the platform capability matrix, and "Requirements Intelligence," a capability document within the Engineering Intelligence Operating System (EIOS) target-architecture lineage. RAAR-001 recorded this collision as a Governance Debt item of High priority and as the first sequenced step of its recommended roadmap.

The Architecture Review Board approved ACT-001, "Resolve shared capability identifier collision," and entered it into the Architecture Action Register with Exit Criteria admitting either of two resolution forms: assigning each identifier definition a distinct identifier, or formally designating one definition as authoritative, provided no repository document retains an unresolved conflicting definition.

The ACT-001 Architecture Action Execution Record proposed a resolution retaining the Track B "Requirements Intelligence" definition unchanged and reassigning the Track A "Connector Framework & Registry" identifier to the next available identifier within its own domain block. Execution was paused before any repository file was modified. The Implementation Engineer identified that `docs/governance/platform-capability-matrix.md` states, in two separate sections, that assigned capability identifiers are immutable and may never be renumbered — a rule that directly conflicts with the approved resolution's central step.

This governance conflict was not identified during preparation of the Execution Record. It required a decision by the Architecture Review Board before implementation of ACT-001 could resume. The ACT-001 Decision Review Package was prepared to support that deliberation, presenting three decision options and a recommendation, without itself constituting a governance decision.

---

## 3. Decision

The Architecture Review Board adopts **Decision Option 3** as presented in the ACT-001 Decision Review Package.

The Board directs that:

- ACT-001 shall be resolved by formally designating one `CAP-001` definition — the Track B "Requirements Intelligence" definition — as authoritative for repository citation purposes.
- Neither capability's identifier is renumbered or reassigned. Both instances of the identifier string `CAP-001` remain present in the repository, scoped to their respective tracks.
- The identifier-permanence rule recorded in `docs/governance/platform-capability-matrix.md` §3.1 and §8 remains unchanged and in force, without qualification.
- No exception to the identifier-permanence rule is granted. Option 1, which would have required such an exception, is not adopted.
- Repository implementation of this decision shall proceed through formal designation of authoritative status, not through identifier reassignment of either capability.

---

## 4. Decision Rationale

The Board's selection of Option 3 rests on evidence contained in the ACT-001 Decision Review Package:

- The ACT-001 Exit Criteria, as recorded in the Architecture Action Register, explicitly admits resolution by formally designating one definition authoritative, without requiring that any identifier be reassigned. Option 3 satisfies this disjunct directly.
- Option 3 is the only option that avoids both governance conflicts identified during deliberation: it does not require an exception to the identifier-permanence rule in `platform-capability-matrix.md` (the conflict that would attach to Option 1), and it does not require reviewing or amending the thirteen-document footprint associated with Track B, including the closed `STD-002` governance-lifecycle review records (the burden that would attach to Option 2).
- Option 3 aligns with a mitigation already identified in the ACT-001 Execution Record's own Impact Assessment: a supplementary note in `HB-001` §20.4 disclosing that its grandfather clause does not address the Track A definition, without amending either capability's defining document.
- Per the Decision Review Package's Comparative Analysis, Option 3 carries the lowest repository and documentation impact of the three options and preserves both existing identifiers, consistent with the identifier-permanence rule's evident intent.

---

## 5. Conditions

The following conditions shall be satisfied before implementation of ACT-001 resumes:

- The ACT-001 Architecture Action Execution Record shall be revised to reflect the approved implementation approach (Option 3), replacing the reassignment-based resolution originally proposed in its Section 6 and the dependent steps, evidence requirements, and validation checklist that follow from it.
- The specific mechanism constituting "formal designation" of the authoritative `CAP-001` definition shall be defined as part of the revised execution package. The Decision Review Package identifies this mechanism as undetermined by any of the four input documents; this Decision Record does not itself define it.
- Repository traceability shall be preserved: no repository document shall be modified other than as necessary to record this designation, and no historical governance record — including the original ACT-001 Execution Record and the ACT-001 Decision Review Package — shall be altered except as expressly authorized in Section 7 below.

---

## 6. Implementation Authorization

The Board authorizes preparation of the **ACT-001 Execution Record v2**, revising the implementation approach to Option 3 as decided in Section 3 of this record.

Implementation of ACT-001 may resume only after the revised execution package (ACT-001 Execution Record v2) has been submitted to, and approved by, the Architecture Review Board.

---

## 7. Governance Effects

| Document | Effect |
|---|---|
| Repository Architecture Assessment Report (RAAR-001) | Remains unchanged. The underlying finding of a shared capability identifier is unaffected by this decision. |
| Architecture Action Register | Requires revision. ACT-001's recorded status shall be updated to reflect this decision, including which disjunct of the Exit Criteria is being satisfied (formal designation, not distinct reassignment). |
| ACT-001 Architecture Action Execution Record | Requires revision. Superseded in relevant part by the ACT-001 Execution Record v2 authorized in Section 6. The original version is retained as part of the governance history and is not deleted or overwritten. |
| ACT-001 Decision Review Package | Remains unchanged. It stands as the evidentiary and deliberative record supporting this decision. The blank decision fields in its Section 9 are superseded by this Decision Record, which is the authoritative record of the Board's decision. |

---

## 8. Follow-up Actions

- Revise the ACT-001 Architecture Action Execution Record (produce ACT-001 Execution Record v2) per Section 6.
- Resume implementation of ACT-001 under the revised execution package.
- Perform verification against the ACT-001 Exit Criteria, per the Verification Procedure already established in the Execution Record.
- Update the Architecture Action Register to reflect ACT-001's status following verification.
- Close ACT-001 upon recorded Verification Evidence, consistent with the Governance Rules of the Architecture Action Register.

---

## 9. Traceability

```
Repository Assessment
    ↓
Action Register
    ↓
Execution Record
    ↓
Execution Report
    ↓
Decision Review Package
    ↓
Decision Record
    ↓
Execution Record v2
    ↓
Implementation
    ↓
Verification
    ↓
Action Closed
```

---

## 10. Approval

**Architecture Review Board Chair:** _________________________

**Architecture Review Board Secretary:** _________________________

**Decision Date:** _________________________
