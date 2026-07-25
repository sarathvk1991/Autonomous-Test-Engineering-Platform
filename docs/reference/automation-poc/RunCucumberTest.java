package com.automation.runners;

import org.junit.platform.suite.api.ConfigurationParameter;
import org.junit.platform.suite.api.IncludeEngines;
import org.junit.platform.suite.api.SelectClasspathResource;
import org.junit.platform.suite.api.Suite;

import static io.cucumber.junit.platform.engine.Constants.FILTER_TAGS_PROPERTY_NAME;
import static io.cucumber.junit.platform.engine.Constants.GLUE_PROPERTY_NAME;
import static io.cucumber.junit.platform.engine.Constants.PLUGIN_PROPERTY_NAME;
import static io.cucumber.junit.platform.engine.Constants.SNIPPET_TYPE_PROPERTY_NAME;

/**
 * Cucumber test runner using the JUnit Platform Suite engine.
 *
 * How it works:
 *   @Suite          — tells Maven Surefire this is a JUnit Platform test suite.
 *   @IncludeEngines — hands execution off to the Cucumber engine specifically.
 *   @SelectClasspathResource — resolves to src/test/resources/features/ at runtime.
 *
 * Running subsets from the command line (overrides FILTER_TAGS_PROPERTY_NAME):
 *   mvn test -Dcucumber.filter.tags="@smoke"
 *   mvn test -Dcucumber.filter.tags="@regression and not @wip"
 */
@Suite
@IncludeEngines("cucumber")
@SelectClasspathResource("features")

// Glue: packages Cucumber scans for @Before/@After hooks and step definitions.
// Both packages are required — base contains lifecycle hooks, steps contains step definitions.
@ConfigurationParameter(
        key   = GLUE_PROPERTY_NAME,
        value = "com.automation.base,com.automation.steps")

// Tag filter: @wip scenarios are excluded by default so in-progress work never
// blocks the pipeline. Override at runtime with -Dcucumber.filter.tags="...".
@ConfigurationParameter(
        key   = FILTER_TAGS_PROPERTY_NAME,
        value = "not @wip")

// Snippet style: camelCase matches the Java method naming convention, so generated
// step snippets paste cleanly into step definition classes without renaming.
@ConfigurationParameter(
        key   = SNIPPET_TYPE_PROPERTY_NAME,
        value = "camelcase")

// Reporting plugins — all outputs land under target/cucumber-reports/:
//   pretty       — human-readable console output with colours and step timings.
//   html         — self-contained HTML report for local review after a test run.
//   json         — machine-readable format consumed by CI dashboards, Allure,
//                  and ExtentReports. Attach as a build artefact in the pipeline.
//   junit        — JUnit XML understood by Jenkins, GitHub Actions, and GitLab CI
//                  for pass/fail trend graphs without extra plugins.
//   rerun        — writes the URI of every failed scenario; feed back with
//                  -Dcucumber.features=@target/cucumber-reports/rerun.txt to
//                  re-execute only failures without re-running the whole suite.
@ConfigurationParameter(
        key   = PLUGIN_PROPERTY_NAME,
        value = "pretty,"
              + "html:target/cucumber-reports/report.html,"
              + "json:target/cucumber-reports/cucumber.json,"
              + "junit:target/cucumber-reports/cucumber.xml,"
              + "rerun:target/cucumber-reports/rerun.txt")

public class RunCucumberTest {
    // No body — the annotations above drive the entire execution.
}
