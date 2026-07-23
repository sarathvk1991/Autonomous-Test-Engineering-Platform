# Architecture Action Execution Record — ACT-001

Status: Execution package prepared for Architecture Review Board review. This is a temporary execution document that exists only while ACT-001 is active in the Architecture Action Register. It is superseded by the Verification Evidence recorded against ACT-001 once the action is Closed.

---

## 1. Action Summary

| Field | Value |
|---|---|
| Action ID | ACT-001 |
| Title | Resolve shared capability identifier collision |
| Priority | High |
| Current Status | Identified |
| Source Assessment References | RAAR-001 §4 Repository Identity; §10 Repository Risks (Architectural); §11 Architectural Debt (Governance Debt, High); §13 Prioritized Recommendations, Immediate; §14 Recommended Roadmap, Step 1 |
| Exit Criteria | A governance action assigns each identifier definition a distinct identifier, or formally designates one definition as authoritative, and no repository document retains an unresolved conflicting definition. |

This summary is reproduced from the Architecture Action Register without modification.

---

## 2. Objective

This action exists because the repository's capability identifier `CAP-001` is assigned, independently, to two unrelated capabilities: "Connector Framework & Registry," a real, implemented capability governed by the platform's capability matrix, and "Requirements Intelligence," a capability document within the Engineering Intelligence Operating System (EIOS) target-architecture lineage. Neither definition cites or acknowledges the other. This is the architectural issue RAAR-001 identifies as a Governance Debt item of High priority, and as the single most-cited unresolved inconsistency across the assessment.

The issue this action resolves is one of identifier integrity: a reader, a future document, or a future capability registration cannot reliably cite "CAP-001" and be understood to mean one specific capability. Left unresolved, every future document that cites CAP-001 by number inherits this ambiguity.

Successful completion looks like a repository in which the string `CAP-001` resolves, without qualification, to exactly one capability definition, with the alternate definition either reassigned a distinct identifier or the collision otherwise formally and permanently closed by a recorded governance action, and with every existing repository reference updated to remain accurate.

---

## 3. Repository Scope

The following repository areas are within scope for this action.

**Governance documents (define or mirror the Track A definition of CAP-001).**

- `docs/governance/platform-capability-matrix.md` — the defining source of `CAP-001` as "Connector Framework & Registry," section 5.1, within the `CAP-001…009 Ingestion & Core` domain block.
- `docs/governance/architecture-coverage-dashboard.md` — a derived, downstream view that mirrors the same `CAP-001` row from the capability matrix.

**Product and architecture documents (cite or define the EIOS-lineage definition of CAP-001).**

- `docs/product/CAP-001-requirements-intelligence.md` — the defining source of `CAP-001` as "Requirements Intelligence."
- `docs/product/ADR-001-engineering-intelligence-platform-architecture.md`
- `docs/product/ADR-100-engineering-intelligence-operating-system-architecture.md`
- `docs/product/ADR-HAP-001-requirements-intelligence-architecture.md`
- `docs/product/CAP-100-engineering-intelligence-operating-system-platform-capability-architecture.md`
- `docs/product/PRA-001-engineering-intelligence-platform-reference-architecture.md`
- `docs/product/PRA-100-engineering-intelligence-operating-system-reference-architecture.md`
- `docs/product/PRD-100-engineering-intelligence-operating-system.md`
- `docs/product/PRD-HAP-001-requirements-intelligence.md`
- `docs/product/RUN-001-requirements-intelligence-runtime.md`
- `docs/product/RUN-100-engineering-intelligence-operating-system-runtime-architecture.md`
- `docs/product/SYS-001-requirements-intelligence-system-specification.md`
- `docs/product/SYS-100-engineering-intelligence-operating-system-logical-system-architecture.md`

**Standards and governance-lifecycle documents.**

