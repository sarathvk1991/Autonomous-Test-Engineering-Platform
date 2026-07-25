@smoke @baseline
Feature: Baseline smoke check

  Hand-written, tracked self-test for the walking skeleton itself (ADR-0037 tracked tier) --
  not a generated artifact. Proves the spine: driver launch, one navigation, one assertion,
  driver quit.

  Scenario: The skeleton can launch a browser and reach the SUT
    Given I open the application under test
    Then the page title is not empty
