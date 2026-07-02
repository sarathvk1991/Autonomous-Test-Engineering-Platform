# ADR 0009 — Contradiction Judgement Mechanism (REASONING-0001)

- **Status:** Proposed
- **Date:** 2026-07-02

## Context

The mandatory design review for **`REASONING-0001` (ContradictoryRequirementRule)** halted
on a mechanism gap deeper than the one ADR-0008 resolved for `REASONING-0002`.

- Validation Rule Catalog §9.8: `REASONING-0001 | ContradictoryRequirementRule | `**`No two
  requirements contradict each other.`** — the mechanism is unspecified.
- Validation Rule Catalog §8.8 (Reasoning): "Confirm the output is **internally coherent
  and self-consistent** … Detect **contradictions** …"; worked example: *"Two requirements
  asserting different limits for the same field is a Reasoning finding."*
- The governed response represents each requirement as a **bare string statement**
  (Prompt Framework `OUTPUT_REQUIREMENTS`: "Every array element must be a string
  statement"); there is no structured `(field, value)` claim to compare.
- AI Response Validation Architecture lists **"Semantic validation — assess meaning-level
  coherence beyond structure"** as a **future capability** ("a richer Reasoning layer; must
  remain **deterministic**").
- ADR-0008 froze **byte-exact** comparison **only for `REASONING-0002`** (duplicates),
  where a surface-form mechanism is faithful.

**Contradiction is inherently semantic/logical.** Judging that two natural-language
requirement statements *contradict* (e.g. asserting different limits for the same field) is
a meaning-level relationship. Unlike duplication — which has a faithful, deterministic
surface-form mechanism (byte-exact) — **no surface-form (byte / lexical / normalized)
mechanism detects contradiction**: contradictory statements are almost never byte-related,
and a surface-form "contradiction" rule would either never fire meaningfully or fire on
unrelated inputs. A faithful mechanism requires semantic or logical inference (NLP,
embeddings, an LLM judge, or a structured-claim logic model) — **none of which is governed,
and all of which the platform's no-invention discipline (ADR-0005/0006) and determinism
requirement forbid introducing here.**

### The hidden inconsistency this ADR corrects

ADR-0006 classified `REASONING-0001` **Implementable**, on the stated basis that
classification is "based only on **information sufficiency**" and that a "hard-to-build rule
is still Implementable if its governed input exists." That reasoning holds for
`REASONING-0002` (byte-exact duplicates genuinely work), but it is **incorrect for
contradiction**: information sufficiency (the requirement strings exist) is **necessary but
not sufficient** — implementability also requires a **governed, deterministic judgement
mechanism**, which does not exist for contradiction. This ADR corrects that classification.

### Design review findings

1. **Is the contradiction mechanism governed?** **No.**
2. **Is contradiction byte-exact / lexical / normalized / semantic / logical?**
   **Semantic/logical** — not surface-form.
3. **Deterministic judgement possible today?** **No** — requirements are bare strings; no
   governed semantic/logical mechanism exists.
4. **Would implementation invent semantic behaviour / need a new governed mechanism?**
   **Yes to both.**
5. **Ownership overlap?** **None** (Content/Schema/Business/future Evidence/Traceability are
   distinct from internal-coherence contradiction).
6. **Hidden inconsistency?** **Yes** — ADR-0006's information-sufficiency-only classification
   of `REASONING-0001` as Implementable; corrected here.

No additional inconsistency was discovered.

## Decision

**`REASONING-0001` (ContradictoryRequirementRule) is Reserved · Deferred. No governed
comparison mechanism is adopted, because no deterministic mechanism faithfully detects
contradiction under the current governed architecture.**

- Contradiction detection is an inherently **semantic/logical** judgement. It belongs to
  the platform's reserved **semantic-validation future capability** ("a richer Reasoning
  layer", AI Response Validation Architecture) and requires a **governed, deterministic
  judgement mechanism** that does not exist today.
- **No surface-form mechanism is adopted.** Unlike ADR-0008 (byte-exact for duplicates),
  there is no byte/lexical/normalized mechanism that faithfully represents "contradiction";
  adopting one would create a mislabelled rule. This ADR therefore adopts **no** mechanism
  rather than a fabricated one.
- `REASONING-0001` remains a **permanently reserved catalog identity** (its Rule ID is
  frozen and never reused, Catalog §4.3); its implementation is **deferred** until a future
  ADR introduces a governed, deterministic contradiction-judgement mechanism.
- **This ADR supersedes ADR-0006's classification of `REASONING-0001`** from
  **Implementable** to **Reserved · Deferred**. (ADR-0006's classifications of all other
  rules are unchanged.)

This ADR fixes only the **disposition and mechanism question** of an existing catalogued
rule. It changes **no** rule identity, name, severity, blocking, layer, or number, and
introduces **no** new rule.

## What is explicitly out of scope

The following are **rejected as the governed mechanism** and must not be introduced to
implement `REASONING-0001` without a future ADR:

- **byte-exact / lexical / normalized string comparison** — does not detect contradiction;
- **embeddings / vector similarity** — not governed; not deterministic in the required
  sense;
- **NLP heuristics** (negation detection, entailment models) — invented semantic behaviour;
- **LLM judgement** — not deterministic (AI Response Validation §3.4; "must remain
  deterministic"); not governed;
- **any invented normalization or claim-extraction** — a schema/canonical change requiring
  its own ADR.

## Relationship with future semantic reasoning

Contradiction detection is part of the reserved **"richer Reasoning layer" / semantic
validation** capability. Its future enabling ADR must supply a **governed, deterministic**
mechanism — for example a governed structured-claim representation the response would carry
(a schema-enrichment decision, cf. ADR-0006's deferred capabilities) **or** a governed
deterministic judgement specification. **That design is out of scope here** (this ADR does
not design the mechanism, propose field names, or enrich any schema). When such a mechanism
is governed, `REASONING-0001` is activated by its own ADR under the same verdict model.

## Ownership

`REASONING-0001` owns exactly one concern: **contradictions between requirement statements**
(internal coherence, §8.8). It never owns value quality (Content), shape/existence (Schema),
declared policy/coverage (Business), grounding (future Evidence), or link resolution (future
Traceability). Deferral does not move the concern to any other layer; it records that the
concern has no governed mechanism yet.

## Impact on existing rules

- **Supersedes ADR-0006** only for `REASONING-0001` (Implementable → Reserved · Deferred).
- **`REASONING-0002`** (DuplicateRecommendationRule, implemented; ADR-0008 byte-exact) is
  **unaffected** — duplication has a faithful deterministic mechanism; contradiction does
  not.
- **`REASONING-0003`** (CircularLogicRule) faces the **same class** of semantic-mechanism
  gap and its Implementable classification is likely to require the same correction — but
  `REASONING-0003` is **not decided here** and remains as classified by ADR-0006 pending its
  own review/ADR.
- **No implemented rule changes behaviour**; no code changes.

## Alternatives considered

- **A — Adopt a deterministic surface-form mechanism (byte/lexical/normalized).**
  **Rejected:** such a mechanism does not detect contradiction; it would be a mislabelled
  rule firing on unrelated inputs (or never firing meaningfully). Contradiction is
  meaning-level, not surface-level.
- **B — Adopt embeddings / NLP / LLM judgement.** **Rejected:** not governed, not
  deterministic (AI Response Validation §3.4, "must remain deterministic"), and inventing
  semantic behaviour is prohibited (ADR-0005/0006).
- **C — Leave the mechanism undefined.** **Rejected:** implementers could invent divergent,
  non-deterministic heuristics — the anti-pattern ADR-0008 exists to prevent.
- **D — Chosen: defer `REASONING-0001` as Reserved · Deferred**, with contradiction judged a
  reserved future semantic capability behind its own governed, deterministic mechanism.
  **Accepted (Proposed):** faithful, invention-free, and consistent with the ADR-0005
  deferral precedent.

## Consequences

- ✅ `REASONING-0001` has a clear, honest disposition: **Reserved · Deferred** — not a
  fabricated mechanism.
- ✅ The classification inconsistency in ADR-0006 is corrected on the record.
- ✅ A future semantic-reasoning ADR has a clean home for contradiction detection without
  disturbing `REASONING-0001`'s identity.
- ⚠️ **Status is Proposed.** Until Accepted, this ADR records the proposed correction; on
  acceptance, governance reflects `REASONING-0001` as Reserved · Deferred.
- ⚠️ **Version impact:** this ADR reclassifies a **not-yet-implemented** rule and adopts no
  mechanism. It changes no concern meaning, severity, blocking, identity, number, or
  canonical model, and advances **no** version (Rule Catalog / Validation Contract /
  Validator / Rule Version all unchanged; Catalog §20) — consistent with ADR-0005/0008.
- ⚠️ **Governance registration applied** (no implementation, no Rule Catalog, no contract,
  no canonical-model changes; see "Governance registration").

## Governance registration

On this ADR being recorded (Proposed), the following governance documents register it (no
code, no Rule Catalog, no contract, no canonical-model changes):

- `docs/governance/architecture-freeze-index.md` — §6 Relationship to ADRs registers
  ADR-0009; the Validation Rule Catalog artifact row references it.
- `docs/governance/platform-capability-matrix.md` — the CAP-049 (Reasoning Layer) note
  records `REASONING-0001` as **Reserved · Deferred** (proposed correction of ADR-0006).
- `docs/governance/architecture-coverage-dashboard.md` — the readiness notes record the
  contradiction-mechanism deferral.

## Scope note

This ADR decides **only** the disposition and mechanism question of `REASONING-0001`. It
does **not** implement any rule, design a contradiction mechanism, propose field names,
enrich any schema, create or modify tests, or change any code, framework, `ValidationInput`,
`ParsedResponse`, `NormalizationResult`, `ResponseValidator`, `ResponseNormalizer`, canonical
model, the Rule Catalog, or the Validation Rule / Schema Implementation Contracts. It changes
no rule identity, number, severity, or blocking. Activation of `REASONING-0001` is contingent
on a **future** ADR introducing a governed, deterministic contradiction-judgement mechanism.