- `docs/handbook/HB-001-platform-engineering-handbook.md` — contains the Bounded Context Classification and grandfather clause governing the EIOS-lineage `CAP-001`.
- `docs/standards/STD-006-engineering-governance-standard.md`
- `docs/standards/STD-009-engineering-adoption-standard.md`
- `docs/proposals/capability-contract-standard-std-002-revision-proposal.md`
- `docs/proposals/capability-contract-standard-std-002-revision-3-proposal.md`
- `docs/reviews/SRR-STD-002-R2-standards-review-record.md`
- `docs/reviews/SRR-STD-002-R3-standards-review-record.md`
- `docs/reviews/DRC-STD-002-R2-disposition-of-review-comments.md`
- `docs/reviews/BLR-STD-002-V2.0-baseline-record.md`

**Release documentation.**

- `docs/releases/v1.1.0-requirement-intelligence.md` — cites the Track A `CAP-001` in connection with `CONNECTOR_REGISTRY_VERSION`.

**Diagrams.** None identified. No diagram files exist in the repository outside inline Markdown structures.

**Source code.** None identified. A repository-wide search of `requirement_intelligence/`, `app/`, `shared/`, `infrastructure/`, `tests/`, and `scripts/` found no occurrence of the literal identifier `CAP-001` in source or test files. The collision is confined to documentation and governance artifacts.

**Assessment record.** `docs/EIOS-REPOSITORY-AUDIT-implementation-baseline.md` documents the collision as a finding. This document is a point-in-time audit record and is not itself modified by this action; it is listed here for completeness of scope review only.

---

## 4. Current State Analysis

This section records the repository's current state. It does not resolve the collision.

**Where the collision exists.** The identifier `CAP-001` is assigned to two capability definitions that do not reference one another.

| Definition | Title | Location | Status | Nature |
|---|---|---|---|---|
| Track A | Connector Framework & Registry | `docs/governance/platform-capability-matrix.md`, §5.1; mirrored in `docs/governance/architecture-coverage-dashboard.md` | Production Ready, Complete | A real, implemented capability integrating external systems (Jira, ZAP, SonarQube) behind one contract, versioned `CONNECTOR_REGISTRY_VERSION` 1.0.0. |
| Track B | Requirements Intelligence | `docs/product/CAP-001-requirements-intelligence.md` | Draft, pending Capability Board approval | A capability document within the EIOS target-architecture lineage, derived from `ADR-001` and `PRD-001`, anchoring a further document chain (`RUN-001`, `SYS-001`, `PRA-001`). |

**Which references are inconsistent.** No document in the Track A governance family (the capability matrix, the coverage dashboard) cites or acknowledges the Track B `CAP-001` definition. No document in the Track B lineage (the capability document itself, or any of the thirteen product, architecture, and standards documents identified in Section 3 that cite `CAP-001`) cites or acknowledges the Track A definition. The two definitions coexist under the same identifier without cross-reference in either direction.

**Which definition appears authoritative.** Neither definition is designated authoritative over the other by any existing governance record. `HB-001` §20.4 records a grandfather clause explicitly exempting the platform's existing `-001` series, including the Track B `CAP-001`, from renumbering under its own Bounded Context Classification scheme. This clause reconciles Track B's `CAP-001` against Track B's own later numbering scheme; it does not reference, and does not resolve, the separate fact that Track A independently assigns the same identifier string to a different, real capability. The governance record that produced this grandfather clause did not contemplate the Track A definition.

**Which definitions appear duplicated.** The definitions are not duplicated in content. They describe two genuinely different capabilities. Only the identifier string is shared. This is a naming collision, not a content duplication.

---

## 5. Impact Assessment

