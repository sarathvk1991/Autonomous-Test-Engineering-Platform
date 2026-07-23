# Architecture Action Register

## 1. Purpose

This register records the architectural, governance, documentation, and validation actions approved by the Architecture Review Board following the Repository Architecture Assessment Report (RAAR-001). It provides traceability from each assessment finding through planning, implementation, and verification.

Unlike the assessment report, which is a point-in-time document, this register is continuously maintained. It is updated as actions progress through their lifecycle and as subsequent assessment reports approve further actions. The assessment report remains the authoritative source of findings; this register tracks execution against those findings only.

This register is distinct from a project plan, a sprint backlog, or an issue tracker. It does not schedule engineering work, estimate effort, or assign implementation tasks. It governs architectural actions at the level the Architecture Review Board approved them, and exists to answer one question: which Board-approved architectural actions exist, and what is their current status. Engineering task management, however it is conducted, is a separate concern that this register does not track.

---

## Related Documents

This register should be read alongside the following documents:

- The Repository Architecture Assessment Report, the governing source from which every action in this register is derived.
- The Repository Audit, which supplies the underlying repository evidence on which the assessment report's findings are based.
- The Architecture Review Records, comprising the individual architecture decision reviews, the program review, and the strategy review considered by the Architecture Review Board in reaching the assessment report's conclusions.

This register derives its actions exclusively from approved assessment findings. It does not restate the reasoning, evidence, or ratings contained in those documents, and it should not be read as a substitute for them.

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
| ACT-001 | Resolve shared capability identifier collision | RAAR-001 §4 Repository Identity; §10; §11; §13 Immediate; §14 Step 1 | Governance | High | Identified | Architecture Review Board | TBD | TBD | A governance action assigns each identifier definition a distinct identifier, or formally designates one definition as authoritative, and no repository document retains an unresolved conflicting definition. |
| ACT-002 | Review transformation artifact | RAAR-001 §4 Transformation; §11; §13 Immediate; §14 Step 2 | Governance | Medium | Identified | Architecture Review Board | TBD | TBD | The transformation artifact has completed every stage of the existing documentation review workflow and carries an Approved status. |
| ACT-003 | Correct repository status summary | RAAR-001 §4 Documentation; §6; §10; §11; §13 Immediate; §14 Step 3 | Documentation | Low | Identified | Architecture Review Board | TBD | TBD | The top-level status summary reflects the phase status recorded in the release history and capability matrix, confirmed by direct comparison. |
| ACT-004 | Verify flagship Hosted Application claim | RAAR-001 §4 Capability Validation; §6; §11; §13 Near-Term; §14 Step 4 | Validation | High | Identified | Architecture Review Board | TBD | TBD | The flagship claim has been checked against the existing capability maturity model and is either confirmed at the maturity level asserted or corrected to the verified maturity level. |
| ACT-005 | Resolve standards citation inconsistency | RAAR-001 §4 Governance; §11; §13 Near-Term; §14 Step 5 | Governance | High | Identified | Architecture Review Board | TBD | TBD | The citation rule and the affected standards documents are made consistent through a recorded harmonization action, with no remaining self-acknowledged conflict. |
| ACT-006 | Reconcile authoritative standard version mismatch | RAAR-001 §11; §13 Long-Term; §14 Step 6 | Documentation | High | Identified | Architecture Review Board | TBD | TBD | The version recorded in the standard's file on disk matches the version declared authoritative by its governance record. |
| ACT-007 | Implement documented REST endpoint | RAAR-001 §4 Implementation; §6; §10; §11; §14 Step 7 | Technical Architecture | Medium | Identified | Architecture Review Board | TBD | TBD | The endpoint returns a functional response rather than a not-implemented error, and the behavior is covered by a passing test. |
| ACT-008 | Evaluate broader implementation-target architecture reconciliation | RAAR-001 §4 Traceability; §4 Repository Evolution; §10; §11; §13 Long-Term; §14 Step 8 | Architecture | High | Identified | Architecture Review Board | TBD | TBD | A governance decision is recorded that either charters or explicitly defers a broader reconciliation activity, using existing governance mechanisms only, contingent on ACT-001 through ACT-007 reaching Closed status. |

---

## Governance Notes

The following principles govern how this register is interpreted and applied. They exist to keep the register's governance function distinct from delivery activity.

- Each action represents a Board-approved architectural decision, not an engineering task.
- Individual implementation tasks needed to carry out an action may exist elsewhere, in whatever engineering tracking system the repository's contributors use.
- One architectural action may map to multiple engineering work items, and the register does not enumerate them.
- Completion of the engineering work associated with an action does not, by itself, close the action.
- An action closes only when its stated exit criteria have been verified and recorded in this register.

---

## 5. Metrics

| Metric | Value |
|---|---|
| Total Actions | 8 |
| Open | 8 |
| In Progress | 0 |
| Verified | 0 |
| Closed | 0 |
| Superseded | 0 |
| High Priority | 5 |
| Medium Priority | 2 |
| Low Priority | 1 |

---

## 6. Governance Rules

- Only actions approved through a formal repository assessment may be added to this register.
- Every action must remain traceable to its originating assessment, as recorded in the Source column.
- An action may not be marked Closed without recorded Verification Evidence.
- Verification evidence must remain available after an action reaches Closed status.
- Exit criteria may only be changed through architectural review.
- Actions are never deleted from this register. They may only be closed or superseded by a later action.
- A superseded action must reference the action that replaces it.
- Closed actions remain part of repository history and are retained in this register rather than removed.
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

Assessment findings become governance actions when the Architecture Review Board approves them into this register. Governance actions, in turn, generate implementation work, which is tracked outside this register. That implementation work produces verification evidence, which is recorded against the originating action's exit criteria. That evidence then informs the next Repository Architecture Assessment Report, which may confirm an action's closure, identify further gaps, or approve new actions.

This forms a continuous architecture governance cycle, in which each assessment builds on the recorded outcome of the actions approved by the assessment before it, preserving complete architectural traceability across assessment cycles.

---

## Register Maintenance

- Status changes to an action require supporting evidence appropriate to the new status.
- New actions originate only from an approved repository assessment; this register does not accept actions from any other source.
- Closed actions remain unchanged except through formal supersession by a new action.
- This register is reviewed whenever a new Repository Architecture Assessment Report is issued, to confirm existing action status and incorporate any newly approved actions.

---

## 8. Change History

| Version | Date | Summary |
|---|---|---|
| 1.0 | 2026-07-23 | Initial publication. Register populated with the eight actions approved by RAAR-001. |
| 1.1 | 2026-07-23 | Editorial refinement. Added Related Documents, Governance Notes, and Register Maintenance sections. Expanded Governance Rules and Traceability. Added Verified and Superseded metrics. Standardized action titles, categories, and exit-criteria wording for consistency. |
