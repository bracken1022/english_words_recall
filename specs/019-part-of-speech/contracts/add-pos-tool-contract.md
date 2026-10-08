# Contract: `python -m src.tools.add_pos`

This is the one-time fill for FR-012 and US3. It mirrors spec 017's
`add_ipa` contract.

```text
python -m src.tools.add_pos --mapping MAPPING.tsv [--backup-root backups] [--dry-run] FILE...
```

## Mapping file

The mapping file is UTF-8 TSV, `file<TAB>english<TAB>pos<TAB>note`.
`#` lines and blank lines are ignored.

- `file`: the path exactly as given on the command line.
- `pos`: any spelling accepted by `normalize_pos`. Leave it empty to
  leave the word without labels; `note` then says why.

**Validation**: every non-empty `pos` must normalise. If any doesn't,
each problem is printed as `file: english: <problem>`, nothing is
written, and the tool exits with 1.

## Behaviour

1. **Plan**: for each block, the tool does one of these:
   - if the block already has a `pos:` line, counts it as "already" and
     leaves it untouched;
   - if the mapping has labels for it, inserts `pos: [<labels>]` right
     after the `ipa:` line, or after `english:` when there is no `ipa:`;
   - if the mapping has an empty value, counts it as "left empty" with
     its note;
   - if the mapping has no entry, counts it as "missing".
2. **Dry run**: `--dry-run` prints the totals and writes nothing.
3. **Backup**: each file that changes is copied to
   `<backup-root>/pos-<stamp>/files/<path>` before writing.
4. **Write**: files are written atomically.
5. **Verify**: each file is reloaded. If any block's `english`,
   `chinese`, `alternates`, `group` or `ipa` differs, or the file gains a
   load warning, **all** changed files are restored from backup and the
   tool exits with 1.
6. **Review**: the tool writes `<backup-root>/pos-<stamp>/REVIEW.md`,
   containing:
   - the totals;
   - a "Filled" table with file, word, labels and note;
   - "Left empty", with reasons;
   - "Missing from mapping";
   - "Spot check (30)", a seeded random sample to tick against a
     learner's dictionary.

   It also copies the mapping as `mapping.tsv`, and prints the totals
   and the review path.

The tool exits with 0 on success, including the case where there is
nothing to change.
