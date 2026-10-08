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
    """Broadsheet redesign: recall and review results are rubber stamps
    whose wording carries the verdict as well as the color."""
    js = JS_PATH.read_text(encoding="utf-8")
    for label in ('"Correct"', '"Not quite"', '"Natural"', '"Small fix"'):
        assert label in js, f"app.js missing stamp wording {label}"


def test_feedback_correct_uses_cyan_and_incorrect_uses_magenta():
    """Spec 008, restated for the Broadsheet ramps: a correct result is
    cyan (accent) and never magenta; an incorrect one is magenta (accent-2)."""
    css = CSS_PATH.read_text(encoding="utf-8")

    correct = re.search(r"\.feedback-correct\s*{([^}]*)}", css)
    assert correct is not None, "style.css must define a .feedback-correct rule"
    assert "--color-accent-700" in correct.group(1)
    assert "--color-accent-2" not in correct.group(1)

    incorrect = re.search(r"\.feedback-incorrect\s*{([^}]*)}", css)
    assert incorrect is not None, "style.css must define a .feedback-incorrect rule"
    assert "--color-accent-2-700" in incorrect.group(1)


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


def test_app_js_tracks_mode_and_sends_it_with_select():
    """Spec 012: the choose screen's mode toggle is submitted together
    with the collection (and order) in one POST /api/select call."""
    js = JS_PATH.read_text(encoding="utf-8")
    assert "mode-choice" in js
    assert "getSelectedMode" in js
    select_call_start = js.index('await fetch("/api/select"')
    select_call_end = js.index(");", select_call_start)
    assert "mode" in js[select_call_start:select_call_end]


def test_app_js_answer_handler_never_auto_advances():
    """Broadsheet redesign: every recall result (correct or not, either
    mode) waits for the learner's Enter / Continue. The answer handler
    must not schedule a timed advance."""
    js = JS_PATH.read_text(encoding="utf-8")
    answer_handler_start = js.index('answerForm.addEventListener("submit"')
    answer_handler_end = js.index("\n  });", answer_handler_start)
    assert "setTimeout" not in js[answer_handler_start:answer_handler_end]


def test_choose_view_offers_a_mode_toggle():
    """Spec 012: the mode choice lives on the existing collection/order
    choice screen (specs 007/011), not a separate one."""
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    choose_start, choose_end = _section_bounds(html, "choose-view")
    choose_html = html[choose_start:choose_end]
    assert 'name="mode-choice"' in choose_html
    assert 'value="sentence"' in choose_html
    assert 'value="recall-only"' in choose_html


def test_continue_button_exists_outside_step_sections():
    """Spec 013: the Continue button must be a persistent element (like
    #word-feedback), reused for both the "feedback" step (sentence mode)
    and the new "reveal" step (recall-only wrong answer) — not nested
    inside #feedback-view, which is hidden for the "reveal" step."""
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert 'id="continue-button"' in html

    button_pos = html.index('id="continue-button"')
    for section_id in ("recall-view", "sentence-view", "feedback-view"):
        section_start, section_end = _section_bounds(html, section_id)
        assert not (section_start < button_pos < section_end), (
            f"continue-button must not be nested inside #{section_id}"
        )


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


# --- Broadsheet redesign (design_handoff_english_tutor) ---


def test_style_carries_broadsheet_tokens():
    css = CSS_PATH.read_text(encoding="utf-8")
    for token in (
        "--color-bg: #f3f2f2",
        "--color-text: #201e1d",
        "--color-accent: #0088b0",
        "--color-accent-2: #d6006c",
        '"Source Serif 4"',
    ):
        assert token in css, f"style.css missing Broadsheet token {token}"


def test_template_loads_fonts_and_icons_with_fallbacks():
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert "fonts.googleapis.com" in html and "Noto+Serif+SC" in html
    assert "@phosphor-icons/web@2.1.1" in html
    css = CSS_PATH.read_text(encoding="utf-8")
    assert "Songti SC" in css, "Chinese text needs a local serif fallback when offline"


def test_session_controls_are_wired_to_their_endpoints():
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    js = JS_PATH.read_text(encoding="utf-8")
    for element_id, endpoint in (
        ("end-session-button", "/api/end"),
        ("retry-sentence-button", "/api/retry-sentence"),
        ("skip-button", "/api/skip"),
    ):
        assert f'id="{element_id}"' in html
        assert endpoint in js


def test_show_answer_submits_a_blank_answer():
    """"Show answer" counts as wrong: it goes through the same /api/answer
    grading as a typed guess (a blank answer is graded incorrect)."""
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    js = JS_PATH.read_text(encoding="utf-8")
    assert 'id="show-answer-button"' in html
    handler = js[js.index("showAnswerButton.addEventListener") :]
    handler = handler[: handler.index("\n  });")]
    assert "submitAnswer(\"\")" in handler


