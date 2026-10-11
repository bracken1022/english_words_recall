# Example-sentence evaluation (spec 021, T034)

Run: `python -m src.tools.eval_examples --sample 50 --out backups/examples-021-eval`
on 2026-10-11, model `qwen3:14b` at `http://localhost:11434`, fixture
`tests/fixtures/example_eval.yml` (35 words, 10 phrases, 5 words with
several meanings, each with the meaning to use).

## Automatic checks

| Check | Result | Target |
|---|---|---|
| Valid examples (one sentence, 3–20 words, uses the word, translation, content filter) | **50/50 (100%)** | ≥ 95% |
| Rejected attempts | 0 | — |
| Time per word | median 1.3 s, max 3.1 s, 0 over 5 s | SC-001: ≤ 5 s on first sight |

Result: **PASS (automatic checks)**.

## Human review (SC-002 gate): passed

`backups/examples-021-eval/REVIEW.md` lists all 50 examples, each with
**OK** and **Unsafe** boxes. The release gate is at least 48/50 OK (≥ 95%)
and 0 unsafe.

Pre-read notes given to the reviewer (all six were judged OK):

| # | Word | Note |
|---|---|---|
| 12 | neighbor | Chinese 「给我了一些」 reads a little awkwardly (「给了我一些」 is usual). |
| 18 | inevitable | "success … was inevitable once we started working together": grammatical, but the logic is a bit odd. |
| 20 | reluctant | 「她不情愿地离开」 means "she left reluctantly", not "she was reluctant to leave". |
| 41 | look up | The Chinese 「你能在这个词在字典里查一下意思吗」 is ungrammatical. |
| 44 | get along with | The English is a comma splice ("…my neighbor, we often…"). |
| 47 | figure | "the total figure for the project" sounds stilted. |

Everything else read as natural, correct, and in the given meaning. Nothing
looked unsafe.

| Reviewed by | Date | OK | Unsafe | Gate |
|---|---|---|---|---|
| learner | 2026-10-11 | 50/50 | 0 | **PASS** (≥ 95% OK, 0 unsafe) |

The reviewer gave this verdict in conversation ("all are ok") rather than by ticking each box in REVIEW.md.
