"""`traceability.json` -- a DERIVED index (ADR-0043 D2), never the source of
truth.

Built entirely by reading `@REQ-*`/`@AC-*`/`@SCN-*` tags back out of the
emitted `.feature` files themselves -- never from `FeatureRecord.scn_ids`/
`ac_ids_covered` alone, so a future drift between what the package
remembers and what the file actually contains would show up here (this
function trusts the on-disk file, not the package record, for tag content).
Deleting this file loses no traceability information: every entry is
re-derivable from the tags still present in the `.feature` files, which is
where each entry came from in the first place.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from feature_engineering.gherkin_lint import parse_source_text
from feature_engineering.stage.models import FeatureRecord

TRACEABILITY_FILENAME = "traceability.json"

_AC_TAG_RE = re.compile(r"^@AC-\S+$")
_SCN_TAG_RE = re.compile(r"^@SCN-\S+$")


def build_traceability_index(
    records: tuple[FeatureRecord, ...], *, features_root: Path
) -> list[dict[str, Any]]:
    """One entry per (requirement, scenario) pair, derived by re-parsing
    each record's own on-disk `.feature` file.

    A record with `feature_path=None` (a pre-assembly generation failure --
    no content ever existed) or whose file is missing contributes nothing --
    there is no tag to read back out.
    """
    entries: list[dict[str, Any]] = []
    for record in records:
        if record.feature_path is None:
            continue
        path = features_root / record.feature_path
        if not path.exists():
            continue
        source = parse_source_text(path.read_text(encoding="utf-8"), path=record.feature_path)
        if source.feature is None:
            continue
        feature_tags = {tag["name"] for tag in source.feature.get("tags", [])}
        for child in source.feature.get("children", []):
            scenario = child.get("scenario")
            if not scenario:
                continue
            own_tags = {tag["name"] for tag in scenario.get("tags", [])}
            effective_tags = own_tags | feature_tags
            ac_ids = sorted(t.removeprefix("@") for t in effective_tags if _AC_TAG_RE.match(t))
            scn_ids = sorted(t.removeprefix("@") for t in effective_tags if _SCN_TAG_RE.match(t))
            for scn_id in scn_ids:
                entries.append(
                    {
                        "requirementId": record.requirement_id,
                        "scenarioId": scn_id,
                        "scenarioName": scenario.get("name"),
                        "acceptanceCriteriaIds": ac_ids,
                        "featurePath": record.feature_path,
                    }
                )
    return entries


__all__ = ["TRACEABILITY_FILENAME", "build_traceability_index"]
