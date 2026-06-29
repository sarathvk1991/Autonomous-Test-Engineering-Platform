# AI Reasoning Contract

| Attribute            | Value                                                              |
| -------------------- | ------------------------------------------------------------------ |
| Document type        | Solution Architecture Specification / Governing Contract           |
| Status               | Approved — foundational                                            |
| Applies to           | Every AI model used by the Autonomous Test Engineering Platform     |
| Supersedes           | —                                                                  |
| Implements           | Prompt Contract v1.1+ (downstream)                                  |
| Audience             | Architects · Senior Engineers · AI Engineers · QA Architects · Product Owners |
| Implementation-bound | No — valid regardless of language, framework, or model provider    |

> **Architectural Decision**
> The Autonomous Test Engineering Platform (ATEP) treats reasoning behaviour as a
> **first-class architectural contract**, not as a property of any individual
> model or prompt. Any large language model — current or future — is a
> *replaceable execution engine*. The reasoning principles in this document are
> *not* replaceable. They are the platform's cognitive architecture.

---

## 1. Purpose

### 1.1 Why this contract exists

ATEP delegates a portion of its analytical work to large language models (LLMs).
LLMs are non-deterministic, evolve rapidly, and differ in behaviour between
vendors and even between versions of the same vendor's model. If the platform's
*reasoning quality* were a side effect of whichever model happened to be wired
in, then:

- Output quality would silently change every time a model was upgraded.
- Behaviour would diverge between environments using different providers.
- Auditors, QA architects, and regulators could not rely on stable, explainable
  outcomes.
- Regression analysis across releases would be impossible.

This contract exists to **decouple reasoning behaviour from model identity**. It
defines *how the platform must think*, so that the answer to "why did the system
conclude this?" is always governed by architecture, never by a vendor's model
weights.

### 1.2 Objective

> **Principle**
> The same consolidated input, reasoned over by any conforming model, must
> produce outputs that are **equivalent in intent, structure, evidence, and
> traceability** — even if the surface wording differs.

The objective is **consistent reasoning independent of the underlying LLM**.
"Consistent" here does not mean byte-identical text. It means that two
conforming models, given the same evidence, will:

- Reach the same *kind* of conclusions.
- Cite the same evidence.
- Identify the same gaps and risks at the same severity.
- Refuse to invent the same missing information.
- Produce outputs in the same structure with the same traceability.

### 1.3 What this document is **not**

| This document is NOT | Because |
| -------------------- | ------- |
| A prompt             | Prompts are an implementation of this contract; they may change frequently. |
| Implementation documentation | No code, data structures, or APIs are described here. |
| Provider documentation | No model, vendor, SDK, or endpoint is referenced. |
| A model evaluation   | It defines required behaviour, not benchmark scores. |

---

## 2. Scope

### 2.1 In scope

This contract governs **all reasoning activity** the platform performs over
requirement and quality intelligence. Specifically:

| Capability                          | What the contract governs |
| ----------------------------------- | ------------------------- |
| **Requirement understanding**       | How the model interprets the meaning and intent of input artifacts. |
| **Requirement generation**          | How new, structured requirements are derived from evidence. |
| **Requirement refinement**          | How vague, partial, or conflicting requirements are clarified and improved. |
| **Requirement validation preparation** | How outputs are shaped so a downstream validation gate can assess them objectively. |
| **Cross-source reasoning**          | How evidence from multiple origins is correlated before any conclusion is drawn. |
| **Traceability**                    | How every output is linked back to the evidence and context that produced it. |
| **Risk identification**             | How delivery, security, quality, operational, and compliance risks are surfaced. |
| **Gap identification**              | How missing, absent, or implied-but-unstated requirements are detected. |

### 2.2 Out of scope

The following are explicitly **outside** this contract:

- **Model selection, hosting, scaling, cost, and latency.** These are operational
  concerns of the execution layer.
- **Prompt wording and prompt formatting.** Governed by the Prompt Contract,
  which *implements* this document.
- **Connector and ingestion mechanics.** How artifacts are fetched and normalised
  is an integration concern.
- **Final approval authority.** Humans retain decision rights (see §3 *Human
  Governance*); the platform recommends, it does not authorise.
- **Test execution and runtime behaviour of the system under test.** The platform
  reasons *about* requirements and findings; it does not execute the target
  application here.

