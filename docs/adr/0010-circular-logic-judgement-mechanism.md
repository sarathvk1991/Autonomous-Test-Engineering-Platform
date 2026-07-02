# ADR 0010 — Circular Logic Judgement Mechanism (REASONING-0003)

- **Status:** Proposed
- **Date:** 2026-07-02

## Context

The mandatory design review for **`REASONING-0003` (CircularLogicRule)** halted on the same
class of mechanism gap that ADR-0009 recorded for `REASONING-0001` — and, if anything, a
deeper one.

- Validation Rule Catalog §9.8: `REASONING-0003 | CircularLogicRule | `**`No chain of
  reasoning is circular.`** — the mechanism is unspecified.
- Validation Rule Catalog §8.8 (Reasoning): "Confirm the output is **internally coherent and
  self-consistent** … Detect … **circular logic** across the output."
- The governed response represents every statement as a **bare string** (Prompt Framework
  `OUTPUT_REQUIREMENTS`: "Every array element must be a string statement"). It carries **no
  inferential / derivation links** between statements — there is no declared "which statement
  is derived from which."
- AI Response Validation Architecture lists **"Semantic validation — assess meaning-level
  coherence beyond structure"** as a **future capability** ("a richer Reasoning layer; must
  remain **deterministic**").
- ADR-0008 froze **byte-exact** comparison only for `REASONING-0002` (duplicates), where a
  surface-form mechanism is faithful. ADR-0009 deferred `REASONING-0001` (contradiction),
  which has no faithful deterministic mechanism.

**Circular logic is inherently semantic/logical, and it presupposes a structure the response
does not contain.** Detecting that "a chain of reasoning is circular" requires **two**
ungoverned steps: (a) **infer the inferential dependency links** between natural-language
statements (which statement supports/derives which — a semantic-inference step), and then
(b) **detect a cycle** over that inferred dependency graph (graph reasoning). The governed
response contains **no dependency links at all** — the statements are independent strings —
so there is no "chain" in the data to traverse. **No surface-form mechanism (byte / lexical /
normalized) detects circular logic**, and a faithful mechanism requires semantic inference
and graph reasoning, **neither of which is governed**, and both of which the platform's
no-invention discipline (ADR-0005/0006) and determinism requirement forbid introducing here.

### The hidden inconsistency this ADR corrects

