# ADR-0041 — Java Stack for the Generated Test Suite

- **Status:** Accepted
- **Date:** 2026-07-24
- **Supersedes:** nothing. **Amends:** nothing. **Resolves:** ADR-0037's Java-stack TBD ("The concrete Java stack: build tool ... To be mined from the `Automation-POC` repository's actual choices, not chosen fresh (D4)" — `docs/adr/0037-generated-test-suite-target-and-sut-binding.md`, TBD section). An inline resolution note is added at that TBD bullet — see ADR-0037 for the added text. No other line of ADR-0037 changes.
- **Governing design:** none.
- **Depends on:** ADR-0037 (Generated Test Suite Target and SUT Binding — origin of the TBD this ADR resolves, and owner of the tracked-baseline/untracked-workspace split D3 and D5 below operate inside); ADR-0040 (Control Point Model and Layer 4 Redefinition — CP3 scans this stack's generated Java output using the `customqa:*` profile ADR-0037 already locked); ADR-0039 (Execution Backend and CI/CD — **Proposed, not Accepted** — the execution backend that will eventually run this stack's build; this ADR specifies what ADR-0039's "local Maven runner as default implementation" concretely runs, without depending on ADR-0039 being ratified).
- **Runtime status:** Not applicable. Documentation-only. This ADR creates no Java module, no `pom.xml`, no build configuration, and no code in this repository. It specifies what a future implementation task must build.

## Provenance — read before trusting any value below

ADR-0037 directed that this stack be "mined from the sibling `Automation-POC` repository's actual choices" (§D4). `Automation-POC` is not part of this repository. `docs/reference/automation-poc/pom.xml` **does exist** in this repository (a reference copy, established under ADR-0040's `docs/reference/` tree), so it was read in full and every decision below was checked against it directly rather than taken on trust.

Two classes of value follow:

1. **Values verified by direct citation of `docs/reference/automation-poc/pom.xml`** — Cucumber 7.18.0, JUnit Platform 1.10.3, JUnit Jupiter 5.10.3, Selenium 4.25.0, package root `com.automation`, and feature-file placement (also independently confirmed in `docs/reference/automation-poc/prompts/generate-feature.md` and `generate-test-data.md`).
2. **Decisions that diverge from what the pom.xml currently does** — BOM-based dependency management (D2), the exclusion of WebDriverManager (D5), and `maven.compiler.release` in place of separate `source`/`target` properties (D1). These were **supplied directly by the platform owner on 2026-07-24**, as a deliberate correction to the POC's own current practice, not as a report of what the POC does today. Each divergence is called out explicitly below rather than silently harmonized with the pom.xml. Where this ADR states a value that differs from the committed pom.xml, that is intentional and the discrepancy is recorded, not an error in either document.

## Decision

### D1 — Build tool and language level

**Maven**, `pom.xml`. **Java 21**, expressed as `maven.compiler.release = 21`.

*Discrepancy noted:* `docs/reference/automation-poc/pom.xml` does not use `maven.compiler.release`; it sets `<maven.compiler.source>21</maven.compiler.source>` and `<maven.compiler.target>21</maven.compiler.target>` (lines 15–16) as separate properties, and repeats `<source>21</source>`/`<target>21</target>` in the `maven-compiler-plugin` configuration (lines 110–111). Both approaches select Java 21 as the source and target level; `release` additionally constrains compilation to the Java 21 API surface (rejecting use of newer JDK APIs even when compiling with a newer JDK), which `source`/`target` alone does not. This ADR adopts `release` as the stricter, single-property form for the tracked baseline going forward.

### D2 — Dependency versions are BOM-managed

Import `junit-bom:5.10.3` and `cucumber-bom:7.18.x` in `dependencyManagement`; declare member artifacts (`junit-jupiter-api`, `junit-platform-suite`, `junit-platform-launcher`, `cucumber-java`, `cucumber-junit-platform-engine`, etc.) without individual version tags.

**Rationale.** JUnit Platform (1.10.3) and JUnit Jupiter (5.10.3) are separate version lines that pair by generation, not by number. Hand-pinning them in separate places guarantees drift. The owner-supplied "JUnit Platform 1.10.3" is therefore recorded as `junit-bom:5.10.3`, which manages Platform 1.10.3 as its member.

**Discrepancy noted:** `docs/reference/automation-poc/pom.xml` does not use BOM imports or a `dependencyManagement` block at all. It hand-pins `junit.platform.version = 1.10.3` and `cucumber.version = 7.18.0` as raw properties (lines 22–23) and hard-codes `junit-jupiter-api` to literal `5.10.3` (line 81) with no property indirection. The two numbers the POC hand-pins — Platform 1.10.3 and Jupiter 5.10.3 — happen to be exactly the pair `junit-bom:5.10.3` manages, which is confirmation the pairing is correct, not evidence the POC uses BOM management; it does not. This ADR's BOM decision is new discipline layered on top of the POC's verified version numbers, adopted specifically to prevent the drift risk hand-pinning exposes the POC to. `cucumber-bom:7.18.x` covers the POC's exact `cucumber.version = 7.18.0`.

### D3 — Runner model (JUnit Platform Suite, not JUnit 4)

The suite runner uses `@Suite` + `@IncludeEngines("cucumber")` + `@SelectClasspathResource`. Glue, tags, and plugin configuration live in `junit-platform.properties`, **not** in annotations.

**Explicitly prohibited** anywhere in this platform's generated or hand-written Java: `@RunWith(Cucumber.class)` and `@CucumberOptions`. These are the JUnit 4 model, incompatible with the JUnit Platform engine, and they dominate publicly available Cucumber examples — making them the single most likely thing an LLM will emit if not explicitly constrained.

The runner and `junit-platform.properties` belong to ADR-0037's TRACKED baseline tier and are never generated by Layer 3.

*Supporting evidence:* `docs/reference/automation-poc/pom.xml` declares `org.junit.platform:junit-platform-suite` and `org.junit.platform:junit-platform-launcher` as test-scope dependencies (lines 61–75) and does **not** declare `junit:junit` (JUnit 4) anywhere — consistent with the JUnit Platform Suite model this ADR locks. The pom.xml's Surefire configuration (lines 116–125) includes only `**/runners/RunCucumberTest.java`; the runner class itself was not committed to `docs/reference/automation-poc/`, so its internal annotations could not be directly inspected — this ADR's D3 is a forward specification, not a citation of that file's contents.

### D4 — Assertions

**JUnit Jupiter Assertions only.** AssertJ, Hamcrest, and TestNG are prohibited.

**Rationale.** JUnit 5 does not bundle Hamcrest as JUnit 4 did; a hallucinated `assertThat` import fails at compile time rather than silently passing or silently missing an assertion.

### D5 — Browser automation and driver lifecycle

Selenium pinned to an explicit 4.x version, **≥ 4.6**. Exact pin: **4.25.0**, verified against `docs/reference/automation-poc/pom.xml:20` (`<selenium.version>4.25.0</selenium.version>`).

**No WebDriverManager dependency** — Selenium Manager (bundled since Selenium 4.6) resolves driver binaries, which removes driver provisioning from the Jenkins agent and from local dev.

**Discrepancy noted:** `docs/reference/automation-poc/pom.xml` currently declares `io.github.bonigarcia:webdrivermanager:5.9.1` as a live test-scope dependency (lines 38–43). This ADR's exclusion of WebDriverManager is a deliberate departure from the POC's current dependency list, supplied by the platform owner, not a report that the POC has already dropped it. Any future promotion of code from the POC (or code generated using its patterns) into this platform's tracked baseline must drop `webdrivermanager` and rely on Selenium Manager instead.

WebDriver instances are held in a `ThreadLocal` owned by a factory in the tracked baseline module. Generated page objects **receive** a driver; they must never construct one, and must never hold one in a static field.

**Rationale.** The moment `cucumber.execution.parallel.enabled` is set, a static or per-instance driver produces failures indistinguishable from flakiness.

### D6 — Reporters, and the Layer 5 → Layer 6 contract

Three plugins configured, with distinct purposes:

| Plugin | Purpose |
|---|---|
| `message` | Cucumber Messages NDJSON — **the machine-readable input contract for Layer 6** (Failure Intelligence & Self-Healing, ADR-0031). Structured step-level results, error messages, stack traces, attachments. |
| `junit` | JUnit XML — so Jenkins renders trends natively. |
| `html` | Human-readable report. |

**Binding constraint:** Layer 6 parses the NDJSON. It must never parse the HTML or XML reports. Parsing a presentation format couples failure analysis to report styling.

ADR-0034's traceability tags (`@REQ-*`/`@AC-*`/`@SCN-*`) propagate into the NDJSON automatically, which is what gives Layer 6 traceability with no additional plumbing.

*Note:* `docs/reference/automation-poc/pom.xml` does not itself configure Cucumber's runtime `plugin` list (that lives in the runner/`junit-platform.properties`, not committed to the reference copy), so this decision is a forward specification grounded in ADR-0037's Layer 6 boundary and ADR-0040's CP3 evidence discipline, not a citation of the pom.xml.

### D7 — Layout

Feature files live at `src/test/resources/features/` — required for `@SelectClasspathResource` to resolve them, and confirmed as the existing convention in `docs/reference/automation-poc/prompts/generate-feature.md` ("Place the output at `{{TARGET_FILE}}` under `src/test/resources/features/`").

Java package root: **`com.automation`**. Verified against `docs/reference/automation-poc/pom.xml:8` (`<groupId>com.automation</groupId>`) and `docs/reference/automation-poc/prompts/generate-test-data.md` ("Generate a Java test data class ... in `src/test/java/com/automation/utils/`" and "Package: `com.automation.utils`").

## Consequences

- **JDK 21 and Maven become runtime prerequisites for the platform itself**: local development, CP3's SonarQube scan of generated Java (ADR-0040 Decision 1), and any Jenkins agent. A Python platform now compiles Java. A warmed Maven repository on the agent is an operational prerequisite.
- **D3, D4, and D5 are not merely build configuration — they are Layer 3 generation constraints** and must appear in Layer 3's generation prompts (the runner model, the assertion library, and the driver-lifecycle discipline all constrain what Layer 3 is permitted to emit, not just what the tracked baseline provides).
- **ADR-0039 (Proposed) is unaffected**, but its "local Maven runner as default implementation" is now concretely specified: the Maven/`pom.xml` build this ADR defines is exactly what that runner would invoke, once ADR-0039 itself is Accepted.
- **Does not resolve ADR-0037's remaining TBDs**: the tracked baseline's exact repository path, and the exact promotion review mechanism. Both remain open.

## Recommendations (permanent)

1. No `@RunWith` or `@CucumberOptions` in any Java in this repository, generated or hand-written.
2. No assertion library other than JUnit Jupiter.
3. No WebDriverManager.
4. Layer 6 consumes Cucumber Messages NDJSON only.

## Ownership, scope, and governance

- **Owns:** the concrete Java build stack (Maven, Java 21, BOM-managed JUnit/Cucumber versions, the JUnit Platform Suite runner model, JUnit Jupiter–only assertions, the Selenium/Selenium-Manager driver discipline, the three-reporter split, and the `com.automation` layout) — resolving exactly the TBD ADR-0037 §D4 deferred.
- **Does not own:** the tracked baseline's exact repository path or the promotion review mechanism (both remain open, ADR-0037's TBD list); CP3's rule catalogue beyond the `customqa:*` profile ADR-0037 already locked (ADR-0040); ADR-0039's ratification status (still Proposed).
- **Governance:** Accepted. Resolves ADR-0037's Java-stack TBD by additive inline note there (see ADR-0037). Does not amend or supersede any other ADR.