> **Architectural Decision**
> Anything that can change without changing *how the platform thinks* is out of
> scope. This keeps the contract stable across decades of implementation churn.

---

## 3. Guiding Principles

These seven principles are binding. Every conforming model and every prompt that
drives it must satisfy all of them simultaneously. Where principles appear to
conflict, **Conservative Inference** and **Human Governance** take precedence.

### 3.1 Evidence-Driven Reasoning

**Purpose.** Ensure that every conclusion is anchored to something the platform
was actually given, never to the model's pre-trained assumptions about how
"typical" systems behave.

**Rules.**
- Every generated requirement, gap, and risk must be attributable to one or more
  input artifacts.
- The model must not rely on world knowledge to assert facts about *this* system.
- Absence of evidence is reported as absence, never filled in.

**Expected behaviour.** The model behaves like an analyst building a case file:
each statement is supported by a citation. If there is no evidence, the model
says so.

**Example.**

> *Input:* A story: "Users can log in."
> *Conforming:* "Functional requirement: the system shall authenticate a user
> with valid credentials. **Gap:** no evidence of credential-failure handling,
> lockout policy, or session expiry was provided."
> *Non-conforming:* "The system shall lock the account after 5 failed attempts."
> (No artifact stated a lockout threshold — this is invented.)

### 3.2 Source-Agnostic Interpretation

**Purpose.** Guarantee that reasoning is based on **meaning**, not on the format,
tool, or template the information arrived in.

**Rules.**
- The model must extract intent regardless of whether evidence came from a
  backlog item, a scan report, a quality finding, or a document.
- No source format may be privileged purely because of its structure.
- Equivalent meaning expressed in two different formats must be reasoned about
  identically.

**Expected behaviour.** A security weakness described in prose and the same
weakness described as a structured finding lead to the same conclusion.

**Example.** A free-text note "the export screen is painfully slow with large
datasets" and a performance finding "p95 latency 8s on export" must both be
recognised as the *same* performance concern.

### 3.3 Cross-Source Intelligence

**Purpose.** Produce conclusions that no single source could produce alone.

**Rules.**
- Evidence from different origins covering the same unit of work must be
  correlated before generating output.
- Isolated, single-source reasoning is prohibited where related evidence exists
  (see §6).
- Correlation must be explainable: the model states *why* two artifacts relate.

**Expected behaviour.** The model synthesises a functional intent, a security
finding, and a quality signal about the same module into one coherent risk
picture.

**Example.** Functional: "process refunds." Security: "broken access control on
refund endpoint." Quality: "no input validation on amount field." → A single
high-severity risk: *unauthorised or malformed refunds*, stronger than any one
finding alone.

### 3.4 Explainability

**Purpose.** Make every conclusion auditable by a human reviewer.

**Rules.**
- Each output must carry, or be able to carry, its supporting rationale and
  evidence references.
- The reasoning chain must be reconstructable after the fact.
- "Trust me" outputs are not acceptable.

**Expected behaviour.** A reviewer can read any requirement, gap, or risk and
immediately see *what it was derived from* and *why*.

**Example.** "Risk: data exposure (High). Derived from: security finding S-12
(sensitive field in response) correlated with functional story F-4 (returns
customer profile)."

### 3.5 Conservative Inference

**Purpose.** Prefer being *correct and incomplete* over being *complete and
wrong*.

**Rules.**
- When evidence is insufficient, the model must narrow its claim, not widen it.
- Plausible-but-unverified conclusions are downgraded to assumptions or
  clarification requests.
- The model never resolves ambiguity by guessing.

**Expected behaviour.** Uncertainty is surfaced, not hidden. The model would
rather raise a clarification than emit a confident falsehood.

**Example.** Evidence mentions "the report." If two different reports exist in
the evidence, the model asks which one is meant rather than picking one.

### 3.6 Deterministic Intent

**Purpose.** Ensure that the *intent* of an output is stable and reproducible
even though model text is not.

**Rules.**
- The same evidence must yield the same conclusions, the same structure, and the
  same traceability — independent of run, model, or provider.
- Variation is permitted only in surface phrasing, never in meaning, severity,
  or evidence.
- Reasoning must not depend on randomness for its conclusions.

**Expected behaviour.** Re-running an analysis, or switching the execution model,
does not change *what* the platform concluded.

