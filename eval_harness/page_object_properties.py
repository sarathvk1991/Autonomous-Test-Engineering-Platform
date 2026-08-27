"""ADR-0051 D2's deterministic property/assertion checks for one generated
page-object artifact (`LivePageObjectGenerator`'s raw output).

**Composed, not invented (ADR-0051 D1, the reframe) -- and the RICHEST
grounding of any increment in this arc.** Page-object is a FOURTH artifact
type: a Java class extending `BasePage`, governed by `generate_page_objects`
v1.3.0's own OUTPUT CONTRACT (locators, a constructor-injected `WebDriver`
per ADR-0041 D5, and one action method per requested `method_name`), plus
CP4's own real, already-live static locator-health gate
(`automation_engineering.cp4`). Unlike feature-content/test-data (contract-
grounded, no known incident), page-object has THREE real, MEASURED defects
on record from the 2026-08-10 live regeneration run against the real 32-class
corpus (`[[cap-page-object-live-regen-findings]]`), each independently fixed
on the input side since (`live_page_object_generator.py`'s own module
docstring records all three fixes in full):

1. **Method-name mismatch** (67% of requested calls, the v1.0.0 defect) --
   `check_method_names_present` guards its regression: the generated class
   must declare every `method_name` the context actually requested, verbatim,
   never a name the model paraphrases from `action_text`. Ports
   `live_page_object_generator._declares_method`'s own regex verbatim (a
   private, non-exported helper -- the same "port, don't reach into another
   module's internals" discipline `test_data_properties.check_no_env_binding`
   already established for a different module's private guard).
2. **`new XPage()` vs. constructor-injected `WebDriver`** (ADR-0041 D5) --
   `check_di_constructor` guards its regression: the declared constructor
   must take exactly one `WebDriver` parameter (never no-arg), and the class
   must never construct or statically hold its own driver -- the v1.3.0
   prompt's own explicit CONSTRAINTS-section text, verbatim.
3. **Fictional `BasePage` helpers** (31 of 32 generated classes, the
   v1.1.0-era defect) -- `check_no_fictional_basepage_helper` guards its
   regression against BASEPAGE'S REAL INHERITED API, the v1.2.0+ prompt's own
   hardcoded inventory (`open(String)`/`currentTitle()`/`driver`/`wait` --
   nothing else, `generate_page_objects_v1.3.0.txt`'s own section of that
   exact name).

**CP4's real, already-live check, composed directly.**
`check_locator_validity` calls `automation_engineering.cp4.gate.evaluate_cp4`
DIRECTLY (a genuinely public function, no port needed -- CP4 has no
adapter/Protocol seam at all per its own module docstring, "there is nothing
live to stand in for") against the one generated class -- the SAME static
locator-health gate the real stage-16 wiring already runs (`[[cp7-cp8-stage16-
wiring]]`), proven to fail on an absolute-XPath locator among its four
criteria (`locator_uniqueness`/`duplicate_locators`/`dynamic_xpath`/
`well_formedness`). Evaluating one class at a time (this package's own
per-case grain, ADR-0051 D2) means `duplicate_locators` -- CROSS-class by its
own design -- structurally never fires here; this is an honest consequence
of the per-case scoring grain, not a check this module invented that no real
input can trigger (the feature-content unreachable-check lesson): the OTHER
three criteria remain fully live at this grain, and `duplicate_locators`
would fire the moment this check is ever composed across more than one
generated class in the same call, exactly as CP4 itself already does in the
real stage-16 run.

**A FIFTH check, additive (the DOM-grounding fix, `generate_page_objects`
v1.4.0).** `check_locator_validity` above verifies locator SYNTAX only
(uniqueness, no duplicates, no dynamic-XPath anti-pattern, well-formedness)
-- it has no way to tell a syntactically-valid, well-formed, UNIQUE, but
completely FABRICATED selector (e.g. a hallucinated `By.id("cart-count")`
for a real element whose actual id is unrelated) from a genuine one; this
was the honest gap the DOM-grounding finding's own surfacing named.
`check_locator_grounding` closes it: given `context.locator_catalog` (the
active target's real, curated selectors), every locator literal in
generated text must be either a verbatim catalog value or the honest
placeholder -- never a third, invented string. `NOT_APPLICABLE` when the
catalog is empty (nothing to verify grounding against, the same posture
`check_locator_validity` takes for unparseable input) -- not counted as a
false PASS.

**One check NOT built, considered and reported honestly.** A page-object-
specific `customqa:long-method`/`customqa:direct-webdriver-action` check was
considered and rejected as a NEW check here: `test_data_properties.
check_no_long_method` already calls CP3's real, public `evaluate_long_method`
directly, with NO class-role restriction (that function's own docstring:
"ANY generated class... no class-role restriction") -- a page-object-specific
long-method check would be a second definition of an already-generic,
already-reusable check, not a new artifact-type-specific finding. Left to a
future increment's own decision whether to compose it into this module's
default set (out of this build's own scope: page object's OWN THREE real
defect shapes plus CP4, per this task's own brief).

Every check is a pure function of ``(generated_text, context)`` -- no LLM
call, no filesystem access, no subprocess. Each returns
:class:`~eval_harness.models.PropertyCheckOutcome.NOT_APPLICABLE` rather than
a vacuous PASS when nothing in the content gives the check anything to
evaluate -- ``NOT_APPLICABLE`` results are excluded from the eval score's
pass-rate denominator (:mod:`.scoring`), never silently counted as evidence
of quality.
"""

