# Research: Local-AI Enrichment of Uploaded Word Lists

Phase 0 for [plan.md](plan.md). Every open point from the Technical
Context is resolved below.

## R1. Where the unconfirmed upload lives (pending import)

- **Decision**: One JSON file per account, at
  `word-lists/<username>/.pending-import.json`. It is written atomically
  (a temp file followed by `os.replace`) after every item state change.
- **Rationale**:
  - It survives restarts (FR-003).
  - It is private to the account's folder (spec 016 isolation).
  - `WordListStore` and `load_vocabulary()` only glob `*.md`, so the file
    is invisible to "My Word Lists", practice and word counts. No
    existing code path needs to change to ignore it.
  - The file is workflow state, not vocabulary, so JSON is used rather
    than the vocabulary Markdown format. The Markdown persistence rule
    covers vocabulary. Confirmed words still go only to `.md`.
- **Alternatives considered**:
  - **In-memory only**: lost on restart, which violates FR-003 and
    US2-AS2.
  - **A `.md` file with a status field**: it would be picked up by
    `load_vocabulary()` and practiced before confirmation.
  - **SQLite**: databases are out of scope.

## R2. Running enrichment without blocking requests

- **Decision**: An `EnrichmentRunner` service starts one daemon
  `threading.Thread` per account's pending import. It processes the items
  **sequentially**, in file order. The browser polls
  `GET /api/word-lists/import` about once a second while the status is
  `running`.
- **Rationale**:
  - Flask already runs `threaded=True` (spec 015 R3), so a background
    thread needs no new dependency.
  - A single local GPU model gains nothing from parallel requests, and
    sequential calls keep the progress count exact (FR-018, SC-006).
  - Polling is simpler than SSE or WebSockets, and the existing UI
    already uses plain `fetch`.
- **Duplicate prevention (FR-020)**:
  - A per-account `threading.Lock` guards the start/retry check-and-set.
  - A start or retry while `status == running` returns the current state
    without starting a second thread.
  - A confirm while the import is running returns `409`.
  - Discarding sets a cancel flag that the worker checks between items.
- **Restart**: when a pending file is loaded with `status: running`, its
  `enriching` items are reset to `waiting` and the status becomes
  `interrupted`. The batch does not restart until the learner presses
  Retry, as the spec's edge case requires.
- **Alternatives considered**:
  - **A synchronous request that enriches everything**: 40 words at 3–8 s
    each would exceed browser and proxy timeouts, with no progress shown.
  - **A task queue (Celery/RQ)**: an unjustified new dependency for a
    single-household app.

## R3. Calling the local model

- **Decision**: Add a new `src/services/enrichment_client.py` with
  `request_enrichment(english, need, base_url, model, timeout=60)`:
  - It makes one `/api/chat` call per word, with `stream: false`,
    `think: false`, a JSON-schema `format`, and the same configured
    `--ollama-url` and `--model` used by sentence review.
  - It reuses `_post_json`'s plumbing, refactored so that the caller can
    tell **unavailable** apart from a **bad reply**.
  - The reply schema is fixed: `{ "chinese": str, "alternates": [str] }`.
    The first design also asked for `ipa` and `ipa_uncertain`; that was
    dropped when IPA moved to the dictionary (R4).
  - The prompt sends only the English expression and states which fields
    are wanted. It never sends a file name, list name or other words.
- **Outcome classes**:
  - `unavailable`: connection refused, or HTTP 404 (model not pulled).
    The **batch** stops with status `failed` and the reason "local AI
    unavailable". The remaining items stay `waiting`, so Retry resumes
    them (US2-AS1/AS2 and the mid-batch edge case).
  - `bad_reply`: a timeout, another non-200 status, invalid JSON, a
    schema mismatch, or a validation failure. **Only that item** fails,
    with a reason, and the batch continues (FR-005, US2-AS3/AS4).
- **Ignoring model overreach (FR-006)**: only the four schema keys are
  read; any other key (`group`, `file`, `english`…) is dropped. The
  English text and the list name are never taken from the reply.
- **Alternatives considered**:
  - **Several words per call**: faster, but one malformed reply would sink
    the whole chunk, and output-to-word alignment becomes fragile. This
    conflicts with the spec's per-item requirement.
  - **Extending `llm_client.request_correction`**: it has an unrelated
    contract, and its module docstring forbids influencing control flow.
    A separate module keeps sentence review untouched (FR-022).

## R4. American IPA: source, convention and checks (FR-008, FR-009)

*Revised 2026-10-03 during implementation; see eval-report.md.*

- **Source of truth: the CMU Pronouncing Dictionary, not the model.**
  - **Why**: the first real-model evaluation showed `qwen3:14b` writes
    well-formed but **wrong** American IPA for about 40% of words
    (zealous /ˈzeɪləs/, tomato /ˈtɑːmətoʊ/). No symbol-level check can
    catch those errors, and prompt tuning only partly helped.
  - **Decision**: the product owner chose an offline dictionary.
    CMUdict is about 135k entries of General American English. Its
    BSD-licensed data file ships in the `cmudict` package, and
    `src/lib/us_pronunciation.py` reads that file directly.
  - **Scope of the model**: it is now asked only for meanings and
    alternates. That makes each request shorter, and still fully local.
