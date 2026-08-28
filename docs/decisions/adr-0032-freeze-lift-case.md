# Decision-Support Memo: Should the ADR-0032 Layer-1 freeze be lifted to enable Option A?

**Status:** For decision — this memo does not decide; the freeze-lift is the ARB's/Nitin's call.

The platform's generated test data has been entirely empty since Layer 3 test-data generation first shipped: every real requirement produces a `TestDataSpecification` with `fields=[]`, and every generated `Req*TestData.java` is a field-less stub. The root cause is that Layer 1 never populates the two contract fields (`AcceptanceCriterion.data_fields`/`.polarity_hints`) that test-data generation depends on — the fields exist on the frozen contract, they are simply never filled in.

Two fixes exist. **Option A** — teach Layer 1's own analysis to elicit these fields at analysis time, when the model still has the raw source evidence in context — is the higher-fidelity fix, but it is new Layer 1 judgement logic, and new Layer 1 capability is frozen by ADR-0032 until a separate, ARB-approved lifting ADR names it. **Option B** — a downstream, deterministic, post-hoc derivation from a requirement's own already-finalized text — is freeze-clean and has now shipped as an explicit stopgap (commit `97d0f6e`). This memo exists because Option B's own measured limits now quantify, concretely, what lifting the freeze for Option A would actually buy — this is no longer a hypothetical trade-off. The case below lays out both sides evenhandedly; it recommends nothing.

## 1. Background

- **What's already true.** Test data was entirely empty (`fields=[]`, field-less generated stubs) for every real requirement this platform has ever analyzed. A login test has no `standard_user`/`secret_sauce`-shaped values to run with; a postal-code-format test has no values to assert boundary behavior against.
- **Root cause.** `requirement_intelligence/testable_requirement/emitter.py` constructs every `AcceptanceCriterionInput` as `AcceptanceCriterionInput(category=category, statement=statement)` — `data_fields` and `polarity_hints` are never passed, so both default to `()` on every real, emitted `TestableRequirement`. The contract fields exist (ADR-0042); Layer 1 simply never fills them.
- **This is structurally the same shape as three other fields ADR-0042 already ruled on.** `TestableRequirement.priority`, `AcceptanceCriterion.traces_to`, `Risk.category`, and `TestableRequirement.risks[]` (per-requirement attribution) are all real, reserved contract fields that ADR-0042 found `AnalysisResult` carries no honest signal for today — each is explicitly recorded as "requires a future Layer 1 signal... gated behind ADR-0032's freeze-lifting procedure." `data_fields`/`polarity_hints` were not named in that same ADR-0042 pass, but the shape is identical: a real field, no signal, gated behind the same procedure. This is not a novel argument invented for this memo — it is the precedent ADR-0042 already set for sibling fields in the same contract.
- **Two fixes, one shipped.** Option A (elicit at analysis time, Layer 1, higher fidelity) remains unbuilt and freeze-blocked. Option B (infer downstream, Layer 2, lower fidelity) shipped as an explicit, documented stopgap — never presented as the real fix.

## 2. The two fixes at a glance

| | Option A (analysis-time elicitation) | Option B (post-hoc enrichment) |
|---|---|---|
| **Where it acts** | Layer 1 (`requirement_intelligence`) — the analysis prompt/emitter | Layer 2 (`feature_engineering/stage/test_data_enrichment.py`) — downstream of Layer 1 |
| **Fidelity** | Higher — the model sees raw source evidence at analysis time | Lower — infers post-hoc from finalized, already-summarized requirement text |
| **Measured reach** | Not yet built — unmeasured | 4 of 15 real SUT requirements populated (measured, see §3) |
| **Freeze status** | **Blocked** by ADR-0032 (new Layer 1 capability; needs a lifting ADR) | **Freeze-clean** — shipped, `97d0f6e` |
| **Relationship** | The real fix, once buildable | The stopgap; yields automatically to Option A's own real signal whenever it exists — `build_test_data_specification` never overrides real Layer 1 data with the derived fallback |