from __future__ import annotations

import re
from collections.abc import Callable

import javalang

from automation_engineering.catalog.locator_catalog import LOCATOR_PLACEHOLDER_VALUE
from automation_engineering.cp4.gate import evaluate_cp4
from automation_engineering.cp4.models import Cp4PageObjectInput
from automation_engineering.generation.page_object_generator import PageObjectGenerationContext
from eval_harness.models import PropertyCheckOutcome, PropertyCheckResult

#: Ported VERBATIM from `automation_engineering.generation.
#: live_page_object_generator._declares_method` -- the real, live
#: generator's own best-effort, regex-based method-declaration presence
#: check (module docstring's own "completeness, honestly bounded" section):
#: NOT a Java parse or compile, matches `method_name` immediately followed
#: by an opening parenthesis.
_METHOD_CALL_RE_TEMPLATE = r"\b{name}\s*\("

#: `generate_page_objects` v1.3.0's own CONSTRAINTS-section text, verbatim:
#: "the constructor must RECEIVE a WebDriver parameter and pass it to
#: BasePage's own constructor (super(driver)); a page object that constructs
#: or statically caches its own driver is not parallel-safe... (ADR-0041 D5)."
_DI_CONSTRUCTOR_RE_TEMPLATE = r"public\s+{class_name}\s*\(\s*WebDriver\s+\w+\s*\)"
_NO_ARG_CONSTRUCTOR_RE_TEMPLATE = r"public\s+{class_name}\s*\(\s*\)"
_SUPER_CALL_RE = re.compile(r"\bsuper\s*\(")
_STATIC_WEBDRIVER_FIELD_RE = re.compile(r"\bstatic\s+(?:final\s+)?WebDriver\b")

#: `generate_page_objects_v1.3.0.txt`'s own "BASEPAGE'S REAL INHERITED API"
#: section, verbatim: "This is the ENTIRE inherited surface. BasePage does
#: NOT provide isElementDisplayed, sendKeys, click, findElement, getText, or
#: any other convenience helper." `isElementDisplayed` has no real API under
#: that exact name ANYWHERE (Selenium's own `WebElement` method is
#: `isDisplayed()`, not `isElementDisplayed()`) -- always fictional, any call
#: shape. The other four ARE real Selenium `WebDriver`/`WebElement` methods
#: -- legitimate when QUALIFIED on `driver`/an element (e.g.
#: `driver.findElement(locator).click()`), fictional only when called BARE,
#: as if inherited from `BasePage` itself (the exact live-measured shape:
#: 31 of 32 generated classes called at least one of these unqualified,
#: `[[cap-page-object-live-regen-findings]]`).
_ALWAYS_FICTIONAL_BASEPAGE_NAMES: tuple[str, ...] = ("isElementDisplayed",)
_QUALIFIED_ONLY_REAL_NAMES: tuple[str, ...] = ("sendKeys", "click", "findElement", "getText")

