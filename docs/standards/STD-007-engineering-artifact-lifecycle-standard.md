# STD-007 — Engineering Artifact Lifecycle Standard

**Version 1.0 (Draft)**

## 1. Document Metadata

| Field | Value |
| --- | --- |
| Identifier | STD-007 |
| Title | Engineering Artifact Lifecycle Standard |
| Version | 1.0 (Draft) |
| Status | Draft — pending Standards Review Board approval |
| Owner | Platform Architecture, delegated per domain (restates HB-001 §18's own STD-family Owner row) |
| Stakeholders | Constitutional Authority, Standards Authority, Architecture Review Board, Domain Architect, Engineering Lead, Certification Authority (STD-006 §5) |
| **Derived From** | **HB-001 (Revision 4) and STD-000 through STD-006 — the sole content sources.** No Engineering Artifact (a `PRD`, `ADR`, `CAP`, `RUN`, `SYS`, `PRA`, or `IMP`, in any Bounded Context, HB-001 §20.4) is ever a content source of this document. |
| Governing Standards | STD-000 (Principle 6/7, cited throughout §4, §6); STD-001 (§7 Constraint 1, cited in §8); STD-002 (capability-lifecycle vocabulary, §5); STD-003 (evidence vocabulary, §10); STD-004 (relationship and lifecycle vocabulary, §5, §9); STD-005 (transformation semantics, §8–§9); STD-006 (governance/lifecycle separation, §3, and the Governance Lifecycle this document reconciles against in §5). |
| Dependencies | HB-001, STD-000, STD-001, STD-002, STD-003, STD-004, STD-005, STD-006 |
| Related Documents | Every Engineering Artifact this document governs (PRD, ADR, CAP, RUN, SYS, PRA, IMP, in every Bounded Context) **remains a governed subject of STD-007** — never a content source (restates STD-006 §1's own framing one Standard further). |
| Supersedes | Nothing (seventh Standards-family document) |
| Superseded By | Not applicable |

**Reconciliation Note — "STD citing STD," carried forward from STD-006.** HB-001 §13.3's own dependency matrix marks "STD → STD" citation as prohibited; STD-005 and STD-006 already cite sibling Standards in practice regardless (STD-006 §12's own Reconciliation Note). STD-007 continues that same, already-established practice rather than re-litigate it — the gap between the matrix's literal text and the Standards family's own real behavior remains open, tracked once, in STD-006 §13, not re-opened here.

**This is an Engineering Standard, not an Engineering Artifact.** STD-007 carries no Transformation Authority field and no Bounded Context assignment, for the same reasons STD-006 §1 already states of itself, one Standard further.

## 2. Executive Summary

STD-006 answered *who* governs an Engineering Artifact. STD-007 answers a different question STD-006 deliberately left open: ***when*** and ***how*** an Engineering Artifact is permitted to change once it exists, without breaking what already depends on it. **Lifecycle is not governance** — STD-006 §6's own Governance Authority matrix says who approves a change; STD-007 says what kind of change that approval is actually approving, what version it produces, what remains compatible afterward, and what else must be checked as a result. **Lifecycle is not publication** — HB-001 §8's own six-stage Documentation Lifecycle and STD-006 §8's own eight-stage Governance Lifecycle both describe an Artifact's *own document* moving through review to Frozen/Published status; STD-007 §5 describes something that publication status alone does not capture — how mature and how likely-to-change the Artifact's *content* actually is, independent of whether its current version happens to be Frozen. **Lifecycle is not transformation** — STD-005 governs how one Artifact is derived from another (a one-time act, at creation); STD-007 governs how that same Artifact evolves afterward, potentially many times, without ever being re-derived from scratch.

**Artifact evolution, in one sentence:** an Engineering Artifact's own content changes, over calendar time, through a disciplined sequence of Version increments (§6), each checked for Compatibility (§7), each triggering a bounded, non-silent Synchronization check on its immediate neighbors (§8), until it is eventually Superseded or Retired without ever disappearing (§9).

## 3. Position Within Standards Family

| Concern | Question it answers | Governed by |
| --- | --- | --- |
| **Governance** | **Who** may approve a change to an Engineering Artifact? | STD-006, in full. |
| **Lifecycle** | **When**, and under what compatibility discipline, may that change occur? | STD-007 (this document), in full. |
| **Transformation** | **How** does one Engineering Artifact become another in the first place? | STD-005, in full. |

**These three concerns SHALL remain separate, restated as a binding rule, not merely a description.** STD-006 never defines a version number; STD-007 never approves a change; STD-005 never governs a change to an Artifact already derived — it governs only the original act of derivation. A single real-world change to an Engineering Artifact typically engages all three, in this order: STD-006 supplies the Approving Authority; STD-007 supplies the Version increment, Compatibility check, and Synchronization obligation; STD-005 remains silent unless the change is itself a new transformation (a new Artifact derived from the old one, e.g. a superseding ADR).

## 4. Lifecycle Principles

Every principle below restates, and never replaces, a specific STD-000, STD-004, or STD-005 rule.

| Principle | Purpose | Rationale | Preservation Rule |
| --- | --- | --- | --- |
| **Controlled Evolution** | An Engineering Artifact changes only through a classified, versioned act. | Restates STD-000 Principle 7 (Versioned evolution). | §6's Versioning is mandatory before any change is considered complete. |
| **Version Integrity** | An Artifact's own identifier never changes; only its version does. | Restates HB-001 §9's own permanence rule. | §6, in full — a "version" is never a new identity. |
| **Compatibility Preservation** | A change preserves what already depends on the Artifact, unless explicitly and visibly broken. | Restates STD-000 Principle 6 (Backward compatibility). | §7's own seven compatibility kinds are checked before a change is Published (STD-006 §8). |
| **Traceability Continuity** | An Artifact's own traceability chain (HB-001 §20.13) survives every version increment unbroken. | Restates STD-004 in full. | §10's own Lifecycle Evidence requires a traceability check per change. |
| **Lineage Preservation** | An Artifact's own upstream Derived From relationship is never altered by a lifecycle event. | Restates STD-005 §9's own No Circular Transformations constraint, applied to lifecycle rather than transformation. | §9 — supersession creates a new version of the same identity; it never rewrites the original's own lineage. |
| **Non-Silent Supersession** | A superseding Artifact is always recorded as superseding something, never presented as if the predecessor never existed. | Restates STD-005 §4's own No Information Loss principle. | §9, in full. |
| **Historical Preservation** | No Engineering Artifact is ever deleted — only Retired. | Restates STD-000 Principle 6 and HB-001 §8's own Superseded stage. | §9's own "no artifact may disappear" rule. |
| **Deterministic Evolution** | The same change, classified the same way (STD-006 §7), always produces the same version increment (§6). | Restates STD-000 Principle 8. | §6's own Versioning table admits no ambiguous case. |

## 5. Artifact States

**Do not redefine HB-001 §8 or STD-006 §8's own publication states** — this section defines a different axis: an Engineering Artifact's own **content maturity**, independent of whatever its current publication status happens to be.

```
Emerging
        ↓
Active
        ↓
Stable
        ↓
Evolving
        ↓
Deprecated
        ↓
Retired
```

| State | Meaning |
| --- | --- |
| **Emerging** | Recently Published (STD-006 §8); still likely to receive Clarification- or Semantic-category changes (STD-006 §7) as real usage reveals gaps. |
| **Active** | Published, receiving ordinary maintenance; no major change is anticipated. |
| **Stable** | Published, unchanged across multiple Governance Lifecycle cycles (STD-006 §8); changes, if any, are almost always Editorial. |
| **Evolving** | A Behavioral- or Architectural-category change (STD-006 §7) is in progress against this Artifact — a temporary state, exited once the change reaches Governance Approval. |
| **Deprecated** | A successor Artifact exists; this one remains available and, per §9, still governs existing consumers who have not yet migrated. |
| **Retired** | No longer governs anything, even historically — retained for audit only (§9). |

### 5.1 Reconciliation with HB-001 and STD-006 — a genuine terminology inconsistency, made explicit rather than silently resolved

Three documents already use different words for the same two underlying concepts. This section's own choice is a fourth data point, not a resolution:

| Concept | HB-001 §8 | STD-006 §8 | SYS-100 §11 | STD-007 §5 (this document) |
| --- | --- | --- | --- | --- |
| A successor exists; this Artifact remains for historical reference, still governing some consumers. | `Revised` | `Superseded` | `Deprecated` | `Deprecated` |
| No longer governs anything, even historically; permanent, never deleted. | `Superseded` | `Retired` | `Retired` | `Retired` |

**For Concept A, this document's own choice (`Deprecated`) agrees with SYS-100 §11, disagrees with STD-006 §8 (`Superseded`), and disagrees with HB-001 §8 (`Revised`) — a third term for the same idea, not a second.** For Concept B, this document's own choice (`Retired`) agrees with both STD-006 §8 and SYS-100 §11, and disagrees only with HB-001 §8's own `Superseded`. **This document does not adopt any one of the four terms as authoritative over the others** — that would itself be a Constitutional- or Architectural-category change (STD-006 §7) to three documents this one does not govern. It records the inconsistency, names the mapping precisely enough that a reader need not guess, and defers harmonization to a future revision of HB-001 §8 (the root of the terminology) — restating this document's own Writing Guidance: make genuine inconsistencies explicit rather than silently resolve them.

**Relationship to STD-006 §8's own Governance Lifecycle and HB-001 §8's own Documentation Lifecycle.** Both of those describe one *document's* own progression toward Published/Frozen. This section's own six states describe the *content's* own maturity, which may remain `Emerging` for several Governance Lifecycle cycles, or jump straight to `Deprecated` the moment a successor is Published — the two axes are independent, not sequential stand-ins for one another.

## 6. Versioning

Restates HB-001 §9's own Major.Minor.Patch scheme — this document originates no new versioning mechanism, only the mapping between STD-006 §7's Change Classification and which version part increments.

| STD-006 §7 Change Category | Version Part Incremented |
| --- | --- |
| Editorial | Patch. |
| Clarification | Patch, or Minor if new content is genuinely added (restates HB-001 §9's own Minor-trigger example). |
| Semantic | Minor. |
| Behavioral | Minor if backward compatible (§7, below); Major if not. |
| Architectural | Major — and, for the `ADR` and `CAP` families specifically, **a new document identifier, never a version bump of the old one** (restates HB-001 §9's own family-specific rule: "a superseding decision is a *new* ADR number, never a version bump of the old one, because the old decision's text must remain exactly as it was for historical accuracy"). |
| Constitutional | Major, and restricted to STD-000 itself, per STD-000's own §8/§9 amendment process — never performed by incrementing any other family's own version. |

**Family-specific notes, restated from HB-001 §9, not re-derived:** `HB` uses a Revision axis independent of Version (HB-001 §9); `ADR` and `CAP` are numbered permanently, with maturity/supersession — not a version number — carrying the Architectural-category signal; `PRD`, `RUN`, `SYS`, `PRA`, and `IMP` follow the general Major.Minor.Patch scheme in this table directly.

## 7. Compatibility

| Kind | Definition | Expectation |
| --- | --- | --- |
| **Backward compatibility** | An existing consumer of the Artifact's own prior version continues to function unchanged. | Required for every Minor and Patch change (restates STD-000 Principle 6); a Major change may break it, but only when recorded as such (§9). |
| **Forward compatibility** | A change made now does not foreclose a future, not-yet-designed extension. | A SHOULD, not a SHALL — restates ADR-100 §6's own Extensibility principle; checked at Architectural-category review (STD-006 §7), never guaranteed absolutely. |
| **Constitutional compatibility** | The change remains consistent with every STD-000 Principle and Rule. | SHALL, always — restates §4's own Controlled Evolution principle; a Constitutional-category change (STD-006 §7) is the only kind permitted to alter this baseline, and only via STD-000's own amendment process. |
| **Standards compatibility** | The change remains consistent with every applicable Standard (STD-001 through STD-007). | SHALL, always — restates STD-000 Rule 4. |
| **Transformation compatibility** | The change does not invalidate a STD-005 relationship already recorded for this Artifact. | SHALL — a change that would require an existing `derived_from`/`implements`/`belongs_to` relationship to become false is, by definition, an Architectural-category change (STD-006 §7), never a smaller one. |
| **Reference compatibility** | A per-Artifact `PRA-NNN` (e.g. `PRA-100`) remains a valid specialization of the platform-wide `PRA-001` it extends. | SHALL — restates HB-001 §20.12's own "SHALL... never contradict the platform-wide `PRA-001`" rule; a change to either requires the other to be re-checked (§8). |
| **Implementation compatibility** | An `IMP` remains a valid realization of the `PRA`/`SYS` it derives from. | SHALL — restates IMP-100 §7's own Implementation Integrity discipline, generalized to every `IMP` in this lineage. |

**Expectations are stated without technology**, per this document's own Constraints (§11) — a compatibility failure is a fact about meaning and contract, never about a specific API version or wire format.

## 8. Synchronization Rules

Restating SYS-001 §6's own adjacency discipline, generalized to the direction of change propagation: **a change's own mandatory synchronization check propagates exactly one hop at a time, never skipping an intermediate family** — an `ADR` change is never checked directly against an `IMP` without `CAP`, `RUN`, `SYS`, and `PRA` each being checked in turn.

| If this changes | Must the next hop be checked? | Classification (STD-006 §7) required to trigger it |
| --- | --- | --- |
| `PRD` | `ADR` — Mandatory if Architectural-or-above; Optional otherwise. | Architectural, Constitutional. |
| `ADR` | `CAP` — Mandatory. | Semantic and above. |
| `CAP` | `RUN` — Mandatory, since RUN-100 §6.1 realizes CAP-100 §8's own capabilities directly. | Behavioral and above. |
| `RUN` | `SYS` — Mandatory, since SYS-100 §5–§6 traces directly to RUN-100 §6.1. | Behavioral and above. |
| `SYS` | `PRA` — Mandatory, since PRA-100 §6's own compositions are built from SYS-100 §6's own systems directly. | Behavioral and above. |
| `PRA` | `IMP` — Mandatory, since IMP-100 §5–§6 map directly to PRA-100 §6's own compositions. | Behavioral and above. |
| **`PRA-001`** (platform-wide) | **Every per-Artifact `PRA-NNN`** (e.g. `PRA-100`) — Mandatory (restates HB-001 §20.12's own "never contradict" rule, §7 above). | Any change to `PRA-001` at all. |

**Forbidden synchronization.** A downstream Artifact's own change SHALL NEVER be used to silently justify an upstream Artifact's own change — restates STD-001 §7 Constraint 1 ("Architecture cannot change... a perceived gap is resolved by a new or amended ADR, never by implementation-time judgment call"), generalized to every adjacent pair above. Synchronization checks propagate downstream (toward `IMP`) as an obligation to verify continued compatibility; they never propagate upstream as authority to redefine anything.

**Optional synchronization.** An Editorial- or Clarification-category change (STD-006 §7) triggers no mandatory downstream check at all — restating §6's own Version-part mapping, a Patch-level change carries no synchronization obligation.

## 9. Supersession

| Concern | Rule |
| --- | --- |
| **Superseding** | A new Artifact, sharing the same conceptual role but a new identifier (for `ADR`/`CAP`) or an incremented Major version (for others), replaces a prior one going forward — restating §6's own family-specific rule. |
| **Replacement** | The superseded Artifact's own `Superseded By` metadata field (STD-006 §1's own header convention) is updated to name the new one — never left blank once a successor exists. |
| **Retirement** | Occurs only after every known consumer has migrated off the superseded Artifact — restating §5's own `Deprecated → Retired` transition. |
| **Historical preservation** | **No artifact may disappear.** A Retired Artifact's own text remains available for historical reference, permanently — restating STD-000 Principle 6 and HB-001 §8's own Superseded-stage discipline. |
| **Branching** | Two genuinely independent Bounded Contexts (HB-001 §20.4) may each specialize the same upstream Artifact independently — **this is not a fork of one Artifact's own identity; it is two distinct Artifacts sharing a common ancestor**, exactly as the platform-wide `PRA-001` and a per-Artifact `PRA-100` already coexist today (HB-001 §20.12) without either superseding the other. |
| **Parallel evolution** | Two such branches may version independently, at different rates, without requiring the other to synchronize — restating §8's own Synchronization Rules, which bind adjacent *tiers*, never sibling *branches* of the same tier to one another. |

## 10. Lifecycle Evidence

Reuses, never reinvents, STD-006 §9's own Governance Evidence vocabulary, specialized to lifecycle events specifically:

| Evidence | Required for |
| --- | --- |
| **Version record** | Every change, naming the specific Version Part incremented (§6) and the Change Classification (STD-006 §7) that triggered it. |
| **Compatibility assessment** | Every Behavioral-category change and above (§7), naming which of the seven compatibility kinds were checked. |
| **Supersession record** | Every Deprecation and Retirement (§5, §9), naming the successor (if any) and the migration status of known consumers. |
| **Migration note** | Every transition from `Deprecated` to `Retired` (§5), confirming every known consumer has moved to the successor. |
| **Synchronization record** | Every mandatory check §8 requires, naming the adjacent family checked and the outcome. |

## 11. Constraints

STD-007 SHALL NOT: redefine governance (STD-006's own scope, unchanged); redefine transformation (STD-005's own scope, unchanged); redefine architecture; redefine implementation; define technology; or define project management processes (Agile, Scrum, SAFe, or any other methodology) — every rule in this document concerns *when* and *how* an Artifact's own content may change, never *what* process a team uses to produce that change day to day.

## 12. Risks

Maintaining the same honest maturity discipline used throughout EIOS:

| Category | Risk |
| --- | --- |
| **Version drift** | §6's own mapping table is declarative; nothing in this document mechanically confirms a real change's own classification (STD-006 §7) was assigned correctly before its version was incremented. |
| **Branch divergence** | §9's own Branching rule permits two Bounded Contexts to specialize the same upstream Artifact independently — untested against a case where the two branches' own compatibility expectations (§7) genuinely conflict. |
| **Unsynchronized evolution** | §8's own Mandatory checks are declarative — nothing in this document confirms a real `CAP` change actually triggered its own required `RUN` check before `RUN` was, in practice, left stale. |
| **Broken lineage** | §4's own Lineage Preservation principle depends on every Supersession record (§10) being filed correctly — a missed record breaks §9's own "no artifact may disappear" guarantee in practice, even though the rule itself remains intact on paper. |
| **Compatibility failure** | §7's own seven compatibility kinds are checked by human judgment alone — no registry (PRA-001 §8's own Reserved Traceability Service) yet exists to verify any of them mechanically. |
| **Historical loss** | §9's own Historical Preservation principle is a rule, not yet a mechanism — no Engineering Artifact in this lineage has ever actually been Retired to test whether its own text truly remains accessible afterward. |
| **Terminology proliferation** | §5.1's own four-way `Deprecated`/`Superseded`/`Revised` inconsistency is itself a risk this document names but cannot resolve — a fifth document introducing a fifth term for the same concept remains entirely possible until a future HB-001 revision harmonizes all of them. |

## 13. Known Limitations

**Explicit about what has, and has not, been exercised by the existing document set:**

- **No Engineering Artifact in this lineage has ever actually incremented a version** — every PRD/ADR/CAP/RUN/SYS/PRA/IMP produced so far (both the original Requirements-Intelligence-scoped series and the EIOS series) remains at Version 1.0, Draft. §6's own mapping table is therefore entirely unexercised in practice.
- **No real Supersession has ever occurred** — §9's own rules (Superseding, Retirement, Branching) are stated, never demonstrated against a real predecessor/successor pair.
- **The one real candidate for §9's own Branching rule — `PRA-001` and `PRA-100` — predates this document.** Their own coexistence (HB-001 §20.12) is real, but was reconciled by PRA-100 §1 and HB-001 §20.12 directly, never by an explicit application of this document's own §9, which postdates both.
- **§5.1's own terminology reconciliation is this document's own proposal, not an adopted harmonization** — HB-001 §8, STD-006 §8, and SYS-100 §11 each retain their own original wording, unmodified by this document.
- **§8's own Synchronization Rules have never been exercised** — no real `ADR`, `CAP`, `RUN`, `SYS`, or `PRA` change has yet triggered a documented downstream check.
- **§10's own Lifecycle Evidence types are declarative** — no real evidence record of any kind exists yet for any Artifact in this lineage.
- **Future work (reserved, not authorized by this document):** a harmonization revision to HB-001 §8 resolving §5.1's own four-way terminology gap; a mechanical registry checking §8's own Synchronization Rules automatically, restating STD-006 §13's own reserved-not-authorized stance one tier further.

## 14. Final Self Review

- [x] Alignment with HB-001 — §5's own Artifact States are reconciled against HB-001 §8, never redefining it; §6 restates HB-001 §9's own versioning scheme exactly.
- [x] Alignment with STD-000 — every principle in §4 cites a specific STD-000 Principle by number.
- [x] Alignment with STD-001 — §8's own Forbidden Synchronization rule cites STD-001 §7 Constraint 1 directly.
- [x] Alignment with STD-002 — §5's own maturity framing is distinguished from, and does not redefine, STD-002 §3's own capability-lifecycle vocabulary.
- [x] Alignment with STD-003 — §10's own evidence types reuse, never reinvent, STD-003's own evidence vocabulary via STD-006 §9's own reuse discipline.
- [x] Alignment with STD-004 — §4's Traceability Continuity principle and §9's own relationship framing cite STD-004 directly.
- [x] Alignment with STD-005 — §4's Lineage Preservation and Non-Silent Supersession principles cite STD-005 §4 and §9 directly, without redefining either.
- [x] Alignment with STD-006 — §3 draws the Governance/Lifecycle/Transformation distinction explicitly; §5's own reconciliation cites STD-006 §8 by name, never silently diverging from it without saying so.
- [x] Lifecycle completeness — all fifteen required sections are present and address their commissioned objective.
- [x] Compatibility — §7's own seven kinds are each defined with an explicit expectation.
- [x] Technology independence — verified section by section (§11); no language, framework, database, or vendor is named anywhere.
- [x] Governance separation — verified in §3: no Approving Authority, role, or governance matrix is defined or redefined here (that remains STD-006's own scope).
- [x] Transformation separation — verified in §3: no STD-005 semantic is redefined; §8 cites, never reinterprets, STD-005's own relationship vocabulary.

## 15. Lifecycle Compliance Certificate

**This certifies that STD-007, Version 1.0 (Draft):**

- ✅ **Engineering Artifact Lifecycle Standard Complete** — §3–§13 define position within the Standards family, lifecycle principles, artifact states, versioning, compatibility, synchronization rules, supersession, lifecycle evidence, constraints, risks, and known limitations.
- ✅ **Derived Solely from HB-001 and STD-000–STD-006** — verified in §1; no Engineering Artifact is ever a content source, only a governed subject.
- ✅ **Technology Independent** — no language, framework, database, API, or deployment concept appears anywhere (§11, §14).
- ✅ **Governs Engineering Artifact Evolution** — §5–§9 cover artifact states, versioning, compatibility, synchronization, and supersession for every family this lineage produces.
- ✅ **Suitable for Standards Review Board Approval.**

> **STD-007 is the authoritative lifecycle standard for Engineering Artifacts within the Engineering Intelligence Operating System methodology.**

---

*End of STD-007, Version 1.0 (Draft).*