ADR-0006 classified `REASONING-0003` **Implementable** on the basis that classification is
"based only on **information sufficiency**" ("operates on governed statements; … input
present"). As with `REASONING-0001` (corrected by ADR-0009), that reasoning is **incorrect
for circular logic**: information sufficiency (the statement strings exist) is **necessary
but not sufficient** — implementability also requires a **governed, deterministic judgement
mechanism** (here, additionally, a governed dependency structure), which does not exist.
ADR-0009 already flagged that `REASONING-0003` would need the same correction; this ADR makes
it.

### Design review findings

1. **Governed deterministic mechanism?** **No.**
2. **Is "circular logic" defined / detectable on the current schema?** **No** — bare strings
   with no dependency links; no chain to traverse.
3. **Would implementation invent semantic behaviour / need a new governed mechanism?** **Yes
   to both** (dependency inference **and** cycle detection).
4. **Ownership conflict?** **None** (internal-coherence circular logic is distinct from all
   other layers and from `REASONING-0001`/`0002`).
5. **Hidden inconsistency?** **Yes** — ADR-0006's information-sufficiency-only classification
   of `REASONING-0003` as Implementable; corrected here.

No additional inconsistency was discovered.

## Decision

**`REASONING-0003` (CircularLogicRule) is Reserved · Deferred. No governed comparison /
judgement mechanism is adopted, because no deterministic mechanism faithfully detects
circular logic under the current governed architecture.**

- Circular-logic detection is an inherently **semantic/logical, graph-structured** judgement.
  It presupposes a **governed dependency structure** (inferential links between statements)
  that the current response does not carry, plus a **deterministic reasoning mechanism** to
  find cycles. It belongs to the platform's reserved **semantic-validation future capability**
  ("a richer Reasoning layer").
- **No surface-form mechanism is adopted.** Unlike ADR-0008 (byte-exact for duplicates),
  there is no byte/lexical/normalized mechanism that faithfully represents "circular logic";
  adopting one would create a mislabelled rule. This ADR adopts **no** mechanism rather than a
  fabricated one — exactly as ADR-0009 did for contradiction.
- `REASONING-0003` remains a **permanently reserved catalog identity** (Rule ID frozen, never
  reused, Catalog §4.3); implementation is **deferred** until a future ADR introduces both a
  governed dependency representation and a governed, deterministic cycle-judgement mechanism.
- **This ADR supersedes ADR-0006's classification of `REASONING-0003`** from **Implementable**
  to **Reserved · Deferred**. (ADR-0006's classifications of all other rules are unchanged.)

This ADR fixes only the **disposition and mechanism question** of an existing catalogued
rule. It changes **no** rule identity, name, severity, blocking, layer, or number, and
introduces **no** new rule.

## What is explicitly out of scope

The following are **rejected as the governed mechanism** and must not be introduced to
implement `REASONING-0003` without a future ADR:

- **byte-exact / lexical / normalized string comparison** — does not detect circular logic;
- **graph reasoning over an inferred dependency graph** — the dependency links are not
  governed data; inferring them is invented semantic behaviour;
- **embeddings / vector similarity** — not governed; not deterministic in the required sense;
- **NLP heuristics** (entailment/support detection) — invented semantic behaviour;
- **LLM judgement** — not deterministic (AI Response Validation §3.4; "must remain
  deterministic"); not governed;
- **any invented dependency-extraction or normalization** — a schema/canonical change
  requiring its own ADR.

## Relationship with future semantic reasoning

Circular-logic detection is part of the reserved **"richer Reasoning layer" / semantic
validation** capability. Its future enabling ADR must supply **both** a governed
**dependency/derivation representation** the response would carry (a schema-enrichment
decision, cf. ADR-0006's deferred capabilities) **and** a governed, **deterministic** cycle
judgement over it. **That design is out of scope here** (this ADR does not design the
mechanism, propose field names, enrich any schema, or introduce graph reasoning). When such a
mechanism is governed, `REASONING-0003` is activated by its own ADR under the same verdict
model.

## Ownership

`REASONING-0003` owns exactly one concern: **circular chains of reasoning across the output**
(internal coherence, §8.8). It never owns value quality (Content), shape/existence (Schema),
declared policy/coverage (Business), grounding (future Evidence), link resolution (future
Traceability), contradiction (`REASONING-0001`), or duplication (`REASONING-0002`). Deferral
does not move the concern to any other layer; it records that the concern has no governed
mechanism yet.

## Impact on existing rules

- **Supersedes ADR-0006** only for `REASONING-0003` (Implementable → Reserved · Deferred).
- **`REASONING-0002`** (implemented, ADR-0008 byte-exact) is **unaffected** — duplication has
  a faithful deterministic mechanism; circular logic does not.
- **`REASONING-0001`** (ContradictoryRequirementRule) is already **Reserved · Deferred**
  (ADR-0009); this ADR is fully consistent with it.
- With this ADR, the **Reasoning layer disposition is fully settled**: `REASONING-0002`
  implemented; `REASONING-0001` and `REASONING-0003` Reserved · Deferred pending a governed
  deterministic semantic mechanism.
- **No implemented rule changes behaviour**; no code changes.

## Alternatives considered

- **A — Adopt a deterministic surface-form mechanism (byte/lexical/normalized).**
  **Rejected:** does not detect circular logic; a mislabelled rule. Circular logic is
  structural/semantic, not surface-level.
- **B — Infer a dependency graph and run cycle detection.** **Rejected:** the dependency
  links are not governed data; inferring them from NL strings is invented semantic behaviour
  (and non-deterministic).
- **C — Adopt embeddings / NLP / LLM judgement.** **Rejected:** not governed, not
  deterministic (AI Response Validation §3.4), prohibited invention (ADR-0005/0006).
- **D — Leave the mechanism undefined.** **Rejected:** implementers could invent divergent,
  non-deterministic heuristics — the anti-pattern ADR-0008 exists to prevent.
- **E — Chosen: defer `REASONING-0003` as Reserved · Deferred**, with circular logic judged a
  reserved future semantic capability behind a governed dependency representation and a
  deterministic mechanism. **Accepted (Proposed):** faithful, invention-free, consistent with
  ADR-0005/0009.

## Consequences

- ✅ `REASONING-0003` has a clear, honest disposition: **Reserved · Deferred** — not a
  fabricated mechanism.
- ✅ The classification inconsistency in ADR-0006 is corrected on the record (matching
  ADR-0009 for `REASONING-0001`).
- ✅ A future semantic-reasoning ADR has a clean home for circular-logic detection without
  disturbing `REASONING-0003`'s identity.
- ✅ The Reasoning layer is now fully dispositioned (0002 implemented; 0001, 0003 deferred).
- ⚠️ **Status is Proposed.** Until Accepted, this ADR records the proposed correction; on
  acceptance, governance reflects `REASONING-0003` as Reserved · Deferred.
- ⚠️ **Version impact:** this ADR reclassifies a **not-yet-implemented** rule and adopts no
  mechanism. It changes no concern meaning, severity, blocking, identity, number, or canonical
  model, and advances **no** version (Rule Catalog / Validation Contract / Validator / Rule
  Version all unchanged; Catalog §20) — consistent with ADR-0005/0009.
- ⚠️ **Governance registration applied** (no implementation, no Rule Catalog, no contract, no
  canonical-model changes; see "Governance registration").

## Governance registration

On this ADR being recorded (Proposed), the following governance documents register it (no
code, no Rule Catalog, no contract, no canonical-model changes):

- `docs/governance/architecture-freeze-index.md` — §6 Relationship to ADRs registers
  ADR-0010; the Validation Rule Catalog artifact row references it.
- `docs/governance/platform-capability-matrix.md` — the CAP-049 (Reasoning Layer) note
  records `REASONING-0003` as **Reserved · Deferred** (proposed correction of ADR-0006).
- `docs/governance/architecture-coverage-dashboard.md` — the readiness notes record the
  circular-logic-mechanism deferral.

## Scope note

This ADR decides **only** the disposition and mechanism question of `REASONING-0003`. It does
**not** implement any rule, design a circular-logic mechanism, propose field names, enrich any
schema, introduce graph reasoning, create or modify tests, or change any code, framework,
`ValidationInput`, `ParsedResponse`, `NormalizationResult`, `ResponseValidator`,
`ResponseNormalizer`, canonical model, the Rule Catalog, or the Validation Rule / Schema
Implementation Contracts. It changes no rule identity, number, severity, or blocking.
Activation of `REASONING-0003` is contingent on a **future** ADR introducing a governed
dependency representation and a governed, deterministic circular-logic judgement mechanism.