def test_review_shortcut_accepts_cmd_or_ctrl_enter():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "metaKey" in js and "ctrlKey" in js


def test_check_and_review_buttons_disable_when_empty():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "answerSubmitButton.disabled" in js
    assert "sentenceSubmitButton.disabled" in js


def test_narrow_layout_keeps_touch_targets_at_least_44px():
    css = CSS_PATH.read_text(encoding="utf-8")
    narrow = css[css.index("@media (max-width: 600px)") :]
    assert "min-height: 44px" in narrow


# --- spec 015: login screen and account header -----------------------------


def test_login_view_has_labelled_fields_submit_and_error_region():
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    start, end = _section_bounds(html, "login-view")
    section = html[start:end]
    assert 'class="screen"' in section
    assert re.search(r'id="login-username"[^>]*autocomplete="username"', section)
    assert re.search(r'id="login-password"[^>]*type="password"', section) or re.search(
        r'type="password"[^>]*id="login-password"', section
    )
    assert 'autocomplete="current-password"' in section
    assert '<label for="login-username"' in section
    assert '<label for="login-password"' in section
    assert re.search(r'<button type="submit"[^>]*>Log in</button>', section)
    assert re.search(r'id="login-error"[^>]*role="alert"', section)


def test_header_has_account_name_and_logout_button():
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    header = html[html.index("<header") : html.index("</header>")]
    assert 'id="account-name"' in header
    assert 'id="logout-button"' in header


def test_app_js_handles_login_and_unauthorized():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "401" in js
    assert "/api/login" in js
    assert "login-view" in js
    assert "Username or password is incorrect" in js
    assert "Enter both a username and a password" in js
    assert "localStorage" not in js


def test_app_js_logout_button_posts_logout_and_shows_login():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "/api/logout" in js
    handler_start = js.index("logoutButton.addEventListener")
    handler = js[handler_start : js.index("\n  });", handler_start)]
    assert '"/api/logout"' in handler
    assert "showLogin()" in handler


# --- spec 016: word-list upload ----------------------------------------------


def test_choose_view_has_upload_controls():
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    start, end = _section_bounds(html, "choose-view")
    section = html[start:end]
    assert re.search(r'id="upload-button"[^>]*>Upload word list</button>', section)
    assert re.search(
        r'<input id="upload-input" type="file" accept="\.csv,\.txt,\.tsv,\.md,\.markdown"', section
    )
    assert 'id="upload-format-hint"' in section
    assert re.search(r'id="upload-result"[^>]*role="status"', section)


def test_empty_view_has_upload_button():
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    start, end = _section_bounds(html, "empty-view")
    assert 'id="empty-upload-button"' in html[start:end]


def test_app_js_uploads_with_formdata_and_confirms_replace():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "/api/word-lists" in js
    assert "FormData" in js
    assert "replace" in js
    assert "Added " in js
    assert "From now on you'll practice your own lists." in js


def test_word_source_note():
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    start, end = _section_bounds(html, "choose-view")
    assert 'id="word-source-note"' in html[start:end]
    js = JS_PATH.read_text(encoding="utf-8")
    assert "Practicing your own word lists." in js
    assert "Practicing the shared word sets" in js


def test_my_lists_ui_with_delete():
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    start, end = _section_bounds(html, "choose-view")
    assert 'id="my-lists"' in html[start:end]
    js = JS_PATH.read_text(encoding="utf-8")
    assert 'method: "DELETE"' in js
    assert "encodeURIComponent" in js
    assert "Your practice history is kept." in js
    assert "dataset.listName" in js


# --- spec 017: IPA after reveal ------------------------------------------------


def _function_body(js: str, name: str) -> str:
    start = js.index(f"function {name}(")
    end = js.index("\n  function ", start + 1)
    return js[start:end]


def test_sentence_view_has_target_ipa():
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    start, end = _section_bounds(html, "sentence-view")
    assert re.search(
        r'<span id="target-ipa" class="ipa" lang="en-GB-fonipa">', html[start:end]
    )


def test_app_js_renders_ipa_after_reveal():
    js = JS_PATH.read_text(encoding="utf-8")
    assert "en-GB-fonipa" in js
    assert '"ipa"' in js
    for name in ("renderRecallResult", "renderSentence", "renderFeedback"):
        assert "state.ipa" in _function_body(js, name), name


def test_ipa_style_exists():
    assert re.search(r"^\.ipa\s*\{", CSS_PATH.read_text(encoding="utf-8"), re.MULTILINE)


def test_upload_hint_mentions_pronunciation():
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    start = html.index('id="upload-format-hint"')
    assert "/rɪˈsiːv/" in html[start : html.index("</p>", start)]


# --- spec 018: enriched uploads (import panel) --------------------------------


def _import_js_section() -> str:
    js = JS_PATH.read_text(encoding="utf-8")
    start = js.index("// --- word-list import (spec 018)")
    end = js.index("// ---", start + 10)
    return js[start:end]


