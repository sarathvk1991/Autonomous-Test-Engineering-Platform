# Mentor Clarification — Discussion Prep

*Source: `docs/architecture/mentor-feedback-scoping.md`, synthesis group (b). Every "what we
already have" claim below is verified against real code/ADRs (cited inline); nothing here is
asserted from memory of the conversation.*

**Why this doc exists.** A few of the mentor's suggestions look, on inspection, close to things the
platform may already do — but "close" isn't the same as "confirmed," and we don't want to guess
what he actually wants. This is prep for a short calibration conversation, not a rebuttal: for each
item below, we show him exactly what exists today and ask a genuinely open question about the gap.
**"You're already there, skip it" is a good outcome — it shrinks the work.** "No, I mean more than
that" is an equally good outcome — it sharpens exactly what to build. Either answer moves us
forward; the point is not to defend what we have, it's to stop guessing.

---

## #2 — "Skills-first, agents-next" (token minimization)

**His point:** prefer small, deterministic, scoped calls over autonomous multi-step agents, to keep
token spend down and behavior predictable.

**What we already have:** there's no agent/tool-loop architecture anywhere in the platform today —
verified directly, no such pattern exists in the code. Every generation call (step-definitions,
page objects, features, remediation) is a single, stateless `input → output` call
(`LiveStepDefinitionGenerator.generate`, `LivePageObjectGenerator.generate` — one context in, one
string out, no internal loop), sequenced by ordinary Python control flow, never a model deciding
its own next step. Prompts are versioned and governed (ADR-0014), not ad hoc. Different generation
tasks already get differently-scoped models (`STEP_DEF_GEMINI_MODEL` is its own dedicated config,
separate from other callers).

**Ask him:** given we're already single-shot, no-agent-loop — is "skills-first" pointing at
something more specific we're missing (a reusable prompt/skill-library abstraction? a particular
harness he has in mind? a concern about a future self-healing loop — the one place in our roadmap
where something agent-shaped could plausibly show up later, and which doesn't exist yet)? Or does
the current shape already match what he pictured?

---

## #4 — Spec-based development (features, page objects, artifacts)

**His point:** drive generation from structured specs rather than free-text prompting.

**What we already have:** generation is already contract-driven, not prose-driven, in the places
we checked. `TestableRequirementSet` is a structured, versioned, schema-checked contract (not free
text) between requirement analysis and feature generation. `.feature` files are the canonical spec
downstream generation works against. Most specifically: page-object generation derives its request
— the exact method name, return type, and argument count — from the **already-generated
step-definition's own call site**, never from inferring intent out of prose (ADR-0044 D4). The call
site is the spec.

**Ask him:** our generation is call-site/contract-driven specifically for page objects — is
"spec-based development" asking us to extend that same explicit-contract approach elsewhere
(utilities? test data?), or is he picturing something larger — e.g., a single canonical
domain-model-as-source-of-truth, with Gherkin as just one possible rendering of it (we have an
unaccepted, still-open proposal in that direction, materially bigger than what exists today)?

---

## #3 — Knowledge Graph (the "Neo4j" sub-part)

**His point:** build a knowledge graph over requirements (he named Neo4j specifically).

**What we already have — real, but not what he's likely picturing.** An Accepted, live knowledge
graph subsystem already exists: typed nodes/edges/subgraphs, a deterministic engine, results
written into every run's own report. Two honest caveats: **it is not Neo4j** — no graph database
exists anywhere in this stack; it's a bespoke, in-repo model. And **it answers a different
question** — how artifacts across the whole platform structurally relate to each other (which
requirement traces to which evidence, which module, which finding), not specifically "is the
requirement set complete." It's also currently running on a thin, single-run stand-in, since the
real cross-run historical dataset it would need to be meaningful isn't built yet.

**Ask him:** is he picturing a separate, completeness-focused graph, or extending what already
exists? And is Neo4j itself important (a real graph database, for reasons we should understand —
querying power, visualization, something else), or would extending our existing in-repo graph model
satisfy what he's actually after?

---

## Nitin — Eval harness with golden sets

**His point:** an eval harness with golden sets.

**What we already have — real, but for a different purpose.** A golden-baseline regression harness
already exists — it checks whether the platform's own deterministic output *structure* still
matches a frozen baseline, re-verified at nearly every capability milestone. It does **not** grade
whether a *generated artifact* (a step-definition, a page object) is qualitatively good against
curated exemplars — that doesn't exist. Quality issues found so far (e.g. a model's real defect
rate at scale) were caught through one-off live runs, not a standing harness.

**Ask him:** is the existing structural-regression mechanism what he meant by "golden sets," or is
he asking for something that grades generation *quality* specifically — and if the latter, what
would "good" look like to him (a rubric, exemplar comparison, something else)?

---

## Nitin — Agent/re-run token loss

**His point:** concern about token cost lost on re-runs.

**What we already have:** every stage in the pipeline already skips unchanged work on resume — a
governed mechanism compares each stage's own input/output artifacts and skips it entirely if
nothing relevant changed. This is foundational, already in place, not new.

**Ask him:** does this already cover the concern, or is there a more specific scenario he has in
mind — cost *within* one run rather than across re-runs, or a particular stage that doesn't skip
cleanly today?

---

## After the conversation

Whatever comes back — "skip," "extend what exists," or "no, build something new" — feeds back into
the scoping doc's own synthesis before anything gets built. No item above should be treated as
resolved by this document; it only exists to make the conversation sharper.
