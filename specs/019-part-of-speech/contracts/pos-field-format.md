# Contract: The `pos` Field

This extends the vocabulary Markdown format (spec 001, spec 017's `ipa`),
the upload formats (spec 016) and the import flow (spec 018). It covers
FR-001 to FR-003, FR-007 and FR-011.

## Vocabulary Markdown (shared folder, personal lists, `.md` uploads)

| Field | Required | Type | Default |
|---|---|---|---|
| `pos` | no | a list of labels, or a string of labels | none |

```yaml
---
english: rent
ipa: rent
pos: [n., v.]
alternates: []
chinese: 租金；租用；出租
group: ra_z_words
---
```

- **Accepted equivalents**: these all load as `[n., v.]`: `pos: n. v.`,
  `pos: "n., v."`, `pos: noun/verb` and `pos: 名词；动词`. Research R2
  has the full synonym table.
- **Invalid values**: an invalid value, such as `pos: verbish` or
  `pos: 42`, doesn't skip the block. The word loads with no labels, and a
  warning is reported in the same channel as other vocabulary warnings:
  `<file>: '<english>': pos "<raw>" is not a part of speech — shown without one`.
- **Upload warnings**: in uploads, the same message appears in the
  upload result's skip list, prefixed `block N:`. The word still counts
  as added.
- **Writing**: tools write `pos` as a flow list, in display form.

## Simple-list uploads (`.csv` / `.txt` / `.tsv`, and plain-line `.md`)

After the English word, a field counts as the part of speech when every
token in it is a dotted abbreviation (`adj.`, `n.`, `phr. v.`), a full
English name (`adjective`, `phrasal verb`) or a Chinese name (`形容词`).
It may come in any position:

```text
zealous, adj., 热心的
rent, 租金；出租, n. v.
give up, 放弃, phr. v., /ˌɡɪv ˈʌp/
```

- **Which field is the meaning**: the Chinese meaning is the first field
  after the English word that is neither a pronunciation (`/…/`) nor a
  part of speech. This holds in both upload paths. Before this feature,
  `receive, v., 收到` would have stored "v." as the meaning.
- **Repeats**: only the first such field is used. A second one gives the
  skip message `line N: more than one part of speech — kept the first`,
  and the word is still added.
- **Bare letters**: a field like `n` or `a` is **not** a part of speech
  in a simple list. It stays an accepted answer, as before.

## Upload format hint

The hint adds the part of speech to its example:
`… Or add your own: receive, v., 收到, /rɪˈsiːv/ …`
