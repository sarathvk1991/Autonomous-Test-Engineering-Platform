# ADR-0049 — Engineering Constitution

- **Status:** Accepted
- **Date:** 2026-08-13
- **Supersedes:** nothing directly. ADR-0020 ("Platform Evolution Roadmap & Architectural
  Constitution") is already **Superseded by ADR-0031** for its layer/lifecycle content;
  that supersession is unchanged and unrepeated here. This ADR instead takes over
  ADR-0020's other, un-superseded role — the platform's single cited **constitutional**
  authority for principles and rules — a role ADR-0031 never claimed (ADR-0031 §D3
  redesignates capabilities and layers; it says nothing about *principles*). **Amends:**
  nothing. **Ratifies:** ADR-0021, ADR-0024, ADR-0025, ADR-0026, ADR-0028 — each still
  **Status: Proposed** at the time of this ADR, each named individually and ratified by
  declaration, not by editing their own text (D2).
- **Governing design:** none — this ADR *is* the governing design, exactly as ADR-0020,
  ADR-0021, ADR-0024, ADR-0025, ADR-0026, ADR-0028, ADR-0031, and ADR-0038 each introduce
  no proposal document because none of them is subsystem architecture.
- **Depends on:** ADR-0038 (Documentation Track Governance, Accepted — the ADR that makes
  `docs/adr/` Track A normative and `docs/standards/` Track B non-normative; this ADR's
  own authority position is defined against ADR-0038's rule, D1); ADR-0031 (Authoritative
  Layer Model, Accepted — the platform's *current* seven-layer catalogue; consulted so
  this ADR's account of the ratified lineage's own layer terminology is accurate, D2);
  ADR-0020 (Superseded by ADR-0031 — the original, single-document constitution whose
  abandoned principles role this ADR assumes); the ratified lineage itself, ADR-0021/
  ADR-0024/ADR-0025/ADR-0026/ADR-0028 (D2); the four live Layer 2 capabilities built on
  that lineage, ADR-0022/ADR-0023/ADR-0027/ADR-0029 (all Accepted, live — the standing
  gap this ADR closes, D2); `docs/standards/STD-000-platform-constitution.md` (Track B,
  non-normative, Draft — cited here only as raw material for D3's articles, per STD-000
  §7.1's own observational-reference allowance, never as this ADR's authority, D1).
- **Runtime status:** Not applicable. This is a **documentation-only, governance-authority
  milestone**: no code, model, policy, `PlatformContext` method, Execution Package field,
  serializer, CLI change, or version-number change (Architecture, Platform, or otherwise).
  The gate-citation mechanism this ADR adopts (D4) is the doc-level mapping already
  pervasive in module docstrings across the repository; no runtime/code citation field is
  populated by this ADR — `CP1CriterionMetadata.documentation_reference` remains reserved
  and unpopulated (D4), exactly as it was before this ADR.

## Problem

Mentor feedback item #5 (`docs/architecture/mentor-feedback-scoping.md`, Item 5, and its
own design-surfacing follow-up) named a real governance gap, verified directly against
the repository rather than assumed from the feedback's own framing:

**The platform's constitutional authority is fragmented across nine documents, and none
of them is currently citable as Track-A authority by the gates that would need to cite
it.** ADR-0020 ("Platform Evolution Roadmap & **Architectural Constitution**") was the
platform's original single constitution — its own text calls itself exactly that. It is
now **Superseded by ADR-0031** for its layer/lifecycle content, but its principles content
was never re-homed anywhere: ADR-0031 redesignates capabilities and layers (§D3) and says
nothing about the Vision/Mission/Philosophy content ADR-0020 also carried. Beyond it, a
five-document constitutional-tier lineage exists — ADR-0021 (Cross-Execution Data
Architecture & Historical Intelligence Constitution), ADR-0024 (Historical Dataset &
Historical Truth Constitution), ADR-0025 (Derived Knowledge Architecture & Layer 2
Constitution), ADR-0026 (Organizational Knowledge Architecture & Learning Constitution),
and ADR-0028 (Learning Constitution) — **every one of them still `Status: Proposed`**,
verified directly against each ADR's own header, unchanged as of this ADR's date. Yet the
four live capabilities built directly on that lineage — ADR-0022 (Continuous Improvement),
ADR-0023 (Knowledge Graph), ADR-0027 (Organizational Memory), ADR-0029 (Learning
Framework) — are each `Status: Accepted`, **live**, wired into the running pipeline,
verified directly against each ADR's own header. The platform runs real, Accepted,
released capabilities on a constitutional foundation that has never itself been formally
Accepted.

