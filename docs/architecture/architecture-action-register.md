# Architecture Action Register

## 1. Purpose

This register records the architectural, governance, documentation, and validation actions approved by the Architecture Review Board following the Repository Architecture Assessment Report (RAAR-001). It provides traceability from each assessment finding through planning, implementation, and verification.

Unlike the assessment report, which is a point-in-time document, this register is continuously maintained. It is updated as actions progress through their lifecycle and as subsequent assessment reports approve further actions. The assessment report remains the authoritative source of findings; this register tracks execution against those findings only.

---

## 2. Scope

**In scope.**

- Architecture actions arising from formal repository assessments.
- Governance actions arising from formal repository assessments.
- Documentation actions arising from formal repository assessments.
- Validation actions arising from formal repository assessments.
- Technical architecture actions arising from formal repository assessments.

**Out of scope.**

- Product backlog items.
- Sprint-level work.
- Bug reports.
- Feature requests.
- Enhancement requests not originating from a formal assessment.

---

## 3. Lifecycle

Each action progresses through the following statuses, in order:

**Identified.** The action has been named by an approved assessment but has not yet been accepted for execution.

**Approved.** The Architecture Review Board has accepted the action for execution.

**Planned.** The action has an assigned owner and target release.

**In Progress.** Work on the action has begun.

**Implemented.** The change described by the action has been made.

**Verified.** Verification evidence has been recorded confirming the action meets its exit criteria.

**Closed.** The action is complete and requires no further tracking.

---

## 4. Action Register

| Action ID | Title | Source (RAAR Section) | Category | Priority | Status | Owner | Target Release | Verification Evidence | Exit Criteria |
|---|---|---|---|---|---|---|---|---|---|
| ACT-001 | Resolve shared capability identifier collision | RAAR-001 §4 Repository Identity; §10; §11; §13 Immediate; §14 Step 1 | Governance | High | Identified | Architecture Review Board | TBD | TBD | A governance action assigns each of the two identifier definitions a distinct identifier, or formally designates one as authoritative, and no repository document retains an unresolved conflicting definition. |
| ACT-002 | Review transformation artifact | RAAR-001 §4 Transformation; §11; §13 Immediate; §14 Step 2 | Governance | Medium | Identified | Architecture Review Board | TBD | TBD | The transformation artifact has completed the stages defined in the existing documentation review workflow and carries an Approved status. |
| ACT-003 | Correct repository status summary | RAAR-001 §4 Documentation; §6; §10; §11; §13 Immediate; §14 Step 3 | Documentation | Low | Identified | Architecture Review Board | TBD | TBD | The top-level status summary reflects the same phase status recorded in the release history and capability matrix, confirmed by direct comparison. |
| ACT-004 | Verify flagship Hosted Application claim | RAAR-001 §4 Capability Validation; §6; §11; §13 Near-Term; §14 Step 4 | Validation | High | Identified | Architecture Review Board | TBD | TBD | The claim has been checked against the existing capability maturity model, and the claim is either confirmed at the maturity level asserted or corrected to the verified maturity level. |
| ACT-005 | Resolve standards citation inconsistency | RAAR-001 §4 Governance; §11; §13 Near-Term; §14 Step 5 | Governance | High | Identified | Architecture Review Board | TBD | TBD | The citation rule and the affected standards documents are made consistent with one another through a recorded harmonization action, with no remaining self-acknowledged conflict. |
| ACT-006 | Reconcile authoritative standard version mismatch | RAAR-001 §11; §13 Long-Term; §14 Step 6 | Documentation | High | Identified | Architecture Review Board | TBD | TBD | The version recorded in the standard's file on disk matches the version declared authoritative by its governance record. |
| ACT-007 | Implement documented REST endpoint | RAAR-001 §4 Implementation; §6; §10; §11; §14 Step 7 | Technical Architecture | Medium | Identified | Architecture Review Board | TBD | TBD | The endpoint returns a functional response rather than a not-implemented error, and the behavior is covered by a passing test. |
| ACT-008 | Evaluate broader implementation-target architecture reconciliation | RAAR-001 §4 Traceability; §4 Repository Evolution; §10; §11; §13 Long-Term; §14 Step 8 | Architecture | High | Identified | Architecture Review Board | TBD | TBD | A governance decision is recorded either chartering or explicitly deferring a broader reconciliation activity, using existing governance mechanisms only, and is contingent on ACT-001 through ACT-007 reaching Closed status. |

---

## 5. Metrics

| Metric | Value |
|---|---|
| Total Actions | 8 |
| Open | 8 |
| In Progress | 0 |
| Closed | 0 |
| High Priority | 5 |
| Medium Priority | 2 |
| Low Priority | 1 |

---

## 6. Governance Rules

- Only actions approved through a formal repository assessment may be added to this register.
- Every action must reference its originating assessment section in the Source column.
- An action may not be marked Closed without recorded Verification Evidence.
- Actions are never deleted from this register. They may only be closed or superseded by a later action, with the supersession recorded against the original entry.
- Changes to this register, including status transitions and the addition of new actions, are governed through the existing repository review process.
- Reprioritization or reinterpretation of an action's intent requires reference to a new or amended assessment; this register does not itself alter assessment conclusions.

---

## 7. Traceability

This register sits within the following governance chain:

```
Repository
    ↓
Architecture Review
    ↓
Repository Architecture Assessment Report
    ↓
Architecture Action Register
    ↓
Implementation
    ↓
Verification Evidence
    ↓
Next Repository Architecture Assessment Report
```

Each action in this register traces back to a specific section of the Repository Architecture Assessment Report. Each action's eventual verification evidence traces forward into the next assessment cycle, preserving complete architectural traceability across assessment cycles.

---

## 8. Change History

| Version | Date | Summary |
|---|---|---|
| 1.0 | 2026-07-23 | Initial publication. Register populated with the eight actions approved by RAAR-001. |
