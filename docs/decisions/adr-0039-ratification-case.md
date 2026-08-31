# Decision-Support Memo: Should ADR-0039 be ratified (Proposed → Accepted) to unblock Layer 5?

**Status:** For decision — this memo does not decide; ratification is the ARB's/Nitin's call.

ADR-0039 ("Execution Backend and CI/CD") has sat Proposed since 2026-07-24. Its own status line is load-bearing: no component may be built against it until it is ratified, so Layer 5 (Test Execution) cannot even begin while it stands. The case for ratifying is that this is a cheap, low-risk, essentially procedural step — one ARB vote against an architecture that is already internally complete. The honest headline, though, is scope: ratifying ADR-0039 unblocks the *layer* — it clears Layer 5 to be designed and built — but it does not, by itself, produce a runnable suite. The constraints that actually stand between the platform and a suite that runs today are elsewhere (page-object generation is not live-wired, and test data is only partially populated) and are entirely independent of this ADR. Both sides of that trade-off are laid out below; the memo recommends nothing.

## 1. What ADR-0039 proposes

- **Jenkins, in two roles that must not be conflated:** (1) platform CI — running `ruff`/`mypy`/`pytest` against this repo's own Python on every change; (2) an execution backend — running the generated Java suite for Layer 5, and the SonarQube scan Layer 4 consumes.
- **Layer 5 sits behind an `ExecutionBackend` interface.** Jenkins is one implementation of it, never invoked directly by Layer 5's own logic. **A local Maven/Gradle runner is the default implementation** — Layer 5 is buildable and testable with no Jenkins instance available at all. Jenkins is optional and swappable, not an architectural dependency.
- **`run_state.json` (ADR-0036) remains authoritative.** Jenkins's own build log/history is a detail of one backend implementation; a Jenkins URL is never the system of record for what a run did.
- **One substantive open item: D2 (asynchronous execution).** A Jenkins-delegated run is trigger/poll/collect — the first stage in the pipeline that cannot be a single synchronous call under ADR-0036's stage model, which was built against Layer 1's exclusively synchronous phases. ADR-0039 names this problem but does not resolve it: the exact poll/resume/reconciliation mechanism is **deliberately left to Layer 5's own future architecture-freeze ADR**, not treated as a precondition of this ADR's own acceptance.

## 2. The ratification checklist (thinner than it looks)

Stripped down, there are really only two items:

1. **ARB approval** — the one hard requirement, and it is purely procedural. ADR-0039's own governance line states it becomes Accepted "only through the same [process] ADR-0032's freeze-lifting procedure describes — explicit Architecture Review Board approval." (This borrows ADR-0032's *mechanism* — an ARB vote — not any of ADR-0032's Layer-1-specific preconditions; the two ADRs govern unrelated capabilities.)
2. **No additional technical resolution is required first.** The proposal is internally complete: backend choice (Jenkins), interface boundary (`ExecutionBackend`), default implementation (local Maven/Gradle), and the two-role separation are all already decided. D2 is knowingly left open and explicitly assigned downstream to Layer 5's own future ADR — it is not a loose end this ratification has to tie off.

Put plainly: this is not a stack of unresolved technical questions waiting on ratification. It is one deliberately deferred item plus a governance vote.

## 3. What ratification does and does not unblock

| | |
|---|---|
| **Does** | Makes Layer 5 buildable — the layer is no longer governance-blocked from having any component built against it. |
| **Does** | Settles the execution-backend architecture — interface boundary, Maven/Gradle default, Jenkins as optional/swappable — so Layer 5's own design doesn't have to re-litigate it. |
| **Does** | Lets Layer 5's own architecture-freeze ADR proceed (per ADR-0039's own Recommendation 1, that ADR currently must either wait for ratification or treat the backend question as its own open item). |
| **Does not** | Produce a runnable suite by itself. Two independent constraints remain, untouched by this ADR. |
| **Does not** | Touch page-object generation — the live matcher and generator both exist and are tested, but are deliberately not constructed in the live default path (`scripts/run_requirement_analysis.py`, stage-15 automation-engineering wiring): "page objects are not generated, CP4 evaluates vacuously" today. Activation was left as a separate, deliberate decision (real cost: new embedding + LLM calls on every run), not a forced consequence of the matcher existing. |
| **Does not** | Touch test-data coverage — the Option B post-hoc enrichment stopgap (commit `97d0f6e`) derives real fields for 4 of the 15 real SUT requirements; the remaining 11 stay honestly empty (`fields=[]`). Option A, the higher-fidelity fix, is itself frozen behind ADR-0032 pending its own separate ARB lifting decision. |

