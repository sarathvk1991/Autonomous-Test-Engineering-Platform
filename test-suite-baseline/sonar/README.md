# The `customqa` SonarQube quality profile

**What this is.** `customqa-profile.xml` in this directory is the versioned,
importable SonarQube quality-profile artifact ADR-0037 Recommendation 3 calls
for ("the `customqa:*` SonarQube profile is versioned alongside the tracked
baseline it governs"), narrowed to the Sonar-expressible half of `customqa:*`
per ADR-0044 D5's own revision note (2026-08-04): it verifies
`customqa:long-method` only. `customqa:direct-webdriver-action` is NOT in
this profile — it is an architectural, caller-class-role constraint
SonarQube cannot natively express, and is verified by a separate, static
Layer 3 check instead (a second, not-yet-built task; CP3's own gate is the
composite of both).

**What's in the profile.** Every rule the built-in `Sonar way` Java profile
activates (a full backup of it, taken directly from a live server via
`GET /api/qualityprofiles/backup?qualityProfile=Sonar%20way&language=java`
— not hand-typed), plus one addition: `java:S138` ("Methods should not have
too many lines"), activated with `max=40` — the real, existing, built-in
Sonar rule `customqa:long-method` maps to (confirmed live against the
server's own rule catalog, `GET /api/rules/show?key=java:S138`: a native,
non-external, non-template rule, default `max=75`, `MAINTAINABILITY`/
`MEDIUM` impact). Extending `Sonar way` wholesale, rather than starting from
an empty profile, was a deliberate choice: `customqa` is meant to be the
profile CP3 actually scans generated code against, so it should carry the
platform's full baseline quality bar, not just the one rule this profile
happens to add.

## Why this file exists but the profile isn't live yet

The credential this platform's own CP3 adapter runs with (`SONAR_TOKEN` in
`.env`) is deliberately least-privilege — it can submit a scan and read
results, but it has **no global permission** to create/activate quality
profiles or assign them to a project (`api/qualityprofiles/create`,
`activate_rule`, and `add_project` all return `"Insufficient privileges"`
against the live server this platform targets, verified directly, not
assumed). This is correct: a pipeline's own analysis token should not also
be a server administrator. Importing and assigning this profile is
therefore a **one-time, human, admin action** — not something the adapter
does or should do at runtime — documented below as an exact, runnable
procedure.

## One-time admin procedure

Run these with a token that DOES carry the "Administer Quality Profiles"
and "Administer" project permissions (not the pipeline's own `SONAR_TOKEN`).

**1. Import the profile:**

```bash
curl -u <ADMIN_TOKEN>: \
  -F "backup=@test-suite-baseline/sonar/customqa-profile.xml" \
  "http://localhost:9000/api/qualityprofiles/restore"
```

**2. Assign it to the project CP3 scans:**

```bash
curl -u <ADMIN_TOKEN>: -X POST \
  "http://localhost:9000/api/qualityprofiles/add_project?qualityProfile=customqa&language=java&project=Automation-POC"
```

**3. Confirm the assignment took:**

```bash
curl -u <ADMIN_TOKEN>: \
  "http://localhost:9000/api/qualityprofiles/search?project=Automation-POC&language=java"
# expect one profile in the response: "name": "customqa"
```

## The live proof (run 2026-08-04, against the live 26.4.0.121862 server — real, not faked)

Import and assignment were executed with an admin `USER_TOKEN`
(`customqa-admin-setup`, `permissions.global` including `admin` and
`profileadmin`) — never the pipeline's own `SONAR_TOKEN`, which stayed the
same `PROJECT_ANALYSIS_TOKEN`, unchanged, throughout:

- `POST /api/qualityprofiles/restore` → `{"profile":{"name":"customqa",...},
  "ruleSuccesses":550,"ruleFailures":0}`. `GET /api/rules/search?qprofile=
  <key>&activation=true&rule_key=java:S138&f=actives` confirms the active
  param directly: `"params":[{"key":"max","value":"40"}]` (not just rule
  presence — the actual activation value).
- `POST /api/qualityprofiles/add_project?qualityProfile=customqa&language=
  java&project=Automation-POC` → `204`. `GET /api/qualityprofiles/search?
  project=Automation-POC&language=java` confirms exactly one profile on the
  project: `"name":"customqa"`, `projectCount:1`.

**Correction to this section's own prior instruction:** it said to add the
throwaway file under `test-suite-baseline/src/test/java/com/automation/`.
That is wrong and was verified wrong directly, not assumed: `java:S138`'s
own rule metadata (`GET /api/rules/show?key=java:S138`) carries
`"scope":"MAIN"` — SonarQube evaluates `MAIN`-scope rules only against
files the scanner classifies as source (Maven's `sourceDirectory`, default
`src/main/java`), never against files under `testSourceDirectory`
(`src/test/java`). Placed under `src/test/java` as originally written, the
proof file scanned clean — 0 `java:S138` issues, confirmed via
`/api/issues/search?componentKeys=Automation-POC&rules=java:S138` returning
`"total":0` — not because the profile/rule didn't work, but because the
rule never ran against it at all. The throwaway file must go under
`src/main/java` instead (this project has no pre-existing `src/main` tree;
creating one temporarily for this proof, then deleting it afterward, is
correct and was done):

```java
// test-suite-baseline/src/main/java/com/automation/scratch/CustomqaProofOfConcept.java
package com.automation.scratch;

public final class CustomqaProofOfConcept {

    // Clean: well under 40 lines -- S138 should NOT flag this one.
    public void shortMethod() {
        System.out.println("short");
    }

    // Violating: deliberately over 40 lines -- S138 SHOULD flag this one,
    // once the customqa profile above is assigned to this project.
    public void longMethod() {
        System.out.println("line 1");
        System.out.println("line 2");
        // ... repeat System.out.println("line N"); up to line 45+ ...
    }
}
```

Scanned via CP3's own `LiveSonarQualityGateAdapter.submit_scan` (real
subprocess call, `SONAR_TOKEN` — the analysis-scoped pipeline token, exactly
what it's for — passed via env, never a CLI arg), which runs:

```bash
mvn -f test-suite-baseline/pom.xml sonar:sonar \
  -Dsonar.host.url=http://localhost:9000 \
  -Dsonar.projectKey=Automation-POC
```

Real server verdict, `GET /api/issues/search?componentKeys=Automation-POC:
src/main/java/com/automation/scratch/CustomqaProofOfConcept.java`:

- `longMethod()` (declared line 12, 47 lines): **flagged** —
  `"rule":"java:S138"`, `"message":"This method has 47 lines, which is
  greater than the 40 lines authorized. Split it into smaller methods."`
- `shortMethod()` (line 6-8): **not flagged** — zero `java:S138` issues on
  it (the file's other 36 issues are unrelated `java:S106`, System.out
  usage, one per `println`).

The throwaway file (and the `src/main` tree created only to hold it) was
deleted afterward — this project has no tracked `src/main`, and none was
reintroduced.

## Open gap this proof surfaced (not closed by this build)

The proof above establishes the profile/rule *mechanism* works. It does
**not** establish that `customqa:long-method` protects this platform's real
generated code. `automation_engineering/catalog/scanner.py`'s own
`JAVA_SOURCE_SUBPATH = Path("src/test/java")` and
`automation_engineering/promotion/identity.py` both confirm every class CP3
generates or promotes — step definitions, page objects, utilities — is
placed under `src/test/java`, by this platform's own deliberate
architecture (ADR-0037 Path A), not by accident. Because `java:S138` is
permanently `scope:"MAIN"` (a SonarQube rule-catalog property, not
something a quality profile's activation can override), it will **never**
evaluate any of that real generated code, on this server, on this project,
regardless of the `customqa` profile being correctly assigned. The
long-method gate is live and correct as a mechanism; it is currently inert
against the actual pipeline output it was built to check. Closing this gap
(e.g. reclassifying the scanner's source/test split, or moving long-method
enforcement to the same static Layer 3 check `customqa:direct-webdriver-
action` already uses) is a separate, not-yet-scoped follow-up.
