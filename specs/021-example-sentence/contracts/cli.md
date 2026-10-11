# Contract: Command-Line Tutor Changes

- **Modes**: `--mode` accepts `recall-only`, `example` (the default) or
  `example-recall`. `sentence` is accepted as `example`.
- **After each answer** (in the example modes), the CLI prints:
  - `Example: <sentence>`
  - `        <translation>`

  The example is fetched or generated behind the loading indicator, with
  a 6-second limit. If there is none, it prints `(No example right
  now.)`.
- **Example-recall mode**: the CLI prints `Recall the sentence:
  <translation>`, then prompts `Press Enter to show it (s to skip)`.
  After that it shows the sentence and asks `Did you get it? [y/n]`,
  which is recorded as `got` or `not_yet`.
- **Removed**: the "Write a sentence using …" prompt and its review.
