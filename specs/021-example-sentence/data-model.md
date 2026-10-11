# Data Model: Example Sentences Instead of Sentence Review

## VocabularyItem (existing)

| New field | Type | Notes |
|---|---|---|
| `example` | `str \| None` | English example sentence, from the block's `example:` key (own lists). |
| `example_zh` | `str \| None` | Its Chinese translation, from `example_zh:`. Present only together with `example`. |

The block key order a tool writes is english, ipa, pos, alternates,
chinese, group, example, example_zh. The example lines always come last.

## Example (value)

| Field | Rule |
|---|---|
| `sentence` | One sentence, 3–20 words, containing the word or a form of it (research R4), passing the content filter. |
| `translation` | Contains Chinese characters, at most 60 characters, passing the content filter. |

## Shared examples store: `<word file's folder>/.examples.json`

```json
{"version": 1, "examples": {"t-words|tablet|药片": {"sentence": "Take one tablet after each meal.", "translation": "每餐后服用一片药。", "created": "2026-10-11T10:00:00+00:00"}}}
```

The key is `group|english|chinese`, with an empty group for ungrouped
words. The file is written atomically under a per-file lock. Unreadable
files read as empty.

## PracticeAttempt / progress log

| Field | Change |
|---|---|
| `sentence`, `feedback` | Still optional, so old entries load. New entries never set them. |
| `sentence_recall` | **New**, optional: `"got"` or `"not_yet"`. Written only when the learner marked a sentence recall. |

## PracticeSession

| Item | Change |
|---|---|
| `mode` | One of `"recall-only"`, `"example"` (default) or `"example-recall"`. `"sentence"` is accepted as `"example"`. |
| Steps | Adds `sentence-recall`; removes `sentence` and `feedback`. |
| `example_service` | Injected `ExampleService`. Gives `prepare`, `get`, `status` and `renew`. |
| Held attempt | In example modes, every answer is held at `reveal` and recorded at the end of the word, with `sentence_recall` when marked. |