| Document family | Required modification | Reason | Architectural impact | Downstream impact |
|---|---|---|---|---|
| Governance (capability matrix, coverage dashboard) | Reassign the identifier for the "Connector Framework & Registry" capability to a distinct identifier within its existing `CAP-001…009 Ingestion & Core` domain block. | Removes the collision at its Track A source without disturbing the more extensively cited Track B lineage. | Changes the identifier of a capability marked Production Ready and Complete, but no Freeze Date has been recorded for it in the Architecture Freeze Index, so no frozen contract is disturbed by the reassignment. | The domain-block range table in the capability matrix and its mirrored row in the coverage dashboard require corresponding updates. |
| Product and CAP-001-lineage documents (Track B) | None to their defining content. | These documents already cite the Track B `CAP-001` consistently with one another and with `HB-001`'s own grandfather clause; the recommended resolution direction (Section 6) leaves this identifier unchanged. | None, provided the resolution direction in Section 6 is adopted. | None. |
| Standards and governance-lifecycle documents | None to existing content. Optionally, a supplementary note in `HB-001` §20.4 stating explicitly that its grandfather clause addresses only the Track B `-001` series and does not extend to, or resolve against, Track A's independently numbered capability matrix. | Closes an implicit gap: the existing grandfather clause reads as though it fully reconciles the `-001` series, without disclosing that a separate, real numbering scheme exists outside its scope. | Low; editorial addition, not a new governance rule. | None. |
| Release documentation | If the Track A reassignment in Section 6 is adopted, update the historical reference in `docs/releases/v1.1.0-requirement-intelligence.md` to reflect the new identifier, or annotate it as historical under the prior identifier. | Preserves accuracy of a historical release record. | Low. | None. |
| Repository Audit | None. | The audit is a point-in-time record of the repository state that produced this action; retroactively editing it would misrepresent the evidence base the assessment relied on. | None. | None. |
| Source code | None. | No source or test file references the literal identifier `CAP-001` (confirmed by repository-wide search). | None. | None. |

---

## 6. Recommended Implementation Approach

The following is the Implementation Lead's proposed resolution for Architecture Review Board confirmation. It does not itself constitute the governance decision the exit criteria requires; that decision is recorded when the Board formally adopts or amends this resolution, consistent with the Governance Rules already established in the Architecture Action Register.

**Identifier that should remain authoritative.** `CAP-001` — Requirements Intelligence (the Track B definition).

**Reasoning.** `HB-001` §20.4 already grandfathers this identifier as part of the platform's founding `-001` series, exempting it from renumbering under the platform's own later classification scheme. Thirteen further documents across the product, architecture, and governance-lifecycle families cite this definition as precedent or dependency. Renumbering it would require updating a materially larger set of documents than the alternative.

**Identifier that should change.** The Track A capability currently identified as `CAP-001`, "Connector Framework & Registry," should be reassigned the next available identifier within its own existing `CAP-001…009 Ingestion & Core` domain block, without renumbering any other capability in that block.

**Reasoning.** This capability has no recorded Freeze Date in the Architecture Freeze Index, meaning it has not yet been formally frozen and remains eligible for identifier reassignment without violating the platform's own freeze discipline. Its citation footprint is limited to two governance documents (Section 3), the smallest footprint of any resolution direction considered.

**Required repository updates.**

- Reassign the capability's identifier in `docs/governance/platform-capability-matrix.md`, including its row entry and the domain-block range table.
- Mirror the reassignment in `docs/governance/architecture-coverage-dashboard.md`.

**Reference updates.**

- Update the historical citation in `docs/releases/v1.1.0-requirement-intelligence.md` consistent with the approach the Board selects in Section 5.

**Validation activities.**

- Perform a repository-wide search for the string `CAP-001` after the update and confirm every remaining occurrence resolves, without ambiguity, to the Track B "Requirements Intelligence" definition.
- Confirm the Track B `CAP-001` lineage (the thirteen documents identified in Section 3) requires no content change as a result of this action.

---

## 7. Implementation Plan

**Step 1.** Confirm, with the Architecture Review Board, the resolution direction proposed in Section 6, or an amended direction.

**Step 2.** Locate the authoritative definition to be retained (`docs/product/CAP-001-requirements-intelligence.md`) and confirm no change to its content is required.

**Step 3.** Locate the definition to be reassigned (`docs/governance/platform-capability-matrix.md`, §5.1) and identify the next available identifier in the `CAP-001…009 Ingestion & Core` domain block.

**Step 4.** Update the capability's identifier in the platform capability matrix, including the domain-block range table.

**Step 5.** Update the mirrored entry in the architecture coverage dashboard.

**Step 6.** Update the historical citation in the affected release document, per the approach confirmed in Step 1.

**Step 7.** Perform a repository-wide search for `CAP-001` and confirm every remaining reference resolves to the retained, authoritative definition.

**Step 8.** Record the governance action closing the collision, including the identifiers assigned, in a form suitable for citation as Verification Evidence.