The two are complementary, not competing: Option B's own code already treats real Layer 1 signal as authoritative the moment it exists, so shipping Option A later requires no rework of the downstream consumer — the spec-builder, the Layer 3 generator, and the eval harness already consume populated fields correctly, proven by Option B's own end-to-end tests.

## 3. What the stopgap's measured limits tell us

This is the key evidence this memo turns on. Measured directly against the real 15 SUT requirements (post the #2 SUT-vs-framework-SAST filter, ADR-0043 D9) using the real, shipped derivation:

- **4 of 15 populate:** three login-flow requirements (→ `username`/`password`) and one postal-code-format-validation requirement (→ `postalCode`) — arguably the highest-value, most-obviously-data-driven scenarios in the corpus, and Option B reaches all of them.
- **11 of 15 stay honestly empty** — not a defect, a documented structural limit: post-hoc text inference over a finalized, summarized statement cannot recover data needs the statement's own text never signals.
- **A documented real miss**, shown directly in the shipped test suite, not hidden: `REQ-ede9760c`, *"The system shall proceed to checkout when valid checkout information is submitted,"* is exactly the kind of requirement a human reviewer — or a model with the raw source evidence in front of it at analysis time — would read as needing `firstName`/`lastName`/`postalCode` data. Option B's own single login-domain pattern does not cover "checkout information" as a phrase, so this requirement derives nothing.

So the case for Option A is quantified, not speculative: the stopgap closes roughly a quarter of the real corpus's data-field gap (4 of 15), concentrated on the cases where a fixed vocabulary and one hand-written domain pattern happen to match the finalized text. Analysis-time elicitation — the model reasoning over raw source evidence before that evidence is compressed into a one-line requirement statement — is architecturally positioned to reach the other three-quarters, including the documented miss above.

## 4. The case FOR lifting

- **Fidelity where it measurably matters.** The 11 uncovered requirements are not obviously low-value — several (checkout information, order completion) are genuine data-driven SUT scenarios a runnable suite needs real test data for. Option B cannot close this gap by construction; only elicitation at the point where raw evidence still exists can.
- **The gating precondition is already met.** ADR-0032's freeze-lift procedure has three preconditions: (1) Layer 2 has reached Runtime Integration, (2) ARB approval, (3) a lifting ADR naming the specific CAP. Precondition 1 is independently confirmed met (`docs/architecture/mentor-feedback-scoping.md`, 2026-08-24) — what remains is procedural (drafting the ADR and bringing it to the ARB), not a substantive unmet condition.
- **Runnability is a real, near-term concern.** Test data is one of the concrete things a genuinely runnable suite needs, alongside generated page objects/step-definitions and an execution backend — an empty-data suite fails at runtime for want of input regardless of how correct everything else is.
- **The stopgap de-risks the build, it doesn't replace the need for it.** Option B already proves the downstream shape works end-to-end: the spec builder, the Layer 3 generator, and the eval harness (`check_field_coverage`) all correctly consume and verify populated specifications today. Option A would populate the identical fields at higher fidelity — it does not require redesigning anything downstream, only teaching Layer 1 to fill in signal it currently leaves blank.

## 5. The case AGAINST lifting

- **The freeze exists for a specific, deliberate reason, and it is still true today.** ADR-0032's own rationale is that this platform has a mature, well-practiced pattern for growing Layer 1 that has, historically, crowded out investment in the six unbuilt downstream layers. Layer 1 has proven it can build well; it has not proven it can stop growing once permitted to. Every capability the freeze successfully holds the line on is evidence the freeze is doing its job.
- **Every lift is a precedent, not a one-off.** Lifting for test-data elicitation specifically opens the door to the SAME argument for `priority`, `traces_to`, `Risk.category`, and per-requirement risk attribution — ADR-0042 already identified all four as sitting in the identical "real field, no signal, freeze-gated" position. If this memo's own argument (a shipped stopgap quantifies a real gap only Layer 1 can close) is accepted here, the ARB should expect to hear the same argument made for each of those four next, and should decide this case with that in mind, not as an isolated one-off.
- **The stopgap already covers the highest-value cases.** The 4 populated cases are exactly the login-credential and format-validation scenarios most likely to be exercised first and most likely to be the ones an early, partial suite actually runs. The marginal real-world value of the remaining 11 — cart/inventory/checkout-flow behavioral requirements, several of which may never need literal data values beyond what Option B already provides — may be lower than the raw 11-of-15 count implies.
- **Option A is a change to the most-frozen, most load-bearing layer in the platform.** Layer 1 has the platform's deepest test coverage and the most Accepted ADRs of any layer specifically because it has been treated as stable ground for everything above it to build on. A new elicitation capability there is a new prompt, a new output field the model must reliably populate, a new source of non-deterministic output variance, and a new regression surface on the layer every other layer depends on — a materially different risk profile than Option B's fully deterministic, LLM-free downstream module.
- **There is no imminent executor for the higher fidelity.** Layer 5 (Test Execution) is unbuilt (`test_execution/` remains a single-commit placeholder), and ADR-0039 (the execution backend) is Proposed, not Accepted. Even perfectly-elicited test data has nothing running it yet — the value of closing the fidelity gap now, before a suite exists that would consume it, is not obviously urgent.

## 6. What lifting would actually require

If the ARB chooses to proceed, the mechanism is concrete and already specified by ADR-0032 itself:

1. **Draft a new, numbered lifting ADR** stating explicitly which Layer 1 CAP number it authorizes for the new test-data-elicitation capability — the freeze lifts per-capability, never wholesale, so this must name the capability, not simply declare the freeze lifted.
2. **Architecture Review Board approval** of that specific lifting ADR — precondition 1 (Layer 2 at Runtime Integration) is already satisfied; this approval is the remaining substantive gate.
3. **Then Option A is buildable**: extend the analysis prompt to elicit `data_fields`/`polarity_hints`, and wire the emitter to pass them through into `AcceptanceCriterionInput`. No downstream rework is required — `build_test_data_specification`, the Layer 3 test-data generator, and the eval harness's `check_field_coverage` already consume and verify populated specifications correctly, proven by Option B's own end-to-end tests.

Separately: ADR-0039 (Layer 5 execution backend) is also Proposed and also awaits ARB ratification. The two are procedurally similar (both are ARB agenda items) but substantively independent — ratifying one does nothing for the other's own content. If the ARB is convening regardless, considering both in the same session is a scheduling convenience, not a dependency between them.

## 7. Framing for the decision

The honest shape of this decision: Option A is, on fidelity alone, clearly the better fix — that is not seriously in dispute. Option B adequately covers the highest-value data (login-credential and format-validation scenarios) today, at zero governance cost. Option A would cover the rest, at the cost of a change to Layer 1 and an ARB-approved freeze lift, with no imminent consumer (Layer 5) yet built to run the result.

So the decision turns less on "is Option A better" and more on **timing and precedent**: close the measured 11-of-15 gap now, while nothing yet runs the suite it would feed — or sequence the lift with Layer 5 becoming real, so higher-fidelity data arrives paired with something that actually executes against it? A middle path exists and is worth naming, without this memo recommending it: draft the lifting ADR now, so it is ready and vetted, but time the actual freeze lift and Option A build to when Layer 5 is genuinely near completion — pairing the higher-fidelity fix with a real consumer rather than building ahead of one, the same discipline this platform has applied to its other deferred-pending-consumer decisions.

This memo does not make that call. It surfaces the evidence, the two-sided case, and the concrete mechanism, so the ARB and Nitin can decide with the real numbers in front of them.

---

*Prepared as decision-support. All figures measured against the real corpus; the freeze-lift decision is the ARB's/Nitin's to make.*
