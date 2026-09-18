(() => {
  const views = {
    empty: document.getElementById("empty-view"),
    recall: document.getElementById("recall-view"),
    sentence: document.getElementById("sentence-view"),
    feedback: document.getElementById("feedback-view"),
    complete: document.getElementById("complete-view"),
  };
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
    } else if (state.step === "feedback") {
      renderFeedback(state.feedback);
    }
  }

  function renderFeedback(feedback) {
    let text;
    if (!feedback.available) {
      text = "Sorry, sentence correction is unavailable right now.";
    } else if (feedback.uses_expression === false) {
      text = "Your sentence does not use the target expression.";
    } else if (feedback.needs_correction) {
      text = `Corrected: ${feedback.corrected}`;
      if (feedback.explanation) {
        text += ` — ${feedback.explanation}`;
      }
    } else {
      text = "Your sentence is already correct and natural.";
    }
    feedbackResultEl.textContent = text;
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

  fetchState();
})();
