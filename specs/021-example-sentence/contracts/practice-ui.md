# Contract: Practice UI Changes

- **Word-set screen, mode choice**: three options, `Recall only`,
  `Recall + example` (the default) and `Recall + example + sentence
  recall`, with hint text for each. The old "Sentence" option is gone.
- **Reveal step**: below the answer, the IPA and the part of speech,
  there is an **Example** block with the English sentence, its Chinese
  translation under it in `zh-Hans`, and a ghost button **New example**.
  - While the example is pending, the block shows "Writing an example…",
    and the page polls once a second for up to 6 seconds.
  - If none comes, it shows "No example right now." in muted text.
- **Sentence-recall step**:
  - It shows the label "Recall the sentence", the Chinese translation
    large, and an optional text box ("Type it, or just say it").
  - Buttons: **Show sentence** (primary) and **Skip**.
  - After **Show sentence**, the learner's attempt (if any) is shown,
    then the example, with the buttons **Got it** and **Not yet**.
- **Removed**: the sentence view, the mic and recording UI, the review
  spinner, the feedback view and "Try another sentence".
- **Kept**: "Remove this word" (spec 020) is available at `recall`,
  `reveal` and `sentence-recall`.
- **Safety**: all text is set with `textContent`, using the existing
  Broadsheet classes.
