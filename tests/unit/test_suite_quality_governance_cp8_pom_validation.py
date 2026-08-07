"""Proves CP8's `pom.xml` structural-validity component (ADR-0047 D7's own
second bullet): `suite_quality_governance.cp8.pom_validation`.

Covers: a well-formed pom with real declarations passing; missing file,
malformed XML, and structurally-defective dependency/plugin declarations
each failing independently; and that an empty `<dependencies>` section
(declares nothing) is NOT itself flagged -- D7's own explicit "never a
hardcoded expected-dependency list" boundary.
"""

from __future__ import annotations

from pathlib import Path

from shared.enums.base import ValidationVerdict
from suite_quality_governance.cp8.pom_validation import check_pom_well_formed

_VALID_POM = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.automation</groupId>
    <artifactId>test-suite-baseline</artifactId>
    <version>1.0-SNAPSHOT</version>
    <dependencies>
        <dependency>
            <groupId>io.cucumber</groupId>
            <artifactId>cucumber-java</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>
    <build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.13.0</version>
            </plugin>
        </plugins>
    </build>
</project>
"""


class TestWellFormedPomPasses:
    def test_a_real_shaped_pom_passes(self, tmp_path: Path) -> None:
        (tmp_path / "pom.xml").write_text(_VALID_POM, encoding="utf-8")

        result = check_pom_well_formed(tmp_path)

        assert result.verdict == ValidationVerdict.PASS
        assert result.messages == ()

    def test_a_dependency_with_no_explicit_version_is_not_flagged(self, tmp_path: Path) -> None:
        """Normal, valid Maven practice for a BOM-managed dependency --
        this platform's own real pom.xml relies on this for five of its
        six dependencies (module docstring)."""
        (tmp_path / "pom.xml").write_text(_VALID_POM, encoding="utf-8")

        result = check_pom_well_formed(tmp_path)

        assert result.verdict == ValidationVerdict.PASS

    def test_an_empty_dependencies_section_is_not_itself_flagged(self, tmp_path: Path) -> None:
        """D7's own explicit rejection of a hardcoded expected-dependency
        list: declaring zero dependencies is not, by itself, a structural
        defect this module checks for."""
        pom = """<?xml version="1.0" encoding="UTF-8"?>
        <project xmlns="http://maven.apache.org/POM/4.0.0">
            <modelVersion>4.0.0</modelVersion>
            <groupId>com.automation</groupId>
            <artifactId>empty</artifactId>
            <version>1.0</version>
            <dependencies></dependencies>
        </project>
        """
        (tmp_path / "pom.xml").write_text(pom, encoding="utf-8")

        result = check_pom_well_formed(tmp_path)

        assert result.verdict == ValidationVerdict.PASS


class TestEachDefectFailsIndependently:
    def test_missing_pom_fails(self, tmp_path: Path) -> None:
        result = check_pom_well_formed(tmp_path)

        assert result.verdict == ValidationVerdict.FAIL
        assert "no pom.xml found" in result.messages[0]

    def test_malformed_xml_fails(self, tmp_path: Path) -> None:
        (tmp_path / "pom.xml").write_text("<project><unclosed>", encoding="utf-8")

        result = check_pom_well_formed(tmp_path)

        assert result.verdict == ValidationVerdict.FAIL
        assert "not well-formed XML" in result.messages[0]

    def test_dependency_missing_artifact_id_fails(self, tmp_path: Path) -> None:
        pom = """<?xml version="1.0" encoding="UTF-8"?>
        <project xmlns="http://maven.apache.org/POM/4.0.0">
            <modelVersion>4.0.0</modelVersion>
            <groupId>com.automation</groupId>
            <artifactId>bad</artifactId>
            <version>1.0</version>
            <dependencies>
                <dependency>
                    <groupId>io.cucumber</groupId>
                </dependency>
            </dependencies>
        </project>
        """
        (tmp_path / "pom.xml").write_text(pom, encoding="utf-8")

        result = check_pom_well_formed(tmp_path)

        assert result.verdict == ValidationVerdict.FAIL
        assert "missing a non-empty <artifactId>" in result.messages[0]

    def test_dependency_with_empty_version_fails(self, tmp_path: Path) -> None:
        pom = """<?xml version="1.0" encoding="UTF-8"?>
        <project xmlns="http://maven.apache.org/POM/4.0.0">
            <modelVersion>4.0.0</modelVersion>
            <groupId>com.automation</groupId>
            <artifactId>bad</artifactId>
            <version>1.0</version>
            <dependencies>
                <dependency>
                    <groupId>io.cucumber</groupId>
                    <artifactId>cucumber-java</artifactId>
                    <version></version>
                </dependency>
            </dependencies>
        </project>
        """
        (tmp_path / "pom.xml").write_text(pom, encoding="utf-8")

        result = check_pom_well_formed(tmp_path)

        assert result.verdict == ValidationVerdict.FAIL
        assert "declares an empty <version>" in result.messages[0]

    def test_malformed_plugin_declaration_fails(self, tmp_path: Path) -> None:
        pom = """<?xml version="1.0" encoding="UTF-8"?>
        <project xmlns="http://maven.apache.org/POM/4.0.0">
            <modelVersion>4.0.0</modelVersion>
            <groupId>com.automation</groupId>
            <artifactId>bad</artifactId>
            <version>1.0</version>
            <build>
                <plugins>
                    <plugin>
                        <groupId>org.apache.maven.plugins</groupId>
                    </plugin>
                </plugins>
            </build>
        </project>
        """
        (tmp_path / "pom.xml").write_text(pom, encoding="utf-8")

        result = check_pom_well_formed(tmp_path)

        assert result.verdict == ValidationVerdict.FAIL
        assert "missing a non-empty <artifactId>" in result.messages[0]