- **Converter** (`arpabet_to_ipa`, `lookup_american_ipa`): ARPABET is
  converted to the **Oxford Learner's Dictionaries NAmE style**:
  - length marks are kept (`iː ɑː ɔː uː ɜː`);
  - every r is written (`ɑːr ɔːr ɜːr ər`);
  - vowels before r are written `ɪr`, `er`, `ʊr` (here hɪr, care ker,
    sure ʃʊr), and `aɪər`/`aʊər` for tyre and hour;
  - `oʊ` and `ɡ` are used;
  - syllabic n and l are word-final (nation ˈneɪʃn, mobile ˈmoʊbl);
  - stress marks go before the maximal legal onset;
  - secondary stress is marked only before the main stress, as OALD does;
  - a one-syllable word on its own gets no mark;
  - in a phrase, only the last content word keeps the main stress
    (give up ˌɡɪv ˈʌp), and function words take weak forms (tend to
    ˈtend tə).

  Examples: zealous `ˈzeləs`, garage `ɡəˈrɑːʒ`, tomato `təˈmeɪtoʊ`,
  hurry `ˈhɜːri`, tyre `ˈtaɪər`. Over the whole dictionary, 99.9% of
  converted entries pass `check_american_ipa`. The rest are odd entries,
  which would be flagged rather than saved.
- **Choosing among entries**:
  - If a word's entries put the main stress on **different** syllables
    (research, advertisement), it is ambiguous. It is flagged and never
    guessed.
  - Otherwise the first entry is used (either → ˈiːðər). These are
    vowel variants that dictionaries also list.
- **Spelling variants**: a British spelling missing from the dictionary
  (epitomise) is looked up through its kept spelling-variant alternates
  (epitomize). An alternate only counts if `is_spelling_variant` accepts
  it, so a learner-supplied synonym never lends its pronunciation.
- **Defence in depth**: `check_american_ipa(ipa) -> list[str]` still vets
  every converted value. It rejects:
  - British-only markers (`ɒ`, `əʊ`, `eə`, the linking `(r)`, `ɪə`/`ʊə`
    outside `aɪə`/`aʊə`, and `ɜː` not followed by its r, which may come
    after a stress mark);
  - `g` instead of `ɡ`, `ɚ ɝ ɾ`, and any other symbol;
  - missing or doubled primary stress, using a stress helper shared with
    `check_british_ipa`, whose behaviour is unchanged.
- **Ambiguity (FR-009)**: a word is marked "needs review" with no IPA
  when any of these holds:
  1. it is on the reviewed **heteronym list** (record, present, object,
     lead, tear, …). This applies even when the learner supplied a
     meaning, because a dictionary lookup can't use the meaning to pick
     a pronunciation;
  2. it has no lowercase letter (an abbreviation such as NASA or UK);
  3. its dictionary entries disagree on stress;
  4. no spelling of it is in the dictionary.
- **Rationale**: dictionary data is accurate and deterministic, so it can
  be tested. Everything uncertain is flagged rather than guessed
  (Constitution II), and the app stays fully local (FR-004).
- **Alternatives considered**:
  - **Model-generated IPA with a few-shot prompt**: rejected after
    measurement (eval-report.md).
  - **A larger local model**: slower per word, with no guarantee it fixes
    the problem.
  - **No generated IPA at all**: safe, but imports would get no
    pronunciations.

## R5. Chinese meaning validation (FR-010)

- **Decision**:
  - Strip the text, and normalise ASCII `;` and `,` between meanings to
    `；`.
  - Require at least one CJK character (U+4E00–U+9FFF).
  - Allow at most 4 `；`-separated meanings and at most 40 characters in
    total.
  - Reject newlines, Latin sentences longer than 3 consecutive words,
    and dictionary markers such as `n.`, `v.`, `adj.`, `【`.
  - A failure makes the whole item fail, because a word cannot be
    practiced without a meaning.
- **Rationale**: these are the concrete limits stated in the spec. They
  can be checked deterministically and covered by unit tests.

## R6. Conservative alternates (FR-011)

- **Decision**: a **model-proposed** alternate is kept only if it is a
  **spelling variant** of the English text, as determined by a
  deterministic check in `src/lib/alternates.py`:
  1. Both strings are canonicalised: lowercased, hyphens and spaces
     removed, then British→American rewrites applied:
     - `isation→ization`, `ise→ize` (word-final, and before
       `d/s/r/ing`), `yse→yze`;
     - `our→or`, word-final `tre→ter`, `ogue→og`, `ence→ense`;
     - doubled `ll→l` before `ed/ing/er`;
     - `ae/oe→e`.

     If the two canonical forms are equal, the alternate is kept.
  2. Otherwise the alternate is kept if the pair is on a small reviewed
     list of irregular BrE/AmE pairs: tyre/tire, grey/gray,
     aluminium/aluminum, plough/plow, kerb/curb, programme/program,
     cosy/cozy, mould/mold, sceptic/skeptic, pyjamas/pajamas,
     storey/story, …

  Everything else is dropped silently, including near-spellings of
  different words (affect/effect) and synonyms (arduous/difficult). An
  empty list is valid. Duplicates, and entries equal to the English text,
  are also removed.

  **Alternates supplied by the learner** in the upload are kept as given
  (FR-007); they are the learner's own choice.
