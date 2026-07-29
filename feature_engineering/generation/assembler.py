"""The Layer 2 generation core: one TestableRequirement in, one validated
.feature file out.

All deterministic, platform-owned mechanics live here — none of it is
generation logic. Given a :class:`~.content_generator.FeatureContentGenerator`
(a deterministic stub in this task; a live ``llm_factory``-backed
implementation is a separate, later task) and a
:class:`~contracts.testable_requirement.TestableRequirement`,
:func:`generate_feature_file`:

1. Substitutes the one true placeholder (``@SCN-PENDING``) with a real,
   content-addressed ``@SCN-*`` id (``contracts.id_generation``, reused, not
   duplicated) — ``@REQ-*``/``@AC-*`` are already real values the content
   generator wrote verbatim, per the registered prompt's own contract.
2. Hoists any id tag that is identical across every scenario to Feature
   level (ADR-0043 D2).
3. Assembles the full file: the Feature: line derived from ``title`` (D1),
   the requirement's own tag, and the rendered scenario/background content.
4. Computes a deterministic target path (component -> directory, a stable
   key -> file name).
5. Validates the assembled file — parses as Gherkin, lints clean under the
   full 17-rule config (reusing the Layer 2 linter in memory, no disk I/O)
   — and raises rather than returning anything for a file that fails either
   check.

No CP2, no remediation loop, no run-state wiring, and no batch pipeline live
here — see :mod:`feature_engineering.generation.models` for exactly which
future consumer reads which field of the result this module returns.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from contracts.id_generation import generate_scenario_ids
from contracts.testable_requirement import TestableRequirement
from feature_engineering.generation.content_generator import FeatureContentGenerator
from feature_engineering.generation.errors import FeatureGenerationError
from feature_engineering.generation.models import GeneratedFeature, ScenarioAssignment
from feature_engineering.generation.render import (
    render_background,
    render_feature,
    render_scenario,
)
from feature_engineering.gherkin_lint.config import load_config
from feature_engineering.gherkin_lint.linter import lint_source
from feature_engineering.gherkin_lint.source import parse_source_text

#: ADR-0037/ADR-0041: @SelectClasspathResource("features") requires exactly
#: this relative path -- but within a Maven module, not necessarily THE
#: tracked one. Not a default parameter value on `generate_feature_file` --
#: callers pass it explicitly. Stage 14's own live-integration wiring
#: (`feature_engineering.stage.execute_feature_engineering_stage`) does NOT
#: use this constant: per ADR-0037 Path A, it materializes each run's own
#: isolated copy of the tracked baseline
#: (`feature_engineering.stage.workspace.materialize_workspace`) and computes
#: `features_root` within THAT copy, never against this single, shared,
#: tracked path -- sharing this path across runs (or with tracked source)
#: is exactly what ADR-0037 D2 forbids. This constant remains for direct,
#: single-workspace callers (e.g. this module's own tests) that intentionally
#: want the tracked path itself.
DEFAULT_FEATURES_ROOT = Path("test-suite-baseline/src/test/resources/features")

_LINTRC_PATH = Path("docs/reference/automation-poc/.gherkin-lintrc")

_SCN_PENDING_TAG = "@SCN-PENDING"
_AC_TAG_RE = re.compile(r"^@AC-\S+$")
_SLUG_RE = re.compile(r"[^a-z0-9]+")

#: `.gherkin-lintrc`'s own `name-length` limit for `Feature` (verified:
#: `["on", {"Feature": 70, ...}]`), re-verified directly, not reimplemented
#: as a second source of truth -- this constant only needs to stay in sync
#: with that committed config, which this task does not touch.
_FEATURE_NAME_LIMIT = 70


def _slugify(text: str) -> str:
    slug = _SLUG_RE.sub("-", text.strip().lower()).strip("-")
    return slug or "feature"


def derive_feature_name(title: str, requirement_id: str) -> tuple[str, str | None]:
    """Deterministically derive a lint-valid (<=70 char) Feature name from
    Layer 1's unconstrained `title` (ADR-0043 D1's hoist-extension note).

    Same ``(title, requirement_id)`` in -> same ``(name, comment)`` out,
    always -- the same content-addressing discipline the id mechanism
    already carries, so a future SKIP/self-heal diff can depend on it.

    When `title` already fits the limit, it *is* the name and no comment is
    produced -- the common case is a complete no-op, byte-identical to
    behaviour before this function existed.

    When it does not fit, the name is truncated and `requirement_id`'s own
    already-unique short hash is appended as a `[REQ-*]` suffix -- not only
    when a collision is detected, but unconditionally, because this
    function sees one requirement at a time and has no corpus-wide state to
    detect a collision against. Since `requirement_id` is content-addressed
    over the *full* title (`contracts.id_generation.generate_requirement_id`),
    two distinct over-length titles that happen to share a truncation
    prefix are (to cryptographic-hash certainty) never assigned the same
    suffix, so they can never collide onto the same truncated name. The
    Feature *name* itself is never hashed -- only `title` feeds `REQ-*`
    (ADR-0042 Decision 2) -- so shortening the name has no effect on
    `requirement_id` or `content_hash`; both are already fixed by the time
    this function runs.

    The full, untruncated title is never discarded: it is returned as a
    Gherkin comment line to place above the Feature's tag line, verbatim
    except for embedded newlines (defensively collapsed to spaces, since a
    raw multi-line title would otherwise split across multiple comment
    lines or trip raw-source lint rules the platform does not control).

    Returns
    -------
    tuple[str, str | None]
        ``(name, comment)`` -- `comment` is ``None`` exactly when `title`
        already fit and nothing needed preserving separately.
    """
    if len(title) <= _FEATURE_NAME_LIMIT:
        return title, None

    suffix = f" [{requirement_id}]"
    truncated_length = _FEATURE_NAME_LIMIT - len(suffix)
    name = title[:truncated_length].rstrip() + suffix
    single_line_title = title.replace("\n", " ")
    comment = f"# Full requirement title: {single_line_title}"
    return name, comment


def derive_feature_file_path(requirement: TestableRequirement, *, features_root: Path) -> Path:
    """The deterministic target path one requirement's `.feature` file lands
    at -- the same computation `generate_feature_file` performs internally,
    exposed so a caller holding only a `FeatureGenerationError` (raised
    before a `GeneratedFeature` ever existed, e.g. a lint-dirty assembled
    file) can still know where that dirty/escalated content belongs in the
    workspace (ADR-0036 stage 14, ADR-0043 D8) without recomputing the
    naming scheme itself.
    """
    file_name = f"{_slugify(requirement.title)}-{requirement.requirement_id.lower()}.feature"
    return features_root / requirement.component / file_name


def canonical_scenario_content(scenario: dict[str, Any]) -> str:
    """A scenario's own canonical text for content-addressing (D2) — its
    name, steps, and any Examples table, joined; distinct scenario intent
    always yields a distinct string here.

    Public (not module-private): the post-remediation split-scenario re-mint
    step (`feature_engineering.remediation.loop`, ADR-0043 D2's 2026-07-27
    resolution note) reuses this exact function to decide scenario identity
    across a remediation attempt — the same content-addressing computation
    used at first-mint time, not a second, divergent one.
    """
    parts = [scenario.get("name", "")]
    for step in scenario.get("steps", []):
        parts.append(step["keyword"] + step["text"])
    for example in scenario.get("examples", []):
        header = example.get("tableHeader")
        if header:
            parts.append("|".join(cell["value"] for cell in header["cells"]))
        for row in example.get("tableBody", []):
            parts.append("|".join(cell["value"] for cell in row["cells"]))
    return "\n".join(parts)


def generate_feature_file(
    requirement: TestableRequirement,
    content_generator: FeatureContentGenerator,
    *,
    features_root: Path,
) -> GeneratedFeature:
    """Generate, assemble, and validate one ``.feature`` file for ``requirement``.

    Deterministic end to end given deterministic ``content_generator``
    output: the same requirement plus the same raw content always yields
    the same ids, the same assembled bytes, and the same file path, in any
    process.

    Raises
    ------
    FeatureGenerationError
        If the raw content violates its own tag contract (a stray
        ``@REQ-*`` tag, a missing/duplicate ``@SCN-PENDING``, an untagged or
        unknown-``AC``-tagged scenario, a tag on a ``Background:``), fails
        to parse as Gherkin, or the assembled file lints dirty under the
        full 17-rule config.
    """
    raw_content = content_generator.generate(requirement)

    if "@REQ-" in raw_content:
        raise FeatureGenerationError(
            f"requirement_id={requirement.requirement_id!r}: generated content "
            "contains a @REQ-* tag; the content generator must never write one "
            "-- the platform attaches the requirement's id to the derived "
            "Feature line directly."
        )

    # The raw content is deliberately scenario-only (no Feature: line of its
    # own) -- parse it via a temporary header to discover its structure.
    temp_text = "Feature: __GENERATION_TEMP__\n\n" + raw_content
    label = f"<generated:{requirement.requirement_id}>"
    source = parse_source_text(temp_text, path=label)
    if source.parse_error or source.feature is None:
        raise FeatureGenerationError(
            f"requirement_id={requirement.requirement_id!r}: generated content is "
            f"not valid Gherkin: {source.parse_error or 'no Feature block parsed'}"
        )

    known_ac_ids = {ac.criterion_id for ac in requirement.acceptance_criteria}
    ac_coverage: dict[str, bool] = dict.fromkeys(known_ac_ids, False)

    ordered_children: list[tuple[str, dict[str, Any]]] = []
    pending: list[dict[str, Any]] = []

    for child in source.feature["children"]:
        if child.get("background"):
            background = child["background"]
            if background.get("tags"):
                raise FeatureGenerationError(
                    f"requirement_id={requirement.requirement_id!r}: a Background: "
                    "block carries tags, which the content contract forbids."
                )
            ordered_children.append(("background", background))
            continue

        scenario = child["scenario"]
        tag_names = [tag["name"] for tag in scenario.get("tags", [])]

        scn_pending_count = tag_names.count(_SCN_PENDING_TAG)
        if scn_pending_count != 1:
            raise FeatureGenerationError(
                f"requirement_id={requirement.requirement_id!r}: scenario "
                f"{scenario.get('name')!r} has {scn_pending_count} @SCN-PENDING "
                "tags; exactly one is required."
            )

        ac_ids = [t for t in tag_names if _AC_TAG_RE.match(t)]
        if not ac_ids:
            raise FeatureGenerationError(
                f"requirement_id={requirement.requirement_id!r}: scenario "
                f"{scenario.get('name')!r} carries no @AC-* tag."
            )
        unknown = [ac for ac in ac_ids if ac.removeprefix("@") not in known_ac_ids]
        if unknown:
            raise FeatureGenerationError(
                f"requirement_id={requirement.requirement_id!r}: scenario "
                f"{scenario.get('name')!r} tags unknown criterion id(s) {unknown!r}."
            )

        functional_tags = [t for t in tag_names if t != _SCN_PENDING_TAG and t not in ac_ids]

        ordered_children.append(("scenario", scenario))
        pending.append(
            {
                "scenario": scenario,
                "ac_ids": [t.removeprefix("@") for t in ac_ids],
                "functional_tags": functional_tags,
                "canonical_content": canonical_scenario_content(scenario),
            }
        )
        for ac_id in pending[-1]["ac_ids"]:
            ac_coverage[ac_id] = True

    # Mint SCN-* ids, grouped by each scenario's first AC tag (its "parent"
    # for the id's own shape), via a stable content sort within that group.
    groups: dict[str, list[int]] = {}
    for index, item in enumerate(pending):
        groups.setdefault(item["ac_ids"][0], []).append(index)

    scn_id_by_index: dict[int, str] = {}
    for parent_ac_id, indices in groups.items():
        contents = [pending[i]["canonical_content"] for i in indices]
        for i, scn_id in zip(indices, generate_scenario_ids(parent_ac_id, contents), strict=True):
            scn_id_by_index[i] = scn_id

    # Hoist: ANY tag identical across every scenario -- id tag or
    # functional tag alike -- moves to Feature level (D2's hoist-extension
    # note). A homogenous tag is a Feature-level fact by definition, and
    # Cucumber resolves Feature-level and scenario-level tags identically
    # for tag-filtered selection, so hoisting a functional tag changes
    # nothing about which scenarios a filter selects. @REQ-* never enters
    # this computation at all -- it is never per-scenario in this design.
    # @SCN-* is unique per scenario by construction (content-addressed;
    # a shared SCN-* would mean duplicate scenario content, itself a
    # separate no-dupe-scenario-names violation), so it only ever appears
    # in the intersection in the single-scenario case, same as before.
    per_scenario_all_tags = [
        set(item["functional_tags"])
        | {f"@{ac}" for ac in item["ac_ids"]}
        | {f"@{scn_id_by_index[i]}"}
        for i, item in enumerate(pending)
    ]
    hoisted_tags: set[str] = (
        set.intersection(*per_scenario_all_tags) if per_scenario_all_tags else set()
    )

    rendered_blocks: list[str] = []
    scenario_assignments: list[ScenarioAssignment] = []
    scenario_index = 0
    for kind, payload in ordered_children:
        if kind == "background":
            rendered_blocks.append(render_background(payload))
            continue

        item = pending[scenario_index]
        scenario = item["scenario"]
        id_tags = [f"@{ac}" for ac in item["ac_ids"]] + [f"@{scn_id_by_index[scenario_index]}"]
        scenario_tags = [t for t in item["functional_tags"] if t not in hoisted_tags] + [
            t for t in id_tags if t not in hoisted_tags
        ]
        rendered_blocks.append(
            render_scenario(
                keyword=scenario["keyword"],
                name=scenario["name"],
                tags=scenario_tags,
                steps=scenario.get("steps", []),
                examples=scenario.get("examples", []),
            )
        )
        scenario_assignments.append(
            ScenarioAssignment(
                name=scenario["name"],
                scn_id=scn_id_by_index[scenario_index],
                ac_ids=tuple(item["ac_ids"]),
            )
        )
        scenario_index += 1

    req_tag = f"@{requirement.requirement_id}"
    feature_tags = [req_tag, *sorted(hoisted_tags)]
    feature_name, title_comment = derive_feature_name(requirement.title, requirement.requirement_id)
    assembled = render_feature(
        title=feature_name,
        feature_tags=feature_tags,
        body_blocks=rendered_blocks,
        comment=title_comment,
    )

    lint_config = load_config(_LINTRC_PATH)
    assembled_source = parse_source_text(assembled, path=label)
    lint_result = lint_source(assembled_source, lint_config)
    if not lint_result.is_clean:
        raise FeatureGenerationError(
            f"requirement_id={requirement.requirement_id!r}: assembled feature "
            f"failed lint: {lint_result.violations}",
            lint_result=lint_result,
            content=assembled,
        )

    file_path = derive_feature_file_path(requirement, features_root=features_root)

    return GeneratedFeature(
        requirement_id=requirement.requirement_id,
        content=assembled,
        file_path=file_path,
        req_tag=req_tag,
        scenarios=tuple(scenario_assignments),
        acceptance_criteria_coverage=ac_coverage,
        lint_result=lint_result,
    )


def write_generated_feature(generated: GeneratedFeature) -> None:
    """Persist an already-validated :class:`GeneratedFeature` to disk.

    Separate from :func:`generate_feature_file` on purpose: generation and
    validation are pure and side-effect-free; a future caller (run-state
    wiring, ADR-0036) decides *whether* to write based on its own
    ``content_hash``-driven SKIP predicate (D8) -- this function performs
    only the mechanical write once that decision is made.
    """
    generated.file_path.parent.mkdir(parents=True, exist_ok=True)
    generated.file_path.write_text(generated.content, encoding="utf-8")
