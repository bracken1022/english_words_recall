(() => {
  const views = {
    choose: document.getElementById("choose-view"),
    empty: document.getElementById("empty-view"),
    recall: document.getElementById("recall-view"),
    sentence: document.getElementById("sentence-view"),
    feedback: document.getElementById("feedback-view"),
    complete: document.getElementById("complete-view"),
    login: document.getElementById("login-view"),
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
  const targetExpressionEl = document.getElementById("target-expression");
  const targetMeaningEl = document.getElementById("target-meaning");
  const sentenceForm = document.getElementById("sentence-form");
  const sentenceInput = document.getElementById("sentence-input");
  const sentenceSubmitButton = sentenceForm.querySelector("button[type=submit]");
  const skipButton = document.getElementById("skip-button");
  const modKeyEl = document.getElementById("mod-key");
  const recordingStatusEl = document.getElementById("recording-status");
  const recordingTimeEl = document.getElementById("recording-time");
  const spinnerEl = document.getElementById("spinner");
  const feedbackResultEl = document.getElementById("feedback-result");
  const stepActionsEl = document.getElementById("step-actions");
  const continueButton = document.getElementById("continue-button");
  const retrySentenceButton = document.getElementById("retry-sentence-button");
  const sessionTallyEl = document.getElementById("session-tally");
  const scoreEl = document.querySelector("#complete-view .score");
  const restartButton = document.getElementById("restart-button");
  const micButton = document.getElementById("mic-button");
  const micLabelEl = micButton.querySelector(".mic-label");
  const micIconEl = micButton.querySelector("i");
  const transcribingEl = document.getElementById("transcribing");

  const MODE_HINTS = {
    sentence: "Recall the word, then write or say a sentence with it.",
    "recall-only": "Recall the word only. Faster rounds.",
  };

  let currentState = null;
  // Sentence mode, correct answer: the server is already at "sentence",
  // but the learner first sees the recall result and presses "Use it in a
  // sentence →". Purely presentational, so it lives only here.
  let sentenceIntro = false;
  let busy = false;

  modKeyEl.textContent = /Mac|iPhone|iPad/.test(navigator.platform) ? "⌘" : "Ctrl";

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

  function norm(text) {
    return (text || "").toLowerCase().replace(/[^a-z0-9' ]/g, " ").replace(/\s+/g, " ").trim();
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

  function setActions({ continueLabel = null, retry = false } = {}) {
    continueButton.hidden = continueLabel === null;
    if (continueLabel !== null) continueButton.textContent = continueLabel;
    retrySentenceButton.hidden = !retry;
    stepActionsEl.hidden = continueLabel === null && !retry;
  }

  function showLogin() {
    currentState = null;
    sentenceIntro = false;
    stopRecording(true);
    showOnly("login");
    warningsEl.hidden = true;
    wordFeedbackEl.hidden = true;
    setActions();
    endSessionButton.hidden = true;
    accountNameEl.hidden = true;
    logoutButton.hidden = true;
    loginUsernameInput.focus();
  }

  function showLoginError(message) {
    loginErrorEl.textContent = message;
    loginErrorEl.hidden = false;
  }

  function renderState(state) {
    currentState = state;
    if (state.step !== "sentence") sentenceIntro = false;

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
    }
    wordFeedbackEl.hidden = true;
    setActions();
    if (state.step !== "sentence") stopRecording(true);

    if (state.step === "recall") {
      showOnly("recall");
      renderRecall(state);
      answerInput.focus();
    } else if (state.step === "reveal" || (state.step === "sentence" && sentenceIntro)) {
      showOnly("recall");
      renderRecallResult(state);
      continueButton.focus();
    } else if (state.step === "sentence") {
      showOnly("sentence");
      renderSentence(state);
      sentenceInput.focus();
    } else if (state.step === "feedback") {
      showOnly("feedback");
      renderFeedback(state);
      setActions({ continueLabel: "Continue", retry: true });
      continueButton.focus();
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

  function renderMeanings(chinese) {
    chineseEl.replaceChildren();
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
    renderMeanings(state.chinese);
    answerInput.value = "";
    answerInput.readOnly = false;
    delete answerInput.dataset.result;
    answerSubmitButton.hidden = false;
    answerSubmitButton.disabled = true;
    recallHintsEl.hidden = false;
  }

  function renderRecallResult(state) {
    const accepted = state.accepted_expressions || [];
    const answer = state.answer || "";
    renderMeanings(state.chinese);
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
    } else {
      wordFeedbackEl.append(stamp("incorrect", "x-circle", "Not quite"));
      const reveal = el("div", "answer-reveal");
      reveal.append(el("p", "label", "Answer"), el("span", "answer-text", accepted.join(", ")));
      if (answer.trim()) {
        const wrote = el("span", "you-wrote", "You wrote ");
        wrote.append(el("span", "struck", answer));
        reveal.append(wrote);
      }
      wordFeedbackEl.append(reveal);
    }
    wordFeedbackEl.hidden = false;

    let label;
    if (state.step === "sentence") label = "Use it in a sentence →";
    else if (state.position === state.total) label = "Finish";
    else label = "Next word →";
    setActions({ continueLabel: label });
  }

  function renderSentence(state) {
    const accepted = state.accepted_expressions || [];
    targetExpressionEl.textContent = accepted[0] || "";
    targetMeaningEl.textContent = splitMeanings(state.chinese).join(" · ");
    sentenceInput.value = "";
    sentenceInput.disabled = false;
    spinnerEl.hidden = true;
    transcribingEl.hidden = true;
    micButton.hidden = !state.voice_available;
    updateReviewButton();
  }

  // Word-level LCS between the learner's sentence and the correction: the
  // original's unmatched tokens were removed, the correction's were added.
  function diffTokens(original, corrected) {
    const a = original.split(/\s+/).filter(Boolean);
    const b = corrected.split(/\s+/).filter(Boolean);
    const key = (token) => token.toLowerCase().replace(/[^a-z0-9']/g, "");
    const dp = Array.from({ length: a.length + 1 }, () => new Array(b.length + 1).fill(0));
    for (let i = a.length - 1; i >= 0; i--) {
      for (let j = b.length - 1; j >= 0; j--) {
        dp[i][j] = key(a[i]) === key(b[j]) ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
      }
    }
    const removed = new Set();
    const added = new Set();
    let i = 0;
    let j = 0;
    while (i < a.length && j < b.length) {
      if (key(a[i]) === key(b[j])) {
        i++;
        j++;
      } else if (dp[i + 1][j] >= dp[i][j + 1]) {
        removed.add(i++);
      } else {
        added.add(j++);
      }
    }
    while (i < a.length) removed.add(i++);
    while (j < b.length) added.add(j++);
    return {
      original: a.map((text, index) => ({ text, marked: removed.has(index) })),
      corrected: b.map((text, index) => ({ text, marked: added.has(index) })),
    };
  }

  function tokenParagraph(className, tokens, markedClass) {
    const p = el("p", className);
    tokens.forEach((token, index) => {
      if (index > 0) p.append(" ");
      p.append(token.marked ? el("span", markedClass, token.text) : token.text);
    });
    return p;
  }

  // One note per point: numbered lists ("…two issues: 1) … 2) …") split on
  // their numbers, dropping a colon-ended lead-in; prose splits by sentence.
  function splitNotes(explanation) {
    const text = (explanation || "").trim();
    if (!text) return [];
    const parts = text.split(/(?:^|\s)\(?\d{1,2}[).]\s+/);
    if (parts.length > 2) {
      const [intro, ...items] = parts.map((part) => part.trim());
      const notes = items.map((item) => item.replace(/[;,]$/, "")).filter(Boolean);
      if (intro && !intro.endsWith(":")) notes.unshift(intro);
      return notes;
    }
    return text
      .split(/(?<=[.!?。])\s+/)
      .map((note) => note.trim())
      .filter(Boolean);
  }

  function block(labelText, labelClass) {
    const section = el("div", "feedback-block");
    section.append(el("p", `label${labelClass ? ` ${labelClass}` : ""}`, labelText));
    return section;
  }

  function renderFeedback(state) {
    const feedback = state.feedback;
    const original = state.sentence || "";
    const word = (state.accepted_expressions || [])[0] || "";
    feedbackResultEl.replaceChildren();

    const head = el("div", "feedback-head");
    head.append(el("h2", null, word));
    feedbackResultEl.append(head);

    let kind;
    if (!feedback.available) kind = "unavailable";
    else if (feedback.uses_expression === false) kind = "missing";
    else if (
      feedback.needs_correction &&
      feedback.corrected &&
      norm(feedback.corrected) !== norm(original)
    )
      kind = "fix";
    else kind = "natural";
    feedbackResultEl.dataset.state = kind;

    const notes = splitNotes(feedback.explanation);
    if (kind === "natural") {
      head.append(stamp("correct", "check-circle", "Natural", null, true));
    } else if (kind === "fix") {
      head.append(stamp("incorrect", "pencil-simple-line", "Small fix", null, true));
    } else if (kind === "missing") {
      head.append(stamp("incorrect", "x-circle", "Word missing", null, true));
      notes.unshift(`Your sentence doesn't use “${word}”.`);
    }

    const wrote = block("You wrote");
    if (kind === "fix") {
      const diff = diffTokens(original, feedback.corrected);
      wrote.append(tokenParagraph("original-sentence", diff.original, "token-removed"));
      feedbackResultEl.append(wrote);
      const better = block("More natural", "label--accent");
      better.append(tokenParagraph("corrected-sentence", diff.corrected, "token-added"));
      feedbackResultEl.append(better);
    } else {
      wrote.append(el("p", "original-sentence", original));
      feedbackResultEl.append(wrote);
    }

    if (kind === "unavailable") {
      const why = block("Review");
      why.append(el("p", "note-text", "Sorry, sentence correction is unavailable right now."));
      feedbackResultEl.append(why);
    } else if (notes.length > 0) {
      const why = block("Why");
      why.classList.add("notes");
      for (const note of notes) {
        const p = el("p", "note");
        const dash = el("span", "note-dash", "—");
        dash.setAttribute("aria-hidden", "true");
        p.append(dash, el("span", null, note));
        why.append(p);
      }
      feedbackResultEl.append(why);
    }
  }

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
    return checked ? checked.value : "sentence";
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
      const state = await resp.json();
      sentenceIntro = state.step === "sentence";
      renderState(state);
    } finally {
      busy = false;
    }
  }

  async function continueStep() {
    if (busy || continueButton.hidden) return;
    if (sentenceIntro && currentState && currentState.step === "sentence") {
      sentenceIntro = false;
      renderState(currentState);
      return;
    }
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

  retrySentenceButton.addEventListener("click", async () => {
    const resp = await postJson("/api/retry-sentence");
    if (!resp) return;
    renderState(await resp.json());
  });

  endSessionButton.addEventListener("click", async () => {
    stopRecording(true);
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

  // --- sentence step -------------------------------------------------------

  function updateReviewButton() {
    sentenceSubmitButton.disabled = sentenceInput.value.trim() === "" || !spinnerEl.hidden;
  }

  sentenceInput.addEventListener("input", updateReviewButton);

  sentenceInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
      event.preventDefault();
      sentenceForm.requestSubmit();
    }
  });

  sentenceForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (sentenceInput.value.trim() === "") {
      const shouldSkip = confirm("You didn't write a sentence — skip this word?");
      if (!shouldSkip) {
        return;
      }
      if (!(await postJson("/api/skip"))) return;
      await fetchState();
      return;
    }
    if (!spinnerEl.hidden) return;

    stopRecording(true);
    spinnerEl.hidden = false;
    sentenceInput.disabled = true;
    sentenceSubmitButton.disabled = true;
    try {
      const resp = await postJson("/api/sentence", { sentence: sentenceInput.value });
      if (!resp) return;
      await resp.json();
    } finally {
      spinnerEl.hidden = true;
      sentenceInput.disabled = false;
      updateReviewButton();
    }
    await fetchState();
  });

  skipButton.addEventListener("click", async () => {
    stopRecording(true);
    const resp = await postJson("/api/skip");
    if (!resp) return;
    renderState(await resp.json());
  });

  // Voice input (spec 009): records a short clip and sends it to
  // /api/transcribe, landing the recognized text in the same field a
  // typed sentence uses — never auto-submitted (FR-002).
  let mediaRecorder = null;
  let audioChunks = [];
  let recordingTimer = null;
  let discardRecording = false;

  function setRecordingUi(recording) {
    micLabelEl.textContent = recording ? "Stop" : "Speak instead";
    micIconEl.className = `ph-duotone ${recording ? "ph-stop-circle" : "ph-microphone"}`;
    sentenceInput.classList.toggle("is-recording", recording);
    recordingStatusEl.hidden = !recording;
    clearInterval(recordingTimer);
    if (recording) {
      const startedAt = Date.now();
      recordingTimeEl.textContent = "0:00";
      recordingTimer = setInterval(() => {
        const secs = Math.floor((Date.now() - startedAt) / 1000);
        recordingTimeEl.textContent = `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, "0")}`;
      }, 1000);
    }
  }

  function stopRecording(discard) {
    if (mediaRecorder && mediaRecorder.state === "recording") {
      discardRecording = discard;
      mediaRecorder.stop();
    }
  }

  micButton.addEventListener("click", async () => {
    if (mediaRecorder && mediaRecorder.state === "recording") {
      stopRecording(false);
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      micButton.hidden = true;
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const preferredTypes = [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/ogg;codecs=opus",
        "audio/mp4",
      ];
      const mimeType = preferredTypes.find((type) => MediaRecorder.isTypeSupported(type));
      mediaRecorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      audioChunks = [];
      discardRecording = false;

      mediaRecorder.addEventListener("dataavailable", (event) => {
        if (event.data.size > 0) {
          audioChunks.push(event.data);
        }
      });

      mediaRecorder.addEventListener("stop", async () => {
        stream.getTracks().forEach((track) => track.stop());
        setRecordingUi(false);
        if (discardRecording) return;
        const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType || "audio/webm" });
        transcribingEl.hidden = false;
        try {
          const resp = await api("/api/transcribe", {
            method: "POST",
            headers: { "Content-Type": blob.type },
            body: blob,
          });
          if (!resp) return;
          const data = await resp.json();
          if (data.available) {
            sentenceInput.value = data.text;
            updateReviewButton();
          }
        } finally {
          transcribingEl.hidden = true;
        }
      });

      mediaRecorder.start();
      setRecordingUi(true);
    } catch {
      // Microphone permission denied, no device, or an insecure context —
      // fall back to typing only (FR-004).
      micButton.hidden = true;
    }
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
    if (file) await uploadFile(file);
  });

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
