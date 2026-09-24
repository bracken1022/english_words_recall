(() => {
  const views = {
    choose: document.getElementById("choose-view"),
    empty: document.getElementById("empty-view"),
    recall: document.getElementById("recall-view"),
    sentence: document.getElementById("sentence-view"),
    feedback: document.getElementById("feedback-view"),
    complete: document.getElementById("complete-view"),
  };
  const chooseListEl = document.getElementById("choose-list");
  const warningsEl = document.getElementById("warnings");
  const chineseEl = document.getElementById("chinese");
  const targetExpressionEl = document.getElementById("target-expression");
  const wordFeedbackEl = document.getElementById("word-feedback");
  const answerForm = document.getElementById("answer-form");
  const answerInput = document.getElementById("answer-input");
  const sentenceForm = document.getElementById("sentence-form");
  const sentenceInput = document.getElementById("sentence-input");
  const sentenceSubmitButton = sentenceForm.querySelector("button[type=submit]");
  const spinnerEl = document.getElementById("spinner");
  const feedbackResultEl = document.getElementById("feedback-result");
  const continueButton = document.getElementById("continue-button");
  const sessionTallyEl = document.getElementById("session-tally");
  const restartButton = document.getElementById("restart-button");
  const micButton = document.getElementById("mic-button");
  const transcribingEl = document.getElementById("transcribing");

  let lastAcceptedExpressions = [];

  function showOnly(step) {
    for (const [name, el] of Object.entries(views)) {
      el.hidden = name !== step;
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

  function renderWordFeedback(state) {
    // Persistent element, independent of showOnly(): visible whenever the
    // learner's recall outcome is still the relevant context (spec 004
    // FR-002/FR-003 — shown together with the sentence step and carried
    // into the feedback step, not tied to whichever <section> is primary).
    if (state.step === "sentence" || state.step === "feedback") {
      const expressions = (state.accepted_expressions || []).join(", ");
      wordFeedbackEl.textContent = state.correct
        ? `Correct: ${expressions}`
        : `Incorrect. The correct expression is: ${expressions}`;
      wordFeedbackEl.classList.toggle("feedback-correct", state.correct === true);
      wordFeedbackEl.classList.toggle("feedback-incorrect", state.correct === false);
      wordFeedbackEl.hidden = false;
    } else {
      wordFeedbackEl.hidden = true;
    }
  }

  function renderState(state) {
    showWarnings(state.warnings);
    showOnly(state.step);
    renderWordFeedback(state);

    if (state.step === "recall") {
      chineseEl.textContent = state.chinese;
      answerInput.value = "";
    } else if (state.step === "sentence") {
      lastAcceptedExpressions = state.accepted_expressions || [];
      targetExpressionEl.textContent = lastAcceptedExpressions[0] || "";
      sentenceInput.value = "";
      spinnerEl.hidden = true;
      micButton.hidden = !state.voice_available;
    } else if (state.step === "feedback") {
      renderFeedback(state.feedback);
    } else if (state.step === "complete") {
      renderTally(state.total, state.correct);
      restartButton.hidden = !state.can_restart;
    } else if (state.step === "choose") {
      renderChoose(state.collections);
    }
  }

  function getSelectedOrder() {
    const checked = document.querySelector('input[name="order-choice"]:checked');
    return checked ? checked.value : "sequential";
  }

  function renderChoose(collections) {
    chooseListEl.innerHTML = "";
    for (const entry of collections) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = `${entry.label} (${entry.count})`;
      button.addEventListener("click", async () => {
        await fetch("/api/select", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ collection: entry.key, order: getSelectedOrder() }),
        });
        await fetchState();
      });
      chooseListEl.appendChild(button);
    }
  }

  function renderTally(total, correct) {
    const mistakes = total - correct;
    sessionTallyEl.textContent =
      mistakes === 0
        ? `You recalled all ${total} words correctly.`
        : `You recalled ${correct} of ${total} words correctly — ${mistakes} to review.`;
  }

  function renderFeedback(feedback) {
    let text;
    let state;
    if (!feedback.available) {
      text = "Sorry, sentence correction is unavailable right now.";
      state = "unavailable";
    } else if (feedback.uses_expression === false) {
      text = "Your sentence does not use the target expression.";
      state = "missing";
    } else if (feedback.needs_correction) {
      text = `Corrected: ${feedback.corrected}`;
      if (feedback.explanation) {
        text += ` — ${feedback.explanation}`;
      }
      state = "corrected";
    } else {
      text = "Your sentence is already correct and natural.";
      state = "clean";
    }
    feedbackResultEl.textContent = text;
    feedbackResultEl.dataset.state = state;
  }

  async function fetchState() {
    const resp = await fetch("/api/state");
    renderState(await resp.json());
  }

  answerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    await fetch("/api/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answer: answerInput.value }),
    });
    // Word feedback (Correct:/Incorrect. ...) is rendered from GET
    // /api/state, not from this response — see renderWordFeedback().
    await fetchState();
  });

  sentenceForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (sentenceInput.value.trim() === "") {
      const shouldSkip = confirm("You didn't write a sentence — skip this word?");
      if (!shouldSkip) {
        return;
      }
      await fetch("/api/skip", { method: "POST" });
      await fetchState();
      return;
    }

    spinnerEl.hidden = false;
    sentenceInput.disabled = true;
    sentenceSubmitButton.disabled = true;
    try {
      const resp = await fetch("/api/sentence", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sentence: sentenceInput.value }),
      });
      await resp.json();
    } finally {
      spinnerEl.hidden = true;
      sentenceInput.disabled = false;
      sentenceSubmitButton.disabled = false;
    }
    await fetchState();
  });

  continueButton.addEventListener("click", async () => {
    const resp = await fetch("/api/continue", { method: "POST" });
    renderState(await resp.json());
  });

  restartButton.addEventListener("click", async () => {
    const resp = await fetch("/api/restart", { method: "POST" });
    renderState(await resp.json());
  });

  // Voice input (spec 009): records a short clip and sends it to
  // /api/transcribe, landing the recognized text in the same field a
  // typed sentence uses — never auto-submitted (FR-002).
  let mediaRecorder = null;
  let audioChunks = [];

  micButton.addEventListener("click", async () => {
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop();
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

      mediaRecorder.addEventListener("dataavailable", (event) => {
        if (event.data.size > 0) {
          audioChunks.push(event.data);
        }
      });

      mediaRecorder.addEventListener("stop", async () => {
        stream.getTracks().forEach((track) => track.stop());
        micButton.textContent = "Speak instead";
        micButton.classList.remove("recording");
        const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType || "audio/webm" });
        transcribingEl.hidden = false;
        try {
          const resp = await fetch("/api/transcribe", {
            method: "POST",
            headers: { "Content-Type": blob.type },
            body: blob,
          });
          const data = await resp.json();
          if (data.available) {
            sentenceInput.value = data.text;
          }
        } finally {
          transcribingEl.hidden = true;
        }
      });

      mediaRecorder.start();
      micButton.textContent = "Stop";
      micButton.classList.add("recording");
    } catch {
      // Microphone permission denied, no device, or an insecure context —
      // fall back to typing only (FR-004).
      micButton.hidden = true;
    }
  });

  fetchState();
})();
