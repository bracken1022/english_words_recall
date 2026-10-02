# Research: IPA Pronunciation for Vocabulary

Context from the codebase:

- `VocabularyItem` (`src/models/vocabulary_item.py`) has `english`,
  `chinese`, `alternates` and `group`, and is built by `from_block()`.
- It is loaded by `vocabulary_loader.load_vocabulary()` (shared folder and
  personal lists) and by `word_lists.parse_upload()` (uploads).
- Uploaded lists are saved by `word_lists._to_markdown()`.
- The web state exposes `accepted_expressions` only after recall
  (`sentence`, `feedback` and `reveal` steps).
- The front end shows the answer in `renderRecallResult`,
  `renderSentence` and `renderFeedback`.
- The CLI prints the answer in `run_recall_step()` and the target word in
  `run_sentence_step()`.
- Data to fill: 182 words in `vocabulary/*.md`, 47 in
  `word-lists/zhoudan/dan_words_list.md`, and 4 in
  `design/fixtures/vocabulary/`.

## R1. Where the IPA lives

- **Decision**: add an optional `ipa` key to each vocabulary YAML block,
  placed right after `english`. `VocabularyItem` gains `ipa: str | None =
  None`.
- **Rationale**: this matches the user's request ("add an ipa field to
  every vocabulary"). Plain files stay readable, and every existing reader
  gets it through `from_block()`. Files without the key load exactly as
  today (FR-002).
- **Alternatives considered**: a separate `pronunciations.md` lookup
  keyed by word. That would keep the vocabulary files untouched, but it
  goes against the request, can drift from the words, and breaks for
  homographs (*tear*). Rejected.

## R2. Storing, normalising and validating the IPA

- **Decision**: a new `src/lib/ipa.py` with `normalize_ipa(raw) -> (value |
  None, problem | None)`:
  - strip whitespace, then one pair of surrounding `/…/` or `[…]`;
  - store the bare transcription (`rɪˈsiːv`) and display it as
    `/rɪˈsiːv/`;
  - **invalid** if it is not a string, is empty, is longer than 100
    characters, contains an ASCII digit, or has no letter;
  - an invalid value gives `ipa=None` plus a problem message such as
    `'receive': ipa "123" is not a pronunciation`.

  `VocabularyItem` carries that message in a non-compared field,
  `ipa_problem`. `load_vocabulary()` and `parse_upload()` turn it into a
  warning or skip message while still keeping the word (FR-008).
- **Rationale**: a bad IPA must never cost the learner a word. Normalising
  once means display code never needs to worry about slashes.

## R3. When IPA is shown

- **Decision**:
  - **Web**: `state()` adds `"ipa"` (bare text or `null`) **only** in the
    branch that already adds `accepted_expressions`, i.e. the `sentence`,
    `feedback` and `reveal` steps. The front end renders `/{ipa}/` in an
    `.ipa` element:
    - **reveal**: under the stamp for a correct answer, and after the
      answer text for a wrong one;
    - **sentence step**: beside `#target-expression`;
    - **feedback**: in the feedback head next to the word.
  - **CLI**: after recall, `run_recall_step` prints `Pronunciation:
    /…/` on its own line when the item has IPA. `run_sentence_step(...,
    ipa=None)` adds ` /…/` after the target in its prompt.
- **Rationale**: tying the IPA to the existing `accepted_expressions` gate
  means it inherits the guarantee that nothing about the answer appears
  during recall (FR-003, SC-003), and there is a test for that already.
  `lang="en-GB-fonipa"` and the existing serif font render IPA symbols;
  Source Serif 4 covers the IPA block.

## R4. A pronunciation column in uploads

- **Decision**:
  - **Markdown uploads**: the `ipa` key is read by `from_block` as above.
  - **Simple list**: any field after the Chinese meaning that is wrapped
    in `/…/` or `[…]` is the pronunciation; the other extra fields stay
    alternates. Example: `receive, 收到, /rɪˈsiːv/, accept`. If there is
    more than one such field, the first wins and the rest are skipped with
    a warning.
  - **Saving**: `_to_markdown` writes `ipa` after `english` when present.
- **Rationale**: a bare third column is already defined as "alternates"
  (spec 016), so an unmarked column would be ambiguous. Slashes are how
  learners already write IPA, so no header or position rule is needed.