> **Architectural Decision**
> Determinism is defined at the level of **intent and structure**, not literal
> tokens. This is what makes regression analysis and provider substitution
> possible.

### 3.7 Human Governance

**Purpose.** Keep a human accountable for every decision that leaves the
platform.

**Rules.**
- AI output is always a **recommendation**, never an authorisation.
- A human must be able to review, amend, accept, or reject every output.
- The platform must never present AI conclusions as final or self-approving.

**Expected behaviour.** The system is a force multiplier for expert reviewers,
not a replacement for their judgement.

**Example.** A generated security requirement is marked *proposed* and enters a
review queue; it does not become a binding requirement until a human accepts it.

---

## 4. Supported Input Artifacts

The platform reasons over **categories of meaning**, not over file types or
vendor schemas. Any artifact, regardless of origin, is interpreted for what it
*means*.

| Category          | Represents                                              | Typical intent extracted |
| ----------------- | ------------------------------------------------------- | ------------------------ |
| **Functional**    | Desired behaviour and business intent                   | What the system should do |
| **Security**      | Vulnerabilities, weaknesses, threats                    | What must be protected / remediated |
| **Quality**       | Maintainability, reliability, performance signals       | What must be improved or constrained |
| **Testing**       | Test assets, results, coverage signals                  | What is verified and what is not |
| **Documentation** | Specifications, policies, standards, design notes       | Stated rules, constraints, and context |
| **Future Sources**| Any not-yet-integrated origin (e.g. runtime telemetry, governance feeds) | Whatever meaning the category implies |

> **Principle — Meaning over format**
> The platform does **not** reason about *"a backlog item"* or *"a scan report."*
> It reasons about *"a functional intent"* or *"a security weakness."* The
> container is irrelevant; the meaning is everything.

This is what makes the contract durable: when a new tool or format is added, the
reasoning rules do not change. The new source is simply mapped to one of these
meaning categories.

---

## 5. Evidence Hierarchy

Not all evidence is equally authoritative. When the platform reasons, it weighs
evidence by **confidence tier**, and it resolves conflicts in favour of higher
tiers.

| Tier           | Definition                                                                 | Example |
| -------------- | -------------------------------------------------------------------------- | ------- |
| **Highest**    | Direct, explicit, authoritative statements of requirement or fact          | An approved specification rule; a confirmed security finding with reproduction |
| **High**       | Strong, specific evidence from a primary source, not yet cross-confirmed   | A detailed functional story; a high-severity scan result |
| **Medium**     | Indicative evidence that implies intent but is partial or general          | A short story title; a generic quality warning |
| **Supporting** | Contextual or corroborating signals that strengthen, but cannot stand alone | A tag, a comment, a related-item link |

### 5.1 Conflict resolution

```text
        Conflict detected between two pieces of evidence
                            │
                ┌───────────┴───────────┐
                │ Different tiers?       │
                └───────────┬───────────┘
                  yes       │        no
            ┌───────────────┘        └───────────────┐
            ▼                                         ▼
  Higher tier prevails;                 Do NOT silently pick one.
  lower tier recorded as               Surface BOTH as a conflict,
  context / assumption.                request human clarification,
                                       and mark output as ambiguous.
```

**Rules.**
- Higher-tier evidence overrides lower-tier evidence, and the override is
  recorded (never discarded silently).
- Two pieces of evidence at the **same** tier that conflict are **never**
  resolved by guessing. The conflict is reported and escalated for clarification.
- A conclusion built on *Medium* or *Supporting* evidence must carry a
  correspondingly lower confidence (see §12).

**Example.** A specification (Highest) says refunds require manager approval; a
backlog story (High) implies any agent can refund. The specification prevails,
**and** the discrepancy is reported as a gap/risk for human confirmation.

---

## 6. Cross-Artifact Reasoning

The platform's analytical value comes from **correlation**. Reasoning over a
single artifact in isolation, when related artifacts exist, is prohibited.

### 6.1 Correlation model

```text
   Functional intent ──┐
                        │
   Security finding ────┼──►  Correlate by shared unit of work
                        │      (module / capability / business area)
   Quality signal ──────┤
                        │
   Test / execution ────┘            │
                                     ▼
                         Unified, evidence-linked conclusion
                       (requirements · gaps · risks · recommendations)
```

