# Research: Part of Speech for Vocabulary

Phase 0 for [plan.md](plan.md). The spec has no open clarifications;
they were settled 2026-10-05. The decisions below settle the design
choices the spec leaves open.

## R1. How the field is stored

- **Decision**: an optional `pos` key in each vocabulary Markdown block,
  written by the tools as a YAML flow list of FR-002 labels, after `ipa`:

  ```yaml
  english: rent
  ipa: rent
  pos: [n., v.]
  alternates: []
  chinese: 租金；租用；出租
  group: ra_z_words
  ```

  A hand-written value can also be a string: `pos: adj.`, `pos: n. v.`,
  `pos: n., v.` or `pos: noun/verb`.
- **Rationale**:
  - A list keeps the order and allows several labels.
  - The labels contain dots but no YAML-special characters, so `n.` and
    `adj.` load as text under the existing YAML 1.2 loader.
  - Accepting strings keeps hand editing easy (FR-007).
- **Alternatives considered**:
  - **Separate boolean-style keys, or a comma string only**: these are
    harder to validate and to keep in order.
  - **One label per meaning inside `chinese`**: this is what learners
    already do ad hoc ("（动词）出租"), and it is exactly what FR-008 moves
    out of the meaning.

## R2. Normalising labels (`src/lib/pos.py`)

- **Decision**: `normalize_pos(raw) -> (labels | None, problem | None)`.
  1. Split a string on spaces, commas, `/`, `;`, `；` and `、`. Take a
     list as it is.
  2. Map each token, case-insensitively and with or without its dot,
     through a synonym table:
     - English abbreviations: `n`, `v`, `vt`, `vi` → `v.`;
       `a` and `adj` → `adj.`; `ad` and `adv` → `adv.`;
       `prep`, `conj`, `pron`, `det`, `art` → `det.`; `int`, `interj`,
       `num`;
     - full English names: noun, verb, adjective, adverb, preposition,
       conjunction, pronoun, determiner, article, interjection, number,
       numeral, phrasal verb, phrase, idiom;
     - Chinese names: 名词, 动词, 及物动词, 不及物动词, 形容词, 副词, 介词,
       连词, 代词, 限定词, 冠词, 感叹词, 数词, 短语动词, 短语, 习语.
  3. Keep the result in order, without duplicates.
  4. The value is invalid if it is empty, or if any token is unknown.
     Invalid values give no labels and a warning (FR-011).

  Label names (`POS_NAMES`) give the full name of each label, for
  tooltips and accessible names.
- **Simple-list uploads**: an extra field counts as the part of speech
  when it normalises **and** every token is written as a dotted
  abbreviation, a full English name or a Chinese name. A bare `n` or
  `a` is not enough, so ordinary alternates are never mistaken for
  labels. The field may appear anywhere after the English word, as the
  pronunciation field can (spec 017):

  ```text
  zealous, adj., 热心的
  rent, 租金；出租, n. v.
  give up, 放弃, phr. v.
  ```

## R3. Display (FR-004)

- **Web**:
  - `PracticeSession.state()` adds `pos` (a list of labels) wherever it
    already sends `chinese`, which covers the recall, reveal, sentence
    and feedback steps. The labels are a hint and never reveal the
    English word, so sending them during recall is safe (the spec's Q1
    answer).
  - `app.js` renders a `span.pos` before the meanings in `#chinese`, the
    recall prompt (which stays visible on the reveal), and before
    `#target-meaning` on the sentence and feedback steps. Each label gets
    `title` and `aria-label` set to its full name.
  - With no labels, nothing is rendered.
- **CLI**: the recall prompt becomes
  `Chinese meaning: adj. 热心的` (the labels come before the bold
  meaning). The sentence prompt doesn't repeat them, because the meaning
  was just shown.
- **Style**: short italic labels in the accent colour, in the
  Broadsheet style, using the existing tokens only.

## R4. Uploads: enrichment (FR-005, FR-006, FR-008)

- **Decision**:
  - The spec 018 model request gains a `pos` key: an array of strings,
    and required. The prompt asks for labels from the fixed list that
    match the meanings it gives, in the same order, and for `phr. v.` /
    `phr.` for multi-word expressions.
  - `validate_item` then works as follows:
    - a supplied `pos` is kept (FR-007);
    - otherwise the reply's labels go through `normalize_pos`;
    - if they are invalid or empty, the item gets `pos = []` and
      `pos_review = "part of speech needs review"`, and it **stays
      savable** (FR-006, US2-AS3).
  - Existing-entry update (spec 018 R7) includes `pos` in the replaced
    fields.
