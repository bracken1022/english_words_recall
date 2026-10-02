# Contract: `python -m src.tools.add_ipa` (fill tool)

Fills `ipa` lines into existing vocabulary files from a mapping file. It is
used once for the existing words, and again whenever the user asks for a
new list to be filled. Covers spec FR-005, FR-006, SC-001, SC-005.

## Usage

```bash
.venv/bin/python -m src.tools.add_ipa --mapping MAPPING.tsv [--backup-root backups] [--dry-run] FILE...
```

- **`FILE...`**: the vocabulary `.md` files to edit, e.g.
  `vocabulary/*.md word-lists/zhoudan/*.md`.
- **`--mapping`**: a TSV file with lines `file<TAB>english<TAB>ipa<TAB>note`.
  - The `file` column is matched against each FILE argument as given.
  - Blank lines and lines starting with `#` are ignored.
- **`--dry-run`**: validates everything and prints the summary, but writes
  no files and creates no backup.

## Behaviour

1. **Parse and validate.** Validate **every** non-empty mapping IPA with
   `check_british_ipa()` (research R6). On any failure, print
   `<file>: <english>: <reason>` for each one and exit `1`. No file is
   touched.
2. **Plan the edits.** For each FILE, for each `---` block:
   - **Already has an `ipa:` line**: leave it alone and count it as
     *already had*.
   - **(file, english) is in the mapping with an IPA**: insert
     `ipa: <value>` on the line directly after the block's `english:`
     line, using the same indentation (none). Count it as *filled*.
   - **In the mapping with an empty IPA**: no change; count it as *left
     empty* and keep the note.
   - **Not in the mapping**: no change; count it as *missing from
     mapping*.
3. **Back up and review.** Unless `--dry-run`:
   - copy each FILE that will change to
     `<backup-root>/ipa-<YYYYMMDD-HHMMSS>/files/<same relative path>`;
   - write the edited files, each to a temporary file followed by
     `os.replace`;
   - write `<backup-root>/ipa-<ts>/REVIEW.md`, per `data-model.md`;
   - copy the mapping file in beside it.
4. **Verify.** Reload every edited file with `load_vocabulary`. Its block
   count and every block's `english`, `chinese`, `alternates` and `group`
   must equal the values from before the edit, and no new warnings may
   appear. If verification fails, restore from the backup and exit `1`.
5. **Summarise.** Print the counts for filled, already had, left empty and
   missing from mapping, and the path to `REVIEW.md`. Exit `0`.

## Guarantees

- Apart from the inserted `ipa:` lines, every byte of an edited file is
  unchanged: the same line endings, quoting and list style.
- Running the tool twice is a no-op the second time (everything counts as
  *already had*).
- The tool never writes outside the given FILEs and `<backup-root>`.
- `backups/` is gitignored.
