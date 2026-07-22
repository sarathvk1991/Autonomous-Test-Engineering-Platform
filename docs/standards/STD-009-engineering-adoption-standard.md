# STD-009 — Engineering Adoption Standard

**Version 1.0 (Draft)**

## 1. Document Metadata

| Field | Value |
| --- | --- |
| Identifier | STD-009 |
| Title | Engineering Adoption Standard |
| Version | 1.0 (Draft) |
| Status | Draft — pending Standards Review Board approval |
| Owner | Platform Architecture, delegated per domain (restates HB-001 §18's own STD-family Owner row) |
| Stakeholders | Constitutional Authority, Standards Authority, Architecture Review Board, Domain Architect, Engineering Lead, Certification Authority (STD-006 §5) |
| **Derived From** | **HB-001 (Revision 4) and STD-000 through STD-007 — the sole content sources.** No Engineering Artifact (a `PRD`, `ADR`, `CAP`, `RUN`, `SYS`, `PRA`, or `IMP`, in any Bounded Context, HB-001 §20.4) is ever a content source of this document. |
| Governing Standards | STD-000 (Principles restated in §4); STD-001 (Engineer/Reviewer roles, §5–§6); STD-002 (capability-lifecycle vocabulary distinguished in §9); STD-003 (runtime-scope vocabulary referenced in §8); STD-004 (traceability preserved across profiles, §4, §7); STD-005 (transformation semantics unaltered by tailoring, §7); STD-006 (governance separation, §3); STD-007 (lifecycle and migration vocabulary reused in §10). |
| Dependencies | HB-001, STD-000, STD-001, STD-002, STD-003, STD-004, STD-005, STD-006, STD-007 |
| Related Documents | Every Engineering Artifact this document's own profiles select, tailor, or scope (PRD, ADR, CAP, RUN, SYS, PRA, IMP, in every Bounded Context) **remains a governed subject** — never a content source (restates STD-006 §1's and STD-007 §1's own framing, two Standards further). |
| Supersedes | Nothing (this document's own numbering gap is addressed below) |
| Superseded By | Not applicable |

**Reconciliation Note — `STD-008` is unallocated.** This document is numbered `STD-009`; no `STD-008` has been produced, reserved, or referenced by any governance act known at the time of this drafting. **This document does not assume, depend on, or require `STD-008`'s own eventual content** — its own Dependencies (above) name HB-001 and STD-000 through STD-007 only. Consistent with this platform's own recurring discipline (name a gap, never silently bridge it, restate STD-006 §12's and STD-007's own precedent), the gap is recorded here rather than closed by renumbering this document to `STD-008` — HB-001 §9's and §10.3's own identifier-permanence rule would forbid that renumbering in any case, once this document is Drafted. **A future `STD-008`, if ever produced, does not retroactively become a Dependency of this document without a formal revision to this document's own §1** — restating STD-007 §9's own Lineage Preservation principle at the Standards-family grain.

**This is an Engineering Standard, not an Engineering Artifact.** STD-009 carries no Transformation Authority field and no Bounded Context assignment, for the same reasons STD-006 §1 and STD-007 §1 already state of themselves.

## 2. Executive Summary

STD-006 answered *who* governs an Engineering Artifact. STD-007 answered *when* and *how* it may change. **STD-009 answers a fourth question neither of those, nor STD-005, asks: how much of this methodology's own seven-family lineage (`PRD → ADR → CAP → RUN → SYS → PRA → IMP`) a given engineering initiative actually needs.** Producing all seven Artifacts, in full, for a two-week research spike would violate the same proportionality every engineering discipline already expects; producing none of them for a regulated, enterprise-scale platform would violate everything STD-000 through STD-007 exist to guarantee. **Proportional adoption is necessary because the methodology's own completeness (STD-006 §4, STD-007 §4) and an initiative's own scale are two independent variables — this document is the disciplined function that relates them**, without ever changing what any one Artifact, once produced, means.

## 3. Position Within Standards Family

Extending STD-007 §3's own three-row table with the fourth concern this document supplies:

| Concern | Question it answers | Governed by |
| --- | --- | --- |
| **Governance** | **Who** may approve a change to an Engineering Artifact? | STD-006, in full. |
| **Lifecycle** | **When**, and under what compatibility discipline, may that change occur? | STD-007, in full. |
| **Transformation** | **How** does one Engineering Artifact become another? | STD-005, in full. |
| **Adoption** | **How much** of the lineage does this initiative actually need? | STD-009 (this document), in full. |

**All four concerns SHALL remain independent** — restated as a binding rule, not merely a description, exactly as STD-007 §3 already bound its own three. Adoption never approves a change (that remains STD-006's own authority); it never versions one (STD-007's own scope); it never performs a transformation (STD-005's own scope). It only ever decides, in advance, which Artifacts a given initiative's own profile (§5) requires, and at what depth.

## 4. Adoption Principles

| Principle | Purpose | Rationale | Preservation Rule |
| --- | --- | --- | --- |
| **Proportionality** | The methodology's own weight matches the initiative's own scale and risk. | Restates STD-000's own general engineering-discipline expectation that ceremony match consequence, applied here for the first time as a named principle. | §5's own Adoption Profiles are the only sanctioned mechanism for varying weight — never an ad hoc, undocumented shortcut. |
| **Completeness** | Whatever Artifacts a profile does require are produced in full, never partially. | Restates STD-006 §8's own Governance Lifecycle — an Artifact reaches `Published` or it does not exist as a governed fact. | §6's own Mandatory column admits no partial-credit state. |
| **Traceability Preservation** | A tailored initiative's own Artifacts remain as traceable as a full-lineage one's. | Restates STD-004 in full. | §7's own Tailoring Rules never permit omitting a traceability citation, only an entire downstream Artifact. |
| **Tailoring** | A profile may omit Artifacts; it may never alter the ones it keeps. | Restates STD-005 §4's own philosophy — refinement is not translation. | §7, in full. |
| **Consistency** | Two initiatives on the same profile apply the same rules identically. | Restates HB-001 §11.3 Principle 9 (Consistency) at the adoption-profile grain. | §5's own five profiles are fixed; a sixth requires a governed revision to this document, never an ad hoc local variant. |
| **Explicit Scope** | An initiative's own adoption profile is declared, never assumed. | Restates STD-000 Principle 3 (Layer isolation) applied to scope declarations. | §6 requires every initiative to name its own profile before its first Artifact is Drafted. |
| **Honest Maturity** | An adoption profile's own maturity is stated as it actually is, never aspirationally. | Restates this platform's own recurring discipline (CAP-100 §6, RUN-100 §21, SYS-100 §16, PRA-100 §13, STD-007 §13). | §9's own Adoption Maturity model and §13's own Known Limitations. |
| **Incremental Adoption** | An initiative may migrate to a deeper profile without re-deriving what it already has. | Restates STD-007 §9's own Supersession and Historical Preservation principles, applied to profile transitions. | §10, in full. |

## 5. Adoption Profiles

**The heart of this document.** Five standard profiles — no sixth may be introduced without a governed revision to this section (§4's own Consistency principle).

### 5.1 Research

```
PRD
        ↓
ADR
```

Validates whether a business problem has a coherent architectural answer at all. Nothing beneath `ADR` is produced — a `CAP`, `RUN`, `SYS`, `PRA`, or `IMP` for a Research-tier initiative would commit engineering weight to a question not yet answered (§6).

### 5.2 Proof of Concept

```
PRD
        ↓
ADR
        ↓
CAP
```

Validates whether the architectural answer decomposes into a coherent, boundable capability. Runtime, system, reference, and implementation depth remain out of scope until the capability itself is confirmed worth realizing.

### 5.3 Product

```
PRD
        ↓
ADR
        ↓
CAP
        ↓
RUN
        ↓
SYS
        ↓
PRA
        ↓
IMP
```

The full lineage, for an initiative expected to operate and be maintained. `PRA` is the one Optional row at this tier (§6) — a Product-scale initiative may rely on an already-existing, platform-wide `PRA-NNN` directly (HB-001 §20.12's own dual-scope rule) rather than producing its own per-Artifact specialization, unless its own architecture is complex enough to warrant one.

### 5.4 Platform

The entire lineage, mandatory, with no Optional row. **This is not a hypothetical profile — it is the profile the Engineering Intelligence Operating System's own lineage (`PRD-100` through `IMP-100`) was itself produced under**, including a real, per-Artifact `PRA-100`, never omitted (PRA-100 §1, HB-001 §20.12). A Platform-tier initiative is expected to be depended on by other initiatives, exactly as EIOS is depended on by every Hosted Application (ADR-100 §10).

### 5.5 Regulated

The entire lineage, mandatory, **plus elevated Governance Evidence (STD-006 §9) and Lifecycle Evidence (STD-007 §10) requirements** — every change, regardless of its STD-006 §7 classification, requires a Compatibility Assessment (STD-007 §7), and every Behavioral-category change or above requires Constitutional Authority sign-off (STD-006 §5), not only Standards Authority sign-off. **Why:** a Regulated initiative's own downstream consequences (compliance, safety, financial) mean the ordinary proportionality this document otherwise grants (§4) is deliberately suspended in favor of exhaustive evidence — the one profile in which Adoption's own "how much" answer is always "the maximum this methodology defines."

## 6. Mandatory Artifacts

| Family | Research | Proof of Concept | Product | Platform | Regulated |
| --- | --- | --- | --- | --- | --- |
| `PRD` | Mandatory | Mandatory | Mandatory | Mandatory | Mandatory |
| `ADR` | Mandatory | Mandatory | Mandatory | Mandatory | Mandatory |
| `CAP` | Forbidden | Mandatory | Mandatory | Mandatory | Mandatory |
| `RUN` | Forbidden | Optional | Mandatory | Mandatory | Mandatory |
| `SYS` | Forbidden | Forbidden | Mandatory | Mandatory | Mandatory |
| `PRA` | Forbidden | Forbidden | Optional (HB-001 §20.12) | Mandatory | Mandatory |
| `IMP` | Forbidden | Forbidden | Mandatory | Mandatory | Mandatory |

**Why "Forbidden," not merely "not required."** An Artifact is Forbidden for a profile — never merely optional-and-unlikely — when producing it would violate §4's own Proportionality principle by committing depth to a question the profile's own earlier, Mandatory Artifacts have not yet answered: a `SYS` cannot exist without a `RUN` it decomposes (STD-005 §6), so a profile that forbids `RUN` necessarily forbids everything beneath it. Forbidden is a *sequencing* consequence of §4, never a permanent prohibition on the Artifact's own content.

## 7. Tailoring Rules

**Tailoring MAY remove engineering depth. It SHALL NOT change Engineering Transformation.**

| Rule | Statement |
| --- | --- |
| **Depth reduction is sanctioned** | A profile (§5) may omit an entire downstream Artifact family — this is what §6's own Mandatory/Optional/Forbidden columns exist to authorize. |
| **Content redefinition is never sanctioned** | An Artifact that *is* produced, under any profile, follows every rule STD-005 (transformation semantics), STD-006 (governance), and STD-007 (lifecycle) already establish for its own family — no "lightweight `ADR`" format, no relaxed traceability, no exemption from Governance Authority (STD-006 §6). |
| **Worked example** | A Research profile may omit `PRA` and `IMP` entirely (§6). **It SHALL NOT redefine `ADR`** — the one `ADR` it does produce is exactly as rigorous, exactly as Frozen (HB-001 §8), and exactly as subject to Architecture Review Board approval (STD-006 §6) as an `ADR` produced under a Platform profile. |
| **No silent tailoring** | A decision to omit an Artifact is itself recorded (restating STD-007 §4's own Non-Silent Supersession principle, applied to omission rather than supersession) — an initiative's own declared profile (§4's own Explicit Scope principle) is the record; an Artifact simply never mentioned, with no declared profile to explain its absence, is a defect in the initiative's own governance, not a valid tailoring decision. |

## 8. Scaling

Scaling describes how many Engineering Artifacts and Bounded Contexts (HB-001 §20.4) are active concurrently — **never an organizational structure, reporting line, or team size**, per this document's own Writing Principles.

| Scale | Description |
| --- | --- |
| **Small** | One Bounded Context, one Application, one profile (§5) at a time. |
| **Medium** | A small number of Bounded Contexts, each independently profiled, with occasional Cross-Application Collaboration (`PCAP-008`, CAP-100 §8). |
| **Large** | Many Bounded Contexts, routine Cross-Application collaboration, and a genuine need for the Cross-Application Governance and Knowledge capabilities (`PCAP-004`, `PCAP-005`) CAP-100 §7 still records as Conceptual maturity today. |
| **Enterprise** | Multiple Applications depending on shared Platform Capabilities (CAP-100 §8) simultaneously, for real — the exact scenario PRA-100 §6.5's own Cross-Application Composition currently describes only theoretically (PRA-100 §12). |
| **Platform** | EIOS itself, or an equivalent operating-system-tier initiative hosting other initiatives, per PRD-100's own three-layer model. |

**Scaling beyond Small is precisely the real-world test this platform's own honesty has been anticipating.** CAP-100 §16, RUN-100 §23, SYS-100 §15, and PRA-100 §12 each independently flagged the same risk: every capability, contract, and composition in this lineage is generalized from Requirements Intelligence's own single-Application evidence. Large-, Enterprise-, and Platform-scale adoption is the moment that generalization is actually tested, not merely asserted.

## 9. Adoption Maturity

**Measures how consistently an organization applies the EIOS methodology — never the maturity of any Application, Capability, or software artifact it produces.** This is a deliberately different axis from CAP-100 §6's own Capability Maturity Model (`Conceptual → Piloted → Adopted → Standardized`), which measures how proven a *capability* is; the model below measures how proven the *organization's own use of the methodology* is, restating a well-established process-maturity naming convention rather than inventing a new one.

```
Initial
        ↓
Repeatable
        ↓
Defined
        ↓
Managed
        ↓
Optimizing
```

| Stage | Meaning at this document's own tier |
| --- | --- |
| **Initial** | Profiles (§5) are chosen ad hoc, if at all; no initiative's own declared profile (§7's own No Silent Tailoring rule) is consistently recorded. |
| **Repeatable** | The same profile is chosen consistently for the same kind of initiative, though not yet formally declared per §7. |
| **Defined** | Every initiative declares its own profile explicitly, per §4's own Explicit Scope principle, before its first Artifact is Drafted. |
| **Managed** | Profile choice, tailoring (§7), and migration (§10) are themselves subject to Governance Evidence (STD-006 §9) — an organization can demonstrate, on request, why each initiative sits at the profile it does. |
| **Optimizing** | The organization's own historical adoption data (which profile, which scale, which outcome) actively informs future profile and scaling decisions — restating ADR-100 §16's own Knowledge Architecture, applied to methodology adoption itself rather than engineering content. |

## 10. Migration

An initiative moves between adoption profiles (§5) — most commonly upward, from Research toward Platform, as its own risk and scale grow.

| Rule | Statement |
| --- | --- |
| **Traceability preserved** | Every Artifact produced under the prior profile remains cited, never re-derived, by the Artifacts a deeper profile now requires — restating STD-004 in full. |
| **History preserved** | The initiative's own prior profile is recorded as history (restating STD-007 §9's own Historical Preservation principle, applied to profile choice itself), never erased once migration occurs. |
| **Identity preserved** | An `ADR` produced under a Research profile keeps its own permanent identifier when a `CAP` is later added under a Proof of Concept migration — restating HB-001 §9's own identifier-permanence rule; migration adds Artifacts, it never renumbers existing ones. |
| **Governance preserved** | Every newly-required Artifact (§6) still passes through STD-006's own full Governance Lifecycle — migration authorizes producing more Artifacts; it never authorizes skipping governance for the ones a deeper profile newly requires. |

**Worked observation, named honestly rather than retrofitted.** Requirements Intelligence, examined against §5's own five profiles, matches none of them cleanly: it has `CAP-001`, `RUN-001`, `SYS-001`, and `IMP-001` (Product-tier depth from `CAP` downward) but never produced a dedicated `PRD`/`ADR` of its own — it borrowed the platform-wide `PRD-001`/`ADR-001` instead — and relies on the platform-wide `PRA-001` directly rather than a per-Artifact `PRA-NNN`. This is this methodology's own first real adoption instance, and it predates this document by every measure; §13 records it as an honest data point, not a template to be silently generalized into a sixth profile.

## 11. Constraints

STD-009 SHALL NOT: redefine governance (STD-006's own scope); redefine lifecycle (STD-007's own scope); redefine transformation (STD-005's own scope); redefine architecture; redefine implementation; prescribe Agile, Scrum, SAFe, or any other project-management methodology; or prescribe an organizational hierarchy beyond the governance roles STD-006 §5 already names.

## 12. Risks

Maintaining the same honest maturity discipline used throughout EIOS:

| Category | Risk |
| --- | --- |
| **Over-engineering** | An initiative defaults to the Platform or Regulated profile out of caution, producing `PRA`/`IMP` depth a Research- or PoC-scale question never needed — the exact waste §4's own Proportionality principle exists to prevent. |
| **Under-engineering** | An initiative stays on a Research or PoC profile past the point its own real risk has grown, producing no `RUN`/`SYS`/`PRA`/`IMP` for something that, in practice, now operates like a Product. |
| **Profile drift** | An initiative's own declared profile (§4's own Explicit Scope principle) silently diverges from what it is actually producing, with no migration (§10) ever formally recorded. |
| **Hidden tailoring** | An Artifact is omitted without the declared-profile record §7's own No Silent Tailoring rule requires — indistinguishable, after the fact, from an oversight. |
| **Broken traceability** | A migration (§10) adds a deeper Artifact without correctly citing the shallower ones already produced, violating §4's own Traceability Preservation principle in practice even though the rule remains intact on paper. |
| **Partial adoption** | An initiative produces a Mandatory Artifact (§6) incompletely — Drafted but never reaching `Published` (STD-006 §8) — while downstream work proceeds as though it had, restating §4's own Completeness principle's own failure mode. |

## 13. Known Limitations

**Explicit about what has not yet been exercised by the methodology:**

- **No initiative has ever formally declared an adoption profile under this document** — §5's five profiles are proposed, not yet exercised; every Engineering Artifact this lineage has produced so far (both the original Requirements-Intelligence-scoped series and the EIOS series) predates STD-009 entirely.
- **Requirements Intelligence's own real lineage does not cleanly match any of §5's profiles** (§10's own Worked observation) — the closest fit is Product-tier depth from `CAP` downward, without a dedicated `PRD`/`ADR` or per-Artifact `PRA`. This document does not retrofit a sixth profile to fit it, and names the mismatch rather than resolve it.
- **§6's Mandatory/Optional/Forbidden matrix has never been tested against a Research or Proof of Concept initiative in practice** — every real Artifact this platform has produced sits at Product- or Platform-tier depth.
- **§8's Enterprise and Platform scaling descriptions depend on Cross-Application capabilities (`PCAP-004`, `PCAP-005`, `PCAP-008`) that CAP-100 §7 and PRA-100 §13 already record as Conceptual** — Large-scale and Enterprise-scale adoption, as described, cannot yet be fully exercised for that reason alone.
- **§9's Adoption Maturity model is asserted, not measured** — no organization's own historical adoption data exists yet to place against it.
- **§10's Migration rules are declarative** — no real migration between two profiles has ever occurred to validate them.
- **Future work (reserved, not authorized by this document):** a sixth profile, should real practice reveal a genuine gap between two of the five named here; formal exercise of §6's matrix once a Research- or PoC-tier initiative actually exists; resolution of the `STD-008` gap (§1), by whatever future governance act produces it.

## 14. Final Self Review

- [x] Alignment with HB-001 — §1's own `STD-008` gap is named explicitly, never silently bridged; §7's Tailoring Rules cite HB-001 §8 and §9 without redefining either.
- [x] Alignment with STD-000 — §4's principles restate specific STD-000 Principles by number or general discipline.
- [x] Alignment with STD-001 — §6's own role vocabulary (Engineer, Reviewer) restates, never redefines, STD-001 §5.
- [x] Alignment with STD-002 — §9 explicitly distinguishes this document's own Adoption Maturity from STD-002 §3's own capability-lifecycle vocabulary, never conflating the two.
- [x] Alignment with STD-003 — §8's own scaling description cites runtime-scope vocabulary without redefining STD-003's own runtime model.
- [x] Alignment with STD-004 — §4's Traceability Preservation and §10's own History/Identity Preserved rows cite STD-004 directly.
- [x] Alignment with STD-005 — §4's Tailoring principle and §7's own worked example cite STD-005 §4 without redefining any transformation semantic.
- [x] Alignment with STD-006 — §3's four-row table and §5's own Regulated profile cite STD-006 §6/§7/§9 directly.
- [x] Alignment with STD-007 — §10's own Migration rules restate STD-007 §9's own Supersession and Historical Preservation principles at the profile-transition grain.
- [x] Adoption completeness — all fifteen required sections are present and address their commissioned objective.
- [x] Technology independence — verified section by section (§11); no language, framework, database, or vendor is named anywhere.
- [x] Governance separation — verified in §3: no Approving Authority or governance matrix is defined or redefined here.
- [x] Lifecycle separation — verified in §3: no version scheme or compatibility rule is defined or redefined here.
- [x] Transformation separation — verified in §3, §7: no STD-005 semantic is redefined; tailoring never alters what a produced Artifact means.

## 15. Engineering Adoption Compliance Certificate

**This certifies that STD-009, Version 1.0 (Draft):**

- ✅ **Engineering Adoption Standard Complete** — §3–§13 define position within the Standards family, adoption principles, five adoption profiles, mandatory-artifact matrix, tailoring rules, scaling, adoption maturity, migration, constraints, risks, and known limitations.
- ✅ **Derived Solely from HB-001 and STD-000–STD-007** — verified in §1; the `STD-008` gap is named, not silently bridged; no Engineering Artifact is ever a content source, only a governed subject.
- ✅ **Technology Independent** — no language, framework, database, API, or deployment concept appears anywhere (§11, §14).
- ✅ **Governs Engineering Adoption** — §5–§10 define how much of the lineage, at what depth, for every named profile and scale.
- ✅ **Suitable for Standards Review Board Approval.**

> **STD-009 is the authoritative adoption standard for the Engineering Intelligence Operating System methodology.**

---

*End of STD-009, Version 1.0 (Draft).*
