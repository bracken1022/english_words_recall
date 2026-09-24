"""Static-content assertions for src/web/templates/index.html and
static/{style.css,app.js} (spec 004). These check that expected structure/
class names/wording are actually present in the shipped files — not
rendered output, per research.md's established "no JS test runner"
convention. Deep visual verification stays manual (quickstart.md)."""

import re
from pathlib import Path

TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "src/web/templates/index.html"
CSS_PATH = Path(__file__).resolve().parents[2] / "src/web/static/style.css"
JS_PATH = Path(__file__).resolve().parents[2] / "src/web/static/app.js"


def _section_bounds(html: str, section_id: str) -> tuple[int, int]:
    start = html.index(f'id="{section_id}"')
    open_tag_start = html.rindex("<section", 0, start)
    close_tag = html.index("</section>", start)
    return open_tag_start, close_tag


def test_word_feedback_element_exists_outside_step_sections():
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert 'id="word-feedback"' in html

    feedback_pos = html.index('id="word-feedback"')
    for section_id in ("recall-view", "sentence-view", "feedback-view"):
        section_start, section_end = _section_bounds(html, section_id)
        assert not (section_start < feedback_pos < section_end), (
            f"word-feedback element must not be nested inside #{section_id}"
        )


def test_style_defines_feedback_color_classes():
    css = CSS_PATH.read_text(encoding="utf-8")
    assert ".feedback-correct" in css
    assert ".feedback-incorrect" in css


def test_app_js_uses_the_requested_feedback_wording():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "Correct:" in js
    assert "Incorrect. The correct expression is:" in js


def test_feedback_correct_uses_green_not_red():
    """Spec 008: a correct recall result must render in a distinct green,
    while an incorrect one keeps today's red (no new .feedback-incorrect
    color override should be needed at all)."""
    css = CSS_PATH.read_text(encoding="utf-8")

    match = re.search(r"\.feedback-correct\s*{([^}]*)}", css)
    assert match is not None, "style.css must define a plain .feedback-correct color rule"
    rule_body = match.group(1)
    assert "--green" in rule_body
    assert "--red" not in rule_body

    assert re.search(r"\.feedback-incorrect\s*{([^}]*)}", css) is None, (
        ".feedback-incorrect should need no color override — it already inherits "
        "#word-feedback's base red"
    )


def test_style_defines_field_row_layout():
    css = CSS_PATH.read_text(encoding="utf-8")
    assert ".field-row" in css


def test_answer_and_sentence_forms_use_field_row():
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    for form_id, input_id in (("answer-form", "answer-input"), ("sentence-form", "sentence-input")):
        form_start = html.index(f'id="{form_id}"')
        form_end = html.index("</form>", form_start)
        form_html = html[form_start:form_end]
        assert "field-row" in form_html, f"#{form_id} must contain a field-row wrapper"
        assert f'id="{input_id}"' in form_html


def test_hidden_attribute_override_rule_exists():
    """Regression guard (spec 005): style.css sets `display: none` on
    `section` and `.spinner`, which silently defeats the HTML `hidden`
    attribute unless an explicit, higher-priority override exists. See
    research.md "Root cause, confirmed by reading the shipped code"."""
    css = CSS_PATH.read_text(encoding="utf-8")
    match = re.search(r"\[hidden\]\s*{([^}]*)}", css)
    assert match is not None, "style.css must define a [hidden] rule that overrides other display rules"
    rule_body = match.group(1)
    assert "display" in rule_body and "none" in rule_body
    assert "!important" in rule_body, (
        "the [hidden] override must use !important — without it, .spinner{display:flex} and "
        "section{display:flex} (equal or higher specificity/order) can still win the cascade"
    )


def test_app_js_confirms_before_skipping_an_empty_sentence():
    """Spec 006: submitting the sentence step with an empty/whitespace-only
    sentence must show a confirmation prompt and call POST /api/skip,
    rather than silently sending nothing off for correction."""
    js = JS_PATH.read_text(encoding="utf-8")
    assert ".trim()" in js
    assert "confirm(" in js
    assert "/api/skip" in js


def test_app_js_renders_choose_view_from_state_collections():
    """Spec 007: the choice screen's entries are rendered client-side from
    GET /api/state's `collections` list, each posting its own key to
    POST /api/select — not static markup."""
    js = JS_PATH.read_text(encoding="utf-8")
    assert "state.collections" in js
    assert "/api/select" in js
    assert "choose-view" in js


def test_app_js_wires_up_voice_input():
    """Spec 009: recording is captured via MediaRecorder and uploaded to
    /api/transcribe; the mic control's visibility follows state.voice_available
    rather than always being shown."""
    js = JS_PATH.read_text(encoding="utf-8")
    assert "MediaRecorder" in js
    assert "getUserMedia" in js
    assert "/api/transcribe" in js
    assert "voice_available" in js


def test_app_js_tracks_order_and_sends_it_with_select():
    """Spec 011: the choose screen's order toggle is submitted together
    with the collection in one POST /api/select call, not a second step."""
    js = JS_PATH.read_text(encoding="utf-8")
    assert "order-choice" in js
    assert "getSelectedOrder" in js
    select_call_start = js.index('await fetch("/api/select"')
    select_call_end = js.index(");", select_call_start)
    assert "order" in js[select_call_start:select_call_end]


def test_choose_view_offers_an_order_toggle():
    """Spec 011: the order choice lives on the existing collection-choice
    screen (spec 007), not a separate one."""
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    choose_start, choose_end = _section_bounds(html, "choose-view")
    choose_html = html[choose_start:choose_end]
    assert 'name="order-choice"' in choose_html
    assert 'value="sequential"' in choose_html
    assert 'value="random"' in choose_html


def test_spinner_uses_hidden_attribute_not_a_separate_mechanism():
    """Regression guard (spec 005, User Story 2): confirms the spinner is
    actually covered by the [hidden] override above, rather than using
    some other visibility mechanism the fix wouldn't reach."""
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    spinner_tag_start = html.index('id="spinner"')
    tag_open = html.rindex("<", 0, spinner_tag_start)
    tag_close = html.index(">", spinner_tag_start)
    spinner_tag = html[tag_open:tag_close]
    assert "hidden" in spinner_tag.split(), "the spinner element must use the plain `hidden` attribute"
    assert "style=" not in spinner_tag, "the spinner must not hide itself via an inline style"