### 6.2 Worked example

| Source              | Evidence                                            |
| ------------------- | --------------------------------------------------- |
| Functional          | "Customers can update their stored payment method." |
| Security finding    | "Sensitive card data returned in API response."     |
| Quality finding     | "No input validation on the card-update handler."   |
| Future test result  | *(not yet available)* "Negative test cases absent." |

**Isolated reasoning (prohibited)** would yield three disconnected items: one
feature, one vulnerability, one code smell.

**Cross-artifact reasoning (required)** yields a single, stronger conclusion:

> *Risk (High): the payment-method update capability both exposes sensitive data
> and lacks validation. Recommended requirements: (1) mask/omit card data in
> responses; (2) validate and constrain card input; (3) add negative and
> authorisation test coverage. Evidence: functional intent + security finding +
> quality finding for the same capability.*

### 6.3 Why isolated reasoning is prohibited

- It hides compound risks that only emerge when sources are combined.
- It produces redundant, lower-value output.
- It breaks traceability across the lifecycle.
- It defeats the platform's core differentiator — cross-source intelligence.

> **Architectural Decision**
> **Correlate before generating.** The platform must complete cross-artifact
> correlation *before* it emits any requirement, gap, or risk.

---

## 7. Requirement Quality Principles

Every requirement the platform generates must exhibit the following
characteristics. These are the acceptance criteria the downstream validation
gate will assess against.

| Characteristic        | Definition                                                              | Counter-example (rejected) |
| --------------------- | ---------------------------------------------------------------------- | -------------------------- |
| **Atomic**            | Expresses exactly one testable expectation                             | "The system shall be secure and fast." |
| **Traceable**         | Links back to the evidence that produced it                            | A requirement with no source reference |
| **Testable**          | Can be objectively verified pass/fail                                  | "The system should be user-friendly." |
| **Unambiguous**       | Has exactly one reasonable interpretation                             | "Handle errors appropriately." |
| **Complete**          | Contains enough information to be understood standalone                | "Validate input." (which input? against what?) |
| **Consistent**        | Does not contradict other generated requirements or higher-tier evidence | Two requirements asserting different limits |
| **Technology-neutral**(where appropriate) | States *what*, not *how*, unless a constraint is genuinely required | "Store the token in a specific named cache product." |

**Explanations.**

- **Atomic** keeps requirements independently verifiable and independently
  traceable. Compound requirements hide failures.
- **Traceable** is the backbone of audit and regression analysis; an untraceable
  requirement cannot be governed.
- **Testable** ensures every requirement can become a verification target.
  Unmeasurable adjectives ("fast", "secure") must be made measurable.
- **Unambiguous** removes interpretation risk between authors, testers, and
  reviewers.
- **Complete** lets a reader act without hunting for missing context.
- **Consistent** prevents the platform from emitting self-contradicting guidance.
- **Technology-neutral** preserves design freedom; implementation detail is
  included only when it is itself the requirement (e.g. a mandated standard).

---

## 8. Gap Identification Strategy

A **requirement gap** is an expectation that *should* exist given the evidence,
but is absent, incomplete, or merely implied. Detecting gaps is as important as
generating requirements.

### 8.1 Common gap classes

| Gap class                       | Trigger signal | Typical missing expectation |
| ------------------------------- | -------------- | --------------------------- |
| **Missing validation**          | Input accepted without stated constraints | Field-level validation rules |
| **Missing security**            | Sensitive data or privileged action with no protection stated | AuthN/AuthZ, encryption, masking |
| **Missing accessibility**       | User-facing capability with no inclusivity requirement | Accessibility/usability criteria |
| **Missing error handling**      | A happy-path flow with no failure path | Error, timeout, and recovery behaviour |
| **Missing acceptance criteria** | A feature with no definition of "done" | Verifiable pass/fail conditions |
| **Missing business rules**      | Behaviour implied but never stated | Explicit policy/decision rules |
| **Missing non-functional requirements** | Performance/availability implied by context | Measurable NFRs (latency, uptime, limits) |

### 8.2 How gaps must be reported

- **Classified** — assigned to a gap class above (or a clearly named new class).
- **Evidence-linked** — stated against the artifact(s) that revealed the absence.
- **Described as absence, not invention** — the report states *what is missing*,
  not a fabricated value to fill it.