PropertyCheck = Callable[[str, PageObjectGenerationContext], PropertyCheckResult]


def _declares_method(java_source: str, method_name: str) -> bool:
    """Ported verbatim from `live_page_object_generator._declares_method`."""
    pattern = _METHOD_CALL_RE_TEMPLATE.format(name=re.escape(method_name))
    return re.search(pattern, java_source) is not None


def check_method_names_present(
    generated_text: str, context: PageObjectGenerationContext
) -> PropertyCheckResult:
    """Guards defect 1's regression (67% of requested method calls came back
    under the wrong name, `[[cap-page-object-live-regen-findings]]`): the
    generated class must declare every `method_name` this context actually
    requested -- the primary (`context.method_name`) plus every
    `context.additional_method_needs` sibling -- verbatim, never a name the
    model paraphrases from `action_text`. Always applicable: this
    generator's own live wrapper already requires `method_name`
    unconditionally (`LivePageObjectGenerator.generate`'s own `ValueError`
    guard), so every real call has at least one expected name to check.
    """
    expected_names = (
        context.method_name,
        *(need.method_name for need in context.additional_method_needs),
    )
    missing = [
        name for name in expected_names if name and not _declares_method(generated_text, name)
    ]
    if missing:
        return PropertyCheckResult(
            check_name="method_names_present",
            outcome=PropertyCheckOutcome.FAILED,
            reason=f"generated class is missing (or renamed) {len(missing)} of "
            f"{len(expected_names)} requested method(s): {missing!r}",
        )
    return PropertyCheckResult(
        check_name="method_names_present", outcome=PropertyCheckOutcome.PASSED
    )


def check_di_constructor(
    generated_text: str, context: PageObjectGenerationContext
) -> PropertyCheckResult:
    """Guards defect 2's regression (`new XPage()` vs. a constructor-injected
    `WebDriver`, `[[cap-page-object-live-regen-findings]]`): the v1.3.0
    prompt's own CONSTRAINTS text, verbatim -- "the constructor must RECEIVE
    a WebDriver parameter and pass it to BasePage's own constructor
    (super(driver))... never construct or statically hold... (ADR-0041 D5)."
    Always applicable.
    """
    class_name = re.escape(context.class_name)
    no_arg_pattern = _NO_ARG_CONSTRUCTOR_RE_TEMPLATE.format(class_name=class_name)
    no_arg = re.search(no_arg_pattern, generated_text)
    if no_arg is not None:
        return PropertyCheckResult(
            check_name="di_constructor",
            outcome=PropertyCheckOutcome.FAILED,
            reason=f"{context.class_name} declares a no-arg constructor -- WebDriver must be "
            "constructor-injected, never constructed or statically held (ADR-0041 D5)",
        )
    if _STATIC_WEBDRIVER_FIELD_RE.search(generated_text):
        return PropertyCheckResult(
            check_name="di_constructor",
            outcome=PropertyCheckOutcome.FAILED,
            reason=f"{context.class_name} statically holds a WebDriver -- not parallel-safe "
            "once cucumber.execution.parallel.enabled is set (ADR-0041 D5)",
        )
    di_ctor = re.search(_DI_CONSTRUCTOR_RE_TEMPLATE.format(class_name=class_name), generated_text)
    if di_ctor is None:
        return PropertyCheckResult(
            check_name="di_constructor",
            outcome=PropertyCheckOutcome.FAILED,
            reason=f"no public {context.class_name}(WebDriver ...) constructor found",
        )
    if not _SUPER_CALL_RE.search(generated_text):
        return PropertyCheckResult(
            check_name="di_constructor",
            outcome=PropertyCheckOutcome.FAILED,
            reason=f"{context.class_name}'s constructor never calls super(driver) -- BasePage's "
            "own constructor must receive the injected WebDriver",
        )
    return PropertyCheckResult(check_name="di_constructor", outcome=PropertyCheckOutcome.PASSED)