- **FR-008, labels inside meanings**: `validate_chinese` strips
  parenthesised part-of-speech notes (`（动词）`, `(v.)`, `（名词）`) from a
  **generated** meaning, rather than failing the item, and then applies
  its existing checks. A meaning that is empty after stripping fails as
  before. The prompt also says not to put labels in the meaning.
- **Why the model, and not a dictionary**:
  - CMUdict has no part-of-speech data. WordNet lacks prepositions,
    conjunctions and phrases, and would be a new data dependency.
  - The model already writes the meanings, so labels taken from the same
    reply stay consistent with them.
  - Unlike IPA, the label set is tiny and closed, and validation catches
    anything outside it.
  - The accuracy gate (R6) measures it. If it fails, the fallback is the
    same as spec 018's: decide with the user before shipping.

**Revision (2026-10-05)**: the first real-model gate failed: part of
speech 85%, and spelling variants fell to 64%. The product owner chose a
**separate, stricter part-of-speech request** that is given the meanings
and told that most words have one class. The meaning request is back to
its spec 018 form. See `contracts/enrichment-pos-delta.md` and
eval-report.md.

## R5. Filling existing words (FR-012, US3)

- **Decision**: a one-time fill tool, `python -m src.tools.add_pos`,
  built like spec 017's `add_ipa`:
  - It reads a reviewed mapping, `file<TAB>english<TAB>pos<TAB>note`.
  - It validates every value with `normalize_pos`, and nothing is
    written if any value is invalid.
  - It backs up each changed file under
    `backups/pos-<stamp>/` (gitignored).
  - As a text edit, it inserts only a `pos: [...]` line, after the
    block's `ipa:` line if there is one, otherwise after `english:`.
  - It reloads each file and checks that english, chinese, alternates,
    group and ipa are unchanged, restoring the backup on any mismatch.
  - It writes `REVIEW.md` with every filled word, the words left empty
    with reasons, and a 30-word spot-check sample.
  - Helpers are shared with `add_ipa` (`_english_of`, `_write_atomic`).
- **Producing the mapping**: as in spec 017, I write it during
  implementation for all about 710 words (182 shared, about 530
  uploaded). Each word is classified **from its own recorded Chinese
  meanings**, so *rent* "租金；出租" gets `[n., v.]` in meaning order.
  Words whose meanings don't settle the class are left empty with a
  reason (FR-012). The user then does the 30-word spot check (SC-006).
- **Alternatives considered**:
  - **Running the local model over existing words**: it is unmeasured
    until R6, and it is slower. The fill is one-off and reviewed, so a
    carefully written mapping is more accurate.
  - **Leaving existing words empty**: ruled out by the Q2 answer.

## R6. Accuracy gate (FR-009, SC-002)

- **Decision**:
  - Extend `tests/fixtures/enrichment_eval.yml`: each `words` entry gains
    `pos` (the labels that must be present) and optional `pos_ok` (also
    acceptable).
  - Add 10 or more multi-class words (rent, record, light, present,
    increase, …) and 5 or more phrases, the latter already present.
  - `eval_enrichment` reports part-of-speech accuracy. A reply counts as
    a match when all its labels are in `pos ∪ pos_ok` and at least one
    is in `pos`, or when it is flagged.
  - **Revised 2026-10-05, after run 3**: for a multi-word expression, all
    labels in `pos ∪ pos_ok` is enough. For example, *tend to* labelled
    `v.` counts, because OALD files such phrases under the verb. This
    was the product owner's decision, and it is recorded in
    eval-report.md.
  - The target is ≥ 95% (SC-002), with 0 out-of-set labels saved, and 0
    meanings left with part-of-speech notes (SC-003).
- **Rationale**: this is the same gate as spec 018 uses, measured on the
  real local model before release (Constitution II).

## R7. Compatibility (FR-003, FR-010)

- `pos` is optional everywhere. Files without it load with 0 new
  warnings.
- Grading, `accepted_expressions`, the progress log, word sets and IPA
  don't read `pos`.
- Spec 016's legacy upload route accepts and keeps `pos` like any other
  field.
- The pending-import file (spec 018) gains `pos` and `pos_review` on
  each item. Older pending files without them load as `[]` and `None`;
  the file version is unchanged, because both fields are additive with
  defaults.
