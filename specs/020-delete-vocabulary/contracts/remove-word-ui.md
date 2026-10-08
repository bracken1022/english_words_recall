# Contract: Remove This Word (web UI)

This covers FR-001, FR-004 and SC-001.

- **Button**: a `Remove this word` ghost button, `#remove-word-button`.
  - On recall, it sits next to "Show answer".
  - On reveal and sentence, it sits in the step actions.
  - It is hidden when the server has no word-list store, i.e. when the
    state has no `word_source`.
- **Confirmation**:
  - At recall, the dialog shows the meaning:
    `confirm("Remove the word for “<meaning>” from your words? You can undo this only until you move on.")`.
  - At reveal and sentence, it names the word:
    `confirm("Remove “<english>” from your words? You can undo this only until you move on.")`.
  - If the learner cancels, nothing happens.
- **On `200`**:
  - The page renders the returned state, which is the next word or the
    end screen.
  - It shows `#remove-toast`, with `role="status"`, reading
    `Removed “<english>”.` and an `Undo` button when `undo` is true.
  - The toast hides after 15 s, or as soon as the learner does anything
    else (answer, skip, continue, choose a set).
- **Undo**: posts to `/api/undo-remove`, renders the state, and hides the
  toast.
- **Safety**: the toast and button use the existing Broadsheet classes
  (`btn btn-ghost`, `text-muted`). The text is set with `textContent`,
  never `innerHTML`.