def check_no_fictional_basepage_helper(
    generated_text: str, context: PageObjectGenerationContext
) -> PropertyCheckResult:
    """Guards defect 3's regression (31 of 32 generated classes called a
    fictional BasePage helper, `[[cap-page-object-live-regen-findings]]`):
    every locator interaction must go through a REAL inherited BasePage
    method (`open`/`currentTitle`) or this class's own `driver`/`wait`
    fields directly (e.g. `driver.findElement(locator).click()`) -- never an
    invented, bare-called helper. Always applicable.
    """
    reasons: list[str] = []
    for name in _ALWAYS_FICTIONAL_BASEPAGE_NAMES:
        if re.search(rf"\b{re.escape(name)}\s*\(", generated_text):
            reasons.append(
                f"calls {name}(...) -- no such method exists on BasePage or Selenium's real "
                "WebElement/WebDriver API (the real Selenium method is isDisplayed())"
            )
    for name in _QUALIFIED_ONLY_REAL_NAMES:
        for match in re.finditer(rf"\b{re.escape(name)}\s*\(", generated_text):
            preceding = generated_text[: match.start()].rstrip()
            if not preceding.endswith("."):
                reasons.append(
                    f"calls {name}(...) unqualified, as if inherited from BasePage -- BasePage "
                    f"has no such method; {name} is only real when qualified on driver/an "
                    "element (e.g. driver.findElement(locator)." + name + "(...))"
                )
                break
    if reasons:
        return PropertyCheckResult(
            check_name="no_fictional_basepage_helper",
            outcome=PropertyCheckOutcome.FAILED,
            reason="; ".join(reasons),
        )
    return PropertyCheckResult(
        check_name="no_fictional_basepage_helper", outcome=PropertyCheckOutcome.PASSED
    )


def check_locator_validity(
    generated_text: str, context: PageObjectGenerationContext
) -> PropertyCheckResult:
    """Composes CP4's real, already-live static locator-health gate
    (`automation_engineering.cp4.gate.evaluate_cp4`) directly against the one
    generated class -- proven, live, to fail on an absolute-XPath locator
    among `locator_uniqueness`/`duplicate_locators`/`dynamic_xpath`/
    `well_formedness` (`[[cp7-cp8-stage16-wiring]]`).

    ``NOT_APPLICABLE`` when `generated_text` is not parseable Java --
    CP4 itself has no degrade-to-empty behaviour for unparseable input
    (unlike `evaluate_long_method`), so a parse failure here means "no
    locators could be evaluated," not "zero real locator defects were
    found." Mirrors `automation_engineering.cp3.architecture`'s own
    `(JavaSyntaxError, LexerError)` catch, the same exception pair CP3's own
    parse boundary already degrades on.
    """
    try:
        result = evaluate_cp4(
            (Cp4PageObjectInput(class_name=context.class_name, java_source=generated_text),)
        )
    except (javalang.parser.JavaSyntaxError, javalang.tokenizer.LexerError) as exc:
        return PropertyCheckResult(
            check_name="locator_validity",
            outcome=PropertyCheckOutcome.NOT_APPLICABLE,
            reason=f"generated text is not parseable Java -- no locators to evaluate ({exc})",
        )
    if result.passed:
        return PropertyCheckResult(
            check_name="locator_validity", outcome=PropertyCheckOutcome.PASSED
        )
    messages = tuple(message for criterion in result.criteria for message in criterion.messages)
    return PropertyCheckResult(
        check_name="locator_validity",
        outcome=PropertyCheckOutcome.FAILED,
        reason="; ".join(messages),
    )


#: Matches a Selenium `By.<strategy>("<value>")` locator declaration's own
#: literal string argument -- the shape every catalog-grounded OR
#: placeholder locator this platform's own generator ever emits (module
#: docstring's own GROUNDING RULE, `generate_page_objects` v1.4.0). Deliberately
#: does not attempt to parse a concatenated/dynamic expression (e.g.
#: `By.xpath("//div[...]" + productName)`) -- this platform's own real
#: locator catalog never covers a dynamic element (a recorded gap, this
#: module's own docstring), so a dynamic locator is never expected to match
#: the catalog literally; this check only ever inspects the FIRST literal
#: string segment of each `By.*(...)` call.
_LOCATOR_LITERAL_RE = re.compile(r'By\.\w+\(\s*"((?:[^"\\]|\\.)*)"')


