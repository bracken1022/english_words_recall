# Contract Delta: Part of Speech in Upload Enrichment

These are changes to spec 018's `enrichment-llm-contract.md` and
`enrichment-validation.md`. They cover FR-005, FR-006 and FR-008.

## Model requests

*Revised 2026-10-05 after the first T030 run (eval-report.md).* Asking
for `pos` inside the meaning request over-labelled words (tomato →
`n. adj.`) and cost spelling variants. The part of speech now has its own
request.

- **Meaning request** (`request_enrichment`): unchanged from spec 018,
  with no `pos` key. Its prompt also says not to put labels like （动词）
  inside `chinese`.
- **Part-of-speech request** (`request_pos(english, chinese, …)`): one
  more `/api/chat` call per word. It is made only after a usable meaning
  exists, and only when the upload didn't supply `pos`.
  - **Format**: `{"pos": [string]}`, required `["pos"]`.
  - **User message**: `English: "<english>"` and `Meaning: "<the validated
    or supplied Chinese>"`.
  - **The system prompt says**:
    - use labels from the fixed list;
    - most words have exactly one part of speech;
    - add another label only if one of the given meanings clearly belongs
      to that class;
    - keep the order of the meanings;
    - use phr. v. or phr. for multi-word expressions.
  - **Outcomes**:
    - `unavailable`: the word goes back to waiting and the batch stops,
      as for the meaning request;
    - `bad_reply`, or `pos` that isn't an array of strings: labels `[]`,
      so the word is marked for review (rule 3);
    - `ok`: labels are passed to rule 2.

## Validation (`validate_item`)

| # | Condition | Result |
|---|---|---|
| 1 | The upload supplied `pos` | Keep it as given (already normalised). `pos_review = null`. |
| 2 | `normalize_pos(reply.pos)` gives labels | `pos = [labels[0]]`: **only the first label** (decided 2026-10-05 after T030; the model adds classes the meanings don't support). `pos_review = null`. |
| 3 | Otherwise (empty, unknown label, or wrong type) | `pos = []`, `pos_review = "part of speech needs review"` |

A part-of-speech problem never fails the item.

## Chinese meaning (FR-008)

Before the existing checks, a **generated** meaning has parenthesised
part-of-speech notes removed. That covers full-width or ASCII brackets
around any Chinese or English name in the synonym table: `（动词）`,
`(v.)`, `（名词）`.

- **Separators**: leftover empty `；` parts and spaces are cleaned up.
- **Empty result**: a meaning that is empty after this fails as before,
  with "meaning was unusable".
- **Supplied meanings**: a meaning the learner supplied is never changed.

## Existing entries

"Update with this" (spec 018) also replaces the entry's `pos`. If the
new labels are empty, it removes the key.
