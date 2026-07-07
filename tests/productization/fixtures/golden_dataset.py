"""Golden dataset fixtures for CAP-070.

A deterministic, representative set of :class:`SourceArtifact` records and the
companion golden LLM response for long-term regression testing.

The dataset exercises every governed requirement category the pipeline handles:

* Functional requirements   — JIRA stories and an epic for the Auth Service.
* Security requirements     — OWASP ZAP DAST findings on auth endpoints.
* Quality requirements      — SonarQube SAST issues in the auth codebase.
* Risks                     — derived by the stub AI from the above evidence.
* Recommendations           — actionable closure recommendations.

All identifiers and timestamps are fixed so the dataset is byte-identical across
runs; only the run-specific provenance fields (IDs, timestamps) that the pipeline
generates per-invocation are expected to differ.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from requirement_intelligence.models.enums import (
    SourceCategory,
    SourceSystem,
    SourceType,
)
from requirement_intelligence.models.source_artifact import SourceArtifact

# ---------------------------------------------------------------------------
# Dataset version — advance when the golden inputs change
# ---------------------------------------------------------------------------
GOLDEN_DATASET_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Fixed timestamps (deterministic provenance)
# ---------------------------------------------------------------------------
_CREATED_AT = datetime(2026, 1, 10, 9, 0, 0, tzinfo=UTC)
_UPDATED_AT = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)

# ---------------------------------------------------------------------------
# Source artifacts
# ---------------------------------------------------------------------------

# -- JIRA: Authentication Service functional requirements -------------------

JIRA_EPIC_AUTH = SourceArtifact(
    artifact_id="golden-jira-001",
    source_system=SourceSystem.JIRA,
    source_record_id="AUTH-1",
    source_category=SourceCategory.FUNCTIONAL,
    source_type=SourceType.EPIC,
    title="Authentication Service — Phase 1",
    description=(
        "Deliver a secure, scalable authentication service supporting "
        "username/password login, session management, and account lockout."
    ),
    status="In Progress",
    priority="High",
    component="authentication",
    tags=["auth", "security-gate"],
    created_at=_CREATED_AT,
    updated_at=_UPDATED_AT,
)

JIRA_STORY_LOCKOUT = SourceArtifact(
    artifact_id="golden-jira-002",
    source_system=SourceSystem.JIRA,
    source_record_id="AUTH-2",
    source_category=SourceCategory.FUNCTIONAL,
    source_type=SourceType.STORY,
    title="Account must lock after five consecutive failed login attempts",
    description=(
        "As a security officer I want accounts locked after five failed attempts "
        "so that brute-force attacks are prevented. "
        "Acceptance: the lockout applies per-IP and per-account; admin can unlock manually."
    ),
    status="Open",
    priority="High",
    component="authentication",
    tags=["auth", "lockout"],
    created_at=_CREATED_AT,
    updated_at=_UPDATED_AT,
)

JIRA_STORY_SESSION = SourceArtifact(
    artifact_id="golden-jira-003",
    source_system=SourceSystem.JIRA,
    source_record_id="AUTH-3",
    source_category=SourceCategory.FUNCTIONAL,
    source_type=SourceType.STORY,
    title="New session token must be issued on each successful login",
    description=(
        "As a developer I want a fresh session token generated on each successful "
        "login so that session-fixation attacks are impossible. "
        "Acceptance: tokens are UUID-v4, stored server-side, expire after 30 minutes."
    ),
    status="Open",
    priority="High",
    component="authentication",
    tags=["auth", "sessions"],
    created_at=_CREATED_AT,
    updated_at=_UPDATED_AT,
)

JIRA_STORY_PASSWORD_CHANGE = SourceArtifact(
    artifact_id="golden-jira-004",
    source_system=SourceSystem.JIRA,
    source_record_id="AUTH-4",
    source_category=SourceCategory.FUNCTIONAL,
    source_type=SourceType.STORY,
    title="All active sessions must be invalidated when a user changes their password",
    description=(
        "As a user I want my other sessions revoked when I change my password "
        "so that a compromised device is immediately locked out."
    ),
    status="Open",
    priority="Medium",
    component="authentication",
    tags=["auth", "sessions", "password"],
    created_at=_CREATED_AT,
    updated_at=_UPDATED_AT,
)

# -- OWASP ZAP: Security findings on auth endpoints -------------------------

ZAP_SQL_INJECTION = SourceArtifact(
    artifact_id="golden-zap-001",
    source_system=SourceSystem.OWASP_ZAP,
    source_record_id="ZAP-ALERT-10001",
    source_category=SourceCategory.SECURITY,
    source_type=SourceType.DAST,
    title="SQL Injection in POST /api/auth/login (username parameter)",
    description=(
        "ZAP detected a SQL injection vulnerability in the username parameter of "
        "POST /api/auth/login. The application concatenates the username directly "
        "into the SQL query without parameterization."
    ),
    status="Open",
    severity="High",
    priority="Critical",
    component="authentication",
    location="/api/auth/login",
    tags=["sql-injection", "auth", "critical"],
    created_at=_CREATED_AT,
    updated_at=_UPDATED_AT,
    metadata={"cwe": "CWE-89", "confidence": "High", "risk": "High"},
)

ZAP_WEAK_SESSION = SourceArtifact(
    artifact_id="golden-zap-002",
    source_system=SourceSystem.OWASP_ZAP,
    source_record_id="ZAP-ALERT-10002",
    source_category=SourceCategory.SECURITY,
    source_type=SourceType.DAST,
    title="Weak session token entropy detected on GET /api/auth/session",
    description=(
        "Session tokens returned by GET /api/auth/session are 32-bit sequential "
        "integers, making them trivially predictable."
    ),
    status="Open",
    severity="High",
    priority="High",
    component="authentication",
    location="/api/auth/session",
    tags=["session", "entropy", "auth"],
    created_at=_CREATED_AT,
    updated_at=_UPDATED_AT,
    metadata={"cwe": "CWE-330", "confidence": "Medium", "risk": "High"},
)

ZAP_MISSING_HTTPS = SourceArtifact(
    artifact_id="golden-zap-003",
    source_system=SourceSystem.OWASP_ZAP,
    source_record_id="ZAP-ALERT-10003",
    source_category=SourceCategory.SECURITY,
    source_type=SourceType.DAST,
    title="Authentication endpoints accessible over plain HTTP",
    description=(
        "The authentication endpoints respond to HTTP requests, transmitting "
        "credentials in cleartext. HTTPS is not enforced."
    ),
    status="Open",
    severity="Medium",
    priority="High",
    component="authentication",
    location="/api/auth/*",
    tags=["https", "transport-security", "auth"],
    created_at=_CREATED_AT,
    updated_at=_UPDATED_AT,
    metadata={"cwe": "CWE-319", "confidence": "High", "risk": "Medium"},
)

# -- SonarQube: Code-quality issues in auth codebase -----------------------

SONAR_BRANCH_COVERAGE = SourceArtifact(
    artifact_id="golden-sonar-001",
    source_system=SourceSystem.SONARQUBE,
    source_record_id="SQ-ISSUE-50001",
    source_category=SourceCategory.QUALITY,
    source_type=SourceType.SAST,
    title="Branch coverage on AuthenticationHandler is 42% (threshold: 80%)",
    description=(
        "SonarQube reports that AuthenticationHandler.java has only 42% branch "
        "coverage. The lockout, timeout, and token-refresh paths are untested."
    ),
    status="Open",
    severity="Major",
    component="authentication",
    location="src/main/java/com/platform/auth/AuthenticationHandler.java",
    tags=["coverage", "quality", "auth"],
    created_at=_CREATED_AT,
    updated_at=_UPDATED_AT,
    metadata={"rule": "java:S2699", "effort": "4h"},
)

SONAR_HARDCODED_CREDS = SourceArtifact(
    artifact_id="golden-sonar-002",
    source_system=SourceSystem.SONARQUBE,
    source_record_id="SQ-ISSUE-50002",
    source_category=SourceCategory.QUALITY,
    source_type=SourceType.SAST,
    title="Hardcoded database password detected in AuthDataSource.java",
    description=(
        "SonarQube detected a hardcoded plaintext database password in "
        "AuthDataSource.java line 47. This is a critical quality and security concern."
    ),
    status="Open",
    severity="Critical",
    component="authentication",
    location="src/main/java/com/platform/auth/AuthDataSource.java:47",
    tags=["hardcoded-credentials", "security", "quality", "auth"],
    created_at=_CREATED_AT,
    updated_at=_UPDATED_AT,
    metadata={"rule": "java:S2068", "effort": "30min"},
)

# ---------------------------------------------------------------------------
# The complete golden source artifact list (ordered deterministically)
# ---------------------------------------------------------------------------

GOLDEN_SOURCE_ARTIFACTS: list[SourceArtifact] = [
    JIRA_EPIC_AUTH,
    JIRA_STORY_LOCKOUT,
    JIRA_STORY_SESSION,
    JIRA_STORY_PASSWORD_CHANGE,
    ZAP_SQL_INJECTION,
    ZAP_WEAK_SESSION,
    ZAP_MISSING_HTTPS,
    SONAR_BRANCH_COVERAGE,
    SONAR_HARDCODED_CREDS,
]

# ---------------------------------------------------------------------------
# Golden LLM response
#
# A deterministic, well-formed JSON string that:
#   • is strict-JSON-parseable (no Markdown fences, no prose outside the object)
#   • contains every required key
#   • has non-empty, non-duplicate entries in every requirement/risk/recommendation array
#   • passes all implemented Transport, Syntax, Schema, Content, and Reasoning rules
#   • contains at least one functional, one security, and one quality requirement
#     so the CP1-0001 engineering input availability criterion resolves to PASS
# ---------------------------------------------------------------------------

GOLDEN_LLM_RESPONSE_TEXT: str = json.dumps(
    {
        "summary": (
            "The Authentication Service module consolidates four functional requirements "
            "(epic + three stories covering account lockout, session token issuance, and "
            "session invalidation on password change), three OWASP ZAP DAST findings "
            "(SQL injection at login, weak session-token entropy, and cleartext HTTP "
            "transport), and two SonarQube SAST/quality issues (42-percent branch coverage "
            "and a hardcoded database password). The combined risk posture is HIGH: an "
            "exploitable SQL injection vulnerability and a hardcoded credential in production "
            "code are both critical-severity findings that must be remediated before the "
            "service can be considered engineering-ready."
        ),
        "functional_requirements": [
            (
                "The authentication service MUST lock a user account for a minimum of "
                "15 minutes after five consecutive failed login attempts, applying the "
                "lockout per-account and per-source-IP independently."
            ),
            (
                "The authentication service MUST issue a cryptographically unique session "
                "token on every successful authentication event and MUST NOT reuse tokens "
                "across sessions."
            ),
            (
                "The authentication service MUST immediately invalidate all active sessions "
                "associated with a user account when that account's password is changed, "
                "regardless of session age."
            ),
        ],
        "security_requirements": [
            (
                "All database interactions in the authentication handler MUST use "
                "parameterized queries or a prepared-statement ORM; string concatenation "
                "of user-supplied input into SQL statements is prohibited (addresses "
                "CWE-89 / SQL injection at POST /api/auth/login)."
            ),
            (
                "Session tokens MUST be generated using a cryptographically secure "
                "pseudo-random number generator with a minimum of 128 bits of entropy; "
                "sequential integer tokens are prohibited (addresses CWE-330)."
            ),
            (
                "All authentication-related API endpoints MUST enforce HTTPS; plain HTTP "
                "requests to /api/auth/* MUST be rejected with HTTP 301 or terminated at "
                "the load-balancer (addresses CWE-319)."
            ),
        ],
        "quality_requirements": [
            (
                "The AuthenticationHandler class MUST achieve a minimum branch coverage of "
                "80 percent as reported by SonarQube; the lockout, timeout, and "
                "token-refresh code paths MUST each have at least one covering test."
            ),
            (
                "No hardcoded credentials of any kind are permitted in the authentication "
                "codebase; all secrets MUST be injected via the platform secret-management "
                "facility at runtime (addresses SQ-ISSUE-50002 / java:S2068)."
            ),
        ],
        "risks": [
            (
                "CRITICAL — The exploitable SQL injection vulnerability in POST "
                "/api/auth/login allows an attacker to bypass authentication or extract "
                "the full user database without authentication. This risk must be "
                "remediated before any production deployment."
            ),
            (
                "HIGH — The hardcoded database password in AuthDataSource.java is "
                "committed to source control. Any repository access (internal or leaked) "
                "exposes the production database credential directly."
            ),
        ],
        "recommendations": [
            (
                "IMMEDIATE — Replace all string-concatenated SQL in AuthenticationHandler "
                "with parameterized queries using the platform JDBC template; cover the "
                "change with integration tests before the next release candidate."
            ),
            (
                "IMMEDIATE — Rotate the hardcoded database password in AuthDataSource.java, "
                "remove it from source control history, and inject it via the platform "
                "Vault integration."
            ),
            (
                "SHORT-TERM — Increase AuthenticationHandler branch coverage from 42% to "
                "≥80% by adding unit tests for the lockout, timeout, and token-refresh "
                "paths; configure the SonarQube quality gate to fail the build below 80%."
            ),
        ],
    }
)

# ---------------------------------------------------------------------------
# Expected consolidated module name after consolidation
# (all artifacts share component="authentication" so they form one group)
# ---------------------------------------------------------------------------
EXPECTED_MODULE = "authentication"
EXPECTED_CONSOLIDATED_COUNT = 1

# ---------------------------------------------------------------------------
# Expected content counts in the golden response
# ---------------------------------------------------------------------------
EXPECTED_FUNCTIONAL_REQUIREMENTS_COUNT = 3
EXPECTED_SECURITY_REQUIREMENTS_COUNT = 3
EXPECTED_QUALITY_REQUIREMENTS_COUNT = 2
EXPECTED_RISKS_COUNT = 2
EXPECTED_RECOMMENDATIONS_COUNT = 3