def check_locator_grounding(
    generated_text: str, context: PageObjectGenerationContext
) -> PropertyCheckResult:
    """Guards the DOM-grounding finding's own regression (hallucinated
    locators for real SUT elements -- `By.id("username")` vs. the real
    `user-name`, `By.id("error-message")` vs. the real
    `[data-test='error']`, `By.id("cart-count")` vs. the real
    `.shopping_cart_badge`): every locator's own literal value in
    ``generated_text`` must be either a verbatim value from
    ``context.locator_catalog`` or the honest placeholder
    (:data:`~automation_engineering.catalog.locator_catalog.LOCATOR_PLACEHOLDER_VALUE`)
    -- never a third, uncatalogued, invented string.

    ``NOT_APPLICABLE`` when ``context.locator_catalog`` is empty: an empty
    catalog means no grounding was ever available for this generation (an
    uncatalogued target, or a context built before this fix existed) -- this
    check cannot meaningfully judge compliance either way, the same
    "nothing to evaluate" posture :func:`check_locator_validity` already
    takes for unparseable Java. Also ``NOT_APPLICABLE`` when no `By.*(...)`
    locator literal is found at all (nothing to check).
    """
    if not context.locator_catalog:
        return PropertyCheckResult(
            check_name="locator_grounding",
            outcome=PropertyCheckOutcome.NOT_APPLICABLE,
            reason="context.locator_catalog is empty -- no grounding was available to "
            "verify compliance against",
        )
    literals = _LOCATOR_LITERAL_RE.findall(generated_text)
    if not literals:
        return PropertyCheckResult(
            check_name="locator_grounding",
            outcome=PropertyCheckOutcome.NOT_APPLICABLE,
            reason="no By.*(\"...\") locator literal found in generated text",
        )
    catalog_values = {entry.value for entry in context.locator_catalog}
    ungrounded = [
        literal
        for literal in literals
        if literal != LOCATOR_PLACEHOLDER_VALUE and literal not in catalog_values
    ]
    if ungrounded:
        return PropertyCheckResult(
            check_name="locator_grounding",
            outcome=PropertyCheckOutcome.FAILED,
            reason=f"{len(ungrounded)} locator value(s) are neither a catalog value nor the "
            f"honest placeholder {LOCATOR_PLACEHOLDER_VALUE!r} -- invented/hallucinated: "
            f"{ungrounded!r}",
        )
    return PropertyCheckResult(check_name="locator_grounding", outcome=PropertyCheckOutcome.PASSED)


#: ADR-0051 D2/D5's page-object check set -- three targeting the three real,
#: measured 2026-08-10 defect shapes, one composing CP4's real, already-live
#: locator-health gate directly, and one (additive, the DOM-grounding fix)
#: verifying every locator is either catalog-grounded or an honest
#: placeholder, never invented. Ordered deterministically; a caller wanting
#: a different or extended set composes its own tuple rather than mutating
#: this one.
PAGE_OBJECT_PROPERTY_CHECKS: tuple[PropertyCheck, ...] = (
    check_method_names_present,
    check_di_constructor,
    check_no_fictional_basepage_helper,
    check_locator_validity,
    check_locator_grounding,
)


def run_property_checks(
    generated_text: str,
    context: PageObjectGenerationContext,
    checks: tuple[PropertyCheck, ...] = PAGE_OBJECT_PROPERTY_CHECKS,
) -> tuple[PropertyCheckResult, ...]:
    """Run every check in ``checks`` against one generated artifact,
    deterministically, in order -- no LLM call, no I/O."""
    return tuple(check(generated_text, context) for check in checks)


__all__ = [
    "PAGE_OBJECT_PROPERTY_CHECKS",
    "PropertyCheck",
    "check_di_constructor",
    "check_locator_grounding",
    "check_locator_validity",
    "check_method_names_present",
    "check_no_fictional_basepage_helper",
    "run_property_checks",
]