- **Rationale**: SC-003 requires **zero** broad synonyms to be saved.
  Deterministic filtering guarantees this regardless of model behaviour.
  The spec's third category, "very close lexical equivalents", can't be
  verified mechanically. Dropping those is within "be conservative" and
  "acceptable for alternates to be empty".
- **Alternatives considered**:
  - **Trusting the model with prompt rules**: it fails SC-003 whenever
    the model misbehaves.
  - **A `difflib` similarity threshold**: it accepts affect/effect and
    accept/except, which are dangerous for recall.
  - **Letting the learner tick extra synonyms in the preview**: this is
    inline editing, which the spec rules out.

## R7. Existing-entry detection and "Update existing entry" (FR-016/017)

- **Decision**:
  - Matching:
    - The key is `english.strip().casefold()`.
    - It is compared against the account's **effective** vocabulary:
      `store.effective_dir(account, shared)`, loaded with
      `load_vocabulary()`.
    - For own lists, the match records the list's file stem. For the
      shared folder, it records `source: "shared"`.
  - **Match in one of the learner's own lists**:
    - The default choice is `keep`. The word is not added to the new list
      and its stored entry is untouched.
    - With `update`, the stored block's `ipa`, `chinese` and `alternates`
      are replaced by the reviewed values. Its `english` and `group` stay
      the same. The word is still not duplicated into the new list.
  - **Match in the shared folder** (an account with no own lists yet):
    - The word is marked "also in the shared words".
    - It **is** included in the new list, because the first upload
      switches the account away from the shared folder (spec 016 FR-006).
      Leaving it out would make the word vanish from the learner's
      practice.
    - The shared folder is never modified, and no `update` option is
      offered.
  - Duplicates within one upload: the first occurrence is enriched. Later
    occurrences are marked `duplicate`, carry no model call, and are
    never saved twice.
- **Rationale**: this follows "never silently overwrite" while respecting
  spec 016's rule that the shared folder is operator-maintained.

## R8. All-or-nothing save (FR-015)

- **Decision**: add
  `WordListStore.apply_import(account, name, new_items, updates, replace)`.
  It runs under the existing per-account lock:
  1. Render every target file in memory: the new list, and each own list
     touched by an `update`, where only the matched blocks are
     re-rendered.
  2. Write every target to a sibling temp file.
  3. Copy each existing target to `<file>.bak`.
  4. `os.replace` each temp file into place.
  5. On any exception, restore from the `.bak` files and delete the temp
     files.
  6. Delete the `.bak` files on success.
  7. Delete the pending import only after all of this succeeds.

  The `ListExistsError` / `replace` confirmation from 016 is reused
  unchanged.
- **Rationale**: one confirmation can touch several files, and this is
  the simplest rollback scheme that keeps files byte-identical on failure
  (SC-004/SC-007). The existing single-file `save()` stays as it is for
  the legacy endpoint.

## R9. API compatibility with spec 016 (FR-001, FR-022, SC-008)

- **Decision**:
  - `POST /api/word-lists`, the immediate-save endpoint from 016, keeps
    its exact contract, so its existing contract tests pass unchanged.
    It remains usable by scripts.
  - The web UI's upload button now calls a **new** `POST
    /api/word-lists/import` family of endpoints (see
    contracts/import-api-contract.md).
  - `parse_upload()` gains `require_chinese: bool = True`. The import
    path passes `False` and receives `DraftWord`s, so a missing Chinese
    meaning is no longer a skip reason for imports only.
- **Rationale**: this meets SC-008 literally, and keeps the visible
  upload button, file picker, accepted types and limits identical.
- **Alternative considered**: changing `POST /api/word-lists` to return
  `202` plus a pending import. This is cleaner, but it breaks spec 016's
  contract and its tests.

## R10. Verifying accuracy (Constitution II, SC-002, SC-003)

- **Decision**: there are two layers of checking.
  1. **Automated tests with a mocked model**:
     - validation;
     - alternates filtering, including all traps from SC-003;
     - heteronym and acronym flagging;
     - the American IPA checker on a reviewed fixture.
  2. A reviewed **evaluation fixture** at
     `tests/fixtures/enrichment_eval.yml`. It holds at least 50 words with
     dictionary-checked American IPA and accepted Chinese glosses, at
     least 20 broad-synonym traps, and at least 10 spelling-variant pairs.

     An opt-in tool, `python -m src.tools.eval_enrichment`, runs the
     **real local model** through the full enrich→validate pipeline and
     reports IPA match %, flagged %, synonym leaks and variant recall. It
     must meet SC-002/SC-003 before the feature ships. It isn't part of
     `pytest`, because that would need a running Ollama.
- **Rationale**: Constitution II requires a correctness check for any
  feature that generates language content. Mocks prove the guards work;
  the evaluation proves the model is good enough.
