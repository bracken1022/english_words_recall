(() => {
  const views = {
    choose: document.getElementById("choose-view"),
    empty: document.getElementById("empty-view"),
    recall: document.getElementById("recall-view"),
    "sentence-recall": document.getElementById("sentence-recall-view"),
    complete: document.getElementById("complete-view"),
    login: document.getElementById("login-view"),
    corrections: document.getElementById("corrections-view"),
  };
  const chooseListEl = document.getElementById("choose-list");
  const modeHintEl = document.getElementById("mode-hint");
  const warningsEl = document.getElementById("warnings");
  const endSessionButton = document.getElementById("end-session-button");
  const accountNameEl = document.getElementById("account-name");
  const logoutButton = document.getElementById("logout-button");
  const loginForm = document.getElementById("login-form");
  const loginUsernameInput = document.getElementById("login-username");
  const loginPasswordInput = document.getElementById("login-password");
  const loginErrorEl = document.getElementById("login-error");
  const uploadAreaEl = document.getElementById("upload-area");
  const uploadButton = document.getElementById("upload-button");
  const emptyUploadButton = document.getElementById("empty-upload-button");
  const uploadInput = document.getElementById("upload-input");
  const uploadResultEl = document.getElementById("upload-result");
  const emptyHintEl = document.getElementById("empty-hint");
  const wordSourceNoteEl = document.getElementById("word-source-note");
  const myListsEl = document.getElementById("my-lists");
  const myListsItemsEl = document.getElementById("my-lists-items");
  const chineseEl = document.getElementById("chinese");
  const answerForm = document.getElementById("answer-form");
  const answerInput = document.getElementById("answer-input");
  const answerSubmitButton = answerForm.querySelector("button[type=submit]");
  const recallHintsEl = document.getElementById("recall-hints");
  const showAnswerButton = document.getElementById("show-answer-button");
  const wordFeedbackEl = document.getElementById("word-feedback");
  const stepActionsEl = document.getElementById("step-actions");
  const continueButton = document.getElementById("continue-button");
  const sessionTallyEl = document.getElementById("session-tally");
  const scoreEl = document.querySelector("#complete-view .score");
  const restartButton = document.getElementById("restart-button");
  const openCorrectionsButton = document.getElementById("open-corrections");
  const closeCorrectionsButton = document.getElementById("close-corrections");
  const correctionsStatusEl = document.getElementById("corrections-status");
  const correctionsListEl = document.getElementById("corrections-list");

  const MODE_HINTS = {
    "recall-only": "Recall the word only. Faster rounds.",
    example: "Recall the word, then see it in a natural example sentence.",
    "example-recall": "Recall the word, see its example, then try to recall the sentence too.",
  };

  let currentState = null;
  let busy = false;
  let correctionsOpen = false;

  // --- small DOM helpers ---------------------------------------------------

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function icon(name) {
    const node = el("i", `ph-duotone ph-${name}`);
    node.setAttribute("aria-hidden", "true");
    return node;
  }

  function stamp(kind, iconName, label, word, small) {
    const node = el("div", `stamp feedback-${kind}${small ? " stamp--small" : ""}`);
    node.append(icon(iconName), el("span", "stamp-label", label));
    if (word) node.append(el("span", "stamp-word", word));
    return node;
  }

  function splitMeanings(chinese) {
    return (chinese || "").split(/[；;]/).map((part) => part.trim()).filter(Boolean);
  }

  // Every /api/ call goes through here: a 401 (not logged in, or the
  // server restarted) shows the login screen and resolves to null, so
  // callers just stop (spec 015).
  function isUnauthorized(resp) {
    if (resp.status !== 401) return false;
    showLogin();
    return true;
  }

  async function api(url, options) {
    const resp = await fetch(url, options);
    return isUnauthorized(resp) ? null : resp;
  }

  async function postJson(url, body) {
    return api(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  }

  // --- rendering -----------------------------------------------------------

  function showOnly(step) {
    for (const [name, view] of Object.entries(views)) {
      view.hidden = name !== step;
    }
  }

  function showWarnings(warnings) {
    if (warnings && warnings.length > 0) {
      warningsEl.textContent = warnings.join(" | ");
      warningsEl.hidden = false;
    } else {
      warningsEl.hidden = true;
    }
  }

  function setActions({ continueLabel = null } = {}) {
    continueButton.hidden = continueLabel === null;
    if (continueLabel !== null) continueButton.textContent = continueLabel;
    stepActionsEl.hidden = continueLabel === null;
  }

  function showLogin() {
    currentState = null;
    cancelVoice();
    showOnly("login");
    warningsEl.hidden = true;
    wordFeedbackEl.hidden = true;
    setActions();
    endSessionButton.hidden = true;
    accountNameEl.hidden = true;
    logoutButton.hidden = true;
    openCorrectionsButton.hidden = true;
    correctionsOpen = false;
    loginUsernameInput.focus();
  }

  function showLoginError(message) {
    loginErrorEl.textContent = message;
    loginErrorEl.hidden = false;
  }

  function renderState(state) {
    currentState = state;
    // The Corrections page stays up until closed; it then shows this state.
    if (correctionsOpen) return;
    if (state.step !== "sentence-recall" || state.sentence_revealed) cancelVoice();

    showWarnings(state.warnings);
    endSessionButton.hidden = !state.can_end_session;
    // Uploads exist only for a logged-in account on a server with word
    // lists enabled, which is exactly when the state carries word_source.
    const canUpload = Boolean(state.account) && state.word_source !== undefined;
    uploadAreaEl.hidden = !canUpload;
    emptyUploadButton.hidden = !canUpload;
    emptyHintEl.textContent = canUpload
      ? "Upload a word list to start practicing."
      : "Add some to the vocabulary folder to start a session.";
    if (state.step !== "choose") uploadResultEl.hidden = true;
    wordSourceNoteEl.hidden = !canUpload;
    if (canUpload && state.step === "choose") fetchLists();
    else myListsEl.hidden = true;
    if (canUpload && (state.step === "choose" || state.step === "empty")) fetchImport();
    else clearTimeout(importPollTimer);
    if (canUpload) {
      wordSourceNoteEl.textContent =
        state.word_source === "own"
          ? "Practicing your own word lists."
          : "Practicing the shared word sets — upload a list to practice your own words.";
    }
    if (state.account) {
      accountNameEl.textContent = state.account.display_name || state.account.username;
      accountNameEl.hidden = false;
      logoutButton.hidden = false;
      openCorrectionsButton.hidden = false;
    }
    wordFeedbackEl.hidden = true;
    setActions();
    hideExample();

    if (!keepRemoveToast) hideRemoveToast();
    keepRemoveToast = false;
    placeRemoveButton(state);

    if (state.step === "recall") {
      showOnly("recall");
      renderRecall(state);
      answerInput.focus();
    } else if (state.step === "reveal") {
      showOnly("recall");
      renderRecallResult(state);
      renderExample(state);
      continueButton.focus();
    } else if (state.step === "sentence-recall") {
      showOnly("sentence-recall");
      renderSentenceRecall(state);
    } else if (state.step === "complete") {
      showOnly("complete");
      renderComplete(state);
    } else if (state.step === "choose") {
      showOnly("choose");
      renderChoose(state.collections);
    } else {
      showOnly(state.step);
    }
  }

  // Part-of-speech labels (spec 019), shown before the meaning as a hint.
  const POS_NAMES = {
    "n.": "noun",
    "v.": "verb",
    "adj.": "adjective",
    "adv.": "adverb",
    "prep.": "preposition",
    "conj.": "conjunction",
    "pron.": "pronoun",
    "det.": "determiner",
    "int.": "interjection",
    "num.": "number",
    "phr. v.": "phrasal verb",
    "phr.": "phrase or idiom",
  };

  function posList(pos) {
    if (!pos || pos.length === 0) return null;
    const list = el("span", "pos-list");
    for (const label of pos) {
      const node = el("span", "pos", label);
      node.title = POS_NAMES[label] || label;
      node.setAttribute("aria-label", POS_NAMES[label] || label);
      list.append(node);
    }
    return list;
  }

  function renderMeanings(chinese, pos) {
    chineseEl.replaceChildren();
    const labels = posList(pos);
    if (labels) chineseEl.append(labels);
    splitMeanings(chinese).forEach((meaning, index) => {
      if (index > 0) {
        const sep = el("span", "meaning-sep", "/");
        sep.setAttribute("aria-hidden", "true");
        chineseEl.append(sep);
      }
      chineseEl.append(el("span", "meaning", meaning));
    });
  }

  function renderRecall(state) {
    renderMeanings(state.chinese, state.pos);
    answerInput.value = "";
    answerInput.readOnly = false;
    delete answerInput.dataset.result;
    answerSubmitButton.hidden = false;
    answerSubmitButton.disabled = true;
    recallHintsEl.hidden = false;
  }

  // British IPA, shown only once the answer is revealed (spec 017).
  function ipaEl(ipa) {
    if (!ipa) return null;
    const node = el("span", "ipa", `/${ipa}/`);
    node.lang = "en-GB-fonipa";
    return node;
  }

  function renderRecallResult(state) {
    const accepted = state.accepted_expressions || [];
    const answer = state.answer || "";
    renderMeanings(state.chinese, state.pos);
    answerInput.value = answer;
    answerInput.readOnly = true;
    answerInput.dataset.result = state.correct ? "correct" : "wrong";
    answerSubmitButton.hidden = true;
    recallHintsEl.hidden = true;

    wordFeedbackEl.replaceChildren();
    if (state.correct) {
      const matched =
        accepted.find((expr) => expr.trim().toLowerCase() === answer.trim().toLowerCase()) ||
        accepted[0];
      wordFeedbackEl.append(stamp("correct", "check-circle", "Correct", matched));
      const pronunciation = ipaEl(state.ipa);
      if (pronunciation) wordFeedbackEl.append(pronunciation);
    } else {
      wordFeedbackEl.append(stamp("incorrect", "x-circle", "Not quite"));
      const reveal = el("div", "answer-reveal");
      reveal.append(el("p", "label", "Answer"), el("span", "answer-text", accepted.join(", ")));
      const pronunciation = ipaEl(state.ipa);
      if (pronunciation) reveal.append(pronunciation);
      if (answer.trim()) {
        const wrote = el("span", "you-wrote", "You wrote ");
        wrote.append(el("span", "struck", answer));
        reveal.append(wrote);
      }
      wordFeedbackEl.append(reveal);
    }
    const updated = updatedNote(state.corrected);
    if (updated) wordFeedbackEl.append(updated);
    wordFeedbackEl.hidden = false;

    const label = state.position === state.total ? "Finish" : "Next word →";
    setActions({ continueLabel: label });
  }

  // --- word corrections (spec 023) ------------------------------------------

  const FIELD_NAMES = { ipa: "pronunciation", chinese: "meaning", pos: "part of speech" };

  // Fields a background check corrected while the learner answered.
  function updatedNote(corrected) {
    if (!corrected || corrected.length === 0) return null;
    const note = el("p", "updated-note");
    const names = corrected.map((field) => FIELD_NAMES[field] || field).join(", ");
    note.append(icon("sparkle"), el("span", null, `Updated: ${names}`));
    return note;
  }

  function correctionValue(field, value) {
    if (value === null || value === undefined || value.length === 0) return "—";
    if (field === "pos") return value.join(" ");
    if (field === "ipa") return `/${value}/`;
    return value;
  }

  function renderCorrections(data, keepStatus = false) {
    let status = "";
    if (!data.enabled) status = "Qwen is not set up, so words aren't being checked. Earlier corrections are listed below.";
    else if (data.paused) {
      const until = data.paused.until
        ? ` Checks resume at ${new Date(data.paused.until).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}.`
        : " Checks resume after the tutor restarts.";
      status = `${data.paused.reason}${until}`;
    }
    if (!keepStatus) {
      correctionsStatusEl.textContent = status;
      correctionsStatusEl.hidden = !status;
    }

    correctionsListEl.replaceChildren();
    if (data.corrections.length === 0) {
      correctionsListEl.append(el("li", "corrections-empty text-muted", "No corrections yet."));
      return;
    }
    for (const entry of data.corrections) {
      const row = el("li", "correction-row");
      if (entry.undone) row.classList.add("is-undone");
      const head = el("div", "correction-head");
      head.append(
        el("span", "correction-word", entry.english),
        el("span", "tag tag-neutral", FIELD_NAMES[entry.field] || entry.field),
      );
      const when = new Date(entry.at).toLocaleDateString(undefined, { day: "numeric", month: "short" });
      const source = entry.scope === "shared" ? "shared word sets" : entry.list;
      head.append(el("span", "correction-meta text-muted", `${source} · ${when}`));
      const actions = el("span", "correction-actions");
      if (entry.undone) {
        actions.append(el("span", "tag tag-neutral", "Undone"));
      } else if (entry.can_undo) {
        const undoButton = el("button", "btn btn-ghost", "Undo");
        undoButton.type = "button";
        undoButton.setAttribute("aria-label", `Undo the ${FIELD_NAMES[entry.field] || entry.field} change to ${entry.english}`);
        undoButton.addEventListener("click", () => undoCorrection(entry.id, undoButton));
        actions.append(undoButton);
      }
      head.append(actions);
      const change = el("p", "correction-change");
      const oldValue = el("span", "correction-old", correctionValue(entry.field, entry.old));
      const arrow = el("span", "correction-arrow", "→");
      arrow.setAttribute("aria-label", "changed to");
      change.append(oldValue, arrow, el("span", "correction-new", correctionValue(entry.field, entry.new)));
      if (entry.field === "chinese") change.lang = "zh-Hans";
      row.append(head, change);
      correctionsListEl.append(row);
    }
  }

  // Undoes every field changed by that check of the word (its batch).
  async function undoCorrection(id, button) {
    button.disabled = true;
    const resp = await postJson("/api/corrections/undo", { id });
    if (!resp) return;
    if (resp.ok) {
      await loadCorrections();
      return;
    }
    const data = await resp.json().catch(() => ({}));
    correctionsStatusEl.textContent = data.error || "Couldn't undo that correction.";
    correctionsStatusEl.hidden = false;
    await loadCorrections(true);
  }

  // keepStatus leaves an undo error showing instead of the usual status.
  async function loadCorrections(keepStatus = false) {
    const resp = await api("/api/corrections");
    if (!resp) return;
    renderCorrections(await resp.json(), keepStatus);
  }

  function openCorrections() {
    correctionsOpen = true;
    cancelVoice();
    showOnly("corrections");
    wordFeedbackEl.hidden = true;
    hideExample();
    hideRemoveToast();
    setActions();
    endSessionButton.hidden = true;
    correctionsListEl.replaceChildren();
    correctionsStatusEl.hidden = true;
    loadCorrections();
    closeCorrectionsButton.focus();
  }

  async function closeCorrections() {
    correctionsOpen = false;
    await fetchState();
  }

  openCorrectionsButton.addEventListener("click", openCorrections);
  closeCorrectionsButton.addEventListener("click", closeCorrections);

  function renderComplete(state) {
    const score = `${state.correct}/${state.total}`;
    for (const span of scoreEl.children) span.textContent = score;
    sessionTallyEl.textContent = `${state.correct} of ${state.total} recalled correctly.`;
    restartButton.hidden = !state.can_restart;
    if (state.can_restart) restartButton.focus();
  }

  function getSelectedOrder() {
    const checked = document.querySelector('input[name="order-choice"]:checked');
    return checked ? checked.value : "sequential";
  }

  function getSelectedMode() {
    const checked = document.querySelector('input[name="mode-choice"]:checked');
    return checked ? checked.value : "example";
  }

  function wordCount(count) {
    return `${count} ${count === 1 ? "word" : "words"}`;
  }

  function renderChoose(collections) {
    chooseListEl.replaceChildren();
    for (const entry of collections) {
      let button;
      if (entry.key === null) {
        const wrap = el("div", "choose-all");
        button = el("button", "btn btn-primary");
        button.append(entry.label, el("span", "count", ` · ${wordCount(entry.count)}`));
        wrap.append(button);
        chooseListEl.append(wrap);
      } else {
        const short = entry.label.replace(/-words$/, "");
        button = el("button", "set-button");
        button.setAttribute("aria-label", `${entry.label}, ${wordCount(entry.count)}`);
        button.append(
          el("span", `set-key${short.length > 3 ? " set-key--long" : ""}`, short),
          el("span", "set-count", wordCount(entry.count)),
        );
        chooseListEl.append(button);
      }
      button.type = "button";
      button.addEventListener("click", async () => {
        const resp = await fetch("/api/select", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            collection: entry.key,
            order: getSelectedOrder(),
            mode: getSelectedMode(),
          }),
        });
        if (isUnauthorized(resp)) return;
        await fetchState();
      });
    }
  }

  async function fetchState() {
    const resp = await api("/api/state");
    if (!resp) return;
    renderState(await resp.json());
  }

  // --- actions -------------------------------------------------------------

  async function submitAnswer(answer) {
    if (busy) return;
    busy = true;
    try {
      if (!(await postJson("/api/answer", { answer }))) return;
      const resp = await api("/api/state");
      if (!resp) return;
      renderState(await resp.json());
    } finally {
      busy = false;
    }
  }

  async function continueStep() {
    if (busy || continueButton.hidden) return;
    busy = true;
    try {
      const resp = await postJson("/api/continue");
      if (!resp) return;
      renderState(await resp.json());
    } finally {
      busy = false;
    }
  }

  // Every recall result waits for the learner (no timed advance): the
  // result and its Continue button stay until Enter or a click.
  answerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (answerInput.readOnly) {
      await continueStep();
      return;
    }
    if (answerInput.value.trim() === "") return;
    await submitAnswer(answerInput.value);
  });

  answerInput.addEventListener("input", () => {
    answerSubmitButton.disabled = answerInput.value.trim() === "";
  });

  // "Show answer" counts as wrong: a blank answer is graded incorrect.
  showAnswerButton.addEventListener("click", async () => {
    await submitAnswer("");
  });

  continueButton.addEventListener("click", continueStep);

  endSessionButton.addEventListener("click", async () => {
    const resp = await postJson("/api/end");
    if (resp && resp.ok) renderState(await resp.json());
  });

  restartButton.addEventListener("click", async () => {
    const resp = await postJson("/api/restart");
    if (!resp) return;
    renderState(await resp.json());
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" || event.metaKey || event.ctrlKey || event.altKey) return;
    const tag = event.target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "BUTTON") return;
    if (!continueButton.hidden) {
      event.preventDefault();
      continueStep();
    }
  });

  for (const radio of document.querySelectorAll('input[name="mode-choice"]')) {
    radio.addEventListener("change", () => {
      modeHintEl.textContent = MODE_HINTS[getSelectedMode()];
    });
  }

  // --- example sentences (spec 021) ----------------------------------------
  // After each answer the word's example sentence is shown. A new word's
  // example is written in the background while the learner recalls it;
  // while it is still "pending" the page asks again once a second, for at
  // most six seconds (contracts/practice-ui.md).

  const exampleBlockEl = document.getElementById("example-block");
  const exampleSentenceEl = document.getElementById("example-sentence");
  const exampleTranslationEl = document.getElementById("example-translation");
  const exampleNoteEl = document.getElementById("example-note");
  const newExampleButton = document.getElementById("new-example-button");
  const EXAMPLE_POLL_LIMIT = 6;
  let examplePollTimer = null;
  let examplePolls = 0;

  function hideExample() {
    clearTimeout(examplePollTimer);
    examplePolls = 0;
    exampleBlockEl.hidden = true;
  }

  function showExampleNote(text) {
    exampleSentenceEl.textContent = "";
    exampleTranslationEl.textContent = "";
    exampleNoteEl.textContent = text;
    exampleNoteEl.hidden = false;
  }

  function renderExample(state) {
    clearTimeout(examplePollTimer);
    if (!state.example_status || state.example_status === "off") {
      exampleBlockEl.hidden = true;
      return;
    }
    exampleBlockEl.hidden = false;
    newExampleButton.hidden = state.example_status !== "ready";
    if (state.example_status === "ready" && state.example) {
      examplePolls = 0;
      exampleNoteEl.hidden = true;
      exampleSentenceEl.textContent = state.example.sentence;
      exampleTranslationEl.textContent = state.example.translation;
    } else if (state.example_status === "pending" && examplePolls < EXAMPLE_POLL_LIMIT) {
      showExampleNote("Writing an example…");
      examplePolls += 1;
      examplePollTimer = setTimeout(pollExample, 1000);
    } else {
      examplePolls = 0;
      showExampleNote("No example right now.");
    }
  }

  async function pollExample() {
    const resp = await api("/api/state");
    if (!resp) return;
    const state = await resp.json();
    // Only refresh the example, and only if the learner is still there.
    if (currentState && state.step === currentState.step && state.position === currentState.position) {
      currentState = state;
      renderExample(state);
    }
  }

  newExampleButton.addEventListener("click", async () => {
    if (busy) return;
    busy = true;
    newExampleButton.disabled = true;
    try {
      const resp = await postJson("/api/example/new");
      if (!resp) return;
      const data = await resp.json();
      if (!resp.ok) {
        showExampleNote(data.error);
        return;
      }
      currentState = data;
      renderExample(data);
    } finally {
      newExampleButton.disabled = false;
      busy = false;
    }
  });

  // --- sentence recall (spec 021) ------------------------------------------
  // In the example-recall mode the learner sees the example's translation,
  // tries the sentence (typed, or spoken: spec 022), reveals it and marks
  // Got it / Not yet. The attempt is sent once, with the reveal, to get the
  // word-by-word comparison (spec 022, research R3); it is never stored.

  const sentenceRecallTranslationEl = document.getElementById("sentence-recall-translation");
  const sentenceRecallFieldEl = document.getElementById("sentence-recall-field");
  const sentenceRecallInput = document.getElementById("sentence-recall-input");
  const sentenceRecallCheckEl = document.getElementById("sentence-recall-check");
  const sentenceRecallAttemptRowEl = document.getElementById("sentence-recall-attempt-row");
  const sentenceRecallAttemptEl = document.getElementById("sentence-recall-attempt");
  const sentenceRecallSentenceEl = document.getElementById("sentence-recall-sentence");
  const sentenceRecallActionsEl = document.getElementById("sentence-recall-actions");
  const showSentenceButton = document.getElementById("show-sentence-button");
  const skipSentenceButton = document.getElementById("skip-sentence-button");
  const gotItButton = document.getElementById("got-it-button");
  const notYetButton = document.getElementById("not-yet-button");
  const comparisonNoteEl = document.getElementById("comparison-note");
  let sentenceRecallWord = null;
  let lastComparison = null;

  // One span per word; missing / extra words get a class (spec 022 FR-012).
  const WORD_CLASSES = { same: "word", missing: "word word--missing", extra: "word word--extra" };

  function renderWords(target, words) {
    target.replaceChildren();
    words.forEach((mark, i) => {
      if (i > 0) target.append(" ");
      target.append(el("span", WORD_CLASSES[mark.status] || "word", mark.word));
    });
  }

  function renderSentenceRecall(state) {
    const example = state.example || {};
    const revealed = Boolean(state.sentence_revealed);
    // A fresh word clears the box; a re-render of the same word keeps it.
    if (sentenceRecallWord !== state.position) {
      sentenceRecallWord = state.position;
      sentenceRecallInput.value = "";
      lastComparison = null;
    }
    renderVoice(state);
    sentenceRecallTranslationEl.textContent = example.translation || "";
    sentenceRecallFieldEl.hidden = revealed;
    sentenceRecallCheckEl.hidden = !revealed;
    showSentenceButton.hidden = revealed;
    skipSentenceButton.hidden = revealed;
    gotItButton.hidden = !revealed;
    notYetButton.hidden = !revealed;
    if (revealed) {
      const attempt = sentenceRecallInput.value.trim();
      const comparison = state.comparison !== undefined ? state.comparison : lastComparison;
      lastComparison = comparison;
      if (comparison) {
        renderWords(sentenceRecallAttemptEl, comparison.attempt);
        renderWords(sentenceRecallSentenceEl, comparison.sentence);
      } else {
        sentenceRecallAttemptEl.textContent = attempt;
        sentenceRecallSentenceEl.textContent = example.sentence || "";
      }
      sentenceRecallAttemptRowEl.hidden = attempt === "";
      comparisonNoteEl.hidden = !comparison;
      gotItButton.focus();
    } else {
      sentenceRecallInput.focus();
    }
  }

  async function sendSentenceRecall(mark) {
    if (busy) return;
    busy = true;
    try {
      const body =
        mark === "reveal" ? { mark, attempt: sentenceRecallInput.value.trim() } : { mark };
      const resp = await postJson("/api/sentence-recall", body);
      if (!resp) return;
      const data = await resp.json();
      if (!resp.ok) {
        alert(data.error);
        return;
      }
      if (mark !== "reveal") sentenceRecallWord = null;
      renderState(data);
    } finally {
      busy = false;
    }
  }

  showSentenceButton.addEventListener("click", () => sendSentenceRecall("reveal"));
  skipSentenceButton.addEventListener("click", () => sendSentenceRecall("skip"));
  gotItButton.addEventListener("click", () => sendSentenceRecall("got"));
  notYetButton.addEventListener("click", () => sendSentenceRecall("not_yet"));

  // Cmd/Ctrl+Enter in the box shows the sentence (plain Enter adds a line).
  sentenceRecallInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
      event.preventDefault();
      sendSentenceRecall("reveal");
    }
  });

  // --- voice in sentence recall (spec 022) ---------------------------------
  // Speak records a clip (at most 30 s) and sends it to /api/transcribe,
  // which turns it into text on this Mac; the text is added to the attempt
  // box for the learner to fix. Nothing is revealed or marked from here,
  // and nothing about the recording is kept (contracts/voice-input.md).

  const speakButton = document.getElementById("speak-button");
  const speakLabelEl = document.getElementById("speak-label");
  const voiceStatusEl = document.getElementById("voice-status");
  const voiceStatusDotEl = document.getElementById("voice-status-dot");
  const voiceStatusTextEl = document.getElementById("voice-status-text");
  const voiceTimeEl = document.getElementById("voice-time");
  const voiceHintEl = document.getElementById("voice-hint");
  const voiceNoteEl = document.getElementById("voice-note");
  const MAX_RECORDING_MS = 30 * 1000;
  const VOICE_NOTES = {
    insecure: "Voice needs this page on the Mac itself (or over https).",
    blocked: "The microphone is blocked. Allow it in the browser, or type instead.",
    nothing_heard: "Didn't catch that. Try again, or type it.",
    unavailable: "Voice isn't working right now. Type it instead.",
  };

  // Recorded as it is: the browser's call processing (echo cancellation,
  // noise suppression, auto gain) can wipe out a voice on USB speaker-mics,
  // and Whisper copes with raw audio.
  const MIC_SETTINGS = { echoCancellation: false, noiseSuppression: false, autoGainControl: false };

  // The system's input device. Chrome's "default" follows macOS; left to
  // itself Chrome uses its own mic setting, which can be a silent built-in
  // mic (lid closed) and ignores a mere preference. Browsers without a
  // "default" device (Safari) already use the system one.
  async function openSystemMic() {
    try {
      return await navigator.mediaDevices.getUserMedia({
        audio: { ...MIC_SETTINGS, deviceId: { exact: "default" } },
      });
    } catch (err) {
      if (err.name !== "OverconstrainedError" && err.name !== "NotFoundError") throw err;
      return navigator.mediaDevices.getUserMedia({ audio: MIC_SETTINGS });
    }
  }

  let recorder = null;
  let recordingTimer = null;
  let recordingLimit = null;
  let transcribing = false;
  // Bumped whenever the step moves on, so a late recording or reply is dropped.
  let voiceRound = 0;

  function canRecord() {
    return Boolean(window.isSecureContext && navigator.mediaDevices?.getUserMedia && window.MediaRecorder);
  }

  function showVoiceNote(key) {
    voiceNoteEl.textContent = key ? VOICE_NOTES[key] : "";
    voiceNoteEl.hidden = !key;
  }

  function showVoiceStatus(text, recording) {
    voiceStatusEl.hidden = text === null;
    voiceStatusTextEl.textContent = text || "";
    voiceStatusDotEl.classList.toggle("status-dot--recording", Boolean(recording));
    voiceTimeEl.textContent = "";
  }

  function setRecordingUi(recording) {
    speakLabelEl.textContent = recording ? "Stop" : "Speak";
    speakButton.classList.toggle("is-recording", recording);
    clearInterval(recordingTimer);
    clearTimeout(recordingLimit);
    if (recording) {
      showVoiceStatus("Listening…", true);
      const startedAt = Date.now();
      voiceTimeEl.textContent = "0:00";
      recordingTimer = setInterval(() => {
        const secs = Math.floor((Date.now() - startedAt) / 1000);
        voiceTimeEl.textContent = `0:${String(secs).padStart(2, "0")}`;
      }, 1000);
      recordingLimit = setTimeout(() => stopRecording(false), MAX_RECORDING_MS);
    }
  }

  function stopRecording(discard) {
    if (!recorder || recorder.state !== "recording") return;
    recorder.discard = discard;
    recorder.stop();
  }

  // Called whenever the page leaves the unrevealed sentence-recall step.
  function cancelVoice() {
    voiceRound += 1;
    stopRecording(true);
    transcribing = false;
    speakButton.disabled = false;
    showVoiceStatus(null);
    voiceHintEl.hidden = true;
  }

  function renderVoice(state) {
    const offered = Boolean(state.voice_available) && !state.sentence_revealed;
    if (!offered) {
      cancelVoice();
      speakButton.hidden = true;
      showVoiceNote(null);
      return;
    }
    speakButton.hidden = !canRecord();
    if (speakButton.hidden) showVoiceNote("insecure");
  }

  function addHeardText(text) {
    const typed = sentenceRecallInput.value.trim();
    sentenceRecallInput.value = typed ? `${sentenceRecallInput.value.trimEnd()} ${text}` : text;
    voiceHintEl.hidden = false;
    sentenceRecallInput.focus();
  }

  async function sendRecording(blob, round) {
    transcribing = true;
    speakButton.disabled = true;
    showVoiceStatus("Turning speech into text…", false);
    let outcome = "unavailable";
    let text = null;
    try {
      const resp = await api("/api/transcribe", {
        method: "POST",
        headers: { "Content-Type": blob.type || "audio/webm" },
        body: blob,
      });
      if (!resp) return;
      if (resp.ok) ({ outcome, text } = await resp.json());
    } catch {
      outcome = "unavailable";
    } finally {
      if (round === voiceRound) {
        transcribing = false;
        speakButton.disabled = false;
        showVoiceStatus(null);
      }
    }
    if (round !== voiceRound) return; // the step moved on: drop it
    if (outcome === "ok" && text) addHeardText(text);
    else showVoiceNote(outcome === "nothing_heard" ? "nothing_heard" : "unavailable");
  }

  async function startRecording() {
    showVoiceNote(null);
    const round = voiceRound;
    let stream;
    try {
      stream = await openSystemMic();
    } catch {
      showVoiceNote("blocked");
      return;
    }
    if (round !== voiceRound) {
      stream.getTracks().forEach((track) => track.stop());
      return;
    }
    const preferredTypes = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"];
    const mimeType = preferredTypes.find((type) => MediaRecorder.isTypeSupported(type));
    const rec = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
    const chunks = [];
    rec.discard = false;
    rec.addEventListener("dataavailable", (event) => {
      if (event.data.size > 0) chunks.push(event.data);
    });
    rec.addEventListener("stop", () => {
      stream.getTracks().forEach((track) => track.stop());
      if (recorder === rec) recorder = null;
      setRecordingUi(false);
      showVoiceStatus(null);
      if (rec.discard || round !== voiceRound) return;
      sendRecording(new Blob(chunks, { type: rec.mimeType || "audio/webm" }), round);
    });
    recorder = rec;
    rec.start();
    setRecordingUi(true);
  }

  speakButton.addEventListener("click", () => {
    if (transcribing) return;
    if (recorder && recorder.state === "recording") stopRecording(false);
    else startRecording();
  });

  // --- word-list upload (spec 016) ----------------------------------------

  function showUploadResult(lines, isError, skipped = []) {
    uploadResultEl.replaceChildren();
    uploadResultEl.classList.toggle("upload-result--error", isError);
    for (const line of lines) uploadResultEl.append(el("p", "", line));
    if (skipped.length > 0) {
      const list = el("ul", "upload-skipped");
      for (const message of skipped) list.append(el("li", "", message));
      uploadResultEl.append(list);
    }
    uploadResultEl.hidden = false;
  }

  async function uploadFile(file, replace = false) {
    const form = new FormData();
    form.append("file", file);
    if (replace) form.append("replace", "true");
    const resp = await fetch("/api/word-lists", { method: "POST", body: form });
    if (isUnauthorized(resp)) return;
    const data = await resp.json();
    if (resp.status === 409) {
      if (confirm(`Replace your list “${data.name}”?`)) await uploadFile(file, true);
      return;
    }
    if (!resp.ok) {
      // The result area lives on the choose screen; from the empty screen
      // an error has nowhere visible to go, so say it directly.
      if (!currentState || currentState.step !== "choose") alert(data.error);
      else showUploadResult([data.error], true, data.skipped || []);
      return;
    }
    // Re-render first: the new list may switch the screen from "empty" to
    // "choose", and the result lives on the choose screen.
    await fetchState();
    const words = data.added === 1 ? "word" : "words";
    const lines = [`Added ${data.added} ${words} to “${data.name}”.`];
    if (data.skipped_count > 0) lines.push(`Skipped ${data.skipped_count}:`);
    const tail = [];
    if (data.first_list) tail.push("From now on you'll practice your own lists.");
    if (!data.applies_now) {
      tail.push("New lists show up when the tutor isn't locked to one word set.");
    }
    showUploadResult(lines, false, data.skipped);
    for (const line of tail) uploadResultEl.append(el("p", "", line));
  }

  async function fetchLists() {
    const resp = await api("/api/word-lists");
    if (!resp) return;
    const data = await resp.json();
    myListsItemsEl.replaceChildren();
    for (const entry of data.lists) {
      const uploaded = new Date(entry.uploaded_at).toLocaleDateString(undefined, {
        day: "numeric",
        month: "short",
      });
      const words = entry.word_count === 1 ? "word" : "words";
      const deleteButton = el("button", "btn btn-ghost", "Delete");
      deleteButton.type = "button";
      deleteButton.dataset.listName = entry.name;
      deleteButton.addEventListener("click", () => deleteList(entry.name));
      const row = el("li", "my-list-row");
      row.append(
        el("span", "my-list-name", entry.name),
        el("span", "my-list-meta text-muted", `${entry.word_count} ${words} · uploaded ${uploaded}`),
        deleteButton,
      );
      myListsItemsEl.append(row);
    }
    myListsEl.hidden = data.lists.length === 0;
  }

  async function deleteList(name) {
    if (!confirm(`Delete your list “${name}”? Your practice history is kept.`)) return;
    const resp = await fetch(`/api/word-lists/${encodeURIComponent(name)}`, { method: "DELETE" });
    if (isUnauthorized(resp)) return;
    uploadResultEl.hidden = true;
    await fetchState();
  }

  uploadButton.addEventListener("click", () => uploadInput.click());
  emptyUploadButton.addEventListener("click", () => uploadInput.click());
  uploadInput.addEventListener("change", async () => {
    const file = uploadInput.files[0];
    uploadInput.value = "";
    if (file) await startImport(file);
  });

  // --- word-list import (spec 018) ----------------------------------------
  // The upload button now starts an import: the local model fills in each
  // word's pronunciation, meaning and spelling variants, the learner
  // reviews them here, and nothing is saved until they press Save
  // (contracts/import-ui-contract.md). uploadFile above is the spec 016
  // immediate-save path, kept for its API.

  const importPanelEl = document.getElementById("import-panel");
  const importNameEl = document.getElementById("import-name");
  const importStatusEl = document.getElementById("import-status");
  const importPreviewEl = document.getElementById("import-preview");
  const importActionsEl = document.getElementById("import-actions");
  const importProgressEl = el("progress", "import-progress");
  importStatusEl.after(importProgressEl);
  let importPollTimer = null;
  let importBusy = false;

  const IMPORT_COLUMNS = ["English", "IPA", "中文", "Alternates", "Status"];
  const ITEM_STATUS = {
    waiting: "Waiting",
    enriching: "Enriching…",
    enriched: "Ready",
    duplicate: "Repeated — already above",
  };

  function plural(count, word) {
    return `${count} ${count === 1 ? word : `${word}s`}`;
  }

  function setUploadDisabled(disabled) {
    uploadButton.disabled = disabled;
    emptyUploadButton.disabled = disabled;
    uploadInput.disabled = disabled;
  }

  function importStatusText(imp) {
    switch (imp.status) {
      case "running":
        return `Enriching vocabulary: ${imp.done} / ${imp.total}`;
      case "completed":
        return `Enrichment complete — review ${plural(imp.total, "word")} below.`;
      case "partially_failed":
        return (
          `${imp.enriched_count} enriched, ${imp.failed_count} failed — ` +
          "retry the failed words or save the rest."
        );
      case "failed":
        return `${imp.failure_reason || "Enrichment failed."} ${imp.done} / ${imp.total} enriched so far.`;
      default:
        return `Enrichment was interrupted at ${imp.done} / ${imp.total}. Press Retry to continue.`;
    }
  }

  function importCell(label, ...children) {
    const td = el("td");
    td.dataset.label = label;
    td.append(...children.filter(Boolean));
    return td;
  }

  function importIpa(item) {
    if (item.ipa) {
      const span = el("span", "ipa", `/${item.ipa}/`);
      span.lang = "en-US-fonipa";
      return span;
    }
    if (item.ipa_review) {
      const badge = el("span", "badge-review", "Pronunciation needs review");
      badge.title = item.ipa_review;
      return badge;
    }
    return el("span", "text-muted", "—");
  }

  function importChinese(item) {
    if (!item.chinese) return [el("span", "text-muted", "—")];
    const span = el("span", "import-zh", item.chinese);
    span.lang = "zh-Hans";
    if (item.pos_review) {
      const badge = el("span", "badge-review", "Part of speech needs review");
      badge.title = item.pos_review;
      return [badge, span];
    }
    return [posList(item.pos), span];
  }

  function importAlternates(item) {
    if (item.state !== "enriched") return [el("span", "text-muted", "—")];
    const parts = [el("span", "", item.alternates.length ? item.alternates.join(", ") : "none")];
    if (item.dropped_alternates.length) {
      parts.push(
        el("span", "import-dropped text-muted", `not used: ${item.dropped_alternates.join(", ")}`),
      );
    }
    return parts;
  }

  function importItemStatus(item, running) {
    if (item.state === "failed") {
      return [
        el("span", "import-failed", `Failed: ${item.error}`),
        importButton("Retry", "btn-ghost", () => retryImport(item.index), running),
      ];
    }
    return [el("span", "", ITEM_STATUS[item.state] || item.state)];
  }

  function importExisting(item) {
    if (!item.existing) return [];
    const own = item.existing.source === "own";
    const parts = [
      el(
        "span",
        "badge-existing",
        own ? `Already in your words (“${item.existing.list}”)` : "Also in the shared words",
      ),
    ];
    const now = [
      item.existing.pos ? item.existing.pos.join(" ") : null,
      item.existing.ipa ? `/${item.existing.ipa}/` : null,
      item.existing.chinese,
      item.existing.alternates.length ? item.existing.alternates.join(", ") : null,
    ].filter(Boolean);
    if (now.length) parts.push(el("span", "import-existing-now text-muted", `Now: ${now.join(" · ")}`));
    if (own && item.state === "enriched") {
      const choice = el("div", "import-choice");
      for (const [value, label] of [["keep", "Keep mine"], ["update", "Update with this"]]) {
        const input = el("input");
        input.type = "radio";
        input.name = `import-choice-${item.index}`;
        input.value = value;
        input.checked = item.choice === value;
        input.addEventListener("change", () => chooseImport(item.index, value));
        const option = el("label");
        option.append(input, label);
        choice.append(option);
      }
      parts.push(choice);
    }
    return parts;
  }

  function importRow(item, running) {
    const row = el("tr", `import-row import-row--${item.state}`);
    row.append(
      importCell("English", el("span", "import-english", item.english), ...importExisting(item)),
      importCell("IPA", importIpa(item)),
      importCell("中文", ...importChinese(item)),
      importCell("Alternates", ...importAlternates(item)),
      importCell("Status", ...importItemStatus(item, running)),
    );
    return row;
  }

  function renderImportPreview(imp, running) {
    const head = el("tr");
    for (const title of IMPORT_COLUMNS) head.append(el("th", "", title));
    const thead = el("thead");
    thead.append(head);
    const tbody = el("tbody");
    for (const item of imp.items) tbody.append(importRow(item, running));
    const table = el("table", "import-table");
    table.append(thead, tbody);
    importPreviewEl.replaceChildren(table);
  }

  function importButton(label, className, onClick, disabled = false) {
    const button = el("button", `btn ${className}`, label);
    button.type = "button";
    button.disabled = disabled;
    button.addEventListener("click", onClick);
    return button;
  }

  function renderImportActions(imp, running) {
    const updates = imp.items.filter(
      (i) => i.state === "enriched" && i.existing && i.existing.source === "own" && i.choice === "update",
    ).length;
    const leftOut = imp.total - imp.savable_count - updates;
    const buttons = [];
    if (running || imp.savable_count > 0 || updates > 0) {
      let label = `Save ${plural(imp.savable_count, "word")}`;
      // While enriching, unfinished words aren't "left out" yet.
      if (leftOut > 0 && !running) label += ` — ${leftOut} left out`;
      buttons.push(importButton(label, "btn-primary", () => confirmImport(), running));
    }
    if (imp.failed_count > 0 || imp.status === "failed" || imp.status === "interrupted") {
      buttons.push(importButton("Retry failed", "btn-secondary", () => retryImport(), running));
    }
    buttons.push(importButton("Discard", "btn-ghost", discardImport));
    importActionsEl.replaceChildren(...buttons);
  }

  function placeImportPanel() {
    // The panel lives in the upload area; on the "no words" screen it is
    // shown there instead, so an import started from it stays visible.
    if (currentState && currentState.step === "empty") {
      if (importPanelEl.parentNode !== views.empty) views.empty.append(importPanelEl);
    } else if (importPanelEl.previousElementSibling !== uploadResultEl) {
      uploadResultEl.after(importPanelEl);
    }
  }

  function renderImport(imp) {
    clearTimeout(importPollTimer);
    if (!imp) {
      importPanelEl.hidden = true;
      setUploadDisabled(false);
      return;
    }
    const running = imp.status === "running";
    placeImportPanel();
    importPanelEl.hidden = false;
    importNameEl.textContent = imp.list_name || imp.source_filename;
    setUploadDisabled(running);
    importStatusEl.textContent = importStatusText(imp);
    importStatusEl.classList.toggle("import-status--error", imp.status === "failed");
    importProgressEl.hidden = !running;
    importProgressEl.max = Math.max(imp.total, 1);
    importProgressEl.value = imp.done;
    renderImportPreview(imp, running);
    renderImportActions(imp, running);
    if (running) importPollTimer = setTimeout(pollImport, 1000);
  }

  async function fetchImport() {
    const resp = await api("/api/word-lists/import");
    if (!resp) return;
    renderImport((await resp.json()).import);
  }

  function pollImport() {
    if (currentState && (currentState.step === "choose" || currentState.step === "empty")) {
      fetchImport();
    }
  }

  async function startImport(file, discardPending = false) {
    const form = new FormData();
    form.append("file", file);
    if (discardPending) form.append("discard_pending", "true");
    const resp = await api("/api/word-lists/import", { method: "POST", body: form });
    if (!resp) return;
    const data = await resp.json();
    if (resp.status === 409 && data.pending) {
      const name = data.import.source_filename;
      if (confirm(`You have an unfinished import of “${name}”. Discard it and start this one?`)) {
        await startImport(file, true);
      }
      return;
    }
    if (!resp.ok) {
      if (!currentState || currentState.step !== "choose") alert(data.error);
      else showUploadResult([data.error], true, data.skipped || []);
      return;
    }
    uploadResultEl.hidden = true;
    renderImport(data.import);
  }

  async function retryImport(index) {
    if (importBusy) return;
    importBusy = true;
    try {
      const resp = await postJson(
        "/api/word-lists/import/retry",
        index === undefined ? {} : { index },
      );
      if (!resp) return;
      const data = await resp.json();
      if (!resp.ok) {
        showUploadResult([data.error], true);
        await fetchImport();
        return;
      }
      renderImport(data.import);
    } finally {
      importBusy = false;
    }
  }

  async function confirmImport(replace = false) {
    if (importBusy) return;
    importBusy = true;
    let retryWithReplace = false;
    try {
      const resp = await postJson("/api/word-lists/import/confirm", replace ? { replace: true } : {});
      if (!resp) return;
      const data = await resp.json();
      if (resp.status === 409 && data.exists) {
        retryWithReplace = confirm(`Replace your list “${data.name}”?`);
        return;
      }
      if (!resp.ok) {
        showUploadResult([data.error], true);
        await fetchImport();
        return;
      }
      renderImport(null);
      await fetchState();
      const lines = [`Added ${plural(data.added, "word")} to “${data.name}”.`];
      if (data.updated > 0) lines.push(`Updated ${plural(data.updated, "existing word")}.`);
      if (data.left_out > 0) lines.push(`Left out ${data.left_out}.`);
      if (data.first_list) lines.push("From now on you'll practice your own lists.");
      if (!data.applies_now) {
        lines.push("New lists show up when the tutor isn't locked to one word set.");
      }
      showUploadResult(lines, false);
    } finally {
      importBusy = false;
    }
    if (retryWithReplace) await confirmImport(true);
  }

  async function chooseImport(index, choice) {
    const resp = await postJson("/api/word-lists/import/choice", { index, choice });
    if (!resp) return;
    const data = await resp.json();
    if (resp.ok) renderImport(data.import);
    else await fetchImport();
  }

  async function discardImport() {
    if (!confirm("Discard this import? Nothing will be saved.")) return;
    const resp = await api("/api/word-lists/import", { method: "DELETE" });
    if (!resp) return;
    renderImport(null);
  }

  // --- remove word (spec 020) ---------------------------------------------
  // Removes the current word from the learner's practice for good (their
  // own list file loses the entry; a shared word is hidden for them), with
  // an Undo until their next action (contracts/remove-word-ui.md).

  const removeWordButton = document.getElementById("remove-word-button");
  const removeToastEl = document.getElementById("remove-toast");
  const removeToastTextEl = document.getElementById("remove-toast-text");
  const undoRemoveButton = document.getElementById("undo-remove-button");
  const recallHintsHome = removeWordButton.parentNode;
  let keepRemoveToast = false;
  let removeToastTimer = null;

  function placeRemoveButton(state) {
    const steps = ["recall", "reveal", "sentence-recall"];
    removeWordButton.hidden = state.word_source === undefined || !steps.includes(state.step);
    if (removeWordButton.hidden) return;
    if (state.step === "reveal") {
      if (removeWordButton.parentNode !== stepActionsEl) stepActionsEl.append(removeWordButton);
    } else if (state.step === "sentence-recall") {
      if (removeWordButton.parentNode !== sentenceRecallActionsEl) {
        sentenceRecallActionsEl.append(removeWordButton);
      }
    } else if (removeWordButton.parentNode !== recallHintsHome) {
      recallHintsHome.append(removeWordButton);
    }
  }

  function hideRemoveToast() {
    clearTimeout(removeToastTimer);
    removeToastEl.hidden = true;
  }

  function showRemoveToast(english, canUndo) {
    removeToastTextEl.textContent = `Removed “${english}”.`;
    undoRemoveButton.hidden = !canUndo;
    removeToastEl.hidden = false;
    clearTimeout(removeToastTimer);
    removeToastTimer = setTimeout(hideRemoveToast, 15000);
  }

  async function removeWord() {
    if (busy || !currentState) return;
    const revealed = currentState.step !== "recall";
    const word = revealed
      ? (currentState.accepted_expressions || [])[0]
      : `the word for “${currentState.chinese}”`;
    const named = revealed ? `“${word}”` : word;
    if (!confirm(`Remove ${named} from your words? You can undo this only until you move on.`)) {
      return;
    }
    busy = true;
    try {
      const resp = await postJson("/api/remove-word");
      if (!resp) return;
      const data = await resp.json();
      if (!resp.ok) {
        alert(data.error);
        return;
      }
      keepRemoveToast = true;
      renderState(data.state);
      showRemoveToast(data.removed.english, data.undo);
    } finally {
      busy = false;
    }
  }

  async function undoRemove() {
    if (busy) return;
    busy = true;
    try {
      const resp = await postJson("/api/undo-remove");
      if (!resp) return;
      const data = await resp.json();
      hideRemoveToast();
      if (!resp.ok) {
        alert(data.error);
        return;
      }
      renderState(data);
    } finally {
      busy = false;
    }
  }

  removeWordButton.addEventListener("click", removeWord);
  undoRemoveButton.addEventListener("click", undoRemove);

  // --- login (spec 015) -----------------------------------------------------

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const username = loginUsernameInput.value;
    const password = loginPasswordInput.value;
    if (username.trim() === "" || password === "") {
      showLoginError("Enter both a username and a password");
      return;
    }
    const resp = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (resp.status === 401) {
      showLoginError("Username or password is incorrect");
      loginPasswordInput.value = "";
      loginPasswordInput.focus();
      return;
    }
    if (!resp.ok) {
      showLoginError("Enter both a username and a password");
      return;
    }
    loginUsernameInput.value = "";
    loginPasswordInput.value = "";
    loginErrorEl.hidden = true;
    await fetchState();
  });

  logoutButton.addEventListener("click", async () => {
    await fetch("/api/logout", { method: "POST" });
    showLogin();
  });

  fetchState();
})();