Separately, `docs/standards/STD-000-platform-constitution.md` is an actual document
titled "Platform Constitution" — but STD-000 §6 states plainly it does **not** occupy
HB-001 §5's Platform Constitution tier (that tier is realized by the ADR lineage above);
STD-000 occupies the Standards tier, "the Standards family's own constitutional member."
STD-000 §7.1 makes the structural consequence explicit: STD-000 is inherited as an
authority dependency by Capabilities/Runtime/Certification documents, but **never by
Architecture or Governance** — "neither may cite STD-000 as the source of its own
legitimacy." Every deterministic gate checked in this platform
(`requirement_intelligence/cp1/criteria/engineering_input_availability.py`,
`suite_quality_governance/cp7/rating_gate.py`, and every other criterion inspected this
session) is governed by an ADR at the Architecture tier, cited by section in its own
module docstring — never by a Standards-tier document. Promoting STD-000 into Track A
(ADR-0038's normative track) would make it a normative Standards document, not a
Platform-Constitution-tier one; HB-001's own dependency matrix (restated at STD-000
§7.1) still forbids an ADR from citing a Standards document as authority. **Only a
document that itself sits at the Architecture tier — a new Track-A ADR — can be cited as
authority by the gates' own governing ADRs without contradicting that matrix.** This is
the structurally-forced answer the mentor scoping doc's own design-surfacing note named
"Option B," and the reason this ADR exists rather than an STD-000 promotion.

The citation mechanism itself was checked directly, not assumed. Two readings exist:
**(i) documentation mapping** — already real and pervasive: every checked criterion/gate
names its governing ADR (often a specific decision letter) in its own module docstring.
**(ii) runtime/code citation** — not built: `CP1CriterionMetadata`
(`requirement_intelligence/cp1/framework/criterion_metadata.py`) carries a
`documentation_reference` field whose own docstring labels it "Reserved... has no
behaviour today," and no criterion sets it. This ADR adopts (i) as the citation
mechanism it establishes and leaves (ii) explicit future work (D4).

**Motivation.** Nitin (one mentor) raised a centralized constitution in both rounds of
his feedback — the item's own consensus signal was scored highest among the eight items
assessed. The specific citation-shape/authority nuance this ADR resolves (Option A vs. B
vs. C) was **not itself put to Nitin** — the scoping note that sharpened it to Option B
was written after his rounds of feedback closed. This ADR is written to the
structurally-forced Option B answer; if Nitin's own picture of "every gate cites its
article" differs from the doc-mapping reading adopted here, this ADR is adjustable, not
final by mentor confirmation.

## Decision

1. **Establish** the Engineering Constitution (this ADR) as the platform's single,
   Track-A, top-tier normative authority for engineering principles and rules (D1).
2. **Ratify** the constitutional-tier lineage — ADR-0021, ADR-0024, ADR-0025, ADR-0026,
   ADR-0028 — closing the gap between their `Proposed` status and the `Accepted`, live
   capabilities built on them (D2).
3. **State** twelve normative Articles, each grounded in a real, already-enforced
   platform invariant — not an aspiration (D3).
4. **Adopt** documentation-level gate citation as the mechanism satisfying "every gate
   cites its article," and name runtime citation as explicit, additive future work (D4).

---

## D1 — Establishing Track-A authority, and why STD-000 could not be it

This ADR is filed at `docs/adr/`, Track A per ADR-0038's own decision: "Track A is
normative. It governs the real, implemented platform and is the sole authority any
future ADR, ticket, or design document defers to for architecture decisions." Track A
sits, by ADR-0038's own precedence rule, above Track B (`docs/product/`, `docs/handbook/`,
`docs/standards/` — declared non-normative and frozen). Within Track A, this ADR occupies
the position ADR-0020 vacated when ADR-0031 superseded it: the platform's cited authority
for **engineering principles**, sitting above every subsystem ADR the way HB-001 §5's
own documentation hierarchy places "Platform Constitution" above "Architecture."

