package com.automation.runners;

import org.junit.platform.suite.api.IncludeEngines;
import org.junit.platform.suite.api.SelectClasspathResource;
import org.junit.platform.suite.api.Suite;

/**
 * Cucumber test runner on the JUnit Platform Suite engine (ADR-0041 D3).
 *
 * Deliberately annotation-light: glue, tag filters, and the reporter/plugin list are NOT
 * declared here via {@code @ConfigurationParameter}. They live in junit-platform.properties
 * instead, because Layer 3 will rewrite glue configuration as it generates step definitions --
 * a data change the platform can safely write to a properties file, but never a change that
 * should force regenerating this tracked Java source file. See
 * src/test/resources/junit-platform.properties for the actual configuration.
 *
 * No {@code @RunWith(Cucumber.class)}, no {@code @CucumberOptions} -- both prohibited
 * (ADR-0041 D3).
 */
@Suite
@IncludeEngines("cucumber")
@SelectClasspathResource("features")
public class RunCucumberTest {
    // No body -- junit-platform.properties drives glue/tags/plugins.
}
