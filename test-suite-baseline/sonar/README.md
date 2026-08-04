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

## The live proof this unlocks (not run by this build — no verdict faked)

Once assigned, a real scan should flag a method over 40 lines and leave a
method under 40 lines clean. To prove it, add a small throwaway Java file
under `test-suite-baseline/src/test/java/com/automation/` such as:

```java
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

Then run the same scan CP3's own `LiveSonarQualityGateAdapter` runs
(fully-qualified goal, per the F3 fix's own portability note):

```bash
mvn -f test-suite-baseline/pom.xml \
  org.sonarsource.scanner.maven:sonar-maven-plugin:sonar \
  -Dsonar.host.url=http://localhost:9000 \
  -Dsonar.projectKey=Automation-POC
```

And check the finding:

```bash
curl -u <ADMIN_TOKEN>: \
  "http://localhost:9000/api/issues/search?componentKeys=Automation-POC&rules=java:S138"
# expect exactly one issue, on longMethod(), none on shortMethod()
```

Delete the throwaway file afterward — it exists only to produce this proof,
not as tracked-baseline framework code.
