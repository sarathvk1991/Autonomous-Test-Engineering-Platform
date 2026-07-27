@smoke
Feature: Clean baseline feature

  Background:
    Given a clean background precondition

  @alpha
  Scenario: A well formed scenario
    Given a precondition
    When an action happens
    Then an outcome is observed

  @beta
  Scenario Outline: A parametrized scenario
    Given a value of <value>
    Then the result is <result>

    Examples:
      | value | result |
      | 1     | one    |
      | 2     | two    |