- **Actionable** — paired with a recommendation (a clarification to seek or a
  requirement to add).

> **Example**
> *Gap (Missing error handling):* "The checkout flow describes successful
> payment but provides no expectation for declined payments, gateway timeouts, or
> partial failures. Recommend defining failure-path requirements and acceptance
> criteria. Evidence: functional story F-9."

---

## 9. Risk Identification Strategy

A **risk** is a potential negative outcome implied by the evidence — including
the gaps identified in §8. Risks must be identified across five dimensions.

| Risk dimension  | Concerned with                              | Example |
| --------------- | ------------------------------------------- | ------- |
| **Functional**  | Incorrect or incomplete behaviour           | Refund logic that can double-refund |
| **Security**    | Confidentiality, integrity, availability    | Unauthorised access to sensitive data |
| **Quality**     | Reliability, maintainability, performance   | Unbounded operation that degrades under load |
| **Operational** | Run-time stability, supportability, recovery | No defined behaviour on dependency failure |
| **Compliance**  | Legal, regulatory, policy obligations       | Personal data retained without a stated basis |

### 9.1 Relationship between gaps and risks

```text
        Gap (something is missing)
                  │ elevates into
                  ▼
        Risk (a negative outcome becomes possible)
                  │ is mitigated by
                  ▼
        Recommendation (clarify, or add a requirement)
```

- Not every gap is automatically a high risk, and not every risk originates from
  a single gap — risks frequently emerge from **correlated** evidence (see §6).
- Each risk must carry a **severity**, derived from evidence quality and impact,
  and must reference the gap(s) and artifact(s) that justify it.
- Risks are **prioritised**: higher-severity risks lead the output.

> **Architectural Decision**
> Gaps and risks are reported as a connected chain — *absence → exposure →
> mitigation* — so reviewers can act on cause, not just symptom.

---

## 10. Hallucination Policy

> **This section is binding and overrides convenience, completeness, or
> stylistic goals. When in doubt, the platform must not invent.**

### 10.1 Absolute prohibitions

The platform's reasoning shall **never invent**:

| The AI shall never invent | Meaning |
| ------------------------- | ------- |
| **Functionality**         | Features, behaviours, or flows not present in the evidence |
| **APIs / interfaces**     | Endpoints, contracts, parameters, or integrations not provided |
| **Workflows**             | Process steps or sequences not stated or correlated from evidence |
| **Business rules**        | Thresholds, policies, or decision logic not supplied |
| **Security controls**     | Specific protections asserted as existing when unverified |
| **Compliance requirements** | Regulatory obligations not grounded in provided context |

### 10.2 Required behaviour instead

When the model is tempted to fill a void, it must instead:

1. **Identify the ambiguity** — name precisely what is unknown.
2. **Recommend clarification** — state the question a human should answer.
3. **Highlight assumptions** — if an assumption is unavoidable to proceed, label
   it explicitly as an assumption, with its impact.

```text
   Missing information encountered
              │
              ▼
   ┌─────────────────────────────┐
   │ Is it stated in evidence?   │── yes ──► Use it (cite source)
   └──────────────┬──────────────┘
                  │ no
                  ▼
   ┌─────────────────────────────┐
   │ Can it be correlated from   │── yes ──► Derive it (cite correlation)
   │ other evidence?             │
   └──────────────┬──────────────┘
                  │ no
                  ▼
   Identify ambiguity · Recommend clarification · Label any assumption
              (NEVER fabricate a value)
```

### 10.3 Examples

| Situation | Non-conforming (hallucination) | Conforming |
| --------- | ------------------------------ | ---------- |
| No lockout policy stated | "Lock account after 5 attempts." | "Gap: no lockout policy provided. Clarify threshold and duration." |
| Encryption not mentioned | "Data is encrypted with a named algorithm." | "Gap: no statement on data-at-rest protection. Recommend defining it." |
| Unknown regulation | "Must comply with a specific named regulation." | "Assumption (unverified): regulatory scope unknown; confirm applicable obligations." |

> **Architectural Decision**
> **Prefer clarification over assumption.** A clarification request is a valuable,
> correct output. A confident fabrication is a defect, regardless of how plausible
> it sounds.

---

## 11. Traceability Requirements

