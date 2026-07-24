---
title: Architecture Governance Guide
document: AGG-001
status: Final
owner: Architecture Review Board
scope: Repository-wide governance framework
category: Governance

---

# Architecture Governance Guide

This guide is the authoritative entry point into the repository's architecture governance framework. It documents the governance model that already exists in this repository, as evidenced by the Repository Architecture Assessment Report, the Architecture Action Register, the ACT-001 Architecture Action Execution Record, the ACT-001 Architecture Action Execution Report, the ACT-001 Decision Review Package, and the ACT-001 Architecture Review Board Decision Record.

This guide explains the governance framework. It does not create governance, redefine governance, or introduce governance mechanisms beyond those already evidenced in the documents listed above.

---

## 1. Introduction

**Purpose of this guide.** This guide explains how architecture governance operates within this repository: why it exists, how it is structured, who performs it, how its artifacts relate to one another, and how an architectural action moves from identification to closure. It consolidates the governance model demonstrated across the repository's governance artifacts into a single, coherent reference.

**Audience.** This guide is written for Enterprise Architects, Solution Architects, Architecture Review Board members, Repository Maintainers, Contributors, and Reviewers. It assumes no prior familiarity with any individual governance artifact.

**Scope.** This guide covers the governance framework that applies to architectural, governance, documentation, and validation actions arising from formal repository assessments. It does not cover product backlog management, sprint-level engineering work, bug tracking, or feature requests, all of which are explicitly out of scope for the governance artifacts this guide describes.

**How to use this guide.** A reader new to the repository should read Sections 1 through 12 in order to acquire a complete model of the governance framework before consulting any individual governance artifact. A reader already familiar with the framework may use Sections 13 and the Appendices as quick-reference material. A reader facing a specific governance question may consult Section 14, Frequently Asked Questions, directly.

**Relationship to the repository.** This guide sits above the individual governance artifacts it describes. It does not replace them, does not restate their findings or decisions in full, and is not itself a governance artifact of the kind tracked in the Architecture Action Register. It is a reference document explaining how those artifacts function together.

---

## Governance Artifact Inventory

The repository uses a small set of governance artifacts, each serving a distinct purpose within the governance lifecycle. The table below provides an at-a-glance overview of every artifact before the detailed explanations that follow later in this guide.

| Artifact | Abbreviation | Purpose | Owner | Workflow | Lifecycle |
|---|---|---|---|---|---|
| Repository Architecture Assessment Report | RAAR | Establishes the repository's architecture baseline and findings | Architecture Review Board | Normal | Permanent |
| Architecture Action Register | AAR | Authorizes and tracks architectural actions through their lifecycle | Architecture Review Board | Normal | Permanent |
| Architecture Action Execution Record | AAER | Plans the implementation of a single approved action | Implementation Engineer | Normal | Temporary |
| Architecture Action Execution Report | AAExR | Documents a finding or conflict discovered during execution | Implementation Engineer | Exception | Permanent |
| Decision Review Package | DRP | Supports Board deliberation on a governance conflict | Architecture Review Board Secretary | Exception | Permanent |
| Architecture Review Board Decision Record | ARBDR | Records the Board's decision and authorizes resumption of implementation | Architecture Review Board | Exception | Permanent |
| Verification Evidence | VE | Confirms that an action's exit criteria have been satisfied | Implementation Engineer | Both | Permanent |

Normal workflow artifacts are used for every architectural action, from assessment through implementation. Exception workflow artifacts are created only when execution uncovers a governance conflict requiring Architecture Review Board deliberation; they do not arise in an action's ordinary progression. Verification Evidence completes the governance lifecycle by demonstrating that an action's exit criteria have been satisfied, whether the action followed the normal workflow alone or passed through the exception workflow first.

See Section 5, Governance Artifacts, for the complete description of each artifact.

---

## 2. Purpose of Repository Governance

**Why architecture governance exists.** The repository contains two independently coherent bodies of work — a real, evidenced implementation and an extensive, unratified target architecture and governance methodology — that have not yet been reconciled. Governance exists to ensure that architectural findings about this state are captured formally, that action on them is deliberate and Board-authorized rather than ad hoc, and that the repository's evolution proceeds through evidence-based, traceable decisions rather than through undocumented change.

**Why repository architecture must remain consistent.** The Repository Architecture Assessment Report identifies unresolved inconsistencies — including a shared capability identifier naming two unrelated capabilities, and a citation-rule violation across five standards documents — as compounding risks that grow more costly to resolve the longer they remain open. Governance exists to close such inconsistencies through recorded, authoritative action rather than allowing them to propagate into further documents.

**Why governance records exist.** Governance records exist so that a reader can establish, from the repository's own artifacts, what was found, what was approved, what was attempted, what was decided, and what was verified — without relying on undocumented knowledge held by any individual contributor.

**Why architectural decisions require traceability.** The Architecture Action Register exists specifically to provide traceability from each assessment finding through planning, implementation, and verification. Without this chain, a governance action cannot be distinguished from an ordinary engineering task, and its authorization, current status, and closure evidence cannot be independently confirmed.

