# ADR-0050 — Artifact-Level Generation Cache

- **Status:** Accepted (first increment, 2026-08-14 -- see "Implementation Note," below).
- **Date:** 2026-08-14
- **Supersedes:** nothing. **Amends:** nothing.
- **Governing design:** none — this ADR *is* the governing design. It records the decisions
  reached by a design-surfacing task (`docs/architecture/mentor-feedback-scoping.md`, item #1's
  cluster, "ARTIFACT-LEVEL CACHE DESIGN SURFACED," 2026-08-14) rather than a preceding
  `docs/proposals/*.md` document — the surfacing note itself served that role, read in full
  before this ADR was written.
- **Depends on:** `requirement_intelligence/llm/generation_identity.py` (`GenerationIdentity` —
  the prompt/model identity this ADR's key relies on; additive infra, not itself ADR'd);
  ADR-0044 (Layer 3 Automation Engineering Architecture Freeze — governs the four L3 generator
  Protocols this cache wraps: `StepDefinitionGenerator`, `PageObjectGenerator`,
  `UtilityGenerator`, `TestDataGenerator`); ADR-0043 (Layer 2 Feature Engineering Architecture
  Freeze — governs `FeatureContentGenerator`, the fifth wrapped Protocol); ADR-0036 (Run and
  Stage State Model — source of `_hash_artifacts`'s content-hash *pattern*, reused here; its
  `RunStateManager` *class* is explicitly not reused, D2); ADR-0048 (Traceability Graph — sibling
  precedent for a new, standalone capability ADR written for a focused mechanism rather than a
  whole layer, and source of `change_impact_for_method`/`build_change_impact_report`, this
  cache's own downstream consumer once delta-scoped regeneration is built).
- **Runtime status: Built and tested (first increment only — D5's own scope).**
  `requirement_intelligence/llm/generation_cache.py` (`compute_cache_key`, `GenerationCacheEntry`,
  `GenerationCacheStore`) and `automation_engineering/generation/
  caching_step_definition_generator.py` (`CachingStepDefinitionGenerator`) exist, implementing D1–D4
  exactly as decided below, wrapping `LiveStepDefinitionGenerator` only — the other four generators
  and the remediator remain unwrapped, per D5. Both build-time gaps D3 named are closed:
  `automation_engineering/generation/live_step_definition_generator.py` gained
  `resolve_step_definition_identity` (Gap 1, pre-call identity) and `build_step_definition_payload`
  (the single shared payload definition, closing the "serialization drift" residual risk named in
  D1); `requirement_intelligence/llm/token_usage.py` gained `TokenUsageTotals.cache_hit_count` and
  `TokenUsageTracker.record_cache_hit` (Gap 2, the zero-cost-verified bucket). Proven by 33 new
  deterministic unit tests (`requirement_intelligence/tests/unit/test_generation_cache.py`,
  `tests/unit/test_automation_engineering_generation_caching_step_definition_generator.py`, plus
  additive `TestCacheHitRecording`/`TokenUsageTotals` cases) AND by one real, live measured run
  (Implementation Note, below) — not merely unit-tested in isolation. **Not wired into any live
  pipeline.** `scripts/run_requirement_analysis.py` still constructs `LiveStepDefinitionGenerator`
  directly, unwrapped; no `PlatformContext` composition-root method exists for this cache and none
  is added here — a future, separate milestone would wire it live, mirroring how ADR-0048's own
  Traceability Graph stayed unwired after being built and measured.

## Problem

Nitin's mentor feedback named a four-part re-run/delta-scoped-regeneration cluster; part of it —
content-addressed caching — is his own words: key each artifact on spec-slice/source-snapshot +
prompt-version + model-version, reuse anything whose inputs haven't changed, skip regeneration,
save tokens. Two prerequisites now exist: pinning (`GenerationIdentity`, threaded onto every
L2/L3 artifact record, prompt-version + model-version captured) and the token-usage
instrumentation (the scorecard this cache's savings would show against). The design-surfacing
task read the real generation pipeline — five LLM-driven generators' `generate`/`_build_prompt`
methods — against Nitin's own proposed key, and found it **silently incomplete**: `REQ-*`, the
key component the surfacing's own prior note recommended, does not cover everything a generator's
prompt actually serializes. Building the cache on that key, unexamined, would have shipped a
cache that returns wrong artifacts under real, unremarkable edits (D1). This ADR exists to record
the corrected design *before* any of it is built — ADR-first, matching this platform's standing
discipline, not the scores-first inversion `ADR-0048`'s own traceability-graph build used and
documented as a deliberate, one-time exception.

## Decision

Introduce a new, governed subsystem, **artifact-level generation caching**, wrapping the five
LLM-driven generation seams (`LiveStepDefinitionGenerator`, `LivePageObjectGenerator`,
`LiveUtilityGenerator`, `LiveTestDataGenerator`, `LiveFeatureContentGenerator`; the sixth,
`LiveFeatureRemediator`, is explicitly excluded, D5). Five decisions, each detailed below:

1. **The key** is a hash of the exact deterministic payload each generator already serializes
   immediately before its LLM call, combined with its `GenerationIdentity` — not a `REQ-*` or any
   other id-based proxy (D1, the centerpiece).
2. **The store** is on-disk and content-addressed, mirroring `atomic_write.py` +
   `_hash_artifacts`'s content-hash pattern — not `RunStateManager` itself (D2).
3. **Interception** happens at each generator's own Protocol boundary, via one small caching
   decorator per Protocol sharing one store module; a **hit** replays the stored artifact and its
   stored identity, skipping the LLM call (D3).
4. **Correctness and safety**: a hit is guaranteed (by D1's key construction) to be a genuine
   prior output for identical inputs, and flows downstream identically to a fresh generation —
   same record, same validation, same promotion (D4).
5. **Scope and sequence**: build the store, the key, and one decorator first, on one generator,
   measured — not the full five-generator wrap in one step (D5).

---

## D1 — The key, and why the obvious key was wrong (the centerpiece decision)

**The key:**

```
key = sha256(
    prompt_id + "\x00" + prompt_version + "\x00" + prompt_sha256 + "\x00"
    + provider + "\x00" + model + "\x00"
    + input_payload_json
)
```

where `input_payload_json` is the *exact* string each generator's own `_build_prompt` already
builds via `json.dumps(..., sort_keys=True)` immediately before constructing its `LLMRequest` —
for `LiveStepDefinitionGenerator`, the step text/step_type/captures/target_package/
page_object_interface/utility_interface/customqa_constraints payload; for
`LivePageObjectGenerator`, the class_name/need(s)/return_type(s)/parameters/customqa_constraints
payload (including `additional_method_needs`); for `LiveUtilityGenerator`, the equivalent
action-text/captures/class_name payload; for `LiveTestDataGenerator`, the specification/
target_class_name payload; for `LiveFeatureContentGenerator`, the title/narrative/component/
acceptance_criteria payload. `prompt_id`/`prompt_version`/`prompt_sha256`/`provider`/`model` are
exactly `GenerationIdentity`'s own five fields, already captured at every one of these call sites
(the pinning build).

**Why the naive key — `(REQ-* content hash, prompt_sha256, model)`, the prior surfacing note's own
recommendation — is wrong, checked against the real code, not assumed:**

1. **`REQ-*` under-covers even its own generator's input.** `generate_requirement_id`
   (`contracts/id_generation.py`) hashes only `normalize(title) + source_external_ids`. But
   `LiveFeatureContentGenerator._build_prompt` serializes `title`, `narrative`, `component`, *and*
   `acceptance_criteria` (`ac_id`/`statement`/`polarity_hints`) into the prompt.
   `generate_acceptance_criterion_id` is ordinal-based (`AC-<REQ short>-NN`), never content-hashed.
   **An edited `narrative`, `component`, or acceptance-criterion `statement`, with `title`
   unchanged, changes the real output but leaves `REQ-*` identical** — a cache keyed on it would
   return a stale hit, silently, with no signal anything was wrong. This is not a hypothetical edge
   case; requirement narratives and acceptance criteria are edited far more often than titles.
2. **`REQ-*` does not apply at all to the four L3 generators.** Their inputs
   (`StepDefinitionGenerationContext`, `PageObjectGenerationContext`, `UtilityGenerationContext`,
   `TestDataGenerationContext`) carry no `REQ-*`-derived field anywhere — confirmed by reading all
   four context dataclasses. A key built around `REQ-*` simply has nothing to key step-definition,
   page-object, utility, or test-data generation on.

**Why the corrected key is complete, by construction, not by argument:** `input_payload_json` is
not an approximation of what determines the generator's output — it **is** what determines it. It
is the literal string substituted into the rendered prompt (`_build_prompt` builds it, then hands
it straight to the template/LLM request). Hashing it therefore captures every input that varies
the output *to exactly the same degree the generator's own prompt construction already does* —
correctness of the key is bound to correctness of `_build_prompt`'s own serialization, a
pre-existing obligation every one of these generators already carries for the LLM call itself, not
a new one this design invents. `prompt_sha256` separately covers template-text changes (a prompt
version bump); `provider`/`model` cover a model swap. Together, the five components cover
everything a generator call is a deterministic function of.

**Two residual risks, named, not hidden:**

- **Serialization drift.** If a context dataclass ever grows a field a generator's own
  `_build_prompt` forgets to include in `input_payload`, the prompt and the cache key silently
  diverge *together* — the key would still be complete relative to what the LLM actually saw, but
  wrong relative to what the caller intended it to see. This is a code-review-time discipline for
  future context-field additions, not a design gap this ADR can close structurally.
- **Provider-level non-determinism.** Hosted model APIs do not guarantee bit-identical output
  across calls, even at `temperature=0.0`. A perfect key guarantees "this was a genuine prior
  output for these exact inputs" — never "identical to what a fresh call would produce today."
  This is inherent to any LLM-artifact cache, not a defect of this key; the existing downstream
  validation gates (CP1–CP5, promotion) are the mitigation, applied identically to cached and
  fresh artifacts (D4).

`REQ-*`/`AC-*`/`step_text`/`method_name` remain useful as a **human-readable label** stored
alongside a cache entry (diagnosis; a future "invalidate everything touching REQ-1234" tool) — they
are decided **out** of the correctness-bearing hash by this ADR, not merely deprioritized.

`temperature` is a fixed platform-wide constant (`0.0`, `LLMRequest`'s own default) today and is
therefore not part of the key; the moment it becomes a configurable per-call parameter, it must
join `input_payload_json`'s role, an amendment this ADR names in advance rather than leaving to be
rediscovered.

## D2 — The store: on-disk, content-addressed, a new sibling, not `RunStateManager`

The store persists on disk, keyed by D1's hash, surviving across process invocations — cross-run
reuse is the entire point of this capability; an in-run-only cache (a dict) would only prevent
duplicate calls within a single run, which reuse-first orchestration and per-need deduplication
already mostly do, and would not touch Nitin's actual complaint (token cost across re-runs of the
same corpus).

The store reuses `_hash_artifacts`'s (`requirement_intelligence/run_state/run_state_manager.py`)
content-hash *pattern* — sha256 over deterministically serialized content — and
`atomic_write.py`'s durable-write primitive, the same two precedents `RunStateManager` itself
already establishes. It does **not** reuse `RunStateManager` as a class: `RunStateManager.
should_skip` is keyed by `stage_id`, closed to the fixed 19-entry `STAGE_DEFINITIONS` catalogue
(`_find` raises `ValueError` on any other id) — architecturally unable to hold a per-artifact,
open-ended key space. A new, small, sibling module owns the artifact cache; `RunStateManager` is
unmodified.

Entry shape (decision, not implementation): one file per cache entry, path derived from the key
hash (avoiding one flat directory of unbounded size), storing the generated artifact text, its
`GenerationIdentity`, and the human-readable label components named in D1. Where the cache
directory itself lives (a new env var or CLi flag, sibling to how run/workspace directories are
already configured) is left to the implementation milestone — a configuration decision, not an
architectural one.

## D3 — Interception, hit consumption, and the two gaps the build must close

**Interception point.** The five wrapped generators span five distinct Protocols
(`StepDefinitionGenerator`, `PageObjectGenerator`, `UtilityGenerator`, `TestDataGenerator`,
`FeatureContentGenerator`) with different input shapes — there is no single universal wrapper
class. The decision is one small `Caching<X>Generator` decorator **per Protocol**, each
implementing that Protocol and constructor-wrapping any inner generator conforming to it (mirroring
exactly how `LiveStepDefinitionGenerator`/`StubStepDefinitionGenerator` are already interchangeable
peers behind the same seam), with all five decorators delegating their key/get/put logic to the one
shared store module from D2 — one implementation of the mechanism, five thin adapters. Rejected:
wrapping inside each live generator directly (mixes cache concerns into classes whose whole job
today is "render prompt, call provider, wrap response"); wrapping at the orchestrator layer
(`orchestrate_step_definition`, `orchestrate_page_object_method`, `orchestrate_utility_method`,
`generate_test_data_class`, `generate_feature_file` are four-plus distinct call sites — the
identical duplication problem one level up).

Because every downstream consumer (`orchestrator.py`, `runner.py`, `AssetRecord`/`FeatureRecord`
construction) already reads a generator through its Protocol or via
`getattr(generator, "last_identity", None)` — never a concrete class — **zero changes are required
at any downstream site** for this wrap to work (D4, blast radius).

**Hit consumption.** On a HIT, a decorator returns the stored artifact text and sets its own
`last_identity` from the **stored** `GenerationIdentity` — not a freshly-constructed one — so
`AssetRecord`/`FeatureRecord.generation_identity` stays populated exactly as it would for a fresh
generation. On a MISS, the decorator delegates to the wrapped live generator, stores the result and
its `last_identity` under the key, and returns it unchanged.

**Gap 1 — pre-call identity.** Today, `last_identity` populates only *after* a call returns,
because it is read off the `LLMResponse`, not off the generator's own already-fixed
construction-time state. But every component is in fact already fixed before the call:
`prompt_sha256` from the registry (`self._definition.metadata.sha256`, set in `__init__`); `model`/
`provider` from the provider's own construction-time state (`GeminiProvider.__init__` sets
`self._model_name` once and echoes it verbatim into every response, confirmed at
`gemini_provider.py:366,450` — the response never reports a model the provider wasn't already
going to use). A caching decorator must decide hit-or-miss *before* calling, so the build must
expose this pre-call identity (a small additive public accessor, or a constructor-supplied identity
prefix) rather than reading it off `last_identity` after the fact. Named here as a decision the
build must make, not solved by this ADR.

**Gap 2 — the token scorecard.** `TokenUsageTracker.record(call_type, usage)` today treats
`usage=None` as *unmeasured* (`unmeasured_call_count`, an incompleteness signal) — recording a hit
that way would make the scorecard show it as a broken measurement, the opposite of the saving this
whole capability exists to demonstrate. `TokenUsageTotals` needs a small additive third bucket
(e.g. `cache_hit_count`, distinct from both measured and unmeasured) before a hit is trustworthy in
the scorecard. Named here as a required, small, additive extension the build must make — not
performed by this ADR.

## D4 — Correctness and safety posture

A hit returns the same artifact a fresh generation would, for as long as D1's key holds (the
residual risks named there are the only ways this guarantee can fail, and both are named, not
hidden). A hit's artifact flows downstream **identically** to a fresh one: the same
`AssetRecord`/`FeatureRecord` construction, the same CP1–CP5 validation, the same promotion
pipeline — because those sites consume `.generate()`/`.last_identity` through a Protocol/`getattr`,
oblivious to cache involvement (D3). The saving is measurable, not asserted: once Gap 2 (D3) is
closed, the token scorecard shows a hit as zero new tokens against the call type it would otherwise
have cost. **A cache that returns a wrong artifact is worse than no cache** — this is why D1 is
this ADR's centerpiece, not an implementation detail subordinate to D2/D3.

## D5 — Scope and sequence: one generator, measured, before extending

**First build** (a future, separate milestone; not this ADR): the store (D2) + the key (D1) + one
decorator, wrapping `LiveStepDefinitionGenerator` — recommended over the other four for its recent
iteration volume (the live-regeneration defect-fixing line of work has repeatedly re-run step-
definition generation over the same corpus) and its existing measurement infrastructure. Measure
via the token-usage scorecard: run the same corpus twice; the second run's
`step_definition_generation` call-type totals should collapse toward the new `cache_hit_count`
bucket rather than fresh prompt/completion tokens. Only after that saving is demonstrated does
extension to the remaining four generators proceed — scores-first *within* an ADR-first capability,
not in place of one; the surfacing prompt this ADR follows was explicit that this ordering (ADR
before any code) is deliberately not the traceability graph's own scores-first inversion.

**Explicitly excluded:** `LiveFeatureRemediator`. `remediate(content, violations)` repairs a prior
attempt rather than performing first-generation; live remediation is independently known to be
rare, and re-running the identical `(content, violations)` pair across corpus re-runs is far less
likely than re-running the same first-generation call. Weak return on caching complexity; not
recommended as a target even after the five-generator wrap, absent new evidence.

**Deferred, each with its own trigger:**

- **Spec-slice (Nitin's item #4, branch-scoped vertical slices).** Not a blocker at any point in
  this design — D1's key never used `REQ-*`/source-snapshot as a proxy in the first place, so it
  needs neither #4 nor a new raw-evidence hash to be buildable.
- **Delta-scoped regeneration** (cluster item 2). The next piece after this cache exists — it would
  consume this cache as its own staleness signal and `change_impact_for_method`/
  `build_change_impact_report` (`requirement_intelligence/traceability_graph/change_impact.py`,
  built, ADR-0048's own named scope) as its blast-radius input, exactly Nitin's own model ("the
  cache tells you an artifact is stale; the change-impact graph tells you which downstream
  artifacts that staleness actually reaches").
- **The deterministic/LLM split** (cluster item 3). Orthogonal — narrows what ever needs a cache
  entry over time, but does not gate D1–D5; sequenced independently.

---

## Implementation Note (2026-08-14) — D5's first increment, built and measured

The first increment D5 names (store + key + one decorator, wrapping
`LiveStepDefinitionGenerator`, measured) was built the same day this ADR was written, closing both
D3 gaps in the process. This note records what was actually verified — decisions above stay
decisions; this is the separate record of what now backs them.

**Correctness, proven deterministically, no live LLM call involved:**
- A payload field a naive `REQ-*`/id-only key would have missed (`page_object_interface`,
  `customqa_constraints`) changes the corrected key even with the step's own `need.text` held
  fixed — the exact defect shape D1 found, proven not to recur.
- A second `generate()` call with an unchanged context HITS and skips the wrapped generator
  entirely (the inner provider's call count stays at 1, not 2).
- A changed input (page-object interface, a customqa constraint, or the step text itself) MISSES
  and regenerates — never a stale hit.
- A HIT replays the STORED `GenerationIdentity`, not a fresh one, and does so across two
  independent decorator/provider instances sharing only the on-disk store — proving cross-instance,
  not merely intra-object, reuse.
- A HIT records `TokenUsageTotals.cache_hit_count`, never `unmeasured_call_count` — the two
  buckets proven distinct.
- Every pre-existing `LiveStepDefinitionGenerator` test (`tests/unit/
  test_automation_engineering_generation_step_definition_generator.py`) passes unchanged after
  `build_step_definition_payload` was extracted from `_build_prompt` — the refactor is
  behavior-preserving, not merely believed to be.
- A MISS whose real, post-call identity does not match the caller-supplied pre-call identity raises
  (`GenerationCacheIdentityMismatchError`) rather than silently caching under the wrong key.

**The measured saving — one real, live run, not simulated.** A standalone, uncommitted harness
script (mirroring `CAP-088`'s own first-measurement precedent: real code, not committed pipeline
wiring) ran three realistic `StepDefinitionGenerationContext`s against the real, live Gemini API
twice: once against a fresh on-disk cache (every call a genuine LLM call), once against the SAME
on-disk cache from brand-new decorator and provider instances (a fresh process's own cold start,
proxied). Pass 1: 3 real LLM calls, 7003 total tokens. Pass 2: 0 new LLM calls, 0 new tokens, 3
cache hits, byte-identical artifacts to pass 1. `gemini-3.5-flash` (the platform's own
step-definition-generation default) returned transient `503 UNAVAILABLE` ("high demand") from
Google at measurement time — confirmed, by direct probe, to be model-specific, not an API-key or
connectivity problem (`gemini-2.5-flash` and the platform's `GEMINI_MODEL` default both succeeded
immediately) — so the measurement ran against `gemini-2.5-flash` instead, a harness-only
substitution with no bearing on the cache mechanism itself, which is model-agnostic by
construction (D1's key includes `model` as one of its own components precisely so a model swap is
a correctly-computed miss, never a silent hit).

**Scope held exactly as D5 decided.** Only `LiveStepDefinitionGenerator` is wrapped. The other four
generators, the remediator, delta-scoped regeneration, and the deterministic/LLM split are all
untouched by this increment — extending to them is the next, separate step D5 already named, not
performed here.

## Consequences

- **Enables, proven for the first increment, extends to the rest by the same pattern:**
  cross-run artifact reuse, with a measurable token saving now actually shown by the token-usage
  scorecard (Implementation Note, above) for `LiveStepDefinitionGenerator`; the same store/key/
  decorator pattern applies unchanged to the remaining four generators (future work); and the
  staleness signal delta-scoped regeneration will consume next.
- **Corrects a real design defect before it shipped.** The prior surfacing note's own recommended
  key would have produced silent stale hits on ordinary narrative/acceptance-criterion edits (D1).
  This ADR's key is the one any future build must implement — the corrected key is now the
  governed decision, not the prior note's.
- **Both named build-time gaps are closed (Implementation Note, above).** Pre-call identity
  exposure (D3, Gap 1 — `resolve_step_definition_identity`) and the token-scorecard cache-hit bucket
  (D3, Gap 2 — `TokenUsageTotals.cache_hit_count`) are both built, additive, and proven by test —
  no longer open for the step-def generator this increment wraps. Extending either closure to the
  remaining four generators (Gap 1's `resolve_*_identity` equivalent per Protocol) is future work.
- **Dependencies, satisfied or explicitly not required:** pinning (`GenerationIdentity`) is built
  and sufficient for D1's identity component; `_hash_artifacts`'s pattern and `atomic_write.py` are
  built and reusable for D2; the token-usage scorecard is built and is D5's measurement instrument.
  Spec-slice (#4) is confirmed not required (D5).
- **Governance follow-ons, recommended, not performed here** (mirroring exactly how ADR-0048 named
  its own matrix/register follow-ons as separate actions): (1) a
  `docs/governance/platform-capability-matrix.md` entry for **CAP-089** — Artifact-Level
  Generation Cache — confirmed the next unused id after `CAP-088` (Traceability Graph) in the
  open-ended `CAP-060…` block (§3.1); status `Accepted`/`Implementation` (updated from this ADR's
  original `Proposed`/`Architecture` framing, above, now that the first increment is built and
  measured — Implementation Note), mirroring `CAP-088`'s own row shape for a built-and-measured,
  not-yet-wired capability rather than `CAP-087`'s pure-paper-freeze shape; (2) a
  `docs/architecture/architecture-baseline-v2.md` register entry recording this ADR, mirroring how
  ADR-0048's own entry was added in a later, separate task. Neither changes this ADR's Decision
  text if performed later.
- **Became Accepted the same day** (Implementation Note, above): the store, the key, and the first
  decorator (D5) were built directly against this design, both named gaps (D3) were closed, and the
  first real token saving was measured — the exact Proposed-to-Accepted path this ADR named in
  advance, mirroring ADR-0030's own convention. Accepted status covers this first increment's own
  scope only (`LiveStepDefinitionGenerator`); the remaining four generators and the remediator stay
  future, separate work (D5), not implicitly authorized by this status change.
- **Relationship to the mentor cluster.** This is the second of Nitin's (one mentor) four-part
  re-run cluster to receive its own decision record — pinning was built without a dedicated ADR
  (additive infra, precedented shape); this cache, a new store/key/interception mechanism, is not.
  The sequencing recommendation in D5 (this generator first, delta-regen next, the split in
  parallel) is this ADR's own reading of the dependency shape, not something Nitin weighed in on
  directly — the same caveat the surfacing note itself already flagged.

## Ownership, runtime position, governance

- **Owns:** the artifact-level generation cache's key construction (D1), store shape (D2),
  interception pattern and hit-consumption contract (D3), correctness/safety posture (D4), and
  build sequence (D5) — decisions only.
- **Does not own:** `GenerationIdentity`, any live generator, any orchestrator, `RunStateManager`,
  `TokenUsageTracker`'s existing measured/unmeasured buckets (extended, not owned, by D3's Gap 2),
  or delta-scoped regeneration (a future, separate capability that consumes this one once built).
- **Runtime position (built for the first increment; not live-wired):** generator construction
  site → `CachingStepDefinitionGenerator` → key (D1) → store (D2) lookup → HIT: stored artifact +
  stored identity, LLM call skipped; MISS: wrapped `LiveStepDefinitionGenerator` called, result
  stored → identical downstream flow either way (D3/D4, proven — Implementation Note). This chain
  exists and is tested for step-definition generation only; the equivalent `Caching<X>Generator`
  for the other four Protocols does not exist yet. No `PlatformContext` method, no pipeline stage,
  no Execution Package artifact exists for this capability today — `scripts/
  run_requirement_analysis.py` does not construct `CachingStepDefinitionGenerator`.
- **Governance:** recommended `CAP-089` (not yet entered — Consequences) for the Requirement
  Intelligence Platform. This ADR is **Accepted** for its first increment (Implementation Note,
  above) — it now clears the same bar ADR-0048 cleared (built, tested, measured once against real
  data), for the scope D5 defined (one generator). It does not claim the full five-generator wrap is
  built, tested, or measured — that remains future, separate work, exactly as D5 sequenced it.