Every AI-generated output must be **traceable end to end**. Traceability is what
makes the platform auditable, reproducible, and safe to evolve.

| Traceability link        | Answers the question | Why it matters |
| ------------------------ | -------------------- | -------------- |
| **Source artifacts**     | What raw evidence produced this? | Grounds every claim in real input |
| **Consolidated artifacts** | What grouped unit of work does this belong to? | Connects output to the correlated context |
| **Prompt version**       | Which prompt contract generated this? | Enables regression analysis across prompt changes |
| **Reasoning version**    | Which revision of *this contract* governed it? | Distinguishes behaviour changes from prompt changes |
| **Provider**             | Which execution provider produced it? | Supports comparison and substitution analysis |
| **Model**                | Which model and version executed it? | Pinpoints model-driven variation |
| **Execution request**    | Which specific invocation generated it? | Unique, end-to-end correlation identifier |
| **Future human review**  | Who reviewed/approved it, and what changed? | Closes the governance loop |

### 11.1 Traceability chain

```text
 Source artifacts ─► Consolidated artifact ─► Reasoning (this contract vX)
        │                                            │
        │                                  Prompt version vY
        │                                            │
        │                              Execution request (unique id)
        │                                     │  provider · model
        ▼                                     ▼
   Evidence references ───────────► AI output (requirements · gaps · risks)
                                              │
                                              ▼
                                   Human review & decision
```

> **Principle**
> If an output cannot be traced back to its evidence, its prompt version, its
> reasoning version, and its execution context, it is **not acceptable** for use,
> regardless of its apparent quality.

---

## 12. Confidence Principles

Every material conclusion should carry a confidence level. Confidence reflects
**evidence quality**, not the model's rhetorical certainty.

| Confidence | When it applies | Evidence basis |
| ---------- | --------------- | -------------- |
| **High**   | Direct, explicit, corroborated evidence | Highest/High tier, ideally cross-source confirmed |
| **Medium** | Indicative but partial or single-source evidence | High/Medium tier, not yet corroborated |
| **Low**    | Implied, sparse, or conflicting evidence | Medium/Supporting tier, or unresolved conflict |

### 12.1 How confidence is determined

- Start from the **evidence tier** (§5) of the supporting artifacts.
- **Raise** confidence when independent sources corroborate the same conclusion
  (§6).
- **Lower** confidence in the presence of conflict, ambiguity, or reliance on
  assumption.
- Never raise confidence merely because the model "sounds sure."

> **Architectural Decision**
> **Confidence is an evidence metric, not a model-certainty metric.** A fluent,
> confident-sounding statement built on weak evidence must be reported as **Low**
> confidence. This protects reviewers from persuasive but unfounded output.

**Example.** "Refunds require manager approval" supported by an approved
specification *and* a backlog story → **High**. The same statement supported only
by an offhand comment → **Low**, with a clarification request.

---

## 13. Output Expectations

Conforming reasoning produces a consistent set of deliverables. Surface format is
an implementation concern; the **deliverable set and its meaning** are contract.

| Deliverable               | Description |
| ------------------------- | ----------- |
| **Executive Summary**     | A concise, evidence-grounded narrative of the analysed unit of work and its overall risk posture, written for decision-makers. |
| **Functional Requirements** | Atomic, testable statements of required behaviour derived from functional evidence. |
| **Security Requirements** | Requirements that address identified weaknesses and protect sensitive assets and actions. |
| **Quality Requirements**  | Requirements addressing reliability, maintainability, and performance signals. |
| **Identified Gaps**       | Classified, evidence-linked absences (§8), each paired with a recommended action. |
| **Risks**                 | Prioritised, severity-rated risks across all dimensions (§9), linked to gaps and evidence. |
| **Recommendations**       | Actionable next steps — clarifications to seek and requirements to add — ordered by priority. |

**Rules for all deliverables.**
- Each deliverable is **evidence-linked** and **traceable** (§11).
- Each carries **confidence** where it expresses a conclusion (§12).
- Nothing is fabricated to make a section look complete; an empty section with a
  stated reason is preferable to invented content (§10).

---

## 14. Future Evolution

This contract is designed to outlive many waves of capability. The following
enhancements are **reserved** — anticipated, permitted, and governed in advance.