**Why governance separates assessment from implementation.** The Repository Architecture Assessment Report is explicitly a point-in-time document; the Architecture Action Register is explicitly continuous. This separation ensures that assessment findings are not silently reinterpreted during implementation, and that implementation activity is always traceable back to a specific, Board-approved finding rather than to an assessment being revisited informally.

---

## 3. Governance Principles

The following principles are demonstrated by the repository's governance artifacts. Only principles evidenced by those artifacts are included.

**Evidence-based governance.** Every action in the Architecture Action Register derives from a specific, cited section of an approved assessment. The Register itself states that it derives its actions exclusively from approved assessment findings and does not restate their reasoning independently.

**Traceability.** The Architecture Action Register, the ACT-001 Execution Record, and the ACT-001 Decision Review Package each explicitly trace their contents to an originating source: an assessment section, a Register entry, or a prior execution artifact.

**Controlled architectural change.** No repository file is modified as part of an architectural action until the Implementation Plan for that action has been confirmed. When the ACT-001 Execution Record encountered a conflict at Step 3 of its Implementation Plan, execution stopped entirely; no further step was attempted pending resolution.

**Separation of responsibilities.** The Architecture Action Register's Governance Notes state explicitly that each action represents a Board-approved architectural decision, not an engineering task, and that individual implementation tasks are tracked separately from the architectural action itself.

**Board oversight.** Every action in the Register is owned by the Architecture Review Board. The Register's Governance Rules state that only actions approved through a formal repository assessment may be added, and that reprioritization or reinterpretation of an action's intent requires reference to a new or amended assessment.

**Verification before closure.** The Register's Governance Rules state that an action may not be marked Closed without recorded Verification Evidence, and that this evidence must remain available after closure.

**Preservation of governance history.** The Register's Governance Rules state that actions are never deleted, only closed or superseded, and that a superseded action must reference the action that replaces it. The ACT-001 Decision Review Package likewise directs that the original ACT-001 Execution Record be retained as part of governance history following any revision.

**Auditability.** The Repository Architecture Assessment Report identifies a disciplined self-disclosure culture as a major repository strength: governing documents name their own limitations rather than concealing them. The ACT-001 Decision Review Package itself models this by presenting decision options neutrally, including their risks, rather than only their advantages.

**Repeatability.** The Register's own lifecycle — Identified, Approved, Planned, In Progress, Implemented, Verified, Closed — applies uniformly to every action it tracks (ACT-001 through ACT-008), independent of the action's category or priority.

---

## 4. Governance Roles

### Architecture Review Board (ARB)

**Purpose.** The Board is the sole governance authority for architectural actions arising from formal repository assessments.

**Primary Responsibilities.** Approving actions into the Architecture Action Register; confirming or amending proposed resolution directions in Execution Records; deciding governance conflicts referred through a Decision Review Package; authorizing resumption of implementation; confirming verification against exit criteria; recording action closure.

**Decision Authority.** Final authority over action approval, resolution-direction confirmation, exception decisions, and closure. No action may be added to, or closed within, the Register without Board action.

**Inputs.** Repository Architecture Assessment Reports; Execution Records requiring confirmation; Decision Review Packages requiring a Board decision; Verification Evidence.

**Outputs.** Approved Register entries; confirmed or amended resolution directions; Architecture Review Board Decision Records; recorded action closures.

**Interactions with other roles.** Receives Execution Records and Decision Review Packages from the Implementation Engineer (directly or via the Secretary); directs the Secretary to prepare Decision Records; authorizes the Implementation Engineer to resume execution.

### Architecture Review Board Chair

**Purpose.** Presides over Board deliberation and formally signifies Board approval of governance decisions.

**Primary Responsibilities.** Presiding over the Board's consideration of Decision Review Packages and other matters requiring Board decision; signing the Architecture Review Board Decision Record.

**Decision Authority.** Exercises the Board's collective decision authority in a presiding capacity; the Decision Record's approval fields record the Chair's confirmation of the Board's decision alongside the Secretary's.

**Inputs.** Decision Review Packages; draft Decision Records.

**Outputs.** A signed Architecture Review Board Decision Record.

**Interactions with other roles.** Works with the Secretary, who prepares the Decision Record for signature; the Chair's approval, together with the Secretary's, completes the Decision Record.

### Architecture Review Board Secretary

**Purpose.** Prepares the Board's official governance records on the Board's behalf.

**Primary Responsibilities.** Drafting the Architecture Review Board Decision Record following a Board decision; ensuring the Decision Record accurately reflects only the decision the Board has made, without introducing new findings, assessments, or implementation detail.

**Decision Authority.** None over the substance of the decision. The Secretary records the Board's decision; the Secretary does not make it.

**Inputs.** The Decision Review Package; the Board's decision on which option is adopted.

**Outputs.** The Architecture Review Board Decision Record.

**Interactions with other roles.** Receives the Decision Review Package prepared for Board deliberation; produces the Decision Record consumed by the Implementation Engineer (to revise the Execution Record) and by whoever maintains the Architecture Action Register.

### Implementation Engineer

**Purpose.** Plans and executes the repository changes required to satisfy an approved action's exit criteria.