**Step 9.** Submit the updated documents and the governance action record to the Architecture Review Board for verification against the Exit Criteria.

---

## 8. Validation Checklist

- [ ] Resolution direction confirmed by the Architecture Review Board.
- [ ] Track A capability reassigned a distinct identifier within its existing domain block.
- [ ] Platform capability matrix updated, including the domain-block range table.
- [ ] Architecture coverage dashboard updated to match.
- [ ] Historical release documentation updated or annotated as historical.
- [ ] Repository-wide search confirms `CAP-001` resolves to exactly one definition.
- [ ] Track B `CAP-001` lineage confirmed unchanged.
- [ ] Governance action recording the resolution is documented and available as Verification Evidence.

---

## 9. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| A reference to the reassigned Track A identifier is missed during the repository-wide update. | The collision is only partially closed, and the Exit Criteria are not met. | Perform the repository-wide search specified in Step 7 after every document update, not only at the end of the sequence. |
| The Architecture Review Board selects a different resolution direction than the one proposed in Section 6. | The Implementation Plan in Section 7 would need to be re-sequenced around the new direction. | Step 1 requires Board confirmation of the resolution direction before any document is modified, so no work is performed against an unconfirmed direction. |
| A future Architectural-category revision to the Track B `CAP-001` (contemplated but not yet performed, per the capability-contract-standard proposals) is scheduled concurrently with this action. | Concurrent changes to the same document could conflict. | Confirm, before Step 2, whether any such revision is active; if so, sequence this action's confirmation of "no change required" after that revision closes. |
| The reassigned Track A identifier is referenced informally outside the documentation set reviewed in Section 3, such as in an execution artifact under `output/`. | An informal reference could remain inconsistent with the updated documentation. | Extend the repository-wide search in Step 7 to the `output/` directory as a precaution, even though no such reference was identified during scope review. |

---

## 10. Evidence Required

The following evidence must be available before this action can progress through the lifecycle stages described in Section 12.

- The updated `docs/governance/platform-capability-matrix.md`, showing the reassigned identifier.
- The updated `docs/governance/architecture-coverage-dashboard.md`, showing the corresponding change.
- The updated or annotated `docs/releases/v1.1.0-requirement-intelligence.md`.
- A record of the repository-wide search performed in Step 7, showing every remaining `CAP-001` reference and confirming each resolves to the retained definition.
- A record of the governance action confirming the resolution direction and its adoption by the Architecture Review Board.

No evidence beyond what is produced by executing the steps in Section 7 is asserted here in advance of that execution.

---

## 11. Verification Procedure

The Architecture Review Board verifies completion of ACT-001 by confirming, against the Exit Criteria recorded in Section 1:

1. That a governance action exists, recorded per Step 8, either assigning each identifier definition a distinct identifier or formally designating one as authoritative.
2. That the repository-wide search evidence (Section 10) shows no remaining repository document with an unresolved conflicting definition of `CAP-001`.
3. That the Track B `CAP-001` lineage identified in Section 3 remains unchanged, or, if changed, that the change is itself covered by a separate, appropriately governed action.

Verification is satisfied only when all three conditions are confirmed against submitted evidence. Verification is not satisfied by confirmation that document updates were made without the corresponding repository-wide search evidence.

---

## 12. Completion Recommendation

| Transition | Evidence Required |
|---|---|
| Identified → Approved | Architecture Review Board confirms the resolution direction proposed in Section 6, or an amended direction (Step 1). |
| Approved → Planned | An owner and target release are assigned to the action, consistent with the Architecture Action Register's fields for those attributes. |
| Planned → In Progress | Execution of the Implementation Plan (Section 7) begins. |
| In Progress → Implemented | Steps 2 through 6 of the Implementation Plan are complete; the identified documents are updated. |
| Implemented → Verified | The repository-wide search evidence (Step 7) and the governance action record (Step 8) are submitted and confirmed against the Verification Procedure (Section 11). |
| Verified → Closed | The Architecture Review Board records closure of ACT-001 in the Architecture Action Register, with Verification Evidence populated per the Governance Rules already established in that register. |