def test_import_panel_markup():
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    area = html.index('id="upload-area"')
    result = html.index('id="upload-result"')
    panel = html.index('id="import-panel"')
    assert area < result < panel
    panel_tag = html[html.rindex("<", 0, panel) : html.index(">", panel)]
    assert "hidden" in panel_tag
    assert re.search(r'id="import-status"[^>]*role="status"[^>]*aria-live="polite"', html)
    assert 'id="import-preview"' in html
    assert 'id="import-actions"' in html


def test_app_js_import_flow():
    section = _import_js_section()
    assert "/api/word-lists/import" in section
    assert "/api/word-lists/import/confirm" in section
    assert "Enriching vocabulary:" in section
    assert '"progress"' in section
    assert "%" not in section
    assert "innerHTML" not in section


def test_upload_input_starts_an_import():
    js = JS_PATH.read_text(encoding="utf-8")
    handler = js[js.index('uploadInput.addEventListener("change"') :]
    handler = handler[: handler.index("});")]
    assert "startImport(" in handler


def test_upload_hint_mentions_bare_words():
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    start = html.index('id="upload-format-hint"')
    hint = html[start : html.index("</p>", start)]
    assert "just the English is enough" in hint
    assert "/rɪˈsiːv/" in hint


def test_import_styles():
    css = CSS_PATH.read_text(encoding="utf-8")
    for selector in (".import-panel", ".import-preview", ".badge-review"):
        assert selector in css


def test_app_js_import_failure_handling():
    section = _import_js_section()
    for text in (
        "Retry failed",
        "/api/word-lists/import/retry",
        "failure_reason",
        "interrupted",
        "You have an unfinished import",
        "discard_pending",
    ):
        assert text in section


def test_app_js_import_existing_entries():
    section = _import_js_section()
    for text in (
        "Already in your words",
        "Also in the shared words",
        "Keep mine",
        "Update with this",
        "/api/word-lists/import/choice",
        "Repeated — already above",
    ):
        assert text in section


def test_app_js_import_review_badge():
    section = _import_js_section()
    assert "Pronunciation needs review" in section
    assert "item.ipa_review" in section
    assert ".title = item.ipa_review" in section
    assert "en-US-fonipa" in section


# --- spec 019: part-of-speech labels -------------------------------------------


def _js_function(js: str, name: str) -> str:
    start = js.index(f"function {name}(")
    return js[start : js.index("\n  function ", start + 1)]


def test_app_js_shows_pos_labels():
    js = JS_PATH.read_text(encoding="utf-8")
    pos_list = _js_function(js, "posList")
    assert "innerHTML" not in pos_list
    assert "aria-label" in pos_list or "ariaLabel" in pos_list
    assert ".title" in pos_list
    for name in ("renderRecall", "renderSentence", "renderFeedback"):
        assert "state.pos" in _js_function(js, name), name
    for label, full in [
        ("n.", "noun"), ("v.", "verb"), ("adj.", "adjective"), ("adv.", "adverb"),
        ("prep.", "preposition"), ("conj.", "conjunction"), ("pron.", "pronoun"),
        ("det.", "determiner"), ("int.", "interjection"), ("num.", "number"),
        ("phr. v.", "phrasal verb"), ("phr.", "phrase or idiom"),
    ]:  # fmt: skip
        assert f'"{label}": "{full}"' in js


def test_pos_styles():
    css = CSS_PATH.read_text(encoding="utf-8")
    assert ".pos-list" in css
    assert ".pos {" in css or ".pos," in css


def test_import_preview_shows_pos():
    section = _import_js_section()
    assert "posList(item.pos)" in section
    assert "Part of speech needs review" in section
    assert "item.pos_review" in section


def test_upload_hint_shows_pos_example():
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    start = html.index('id="upload-format-hint"')
    assert "v." in html[start : html.index("</p>", start)]


# --- spec 020: remove this word ------------------------------------------------


def _remove_js_section() -> str:
    js = JS_PATH.read_text(encoding="utf-8")
    start = js.index("// --- remove word (spec 020)")
    end = js.index("// ---", start + 10)
    return js[start:end]


def test_remove_word_markup():
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    hints = html.index('id="recall-hints"')
    assert hints < html.index('id="remove-word-button"') < html.index("</div>", hints)
    assert re.search(r'id="remove-toast"[^>]*role="status"[^>]*hidden', html)


def test_app_js_remove_word():
    section = _remove_js_section()
    assert "/api/remove-word" in section
    assert "from your words? You can undo this only until you move on." in section
    assert "Removed “" in section
    assert "innerHTML" not in section


def test_app_js_undo_remove():
    assert "/api/undo-remove" in _remove_js_section()
    assert 'id="undo-remove-button"' in TEMPLATE_PATH.read_text(encoding="utf-8")