**Primary Responsibilities.** Authoring the Execution Record's Current State Analysis, Impact Assessment, and Implementation Plan; executing the Implementation Plan step by step; halting execution and documenting findings if execution surfaces a governance conflict; producing Verification Evidence once implementation is complete.

**Decision Authority.** Proposes a resolution direction for Board confirmation; has no authority to adopt a resolution direction, grant an exception to an existing governance rule, or close an action without the Board.

**Inputs.** An approved Architecture Action Register entry; the assessment sections it derives from; the repository documents in scope for the action.

**Outputs.** The Architecture Action Execution Record; the Architecture Action Execution Report (when execution surfaces a finding requiring Board attention); Verification Evidence.

**Interactions with other roles.** Submits the Execution Record to the Board for confirmation of resolution direction; submits an Execution Report and, where prepared, a Decision Review Package when execution cannot proceed as planned; receives Board decisions authorizing a revised Execution Record.

### Repository Maintainer

**Purpose.** Applies Board-approved changes to repository documents and maintains the mechanical integrity of governance artifacts, including the Architecture Action Register itself.

**Primary Responsibilities.** Making the specific document edits an approved and confirmed Implementation Plan directs (for example, updating a capability matrix entry and its mirrored dashboard row); maintaining the Register consistent with its own Register Maintenance rules, including recording status changes with supporting evidence and reviewing the Register whenever a new assessment report is issued.

**Decision Authority.** None over what changes are made; authority is limited to applying changes already confirmed by the Board through an Execution Record or Decision Record.

**Inputs.** A confirmed Implementation Plan; a Board decision authorizing a specific implementation direction.

**Outputs.** Updated repository documents consistent with the confirmed plan; an updated Architecture Action Register.

**Interactions with other roles.** Acts on direction from the Implementation Engineer's confirmed plan and the Board's decisions; supplies the updated state that Verification checks against exit criteria.

### Contributor

**Purpose.** Performs the engineering work items that support an architectural action's implementation, tracked outside the Architecture Action Register.

**Primary Responsibilities.** Carrying out implementation tasks mapped from an approved action, using whatever engineering tracking system the repository's contributors use. The Register's Governance Notes state explicitly that one architectural action may map to multiple engineering work items, which the Register does not itself enumerate.

**Decision Authority.** None over architectural action approval, resolution direction, or closure. Completion of a Contributor's engineering work does not, by itself, close an action.

**Inputs.** Engineering work items derived from an approved action.

**Outputs.** Completed engineering work supporting an action's Implementation Plan.

**Interactions with other roles.** Supports the Implementation Engineer's execution of the Implementation Plan; does not interact directly with the Board.

### Reviewer

**Purpose.** Performs the repository's existing documentation review workflow against artifacts requiring formal review, such as a transformation artifact or a standards document.

**Primary Responsibilities.** Evaluating a governance artifact against the documentation review workflow's stages and recording the outcome, as required, for example, by the exit criteria of a transformation-artifact review action.

**Decision Authority.** Determines whether an artifact passes a given review stage; does not have Board-level authority to approve an architectural action or grant an exception to a governance rule.

**Inputs.** A governance artifact submitted for review.

**Outputs.** A recorded review outcome (for example, an Approved status, or a standards review record).

**Interactions with other roles.** Provides review outcomes that may serve as Verification Evidence for actions whose exit criteria require a completed review.

---

## 5. Governance Artifacts

### Repository Architecture Assessment Report

**Purpose.** Establishes the repository's executive architecture baseline: findings, maturity ratings, risks, debt, and prioritized recommendations, consolidated from prior review activity.

**Owner.** Architecture Review Board.

**Created When.** At the conclusion of a formal repository assessment cycle.

**Updated When.** Not updated in place. It is explicitly a point-in-time document; a subsequent assessment cycle produces a new report.

**Permanent or Temporary.** Permanent. Retained as the authoritative source of findings for all actions derived from it.

**Inputs.** The Repository Audit and prior architecture decision reviews, program reviews, and strategy reviews.

**Outputs.** Findings, ratings, risks, debt items, and prioritized recommendations that become candidate Architecture Action Register entries.

**Consumers.** The Architecture Action Register; the Architecture Review Board.

**Related Documents.** Architecture Action Register (derives its actions from this report); any subsequent assessment report (which may confirm closure of actions derived from this one).

**Lifecycle Role.** Originates governance actions. Does not itself authorize, plan, or track implementation.

### Architecture Action Register

**Purpose.** Records the architectural, governance, documentation, and validation actions the Board has approved, and tracks each through its lifecycle from Identified to Closed.

**Owner.** Architecture Review Board.

**Created When.** Upon the Board's approval of the first action derived from an assessment report.

**Updated When.** Continuously, as actions progress through lifecycle states, and whenever a new assessment report approves further actions.

**Permanent or Temporary.** Permanent. A continuously maintained living record, versioned (for example, 1.0, 1.1) as it is refined.

**Inputs.** Approved findings from the Repository Architecture Assessment Report; Board decisions on action status changes.

**Outputs.** Recorded actions with status, owner, target release, verification evidence, and exit criteria.

