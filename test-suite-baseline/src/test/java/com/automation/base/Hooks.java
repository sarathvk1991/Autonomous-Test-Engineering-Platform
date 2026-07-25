package com.automation.base;

import io.cucumber.java.After;
import io.cucumber.java.Before;

/** Per-scenario driver lifecycle: create before, quit (and clear the ThreadLocal) after. */
public class Hooks {

    @Before
    public void setUp() {
        DriverFactory.create();
    }

    @After
    public void tearDown() {
        DriverFactory.quit();
    }
}
