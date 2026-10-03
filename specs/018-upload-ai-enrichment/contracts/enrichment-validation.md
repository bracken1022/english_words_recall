# Contract: Enrichment Validation Rules

These rules are pure functions, unit-tested with no model involved:

- `src/services/enrichment.py::validate_item`
- `src/lib/ipa.py::check_american_ipa`, `is_heteronym`
- `src/lib/us_pronunciation.py::lookup_american_ipa` (offline CMU
  dictionary)
- `src/lib/alternates.py::filter_alternates`

They cover FR-008 to FR-012. Validation runs on every model reply before
anything reaches the pending import's "enriched" state, and again at
confirm time, as defence in depth before writing Markdown.

## English (FR-012)

- The item's `english` is never taken from the reply. It must be non-empty
  and equal to the uploaded text after `strip()`.

## IPA (FR-008, FR-009)

The rules are applied in order, and the first one that matches decides
the outcome:

| # | Condition | Result |
|---|---|---|
| 1 | The upload supplied a valid IPA | Keep it as given, whatever its accent. `ipa_review = null`. |
| 2 | The expression has no lowercase letter (acronym or abbreviation, e.g. `NASA`, `UK`) | `ipa = null`, `ipa_review = "abbreviation — check how it's said"` |
| 3 | `is_heteronym(english)`, even if a Chinese meaning was supplied | `ipa = null`, `ipa_review = "pronunciation depends on the meaning"` |
| 4 | Dictionary entries disagree on the stressed syllable | `ipa = null`, `ipa_review = "more than one pronunciation — check which one you need"` |
| 5 | Neither the word nor any kept spelling-variant alternate is in the dictionary | `ipa = null`, `ipa_review = "not in the pronunciation dictionary"` |
| 6 | `check_american_ipa(ipa)` returns problems for the converted value | `ipa = null`, `ipa_review = "dictionary pronunciation failed check: <first problem>"` |
| 7 | Otherwise | `ipa = <converted dictionary value>`, `ipa_review = null` |

Rules 3–7 replaced the first design's model-IPA rules ("the local AI
wasn't sure", "generated pronunciation was unusable/failed check") on
2026-10-03 (research R4).

An IPA problem never fails the item. The word stays savable without a
pronunciation, as allowed by 017.

### `check_american_ipa` (OALD NAmE style, research R4)

It returns a list of problems; `[]` means the transcription passes.

- **Allowed characters**:
  - consonants `p b t d k ɡ f v θ ð s z ʃ ʒ h m n ŋ l r j w`, plus `tʃ dʒ`
    as sequences;
  - vowels `i ɪ e æ ʌ ɑ ɔ ʊ u ə ɜ a o`;
  - marks `ˈ ˌ ː`, space, syllabic `̩`, and the flap mark `̬` (U+032C).
- **Rejected**:
  - `g` (it must be `ɡ`);
  - British markers: `ɒ`, `əʊ`, `eə`, `(r)`, `ɪə` not preceded by `a`,
    `e` or `ɔ` (so `aɪər` in *tire* is fine), `ʊə` not preceded by `a` or
    `o` (so `aʊər` in *hour* is fine), and `ɜː` not followed by `r`;
  - `ɚ ɝ ɾ`, which are not the chosen convention;
  - any other symbol.
- **Stress**: the same rules as `check_british_ipa`, through the shared
  helper.
  - A single word of two or more syllables has exactly one `ˈ`.
  - In a phrase, each content word of two or more syllables has `ˈ` or
    `ˌ`.
  - A phrase has at least one `ˈ`.
  - Weak forms are exempt: `tə ə ən ðə əv fər frəm ənd ət əz ɪn ɑn`.
- **Fixture**: a reviewed fixture of 30 or more OALD NAmE
  transcriptions must all pass. Their British counterparts in the 017
  fixture must all fail.

### `is_heteronym`

`english.strip().casefold()` is looked up in a reviewed constant set in
`src/lib/ipa.py`. The set has at least 40 entries, covering
noun/verb stress pairs and homographs.

## Chinese (FR-010)

1. If Chinese was supplied, keep it exactly as given. No further checks
   apply, because it is the learner's data.
2. Otherwise, take `reply.chinese`, strip it, and replace ASCII `;`,
   full-width `，` and ASCII `,` between meanings with `；`.
3. The item **fails** with `error = "meaning was unusable"` if any of the
   following holds:
   - the value is empty;
   - it contains no character in U+4E00–U+9FFF;
   - it contains a newline;
   - it has more than 4 `；`-separated parts, or any part is empty;
   - it is more than 40 characters long;
   - it contains a part-of-speech label (`n.`, `v.`, `adj.`, `adv.`,
     `vt.`, `vi.`, `prep.`) or `【`/`】`;
   - it contains a run of 4 or more Latin words.

## Alternates (FR-011)

```text
final = supplied_alternates
        + [a for a in reply.alternates
           if is_spelling_variant(english, a)]   # research R6
dedupe case-insensitively, keep first; drop any equal to english
(case-insensitive) or empty after strip; at most 5 entries; each ≤ 64 chars
dropped_alternates = reply.alternates not kept (for display only)
```

`is_spelling_variant(a, b)` holds when either of these is true:

- `canonical(a) == canonical(b)`, where `canonical` lowercases, removes
  hyphens and spaces, and applies the BrE→AmE rewrites in research R6;
- `{a, b}` (lowercased) is in the reviewed `IRREGULAR_VARIANTS` set.

The function must give these results:

| english | proposed | kept? |
|---|---|---|
| tyre | tire | yes |
| epitomise | epitomize | yes |
| colour | color | yes |
| centre | center | yes |
| travelled | traveled | yes |
| e-mail | email | yes |
| arduous | difficult | **no** |
| zealous | enthusiastic | **no** |
| affect | effect | **no** |
| accept | except | **no** |
| big | large | **no** |

## Before writing Markdown (confirm)

Every item about to be written is validated again:

- `VocabularyItem(english, chinese, alternates, ipa=ipa)` must construct
  without error;
- `ipa` is None or passes `normalize_ipa`.

If any item fails, the confirm is aborted with `500` and no file is
touched. This should be impossible after step-wise validation, and a test
covers it.