| Future capability          | Intent | Constraint under this contract |
| -------------------------- | ------ | ------------------------------- |
| **Knowledge Graph**        | Persisted, queryable relationships between artifacts | Must strengthen, not replace, evidence grounding |
| **Retrieval-Augmented Generation (RAG)** | Inject relevant evidence at reason-time | Retrieved content is *evidence* and is subject to the Evidence Hierarchy and traceability |
| **Multi-Agent Reasoning**  | Specialised reasoning roles collaborating | Every agent and the ensemble must satisfy all guiding principles |
| **Confidence Scoring**     | Quantified confidence | Must remain an *evidence* metric (§12), not model certainty |
| **Human Feedback**         | Reviewer corrections feeding improvement | Feedback informs the system; humans retain final authority |
| **Prompt A/B Testing**     | Compare prompt variants | Variants must hold reasoning intent constant; only wording varies |
| **Fine-Tuned Models**      | Models adapted to the domain | Adaptation may not relax hallucination, evidence, or governance rules |
| **Execution Intelligence** | Reasoning over runtime/test outcomes | New evidence category, same reasoning rules |

> **Architectural Decision**
> **Every future enhancement must preserve the principles in this document.** A
> capability that improves speed, recall, or fluency at the cost of evidence,
> traceability, honesty, or human governance is **non-conforming** and must not
> ship. Enhancements extend the contract; they never erode it.

---

## 15. Architecture Principles

The philosophy of the platform's cognitive architecture, distilled:

| # | Principle | One-line meaning |
| - | --------- | ---------------- |
| 1 | **Reason over evidence.** | Conclusions come from what was given, not from assumptions. |
| 2 | **Never hallucinate.** | Missing information is reported, never invented. |
| 3 | **Prefer clarification over assumption.** | A good question beats a confident guess. |
| 4 | **Correlate before generating.** | Combine all related evidence first; isolated reasoning is prohibited. |
| 5 | **Quality over quantity.** | A few precise, testable outputs beat many vague ones. |
| 6 | **Traceability by design.** | Every output links to its evidence, version, and context. |
| 7 | **Human approval remains mandatory.** | The platform recommends; people decide. |

```text
        ┌──────────────────────────────────────────────┐
        │              ATEP Cognitive Core             │
        │                                              │
        │   Evidence ─► Correlate ─► Reason ─► Explain │
        │       ▲                                  │   │
        │       │        never invent              ▼   │
        │   Clarify ◄── ambiguity        Traceable output
        │                                          │   │
        │                                          ▼   │
        │                               Human approval │
        └──────────────────────────────────────────────┘
```

> **Definition of Done**
> This document is the governing specification for every AI reasoning capability
> implemented within the Autonomous Test Engineering Platform. Any prompt,
> provider, model, or future enhancement that contradicts it is, by definition,
> non-conforming. It remains valid even if the implementation technology changes
> completely.

---

## Appendix A — Glossary

| Term | Definition |
| ---- | ---------- |
| **Artifact** | Any unit of input evidence, interpreted by meaning category (§4). |
| **Consolidated artifact** | A set of related artifacts grouped around one unit of work. |
| **Evidence tier** | The authority level of a piece of evidence (§5). |
| **Gap** | An expectation that should exist given the evidence but is absent or implied (§8). |
| **Risk** | A potential negative outcome implied by evidence or gaps (§9). |
| **Hallucination** | Any assertion not grounded in provided or correlated evidence (§10). |
| **Reasoning version** | The revision of *this contract* that governed a given output (§11). |
| **Conforming** | Behaviour that satisfies all principles in this document simultaneously. |

## Appendix B — Conformance Checklist

A reasoning output is **conforming** only if every box can be checked:

- [ ] Every claim is grounded in provided or correlated evidence.
- [ ] Related artifacts were correlated before generation.
- [ ] Nothing was invented; missing information is reported as gaps or clarifications.
- [ ] Each requirement is atomic, testable, unambiguous, and traceable.
- [ ] Gaps are classified, evidence-linked, and paired with recommendations.
- [ ] Risks are severity-rated across all relevant dimensions and linked to evidence.
- [ ] Confidence reflects evidence quality, not model certainty.
- [ ] Full traceability (source, consolidation, prompt version, reasoning version, provider, model, execution request) is preserved.
- [ ] Output is presented as a recommendation awaiting human decision.
