"""Enumerations for the Canonical Data Model.

These enums define the controlled vocabulary that every artifact in the
canonical model is classified against. They are intentionally broad: the
current platform ingests JIRA, OWASP ZAP and SonarQube, but the same
vocabulary is designed to absorb future sources (HP ALM, Azure DevOps,
generated test cases, execution results, failure analysis, self-healing
events and governance metrics) without redesign.

String-valued (``StrEnum``) members serialise cleanly to JSON and to the
database, and compare equal to their plain-string value.
"""

from __future__ import annotations

from enum import StrEnum


class SourceSystem(StrEnum):
    """The upstream system an artifact was ingested *from*.

    ``SourceSystem`` answers *"where did this record physically come from?"* —
    it identifies the vendor / tool of origin, independent of what the record
    means. This is distinct from the two classification axes:

    * :class:`SourceSystem` — the **origin** (JIRA, OWASP ZAP, SonarQube, …).
    * :class:`SourceCategory` — the **domain** the record concerns
      (functional / security / quality / …).
    * :class:`SourceType` — the **record type** (story / defect / DAST / …).

    The same system can emit artifacts across multiple categories and types
    (e.g. JIRA produces both functional stories and functional defects; a
    future ALM could emit requirements *and* test cases), which is exactly why
    origin is modelled separately. Promoting it from a free-form ``str`` to an
    enum gives type safety and a stable, low-cardinality dimension for
    dashboard analytics, trend analysis and governance reporting.
    """

    JIRA = "jira"
    """Atlassian JIRA (functional epics, stories, defects)."""

    OWASP_ZAP = "owasp_zap"
    """OWASP ZAP dynamic security scanner (DAST alerts)."""

    SONARQUBE = "sonarqube"
    """SonarQube static analysis (SAST / quality issues)."""

    HP_ALM = "hp_alm"
    """Micro Focus / HP ALM (future requirement & test management source)."""

    AZURE_DEVOPS = "azure_devops"
    """Azure DevOps Boards / Pipelines (future source)."""

    TEST_ENGINE = "test_engine"
    """The platform's own test generation / execution engine (future source)."""

    FAILURE_ENGINE = "failure_engine"
    """The platform's failure-analysis / self-healing engine (future source)."""


class SourceCategory(StrEnum):
    """High-level lifecycle domain a source artifact belongs to.

    The category answers *"what kind of concern does this artifact express?"*
    and drives how artifacts are grouped during consolidation. It is broader
    and more stable than :class:`SourceType`, so new source types can be added
    under an existing category without changing downstream grouping logic.
    """

    FUNCTIONAL = "functional"
    """Business / functional intent (e.g. JIRA epics and stories)."""

    SECURITY = "security"
    """Security findings (e.g. OWASP ZAP DAST alerts, SAST issues)."""

    QUALITY = "quality"
    """Code-quality / maintainability signals (e.g. SonarQube issues)."""

    TESTING = "testing"
    """Test assets such as generated or authored test cases."""

    EXECUTION = "execution"
    """Runtime signals from test execution (results, failures)."""


class SourceType(StrEnum):
    """The concrete record type a source artifact represents.

    Where :class:`SourceCategory` is the domain, ``SourceType`` is the specific
    shape of the originating record. Each type maps naturally to one category
    (e.g. :attr:`EPIC` / :attr:`STORY` / :attr:`DEFECT` are ``FUNCTIONAL``;
    :attr:`DAST` is ``SECURITY``; :attr:`SAST` is ``QUALITY``/``SECURITY``).
    """

    EPIC = "epic"
    """A large body of functional work (JIRA epic)."""

    STORY = "story"
    """A user story / functional requirement (JIRA story)."""

    DEFECT = "defect"
    """A reported defect or bug (JIRA defect)."""

    DAST = "dast"
    """Dynamic Application Security Testing finding (OWASP ZAP alert)."""

    SAST = "sast"
    """Static Application Security Testing finding (SonarQube issue)."""

    TEST_CASE = "test_case"
    """A generated or authored test case (future phase)."""

    TEST_RESULT = "test_result"
    """The outcome of executing a test case (future phase)."""

    EXECUTION_FAILURE = "execution_failure"
    """A failure captured during execution / failure analysis (future phase)."""


class RiskLevel(StrEnum):
    """Normalised risk rating applied to consolidated artifacts.

    Source systems use heterogeneous severity scales (ZAP risk, Sonar
    severity, JIRA priority). ``RiskLevel`` is the single normalised scale the
    platform reasons about when prioritising work and summarising risk.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