## R5. How the existing words get filled (FR-005, FR-006)

- **Decision**: three steps.
  1. **Mapping file**: I write a British-English IPA mapping for every
     existing word, one tab-separated line per entry:
     `<file>\t<english>\t<ipa>\t<note>`. It uses the Oxford/Cambridge
     learner's-dictionary style: RP vowels (/əʊ/, /ɒ/, /ɑː/, /ɜː/, /eə/,
     /ɪə/, /ʊə/), non-rhotic, primary `ˈ` and secondary `ˌ` stress, and
     length `ː`. Homographs use the sense that matches the entry's Chinese
     meaning. When the meanings cover two pronunciations with different
     stress (a noun/verb pair), the first-listed meaning's pronunciation
     is used and the note says so. Words I'm not confident about get an
     empty IPA and a note.
  2. **Insertion tool**: a small reusable tool, `python -m
     src.tools.add_ipa`, applies the mapping. It inserts one `ipa: <value>`
     line directly after each block's `english:` line, as a **text edit**,
     so every other byte of the file stays as it was (US2 scenario 3). It
     never overwrites an existing `ipa`. It refuses any value that fails
     the checks in R6. It prints a summary: filled, already had IPA, left
     empty, and words in the files that are missing from the mapping.
  3. **Backups and review**: before writing, the tool copies every target
     file to `backups/ipa-<timestamp>/` (gitignored, since the files are
     learner data). It also writes `REVIEW.md` there, listing every word
     and its IPA, the empty ones with reasons, and a random sample of 30
     words marked for a dictionary spot check (SC-002).
- **Rationale**:
  - A text-level insert avoids re-serialising YAML, which would reformat
    `alternates: []` lists and quoting in hand-written files.
  - Keeping the mapping and the review out of git respects the existing
    "learner data stays local" rule.
  - The tool can be reused when the user later asks for a new list to be
    filled (spec Q2).
- **Alternatives considered**:
  - *Generating IPA with the local Ollama model*: inaccurate on stress
    and vowels, which the user declined (Q2) and which conflicts with
    Principle II.
  - *An offline pronunciation dictionary such as CMUdict*: US-only
    (ARPAbet), so not British; needs a new dependency.

  Both rejected.

## R6. Automated accuracy checks (Constitution II)

- **Decision**: `src/tools/add_ipa.py` validates every mapped IPA before
  writing anything:
  - **(a)** only symbols from the British RP inventory:
    - consonants `p b t d k ɡ f v θ ð s z ʃ ʒ h m n ŋ l r j w` (so
      affricates are `tʃ` and `dʒ`);
    - vowels `i ɪ e æ ʌ ɒ ɔ ʊ u ə ɑ ɜ a`, where `a` appears only in `aɪ`
      and `aʊ`;
    - the marks `ˈ ˌ ː`, the syllabic mark `◌̩`, optional-sound brackets
      `( )`, and a space between the words of a phrase;
  - **(b)** exactly one `ˈ` per word of two or more syllables, counting
    syllables by vowel nuclei (a phrase is checked word by word, and
    function words such as "to" may be unstressed);
  - **(c)** non-rhotic British form: every `r` must be followed by a
    vowel symbol, so there is no `r` before a consonant, a mark, or a word
    end. `ɚ`, `ɝ`, `ɹ` and `oʊ` (American forms) fail (a).
  - **(d)** no ASCII `g` mixed with `ɡ`: normalise to `ɡ`.

  Any failure stops the run and names the word. The human spot check of
  the 30 sampled words in `REVIEW.md` stays with the user (SC-002).
- **Rationale**: these catch the most common errors in generated IPA:
  American forms, missing or doubled stress, and non-IPA characters. None
  of them pretends to prove the vowels are right, which is why the sample
  check stays.

## R7. Scope of code changes

- **Changed**: `vocabulary_item.py` (field and parsing), `vocabulary_loader.py`
  (warning), `word_lists.py` (simple-list column, save), `session_state.py`
  (`state()` adds `ipa`), `cli/session.py` (printing), the web
  template/JS/CSS, and the README.
- **New**: `src/lib/ipa.py`, `src/tools/__init__.py`,
  `src/tools/add_ipa.py`.
- **Untouched**: grading (`matcher`), review (`llm_client`), the progress
  log, accounts and sessions (FR-009).
