# Design inputs

Development-time material for redesigning English Tutor's web UI with the
`frontend-design` project skill (`.claude/skills/frontend-design/`). Nothing in
this folder is used at runtime: the app never reads, serves or bundles it, and
it runs normally if `design/` is deleted.

## Layout

| Folder | What goes in it |
|--------|-----------------|
| `references/vocabulary-practice/` | Screenshots that show the look you want for the word recall screen |
| `references/sentence-practice/` | Screenshots for the sentence-writing and sentence-review step |
| `references/progress/` | Screenshots for progress, tallies and the session-complete screen |
| `references/shared/` | References that apply to every page, such as button or input style and typography |
| `fixtures/vocabulary/` | A small fixture word set used when the app is started for screenshot checks, so your real `vocabulary/` and `progress.md` are never touched |
| `verification/` | Screenshots Claude captures while checking a redesign. Git-ignored and created on demand |

Accepted reference image types: `.png`, `.jpg`, `.jpeg`, `.webp`. Other files
are skipped and reported.

Optionally add a `notes.md` beside the images to state your intent, e.g.
"like reference-1's spacing, ignore its sidebar".

To cover a new page, create `design/references/<page-key>/` and put images in
it. The skill does not need to change.

## References are inspiration, not assets

Claude extracts design principles from references: hierarchy, spacing,
typography, density, component treatment. It never copies a logo, trademark,
proprietary illustration, brand-specific asset or text from a reference into
the product, and never downloads or scrapes the reference site.

## Starting a redesign

> Redesign the vocabulary practice page using the frontend-design skill and the
> references in design/references/vocabulary-practice.