**Why STD-000 structurally cannot occupy this position (confirmed directly from its own
text, not inferred).** STD-000 §6 states its own tier explicitly: "STD-000 itself
occupies the **Standards** tier of this hierarchy... it is not the Platform Constitution
tier's own document family." STD-000 §7.1 states the consequence explicitly: "STD-000 is
never inherited, as an authority dependency, by Architecture or Governance... neither may
cite STD-000 as the *source* of its own legitimacy." Promoting STD-000 into Track A (the
alternative "Option A" the mentor scoping note considered) would not change this —
Track A/B is a documentation-normativeness axis (ADR-0038); HB-001's Constitution →
Architecture → Governance → **Standards** → Capabilities → Runtime → Certification tier
axis (STD-000 §6) is a different, orthogonal axis that ADR-0038 does not touch and this
ADR does not touch either. A promoted STD-000 would still be a Standards-tier document;
the gates' own *governing ADRs* (Architecture tier) still could not cite it as authority
without inverting HB-001 §13's matrix. Only a new Architecture-tier (Track-A ADR)
document can be cited as authority by another Architecture-tier document. This ADR is
that document.

**STD-000 as raw material, not authority (the one relationship it is permitted to have
with this ADR).** STD-000 §7.1 permits exactly one direction of reference: "An ADR...
may reference STD-000 for reader convenience... to note that a decision is consistent
with a principle STD-000 restates — but neither may cite STD-000 as the *source* of its
own legitimacy." D3's Articles draw on STD-000 §3 (seven Philosophy statements) and §4
(ten Constitutional Principles) as source material — several Articles below restate a
STD-000 principle in Track-A normative language — but every Article's own authority
citation is to the ADR or the code that already enforces it, never to STD-000 itself.
STD-000 stays exactly where ADR-0038 and its own §6 already place it: Track B,
non-normative, frozen, Draft. This ADR does not amend, promote, or ratify STD-000.

## D2 — Ratifying the constitutional lineage

Each of the five lineage ADRs is named individually, per the family's own convention for
naming what is depended on (every lineage ADR's own header already does this for the ADR
below it):

- **ADR-0021 — Cross-Execution Data Architecture & Historical Intelligence
  Constitution.** Establishes the three-level Truth Hierarchy — Runtime Truth → Historical
  Truth → Derived Knowledge — permanent, one-directional, never merged (§Stage 3);
  execution immutability (§Stage 4); append-only Historical Truth (§Stage 5); Historical
  Dataset ownership (§Stage 6); the rule that every future Layer 2+ capability must
  declare which Truth Hierarchy level it consumes and produces (§Stage 13,
  Recommendation 11).
- **ADR-0024 — Historical Dataset & Historical Truth Constitution.** Elevates the
  Historical Dataset Resolution Principle (`HistoricalDatasetReference` → private,
  replaceable, storage-independent provider → `HistoricalDataset`) from a pattern two
  capabilities (ADR-0022, ADR-0023) independently discovered into a single, citable
  constitutional rule (§Stage 5); freezes storage independence (§Stage 6) and replay
  determinism (§Stage 7).
- **ADR-0025 — Derived Knowledge Architecture & Layer 2 Constitution.** Defines Derived
  Knowledge — deterministic, reproducible, immutable, computed exclusively from Historical
  Truth, never from Runtime Truth directly and never from another Derived Knowledge object
  (§Stage 1); freezes peer independence — no capability at the same tier consumes another's
  output without a deliberate, explicit future ADR (§Stage 7); freezes the fan-out/fan-in
  dependency graph (§Stage 8).
- **ADR-0026 — Organizational Knowledge Architecture & Learning Constitution.** Defines
  Organizational Knowledge as curated, immutable, derived exclusively from Derived
  Knowledge (§Stage 1); freezes the knowledge maturity ladder (Observed → Repeated →
  Verified → Institutionalized → Retired, §Stage 3) and the promotion-not-rewrite
  discipline (§Stage 6).
- **ADR-0028 — Learning Constitution.** Defines Learning as the creation of reusable
  organizational understanding, computed exclusively from Organizational Knowledge
  (§Stage 1/2); freezes Learning Validation's six gates (§Stage 6) and the full lineage
  chain back to Runtime Truth (§Stage 10); names Learning the sole sanctioned Layer 2 →
  Layer 3 bridge (§Stage 16, Recommendation 19).

