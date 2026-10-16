# Contract: Comparing an Attempt with the Sentence

Device-independent rules (FR-010, FR-012). The web server implements them
in `src/lib/word_diff.py`; a future iPhone app either calls
`POST /api/sentence-recall` or follows these rules exactly.

1. **Split** each text on whitespace into words. Keep each word as
   written, for display.
2. **Normalise** each word for comparison only:
   - make it lower case;
   - turn curly apostrophes (’ ‘) into straight ones (');
   - strip punctuation from the start and end of the word (so `team.`,
     `"Team` and `team,` all become `team`), keeping inner apostrophes and
     hyphens (`don't`, `well-known`);
   - a word that is only punctuation (such as `—`) is dropped.
3. **Align** the two lists of normalised words with a longest-matching-
   blocks diff (Python `difflib.SequenceMatcher`, `autojunk=False`).
4. **Mark**:
   - in the sentence, a word in a matching block is `same`; any other
     word (deleted or replaced) is `missing`;
   - in the attempt, a word in a matching block is `same`; any other word
     (inserted or replaced) is `extra`.
5. **Empty attempt** (blank after trimming): no comparison; nothing is
   highlighted.

## Required examples (reviewed fixture, SC-007)

| Attempt | Sentence | Result |
|---|---|---|
| `she is a zealous supporter of the team` | `She is a zealous supporter of the team.` | all `same` |
| `She’s here` | `She's here.` | all `same` |
| `She is a supporter of the team.` | `She is a zealous supporter of the team.` | sentence: `zealous` missing |
| `She is a very zealous supporter of the team.` | `She is a zealous supporter of the team.` | attempt: `very` extra |
| `She was a zealous fan of the team.` | `She is a zealous supporter of the team.` | sentence: `is`, `supporter` missing; attempt: `was`, `fan` extra |
| `I don't know` | `I do not know.` | `do`, `not` missing; `don't` extra (accepted limit) |
| `I have 10 apples` | `I have ten apples.` | `ten` missing; `10` extra (accepted limit) |
| (blank) | any | no comparison |

The full reviewed set lives in `tests/fixtures/word_diff_cases.yml`.

## Display (web)

- Sentence words marked `missing` are underlined in the accent colour;
  attempt words marked `extra` are struck through in a muted colour.
- The block is labelled "Differences are a guide. You decide." The
  "Got it" / "Not yet" buttons are unchanged and are never pressed for
  the learner.
