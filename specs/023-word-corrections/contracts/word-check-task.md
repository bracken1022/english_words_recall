# Contract: Word-Check Task (Qwen)

Built on `qwen_client.complete_json` (commit 75968c1): POST
`{QWEN_BASE_URL}/chat/completions`, `enable_thinking: false`,
`temperature: 0`, `max_tokens: 4096`, `response_format: json_object`,
45 s timeout, key only in the `Authorization` header.

## Request (user message)

```text
English: "tailor"
Dialect: British
Current IPA: "ˈteɪlə"
Current Chinese: "裁缝；定制；使适合"
Current parts of speech: "n. v."
```

Only these five lines are sent (FR-013). The system prompt
(`word_check.SYSTEM_PROMPT`, with the dialect's IPA rule) asks for:

```json
{"ipa": "ˈteɪlə", "chinese": "裁缝；定做（衣服）；使适应", "pos": ["n.", "v."]}
```

## Validation (all must hold, else the word is unchanged, FR-007)

- Exactly the keys `ipa`, `chinese`, `pos`.
- `ipa`: passes `normalize_ipa`, and the dialect's check
  (`check_british_ipa` / `check_american_ipa`) returns no problems.
  Ignored (current IPA kept) for heteronyms.
- `chinese`: non-empty after trimming, ≤ 60 characters, passes the
  family-safe filter.
- `pos`: non-empty list; `normalize_pos` maps every item to a label.

## Outcomes for the service

| Result | Service does |
|---|---|
| Valid answer | Compare with the values sent; save changed fields (research R7). |
| `QwenError("bad_reply" \| "bad_status")` | Leave the word; retry next time it comes up. |
| `QwenError("timeout" \| "unavailable" \| "rate_limited")` | Leave the word; pause checks 5 minutes. |
| `QwenError("auth")` | Leave the word; pause checks until restart. |
| `QwenError("not_configured")` | Not reached: the service isn't built without a key. |