**The gap this closes.** Each of these five is, as of this ADR's date, `Status:
Proposed` — verified directly against each header, not assumed from the mentor scoping
note. Each of the four capabilities built directly against this lineage — ADR-0022
(Continuous Improvement), ADR-0023 (Knowledge Graph), ADR-0027 (Organizational Memory),
ADR-0029 (Learning Framework) — is `Status: Accepted`, live, verified directly against
each header (ADR-0022's own live pipeline wiring: `run_continuous_improvement_phase`;
ADR-0029's: "Layer 2... is now fully operational end to end"). Each of the five lineage
ADRs' own closing "Governance" line already states its own acceptance condition
verbatim, e.g. ADR-0021: "it becomes **Accepted** as CAP-083 and every subsequent Layer
2–7 capability is built under it without deviation." That condition is now satisfied —
CAP-083/084/085/086 (ADR-0022/0023/0027/0029) are each built, Accepted, and live,
without deviation from the lineage each cites. **This ADR ratifies the condition each
lineage ADR already set for itself: ADR-0021, ADR-0024, ADR-0025, ADR-0026, and ADR-0028
are, from this ADR forward, treated as ratified constitutional authority — cited by the
capabilities that already depend on them, and by this ADR — even though their own header
`Status` lines are not edited by this ADR (see the additive note below).**

**Why this ratification is declared, not enacted by editing five files (additive
discipline, per the family's own precedent).** The family's own convention for a status
change *is* to edit the affected document's own header — ADR-0031 §D3/Final Review item
2 states this precisely for ADR-0020: "its status line is updated to reflect this... its
body is left untouched as a historical record." That is the correct mechanism, and it is
recommended as an immediate follow-on to this ADR (Consequences), not performed inside
it — this ADR's own scope, per its brief, is the new document only, with matrix/register/
status-line edits flagged as follow-ons, mirroring exactly how ADR-0048 flagged its own
`CAP-088` matrix row and register entry as recommended-not-performed rather than
executing them in the same change. Until that follow-on lands, a reader encountering
ADR-0021/0024/0025/0026/0028's own header still reading `Proposed` should read this
ADR's D2 as the ratifying act, the same way ADR-0038 §D3 explains that a still-present,
unedited Track B document is understood as resolved by precedence without requiring its
own text to change.

**Honesty guard: the lineage's own "Layer 2" is ADR-0020's superseded numbering, not
today's.** Each lineage ADR calls itself part of "Layer 2 — Continuous Learning" — that
was ADR-0020's own layer catalogue. ADR-0031 (Accepted, the *current* Authoritative
Layer Model) fully superseded ADR-0020, and its own §D3 redesignates ADR-0020's Layer 2
capabilities (Continuous Improvement, Knowledge Graph, Organizational Memory, Learning
Framework — the same four ADR-0022/0023/0027/0029 capabilities this ADR discusses) as
**Layer 1 sub-capabilities** under the current model, not a distinct Layer 2 (today's
Layer 2 is Feature Engineering, a different capability that happens to share the number).
This ADR ratifies the lineage's **substantive constitutional content** — the Truth
Hierarchy, Historical Dataset Resolution Principle, Derived Knowledge/Organizational
Knowledge/Learning definitions — which is unaffected by which layer-numbering scheme the
capabilities are attached to (ADR-0031 §D3 changes designation only, explicitly touching
none of ADR-0021–0029's runtime contracts or constitutional rules). It does not ratify,
repeat, or correct the lineage's own superseded "Layer 2" self-labeling — a reader citing
this lineage today should cite ADR-0031 for current layer placement and the lineage ADRs
themselves (as ratified here) for the constitutional rules.

## D3 — Twelve normative Articles, each grounded in a real, enforced invariant

Each Article restates an invariant this platform already builds and enforces — verified
against the citing ADR and, where a runtime mechanism exists, the enforcing code, this
session. None is aspirational; where an Article's enforcement mechanism is structural
(a containment test, a model convention) rather than a runtime gate, that is stated
explicitly rather than implied to be a gate.

**Article I — Layer Isolation & Upward-Only Dependency.** A capability consumes only a
lower layer's completed, frozen runtime contract — never its internals, never in reverse,
never skipping an intermediate layer. *Grounded in:* ADR-0020 §Stage 3/5 (origin);
ADR-0031 Recommendation 1 (current authority); enforced structurally by the platform's
own containment tests, e.g. `tests/unit/test_traceability_graph.py::
TestScopeDiscipline::test_does_not_import_the_frozen_adr_0023_service` (verified this
session, ADR-0048 §D3), mirrored by ADR-0022 §D6/ADR-0023 §D6.

**Article II — The Truth Hierarchy.** Runtime Truth → Historical Truth → Derived
Knowledge is permanent, one-directional, and never merged; the chain extends to
Organizational Knowledge and Learned Knowledge at the tiers above it. *Grounded in:*
ADR-0021 §Stage 3 (ratified, D2); ADR-0025 §Stage 2, ADR-0026 §Stage 1, ADR-0028 §Stage 2
(the chain's upper extensions, also ratified, D2). Enforcement is architectural, not a
runtime gate: no engine in `continuous_improvement/`, `knowledge_graph/`,
`organizational_memory/`, or `learning/` writes back into a lower tier — verified as an
architectural claim in each subsystem's own ADR, not independently re-audited line by
line this session.

**Article III — Explicit, Versioned Runtime Contracts Are the Sole Integration
Mechanism.** Every capability crosses its boundary through exactly one named, versioned
`*Result` contract; a consumer never reaches past it into a producer's engine, policy, or
provider. *Grounded in:* ADR-0020 §Stage 6; STD-000 §3 "Explicit Contracts" (raw
material, not authority, D1); the platform-wide `*Result`/`*Policy`/`*Service` naming
and boundary convention verified across every subsystem inspected this session (CP1,
Continuous Improvement, Knowledge Graph, Traceability Graph).

**Article IV — Explainability.** A higher-order output must be explainable solely from
the lower, already-frozen contracts it consumed — no hidden inference, no unexplained
conclusion. *Grounded in:* ADR-0020 §Stage 7; the "at least one reference" discipline
first frozen at ADR-0019 §D7 and repeated, verified, at every tier of the ratified
lineage (ADR-0021 §Stage 8, ADR-0025 §Stage 5, ADR-0026 §Stage 9, ADR-0028 §Stage 10).

**Article V — Immutability & Promotion, Never Rewrite.** A fact or conclusion, once
produced, is never edited in place; a correction is a new object that references what it
supersedes. *Grounded in:* ADR-0021 §Stage 4/5, ADR-0024 §Stage 8, ADR-0025 §Stage 4/6,
ADR-0026 §Stage 3/6/7, ADR-0028 §Stage 11 (all ratified, D2). **Enforcement, stated
honestly:** this is a construction and testing discipline, not a Pydantic `frozen=True`
guarantee — a repository-wide check this session found no `ConfigDict(frozen=True)`
usage; immutability is upheld by the models' own lack of mutating methods and by each
subsystem's freeze-milestone tests, not by a language-level frozen flag.

**Article VI — Governance Precedes Intelligence.** Deterministic, governed reasoning is
built and frozen before probabilistic, ML, or LLM reasoning is layered on top of it, for
every capability, every layer. *Grounded in:* ADR-0020 §Stage 11 (Governance →
Determinism → Learning → Prediction → Optimization → Autonomy); ADR-0025 Recommendation
10; STD-000 §1 Vision/§2 Mission (raw material, D1).

**Article VII — Deterministic Gates Decide.** A release or pass/fail verdict is derived
by a single, deterministic, policy-governed engine; an LLM-authored assessment is
advisory only and never gates. *Grounded in:* ADR-0040's control-point rule ("LLM-judged
assessments... are advisory only, never gating"); `requirement_intelligence/
requirement_quality_governance/decision/quality_decision_engine.py`'s own docstring,
verified this session — "Sole owner of the decision (frozen, ADR-0017 Recommendation
2)... Only this engine derives `PASS`/`PASS_WITH_WARNINGS`/`FAIL`"; STD-000 §4 Principle
8 "Deterministic execution" (raw material, D1).

**Article VIII — Fail-Closed, Honestly-Reported Composition.** An unmeasured criterion
resolves to `WARN`, never a silently-passed `PASS` and never a fabricated `FAIL`; a
composite verdict is `FAIL` if any criterion is `FAIL`, else `WARN` if any is `WARN`,
else `PASS`. *Grounded in:* ADR-0012 §8 (origin, CP1's own composition rule);
`suite_quality_governance/cp7/rating_gate.py`, verified this session — its own docstring
cites "ADR-0047 D3's own amendment note... the identical 'unmeasured, never a fabricated
FAIL' treatment... the same governed aggregation rule `ValidationVerdictComposer`
already establishes (ADR-0012 §8)," and its code composes exactly `FAIL > WARN > PASS`.

**Article IX — Single Canonical Owner Per Responsibility.** Every fact, capability, and
document has exactly one accountable owner; no two capabilities compete for the same
responsibility or answer the same question. *Grounded in:* ADR-0001 (modular-monolith
boundary discipline); ADR-0020 §Stage 3; ADR-0025 §Stage 7/Recommendation 5 and §Stage 8
(Layer 2 peer independence, no-peer-coupling, ratified D2); ADR-0026 §Stage 10; STD-000
§4 Principles 2/4 (raw material, D1).

**Article X — Architecture Before Implementation.** A capability's architecture is
frozen — an Accepted, reviewed ADR — before its runtime is built; the seven-stage
capability lifecycle (Architecture Freeze → Deterministic Implementation → Runtime
Contract Freeze → Runtime Integration → Execution Package Integration → Golden
Rebaseline → Architecture Certification) is never skipped or reordered. *Grounded in:*
ADR-0020 §Stage 8; STD-000 §3 "Architecture First"/§4 Principle 1 (raw material, D1).
**Flagged as the one Article this platform has knowingly departed from once:** ADR-0048
(Traceability Graph) was built before its own architecture ADR was written, and ADR-0048
§D5 records that inversion, and the governance debt it created, explicitly rather than
silently — cited here as the platform's own precedent for how a departure from this
Article must be handled (recorded honestly, not hidden) if it recurs.

**Article XI — Reuse Before Regeneration.** An existing, catalogued, content-hash-
validated asset is preferred over generating a new one; generation is attempted only
when reuse's confidence, signature, or hash checks fail. *Grounded in:* ADR-0044 D3 (the
reuse-first catalog design); `automation_engineering/reuse/engine.py::
DEFAULT_CONFIDENCE_THRESHOLD = 0.75`, verified this session; ADR-0045's promotable-gate
discipline.

**Article XII — Bounded Autonomy, Human-Gated Escalation.** Automated remediation is
bounded, and a failure it cannot resolve within that bound routes to a human-reviewed
queue; nothing in this platform authorizes unbounded autonomous retry or autonomous
release. *Grounded in:* ADR-0040, verified this session — "Repair loops are bounded at a
maximum of **2 LLM remediation attempts**; on exhaustion, escalate to human-in-the-loop";
ADR-0045 D3's shared human-review queue for escalated promotions; ADR-0020 §Stage 11's
Autonomy-last ordering. This is also the constitutional grounding for mentor item #6
("human-controlled gate after failure analysis, no unbounded auto-remediate") — the
mentor's ask already matches a built, cited invariant, not a new one this ADR invents.

**Twelve, not more.** Nitin's own number was ~12; the twelve above are the invariants
this session verified as real and load-bearing across the ratified lineage and the live
gates. A thirteenth candidate — reuse-catalog *hygiene* (periodic pruning/auditing, as
opposed to Article XI's reuse-at-generation-time rule) — was considered and dropped: the
mentor scoping doc's own Item 1 sub-analysis found no such periodic mechanism exists,
which would make it an aspiration, not an enforced invariant, and this D3 admits only the
latter (guard, honesty guards below).

## D4 — Gate citation: documentation mapping now, runtime citation deferred

**Adopted mechanism: documentation-level citation, formalized, not newly invented.**
Every criterion/gate this session inspected already names its governing ADR (often a
specific decision letter) in its own module docstring — `engineering_input_availability.py`:
"governed by **ADR-0013 (Accepted)**"; `rating_gate.py`: "ADR-0047 D3's own amendment
note"; `quality_decision_engine.py`: "frozen, ADR-0017 §D23, Recommendation 2." This ADR
extends that already-pervasive pattern one level: a gate's docstring citation to its
governing ADR is, from this ADR forward, understood to also cite whichever Article (D3)
that governing ADR's own rule instantiates, by the mapping this D4 states rather than by
requiring every docstring to be individually rewritten:

| Article | Primarily instantiated by |
| --- | --- |
| I — Layer Isolation | ADR-0020/ADR-0031, every subsystem's containment tests |
| II — Truth Hierarchy | ADR-0021/0024/0025/0026/0028 (ratified, D2) |
| III — Runtime Contracts | ADR-0020 §Stage 6, every subsystem's `*Result` |
| IV — Explainability | ADR-0019 §D7 and its lineage-wide repetition |
| V — Immutability/Promotion | ADR-0021/0024/0025/0026/0028 (ratified, D2) |
| VI — Governance Precedes Intelligence | ADR-0020 §Stage 11 |
| VII — Deterministic Gates Decide | ADR-0040, ADR-0017 Recommendation 2 |
| VIII — Fail-Closed Composition | ADR-0012 §8, ADR-0047 D3/D5 |
| IX — Single Canonical Owner | ADR-0001, ADR-0020 §Stage 3, ADR-0025 §Stage 7 |
| X — Architecture Before Implementation | ADR-0020 §Stage 8 |
| XI — Reuse Before Regeneration | ADR-0044 D3, ADR-0045 |
| XII — Bounded Autonomy | ADR-0040, ADR-0045 D3 |

**What is not built here.** The *runtime/output* citation reading — an Article reference
appearing in a gate's own machine-readable output, not just its source docstring — is
not built by this ADR. `CP1CriterionMetadata.documentation_reference`
(`requirement_intelligence/cp1/framework/criterion_metadata.py`) remains exactly what it
was before this ADR: "Reserved... has no behaviour today," unset by every criterion. This
ADR does not populate it. A future, additive milestone may wire
`documentation_reference` to name a criterion's Article (and its governing ADR) in gate
output — small, layered on top of whichever of this D4's mapping already applies; it does
not change the mapping itself, and it is not authorized or scoped by this ADR.

---

## Consequences

- **A single, citable Track-A authority now exists for engineering principles** — the
  role ADR-0020 vacated when ADR-0031 superseded it, and the role STD-000 structurally
  could not fill (D1).
- **The 0021/0024/0025/0026/0028 governance-consistency gap is closed by declaration**
  (D2) — four live, Accepted capabilities (ADR-0022/0023/0027/0029) now stand on a
  ratified, not merely Proposed, constitutional foundation. **Not fully closed
  mechanically:** the five lineage ADRs' own header `Status` lines still read `Proposed`
  until a follow-on change edits them (recommended below), mirroring exactly how
  ADR-0031 edited ADR-0020's own status line "in the same change as this ADR's
  introduction" — that precedent is named here as the correct next step, not performed
  in this change (D2).
- **Twelve Articles are now the platform's cited normative rules** (D3), each traced to
  a real ADR and, wherever a runtime mechanism exists, real code verified this session —
  not an invented list.
- **Gate citation is formalized as a mapping, not a rewrite.** No gate's docstring was
  edited by this ADR; the D4 table is the citation layer, additive on top of what every
  gate already states about its own governing ADR.
- **STD-000's role is unchanged, not elevated.** It remains Track B, non-normative,
  frozen, Draft (ADR-0038, STD-000 §6) — cited by several Articles as raw material, cited
  by no Article as authority (D1, D3).
- **ADR-0020's status is unchanged, not repeated.** It remains Superseded by ADR-0031;
  this ADR does not re-supersede it, and does not touch ADR-0031's own layer/lifecycle
  content (D1).
- **Deferred, explicitly, not silently:**
  - The five lineage ADRs' own header status-line updates (D2) — recommended as an
    immediate, cheap, additive follow-on mirroring the ADR-0031→ADR-0020 precedent; not
    performed in this change.
  - A `docs/governance/platform-capability-matrix.md` entry and a
    `docs/architecture/architecture-baseline-v2.md` register row for this ADR —
    recommended, mirroring how ADR-0048 flagged its own `CAP-088` matrix row and register
    entry as follow-ons rather than performing them in the same change; not performed
    here.
  - Runtime/output gate citation (`CP1CriterionMetadata.documentation_reference`
    population) — explicit future work, additive, not scoped or authorized by this ADR
    (D4).
  - A periodic reuse-catalog hygiene mechanism — considered as a thirteenth Article
    candidate and dropped for not yet being a real, enforced invariant (D3); remains an
    open future item per the mentor scoping doc's own Item 1 finding, not created here.
- **The Nitin nuance is unconfirmed, stated plainly.** The specific citation-shape
  question this ADR resolves (documentation-mapping vs. runtime citation; a new Track-A
  ADR vs. an STD-000 promotion) was never itself put to Nitin — only the underlying
  "centralized constitution" ask was. This ADR is written to the structurally-forced
  Option B answer the scoping note derived from HB-001/ADR-0038's own rules, not to a
  mentor-confirmed design. If Nitin's own picture differs once asked, this ADR is
  revisable — it is not presented here as mentor-confirmed.
- **One mentor.** Every reference to mentor feedback in this ADR is to Nitin; no other
  mentor's feedback informs this document.

## Cross-references

- Mentor item #5 (`docs/architecture/mentor-feedback-scoping.md`) and its
  design-surfacing follow-up — the Problem statement and the Option A/B/C analysis this
  ADR executes Option B of.
- `docs/standards/STD-000-platform-constitution.md` — raw material for D3's Articles
  (D1); not amended, not promoted, not cited as authority anywhere in this ADR.
- ADR-0021, ADR-0024, ADR-0025, ADR-0026, ADR-0028 — the ratified lineage (D2).
- ADR-0020 — the original, Superseded constitution whose principles role this ADR
  assumes (D1); its Superseded status, set by ADR-0031, is unchanged.
- ADR-0031 — the current Authoritative Layer Model; consulted for accurate layer
  terminology when describing the ratified lineage (D2).
- ADR-0038 — Documentation Track Governance; the Track A/B rule this ADR's own
  authority position is defined against (D1).
- ADR-0022, ADR-0023, ADR-0027, ADR-0029 — the live capabilities whose standing this ADR
  formalizes (D2).

---

## Final review

1. **Does this ADR match the family's own conventions?** Yes — Track A, `docs/adr/`,
   numbered next after ADR-0048 (0049); D-lettered decision sections (ADR-0038/ADR-0048's
   convention, not the older lineage's `Stage N` convention, per this ADR's own brief);
   an `Ownership, scope, and governance` close, below.
2. **Is the ratification honest?** Yes — each lineage ADR named individually, per its
   own real content (D2); each still shows `Proposed` in its own header until a flagged
   follow-on edits it; no lineage ADR's body text is retro-edited.
3. **Are the Articles grounded, not invented?** Yes — each cites the ADR (and, where one
   exists, the code) that already enforces it, verified this session; enforcement
   mechanisms that are structural/conventional rather than a runtime gate are stated as
   such (Articles II, V).
4. **Is the authority position consistent with ADR-0038 and STD-000's own tier rules?**
   Yes — Track A per ADR-0038; the Architecture tier STD-000 §6/§7.1 confirms it cannot
   itself occupy (D1).
5. **Is this additive?** Yes — ADR-0020 referenced as already Superseded, not
   re-superseded; the five lineage ADRs' bodies untouched; STD-000 drawn on, not
   promoted or amended; no gate, code, or test touched.
6. **Is the mentor attribution accurate?** Yes — one mentor (Nitin); the specific
   citation-shape nuance this ADR resolves is flagged unconfirmed by him, not presented
   as his own design.

---

## Ownership, scope, and governance

- **Owns:** the platform's single Track-A constitutional authority position (D1); the
  ratification of ADR-0021/0024/0025/0026/0028 (D2); the twelve normative Articles and
  their grounding (D3); the gate-citation mapping (D4).
- **Does not own:** any subsystem's runtime contract, policy, engine, orchestration, or
  Execution Package (those remain exactly where their own ADRs place them); STD-000's
  own content or status (remains Track B, non-normative, Draft, ADR-0038); ADR-0020's or
  ADR-0031's own layer/lifecycle content (unmodified by this ADR); the five lineage
  ADRs' own body text (referenced, not edited); runtime/output gate citation
  (`CP1CriterionMetadata.documentation_reference` population — explicit, unauthorized
  future work, D4); any matrix or register entry for this ADR itself (recommended
  follow-on, not performed).
- **Governance:** registered as the platform's Engineering Constitution. **Accepted,
  effective immediately** — unlike the future-capability constitutional ADRs it ratifies
  (each of which became Accepted only once a future capability was built under it
  without deviation), this ADR is a governance-authority declaration over an
  already-live foundation, the same immediately-binding kind of decision ADR-0031,
  ADR-0032, and ADR-0038 each already are.