`test_execution/` today is a single-commit placeholder (`303214f`, renamed per ADR-0033) — an empty package with a "Planned (Phase 5 — not implemented)" README and nothing else. The honest chain from here to a running suite is: **ADR-0039 ratified → Layer 5's own architecture-freeze ADR written (resolving D2) → Layer 5 implemented → then something can run a suite** — and even then, that suite only exercises real page objects and real test data once those two independent gaps are separately closed.

## 4. The case for ratifying

- **Cheap and low-risk.** One ARB vote. No technical debt is taken on in the process — D2 is deferred by design, not swept under the rug, and it's explicitly assigned to the ADR that will actually have to resolve it.
- **A genuine unblock.** Layer 5 cannot have a single component built against it while ADR-0039 is Proposed. Ratifying removes a real, current blocker on work that will eventually need to start.
- **The architecture is sound and complete.** Interface-based, Maven/Gradle-default, Jenkins-optional — there is no infrastructure lock-in and no unresolved design question standing in ratification's way.
- **It clears the way for downstream work.** Layer 5's own architecture-freeze ADR is explicitly gated on this one (per ADR-0039 Recommendation 1); ratifying lets that work begin whenever it's scheduled, rather than waiting on it first.
- **The suite a future Layer 5 would run is meaningfully better than it used to be.** Recent quality fixes (DOM-grounded page-object locators, CP4's referential-grounding tally, the CP7 rating gate, the test-data Option B stopgap) mean that whenever Layer 5 does get built, it inherits a less-broken foundation than existed even a few weeks ago.

## 5. The case against ratifying now / for waiting

- **Ratifying unblocks a layer nothing can usefully build against yet.** The real blockers to a runnable suite — page-object activation and test-data coverage — sit outside ADR-0039 entirely and are unaffected by this vote. Ratification alone changes nothing about what actually runs today.
- **The distance from here to a running suite is large, and ADR-0039 is only the first, cheapest step in it.** The full chain is: ratify ADR-0039 → write and freeze Layer 5's own architecture ADR (resolving D2) → implement Layer 5 from an empty placeholder → activate page-object generation → close more of the test-data gap. Treating ratification as a milestone risks it reading as more progress than it is.
- **There is no urgency forcing this vote now.** Nothing is currently waiting to consume a ratified ADR-0039 — no Layer 5 implementation is queued, no sprint depends on it this week. Ratifying ahead of that work being scheduled buys governance clearance the platform isn't yet positioned to spend.
- **Ratifying and then leaving Layer 5 unbuilt doesn't change anything practical.** It moves the ADR's own status line from "Proposed" to "Accepted-but-unbuilt" — a paperwork state change — while `test_execution/` remains exactly the placeholder it is today.

## 6. The sequencing question (the real decision)

Since ratification is cheap but not sufficient on its own, the actual question isn't "is ADR-0039 good architecture" — it evidently is — but *when* to spend the ARB's approval on it:

- **Ratify now** — clear the governance gate early so Layer 5 work can start the moment it's scheduled, with no ADR-approval step sitting on that critical path later.
- **Wait** — ratify as part of actually committing to the Layer 5 build, bundled with a real plan for resolving D2, and alongside progress on the page-object-activation and test-data constraints, so ratification reads as "we're building this" rather than a standalone vote with nothing behind it yet.

Note: the same ARB session could also weigh the [ADR-0032 freeze-lift case](adr-0032-freeze-lift-case.md) (test-data Option A). The two are procedurally similar — both are ARB-vote unblocks — but substantively independent; one governs Layer 1's test-data elicitation, the other Layer 5's execution backend. Bundling them on one agenda is a scheduling convenience, not a substantive link.

Either way, the honest framing holds: ratifying ADR-0039 is low-cost and unblocks the layer, but its value is only realized once the page-object-activation and test-data constraints are also addressed and Layer 5 is actually built.

## 7. Framing for the decision

ADR-0039 is the cheapest and most clearly-decided of Layer 5's blockers — a thin checklist, one deliberately deferred technical item, one procedural vote. But it is not the binding constraint on Layer 5's eventual value; page-object activation is closer to that, with test-data coverage close behind. Ratifying now is defensible as clearing the gate early, before it can block scheduled work. Waiting is equally defensible as ratifying only when the platform is actually ready to build — so "Accepted" means "underway," not "approved and idle." Either way, ratification by itself does not produce a runnable suite. This memo doesn't make that call — it surfaces the thin checklist, what ratification does and doesn't unblock, and the sequencing question, so the ARB can decide.

---

*Prepared as decision-support. Facts verified against the repo; ratification is the ARB's/Nitin's to decide.*