**Consumers.** Implementation Engineers (for action scope and exit criteria); the Architecture Review Board (for status oversight); future assessment reports (which review the Register's state).

**Related Documents.** Repository Architecture Assessment Report (source); Architecture Action Execution Record (per action); Architecture Review Board Decision Record (when a conflict requires Board decision).

**Lifecycle Role.** Authorizes and tracks every action from approval through closure. Does not itself plan or perform implementation.

### Architecture Action Execution Record

**Purpose.** Plans the implementation of a single approved action: current state analysis, impact assessment, recommended implementation approach, implementation plan, validation checklist, risks, evidence requirements, and verification procedure.

**Owner.** Implementation Engineer, for Board confirmation.

**Created When.** Once an action is approved and assigned for planning.

**Updated When.** Revised, as a new version, if the Board's decision on a referred conflict changes the approved implementation approach.

**Permanent or Temporary.** Temporary by its own declaration: it exists only while the action is active and is superseded by Verification Evidence once the action is Closed. Superseded or prior versions are nonetheless retained as governance history rather than deleted.

**Inputs.** The Register entry for the action; the assessment sections the action derives from; the repository documents in the action's scope.

**Outputs.** A confirmed (or Board-amended) resolution direction; an Implementation Plan; a Validation Checklist; a Verification Procedure.

**Consumers.** The Architecture Review Board (to confirm resolution direction); the Implementation Engineer or Repository Maintainer executing the plan; the Architecture Action Execution Report, if execution surfaces a conflict.

**Related Documents.** Architecture Action Register (source of the action); Architecture Action Execution Report and Decision Review Package (if execution is paused); a revised Execution Record version (if the Board decides a different approach).

**Lifecycle Role.** Plans and documents the approach to implementation. Governs Planned through Implemented states.

### Architecture Action Execution Report

**Purpose.** Documents what occurred during execution of an Execution Record's Implementation Plan, including any finding that blocks further progress, such as a conflict between the approved approach and an existing governance rule.

**Owner.** Implementation Engineer.

**Created When.** Execution surfaces a finding — most notably a governance conflict — that the Execution Record did not anticipate.

**Updated When.** Not updated once produced; a further Execution Report would accompany a further, distinct execution attempt.

**Permanent or Temporary.** Permanent as an evidentiary record of what execution found, retained as part of governance history.

**Inputs.** The Execution Record's Implementation Plan and the state of the repository documents encountered during its execution.

**Outputs.** A documented execution finding, forming the evidentiary basis for a Decision Review Package where one is required.

**Consumers.** The Architecture Review Board Secretary (in preparing a Decision Review Package); the Architecture Review Board.

**Related Documents.** The Execution Record it reports against; the Decision Review Package it supports.

**Lifecycle Role.** Bridges a blocked execution attempt to the exception governance workflow described in Section 7.

### Decision Review Package

**Purpose.** Supports Architecture Review Board deliberation on a governance conflict discovered during execution, presenting decision options neutrally, together with a comparative analysis and a recommendation, without itself deciding.

**Owner.** Architecture Review Board Secretary, prepared for the Board.

**Created When.** Execution of an Execution Record's Implementation Plan is paused by a governance conflict requiring Board resolution.

**Updated When.** Not updated once submitted; the Board's decision is recorded separately in the Decision Record.

**Permanent or Temporary.** Permanent. Retained as the deliberative record supporting the Board's decision; its own blank decision fields are superseded by the Decision Record rather than completed in place.

**Inputs.** The Execution Record; the Execution Report's documented finding.

**Outputs.** Decision options, a comparative analysis, questions for the Board, and a recommendation.

**Consumers.** The Architecture Review Board.

**Related Documents.** The Execution Record and Execution Report it draws on; the Architecture Review Board Decision Record it supports.

**Lifecycle Role.** Exception-workflow artifact only; it does not appear in the normal lifecycle described in Section 6.

### Architecture Review Board Decision Record

**Purpose.** Records the Board's decision on a Decision Review Package as the authoritative governance record, and authorizes the next stage of execution.

**Owner.** Architecture Review Board (Chair and Secretary).

**Created When.** Following the Board's decision on a Decision Review Package.

**Updated When.** Not updated once approved and signed.

**Permanent or Temporary.** Permanent.

**Inputs.** The Decision Review Package; the Board's decision.

**Outputs.** A recorded decision, rationale, conditions, an implementation authorization, stated governance effects, and follow-up actions.

**Consumers.** The Implementation Engineer (to prepare a revised Execution Record); whoever maintains the Architecture Action Register (to update recorded status).

**Related Documents.** The Decision Review Package it decides; the revised Execution Record it authorizes; the Architecture Action Register it directs be updated.

**Lifecycle Role.** Exception-workflow artifact only. Authorizes resumption of the normal lifecycle following resolution of a governance conflict.

### Verification Evidence

**Purpose.** Confirms that an action's exit criteria, as recorded in the Architecture Action Register, have been met.

**Owner.** Produced by whoever performs the verification steps the Execution Record's Verification Procedure specifies; confirmed by the Architecture Review Board.

**Created When.** At the transition from Implemented to Verified.

**Updated When.** Not updated once recorded; superseding evidence would attach to a superseding action.

**Permanent or Temporary.** Permanent. The Register's Governance Rules require that Verification Evidence remain available even after an action reaches Closed status.

**Inputs.** The completed Implementation Plan; the Execution Record's stated Evidence Required and Verification Procedure.

**Outputs.** A recorded confirmation against each exit-criteria condition.

**Consumers.** The Architecture Review Board (to confirm closure); future Repository Architecture Assessment Reports (which may review closed actions' evidence).

**Related Documents.** The Execution Record it verifies against; the Architecture Action Register entry it allows to close.

**Lifecycle Role.** Governs the Verified and Closed states.

---

## 6. Governance Lifecycle

The normal governance lifecycle applies when execution of an approved action's Implementation Plan proceeds without discovering a conflict with existing governance.

```
Repository Assessment
        ↓
Action Register
        ↓
Execution Record
        ↓
Implementation
        ↓
Verification
        ↓
Action Register Updated
        ↓
Action Closed
```

**Repository Assessment → Action Register.** A formal Repository Architecture Assessment Report identifies findings and prioritized recommendations. The Architecture Review Board approves selected findings as actions, entering each into the Architecture Action Register with a Source reference, Category, Priority, and Exit Criteria.

**Action Register → Execution Record.** Once an action is Approved and assigned an owner and target release (Planned), an Implementation Engineer prepares an Execution Record: a current-state analysis, impact assessment, recommended implementation approach, and step-by-step Implementation Plan, submitted to the Board for confirmation of the proposed resolution direction.

**Execution Record → Implementation.** With the resolution direction confirmed, the Implementation Engineer (and, for the resulting document edits, the Repository Maintainer) executes the Implementation Plan's steps in sequence, moving the action to In Progress and then Implemented once the described changes are made.

**Implementation → Verification.** The Implementation Engineer produces Verification Evidence against the Execution Record's stated Evidence Required and Verification Procedure, confirming each exit-criteria condition.

**Verification → Action Register Updated.** The Board confirms the Verification Evidence against the action's Exit Criteria and directs that the Register be updated to Verified status.

**Action Register Updated → Action Closed.** The Board records closure of the action in the Register, with Verification Evidence populated per the Register's own Governance Rules. The action remains part of repository history rather than being removed.

---

## 7. Exception Governance Workflow

The exception workflow applies only when execution of a confirmed Implementation Plan discovers an unexpected conflict with an existing governance rule — a circumstance the repository has evidenced once, in ACT-001, where the Execution Record's confirmed resolution direction conflicted with an identifier-permanence rule recorded elsewhere in the same document family.

```
Execution
    ↓
Execution Report
    ↓
Decision Review Package
    ↓
Architecture Review Board Decision
    ↓
Execution Record v2
    ↓
Implementation resumes
```

**Execution → Execution Report.** The Implementation Engineer, executing a confirmed Implementation Plan, encounters a governance conflict the Execution Record did not anticipate. Execution halts at the affected step; no further step is attempted. The finding is documented as an Execution Report.

**Execution Report → Decision Review Package.** The Architecture Review Board Secretary prepares a Decision Review Package, presenting the conflict, the decision options it admits, a comparative analysis, and a recommendation, for Board deliberation. The Package does not decide; it supports deliberation only.

**Decision Review Package → Architecture Review Board Decision.** The Board deliberates on the Package and records its decision — including the option adopted, its rationale, any conditions, and the governance effects on existing documents — in an Architecture Review Board Decision Record.

**Architecture Review Board Decision → Execution Record v2.** The Decision Record authorizes preparation of a revised Execution Record reflecting the Board's decided approach, replacing the implementation approach originally proposed.

**Execution Record v2 → Implementation resumes.** Once the revised Execution Record is itself approved, the Implementation Engineer resumes execution, rejoining the normal lifecycle at the Implementation stage described in Section 6.

**This workflow is exceptional, not normal.** It is triggered only by the discovery of a governance conflict during execution. It introduces no new lifecycle state to the Architecture Action Register: the action remains in the state it was in when execution paused (typically In Progress) throughout the exception workflow, and only advances once implementation resumes under Section 6.

---

## 8. Governance Decision Model

Repository governance separates the following responsibilities, each vested in a distinct artifact and, correspondingly, a distinct role:

| Responsibility | Artifact | Role |
|---|---|---|
| Identifies issues | Repository Architecture Assessment Report | Architecture Review Board |
| Authorizes work | Architecture Action Register | Architecture Review Board |
| Plans implementation | Architecture Action Execution Record | Implementation Engineer |
| Performs implementation | Repository document changes | Implementation Engineer, Repository Maintainer, Contributor |
| Documents execution | Architecture Action Execution Report | Implementation Engineer |
| Supports Board deliberation | Decision Review Package | Architecture Review Board Secretary |
| Authorizes implementation direction | Architecture Review Board Decision Record | Architecture Review Board |
| Confirms completion | Verification Evidence | Implementation Engineer, confirmed by the Architecture Review Board |
| Records closure | Architecture Action Register | Architecture Review Board |

**Why these responsibilities remain separated.** The Architecture Action Register's Governance Notes state that an action represents a Board-approved architectural decision, not an engineering task, and that completion of the engineering work associated with an action does not, by itself, close it. This separation ensures that no single role can both propose and adopt a resolution direction, both execute a plan and confirm its verification, or both discover a governance conflict and unilaterally resolve it. Each transition requires the artifact and role appropriate to it, preserving the evidence-based, Board-authorized character of the framework described in Section 3.

---

## 9. Repository Traceability

Governance traceability is maintained by requiring that each artifact cite the specific artifact and section it derives from, rather than restating or re-deriving prior conclusions independently.

```
Repository
    ↓
Architecture Review
    ↓
Repository Architecture Assessment Report
    ↓
Architecture Action Register
    ↓
Architecture Action Execution Record
    ↓
[ Architecture Action Execution Report → Decision Review Package → Architecture Review Board Decision Record → Execution Record v2 ]
    ↓
Implementation
    ↓
Verification Evidence
    ↓
Architecture Action Register (updated)
    ↓
Next Repository Architecture Assessment Report
```

The bracketed segment represents the exception workflow of Section 7; it is traversed only when a governance conflict is discovered, and traceability continues into Implementation once it resolves.

**How superseded records remain part of governance history.** The Architecture Action Register's Governance Rules state that actions are never deleted, only closed or superseded, and that a superseded action must reference the action that replaces it; closed actions remain part of repository history and are retained in the Register rather than removed. The same principle applies to the Architecture Action Execution Record: when a Board decision revises the approved implementation approach, the original Execution Record is retained as part of governance history rather than being overwritten, and the revised Execution Record (v2) is recorded as the current plan. This ensures that a reader can reconstruct, at any later point, both what was originally approved and what was subsequently decided, and why.

---

## 10. Governance Lifecycle States

The Architecture Action Register defines seven lifecycle states, applied uniformly to every action it tracks.

| State | Entry Criteria | Exit Criteria | Expected Evidence | Responsible Role |
|---|---|---|---|---|
| Identified | Named by an approved assessment | Board accepts the action for execution | Assessment section reference | Architecture Review Board |
| Approved | Board has accepted the action | An owner and target release are assigned | Register entry with owner and release fields populated | Architecture Review Board |
| Planned | Owner and target release assigned | Execution of the Implementation Plan begins | Execution Record confirmed | Implementation Engineer |
| In Progress | Execution has begun | The described changes are made | Implementation Plan steps executed | Implementation Engineer, Repository Maintainer |
| Implemented | The change described by the action has been made | Verification evidence confirms exit criteria | Updated repository documents | Implementation Engineer |
| Verified | Verification evidence recorded and confirmed | Board records closure | Verification Evidence matched against Exit Criteria | Architecture Review Board |
| Closed | Board has recorded closure | None; action requires no further tracking | Verification Evidence retained in the Register | Architecture Review Board |

**How execution may pause pending Board review without introducing additional lifecycle states.** When execution discovers a governance conflict, the action remains in its current state — In Progress, in the one instance evidenced by the repository — while the exception workflow of Section 7 runs to resolution. The Decision Review Package and Architecture Review Board Decision Record are not lifecycle states of the action; they are artifacts of a deliberation that occurs within the In Progress state. The action only advances past In Progress once implementation resumes and the changes described by the (possibly revised) Implementation Plan are made.

---

## 11. Repository Governance Rules

The following operational rules are demonstrated by the repository's governance artifacts.

- **Do not reassess during implementation.** The Architecture Action Register states that it does not restate the reasoning, evidence, or ratings of the assessment report, and that reprioritization or reinterpretation of an action's intent requires a new or amended assessment, not an implementation-time reinterpretation.
- **Do not modify historical evidence.** The ACT-001 Execution Record identifies the Repository Audit as a point-in-time record not to be retroactively edited, since doing so would misrepresent the evidence base the assessment relied on.
- **Preserve governance history.** Actions are never deleted, only closed or superseded; closed actions and superseded Execution Record versions remain part of repository history.
- **Separate findings from decisions.** The Repository Architecture Assessment Report introduces findings; the Architecture Review Board, not the report itself, decides which findings become approved actions and, where a conflict arises, which resolution option is adopted.
- **Separate governance from implementation.** An architectural action is a Board-approved decision, distinct from the engineering tasks that carry it out; completion of engineering work does not by itself close an action.
- **Board decisions supersede implementation proposals.** A proposed resolution direction in an Execution Record is confirmed, or superseded, by the Board; where the Board decides a different approach following a Decision Review Package, the revised Execution Record supersedes the original proposal.
- **Verification requires evidence.** An action may not be marked Closed without recorded Verification Evidence, and that evidence must remain available after closure.
- **Use traceability for every governance action.** Every action must remain traceable to its originating assessment, as recorded in the Register's Source column; every Execution Record, Execution Report, Decision Review Package, and Decision Record likewise cites the specific artifact and section it derives from.

---

## 12. Repository Governance Flow

**End-to-end normal flow:**

```
Repository
    ↓
Assessment
    ↓
Action Register
    ↓
Execution Planning
    ↓
Implementation
    ↓
Verification
    ↓
Closure
```

**Exception workflow (triggered only by a governance conflict discovered during Implementation):**

```
Implementation (paused)
    ↓
Execution Report
    ↓
Decision Review Package
    ↓
Architecture Review Board Decision
    ↓
Execution Record v2
    ↓
Implementation (resumes)
    ↓
Verification
    ↓
Closure
```

---

## 13. Document Relationships

| Document | Purpose | Owner | Created By | Consumed By | Next Document | Lifecycle Stage |
|---|---|---|---|---|---|---|
| Repository Architecture Assessment Report | Establish architecture baseline and findings | Architecture Review Board | Architecture Review Board | Architecture Action Register | Architecture Action Register | Assessment |
| Architecture Action Register | Authorize and track architectural actions | Architecture Review Board | Architecture Review Board | Implementation Engineer, Architecture Review Board | Architecture Action Execution Record | Action Authorization |
| Architecture Action Execution Record | Plan implementation of a single action | Architecture Review Board (confirms) | Implementation Engineer | Architecture Review Board, Implementation Engineer | Implementation (or Execution Report, if paused) | Execution Planning |
| Architecture Action Execution Report | Document an execution finding or conflict | Architecture Review Board | Implementation Engineer | Architecture Review Board Secretary | Decision Review Package | Exception (Execution) |
| Decision Review Package | Support Board deliberation on a conflict | Architecture Review Board | Architecture Review Board Secretary | Architecture Review Board | Architecture Review Board Decision Record | Exception (Decision Support) |
| Architecture Review Board Decision Record | Record the Board's decision and authorize resumption | Architecture Review Board | Architecture Review Board Secretary, Chair | Implementation Engineer, Repository Maintainer | Architecture Action Execution Record (v2) | Exception (Decision) |
| Verification Evidence | Confirm exit criteria are met | Implementation Engineer | Implementation Engineer | Architecture Review Board | Architecture Action Register (updated) | Verification |

---

## 14. Frequently Asked Questions

**Why do we perform architecture governance?** To ensure that architectural findings, approved actions, implementation, and verification are each recorded and traceable, so that the repository's evolution proceeds through evidence-based, Board-authorized decisions rather than undocumented change.

**When is an Assessment created?** At the conclusion of a formal repository assessment cycle. It is a point-in-time document; it is not updated in place.

**When is an Action Register updated?** Continuously: whenever an action's status changes, and whenever a new assessment report approves further actions.

**Who approves implementation?** The Architecture Review Board, by confirming (or amending) the resolution direction proposed in an Execution Record before implementation begins.

**When is a Decision Review Package required?** Only when execution of a confirmed Implementation Plan discovers a conflict with an existing governance rule that the Execution Record did not anticipate, requiring a Board decision before implementation can proceed.

**What happens when execution discovers a governance conflict?** Execution halts at the affected step. The finding is documented in an Execution Report, a Decision Review Package is prepared for Board deliberation, and the Board's decision is recorded in a Decision Record authorizing a revised Execution Record before implementation resumes.

**Can implementation change governance?** No. Implementation executes a Board-confirmed plan; it does not itself decide resolution directions, grant exceptions to existing governance rules, or close actions. Where implementation surfaces a conflict, only the Board can decide how it is resolved.

**Can assessments be modified?** No. A Repository Architecture Assessment Report is a point-in-time document. Its findings are carried forward into the Architecture Action Register rather than revised in place; a subsequent assessment cycle produces a new report.

**What happens to superseded governance records?** They are retained as part of governance history rather than deleted. A superseded action or Execution Record must reference, or be referenced by, the record that replaces it, so that both the original and the revised position remain traceable.

---

## 15. Conclusion

Repository governance, as evidenced across the Repository Architecture Assessment Report, the Architecture Action Register, the ACT-001 Execution Record, the ACT-001 Execution Report, the ACT-001 Decision Review Package, and the ACT-001 Decision Record, exists to ensure that architecture remains:

- **Transparent** — findings, decisions, and their rationale are recorded rather than held informally.
- **Traceable** — every artifact cites the specific artifact and section it derives from.
- **Repeatable** — the same lifecycle and roles apply uniformly to every action, regardless of category or priority.
- **Controlled** — implementation proceeds only from a Board-confirmed plan, and conflicts are resolved only by Board decision.
- **Verifiable** — no action closes without recorded, retained Verification Evidence.
- **Auditable** — superseded and closed records are preserved as governance history rather than removed.

This guide documents that framework as it exists. It introduces no additional governance concept beyond what these artifacts already evidence.

---

## Appendix A — Governance Artifact Matrix

| Artifact | Purpose | Owner | Trigger | Permanent / Temporary | Primary Consumer | Next Artifact | Lifecycle Stage |
|---|---|---|---|---|---|---|---|
| Repository Architecture Assessment Report | Establish baseline findings | Architecture Review Board | Formal assessment cycle | Permanent | Architecture Action Register | Architecture Action Register | Assessment |
| Architecture Action Register | Authorize and track actions | Architecture Review Board | Board approval of assessment findings | Permanent | Implementation Engineer | Architecture Action Execution Record | Action Authorization |
| Architecture Action Execution Record | Plan implementation | Implementation Engineer | Action reaches Planned | Temporary (superseded by Verification Evidence at Closed) | Architecture Review Board | Implementation, or Execution Report | Execution Planning |
| Architecture Action Execution Report | Document execution finding | Implementation Engineer | Governance conflict discovered during execution | Permanent | Architecture Review Board Secretary | Decision Review Package | Exception |
| Decision Review Package | Support Board deliberation | Architecture Review Board Secretary | Execution Report requires Board decision | Permanent | Architecture Review Board | Architecture Review Board Decision Record | Exception |
| Architecture Review Board Decision Record | Record Board decision | Architecture Review Board | Board deliberation concludes | Permanent | Implementation Engineer | Architecture Action Execution Record (v2) | Exception |
| Verification Evidence | Confirm exit criteria met | Implementation Engineer | Implementation complete | Permanent | Architecture Review Board | Architecture Action Register (updated) | Verification |

---

## Appendix B — Governance Decision Matrix

| Decision | Decision Authority | Supporting Artifact | Recorded In | Example |
|---|---|---|---|---|
| Which findings become approved actions | Architecture Review Board | Repository Architecture Assessment Report | Architecture Action Register | ACT-001 through ACT-008 approved from RAAR-001 |
| Which resolution direction to confirm for an action | Architecture Review Board | Architecture Action Execution Record | Architecture Action Register (status), Execution Record | Confirmation of the resolution direction proposed for ACT-001 |
| How to resolve a governance conflict discovered during execution | Architecture Review Board | Decision Review Package | Architecture Review Board Decision Record | Adoption of Option 3 in the ACT-001 Decision Record |
| Whether verification evidence satisfies exit criteria | Architecture Review Board | Verification Evidence | Architecture Action Register | Confirmation required before ACT-001 can be marked Verified |
| Whether an action may be closed | Architecture Review Board | Verification Evidence, Architecture Action Register | Architecture Action Register | Closure recorded only with populated Verification Evidence |

---

## Appendix C — Governance Responsibility Matrix (RACI)

| Activity | Architecture Review Board | Chair | Secretary | Implementation Engineer | Maintainer | Contributor | Reviewer |
|---|---|---|---|---|---|---|---|
| Assessment | A | I | I | I | I | I | I |
| Action Register (approval/entry) | A/R | I | I | I | I | — | — |
| Execution Planning | C | I | I | R/A | C | — | — |
| Implementation | I | I | I | R | R | R | — |
| Execution Reporting | I | I | I | R/A | C | — | — |
| Decision Review | C | I | R/A | C | — | — | — |
| Board Decision | A | R | R | I | I | — | — |
| Verification | A | I | I | R | C | — | C |
| Closure | A/R | I | I | I | I | — | — |

R = Responsible, A = Accountable, C = Consulted, I = Informed.

---

## Appendix D — Governance Lifecycle State Machine

| From State | To State | Responsible Role | Evidence Required | Decision Required |
|---|---|---|---|---|
| (none) | Identified | Architecture Review Board | Named by an approved assessment | None |
| Identified | Approved | Architecture Review Board | None beyond Board acceptance | Board accepts action for execution |
| Approved | Planned | Architecture Review Board / Maintainer | Owner and target release assigned | None |
| Planned | In Progress | Implementation Engineer | Execution Record confirmed | Board confirms resolution direction |
| In Progress | Implemented | Implementation Engineer, Maintainer | Implementation Plan steps executed | None (unless a conflict is discovered — see below) |
| Implemented | Verified | Implementation Engineer | Verification Evidence matched to Exit Criteria | Board confirms verification |
| Verified | Closed | Architecture Review Board | Verification Evidence recorded and retained | Board records closure |
| In Progress | In Progress (paused, exception workflow) | Implementation Engineer, Architecture Review Board | Execution Report, Decision Review Package | Board decision (Decision Record) required before resuming |

The paused transition is not a new lifecycle state; it is the same In Progress state, held pending the Board decision described in Section 7, before advancing to Implemented under a (possibly revised) Implementation Plan.

---

## Appendix E — Governance Quick Reference

**Governance lifecycle (normal):** Assessment → Action Register → Execution Record → Implementation → Verification → Action Register Updated → Closed.

**Exception workflow:** Implementation (paused) → Execution Report → Decision Review Package → Board Decision → Execution Record v2 → Implementation resumes.

**Decision flow:** Assessment identifies → Register authorizes → Execution Record plans → Implementation performs → Execution Report documents (if conflict) → Decision Review supports deliberation (if conflict) → Board Decision authorizes direction (if conflict) → Verification confirms → Register records closure.

**Roles at a glance:** Board decides; Chair and Secretary record the Board's decisions; Implementation Engineer plans and executes; Maintainer applies confirmed changes; Contributor performs mapped engineering work; Reviewer evaluates artifacts against the review workflow.

**Lifecycle states:** Identified → Approved → Planned → In Progress → Implemented → Verified → Closed.

**Repository governance rules:** Do not reassess during implementation. Do not modify historical evidence. Preserve governance history. Separate findings from decisions. Separate governance from implementation. Board decisions supersede implementation proposals. Verification requires evidence. Trace every action to its originating assessment.
