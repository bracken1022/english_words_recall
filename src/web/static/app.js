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
  const answerSubmitButton = answerForm.querySelector("button[type=submit]");
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
  const RECALL_ONLY_FEEDBACK_DELAY_MS = 1200;

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

  function showWordFeedback(correct, acceptedExpressions) {
    const expressions = (acceptedExpressions || []).join(", ");
    wordFeedbackEl.textContent = correct
      ? `Correct: ${expressions}`
      : `Incorrect. The correct expression is: ${expressions}`;
    wordFeedbackEl.classList.toggle("feedback-correct", correct === true);
    wordFeedbackEl.classList.toggle("feedback-incorrect", correct === false);
    wordFeedbackEl.hidden = false;
  }

  function renderWordFeedback(state) {
    // Persistent element, independent of showOnly(): visible whenever the
    // learner's recall outcome is still the relevant context (spec 004
    // FR-002/FR-003 — shown together with the sentence step and carried
    // into the feedback step; spec 013 also carries it into the new
    // "reveal" step, not tied to whichever <section> is primary).
    if (state.step === "sentence" || state.step === "feedback" || state.step === "reveal") {
      showWordFeedback(state.correct, state.accepted_expressions);
    } else {
      wordFeedbackEl.hidden = true;
    }
  }

  function renderContinueButton(state) {
    // Persistent element (spec 013), like #word-feedback: reused for both
    // "feedback" (sentence mode) and "reveal" (recall-only wrong answer)
    // rather than duplicated per step.
    continueButton.hidden = !(state.step === "feedback" || state.step === "reveal");
  }

  function renderState(state) {
    showWarnings(state.warnings);
    showOnly(state.step);
    renderWordFeedback(state);
    renderContinueButton(state);

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

  function getSelectedMode() {
    const checked = document.querySelector('input[name="mode-choice"]:checked');
    return checked ? checked.value : "sentence";
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
          body: JSON.stringify({
            collection: entry.key,
            order: getSelectedOrder(),
            mode: getSelectedMode(),
          }),
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
    const resp = await fetch("/api/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answer: answerInput.value }),
    });
    const result = await resp.json();
    const stateResp = await fetch("/api/state");
    const state = await stateResp.json();

    if (state.step === "sentence" || state.step === "feedback") {
      // Sentence mode: the "sentence" step itself carries the word-feedback
      // stamp (spec 004) — render immediately, no separate reveal needed.
      renderState(state);
      return;
    }

    if (state.step === "reveal") {
      // Recall-only, incorrect (spec 013): the session waits indefinitely
      // here — no timer, no auto-advance. The persistent Continue button
      // (renderContinueButton) is now visible and awaits a click.
      renderState(state);
      return;
    }

    // Recall-only mode (spec 012 FR-003): submit_answer() advances straight
    // past "sentence" to "recall"/"complete", so there is no step left to
    // carry the correct/incorrect reveal. Show it directly from this
    // response and hold it briefly before moving on, so the learner still
    // sees whether they were right (acceptance scenario 2).
    showWordFeedback(result.correct, result.accepted_expressions);
    answerInput.disabled = true;
    answerSubmitButton.disabled = true;
    await new Promise((resolve) => setTimeout(resolve, RECALL_ONLY_FEEDBACK_DELAY_MS));
    answerInput.disabled = false;
    answerSubmitButton.disabled = false;
    renderState(state);
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
