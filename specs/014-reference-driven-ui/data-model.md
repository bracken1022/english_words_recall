# Data Model: Reference-Driven UI Design Workflow

No runtime data. The entities below are dev-time artifacts in files or in the
conversation.

## Reference Set

| Field | Description |
|-------|-------------|
| page key | Folder name under `design/references/` (kebab-case), e.g. `vocabulary-practice` |
| images | `*.png`, `*.jpg`, `*.jpeg`, `*.webp` in that folder. Other files are skipped and reported |
| notes (optional) | `notes.md` in the folder: the developer's intent ("like ref-1's spacing, ignore its sidebar") |
| shared | `design/references/shared/` is always added to any page's set |

**Rules**: Read-only for the assistant. An empty folder (only `.gitkeep`) counts as "no references".
Never referenced from `src/`.

## Design Interpretation

Produced before any page edits, shown to the developer, and repeated in the final report.

| Section | Content |
|---------|---------|
| References used | List of files, plus any skipped and why |
| Visual direction | 1–2 sentences |
| Typography hierarchy | Prompt / question / supporting text levels with relative size and weight |
| Spacing system | Base unit and scale, and where generous vs. tight space goes |
| Actions | The single primary action per state, plus secondary actions and their treatment |
| Component treatment | Inputs, buttons, feedback blocks, progress, and when (rarely) a card is used |
| Feedback behavior | Correct / incorrect / loading / review appearance and disappearance |
| Responsive strategy | What changes at narrow width, and what must not (the hierarchy) |
| Not carried over | Logos, brand marks, copy, illustrations, dashboard structure, … |
| Conflicts / decisions | Reference conflicts, and rule-vs-reference resolutions |

## Verification Pass

| Field | Description |
|-------|-------------|
| pass number | 0 = first capture after implementing, then 1..3 refine passes |
| captures | One per (viewport ∈ {1280, 390}) × (state relevant to the change) |
| findings | Each: category, description, classification ∈ {fix, intentional (reason), matches} |

**State transitions**: pass N with any `fix` → edit → pass N+1. Stop when there are no
`fix` findings or N = 3. Tooling unavailable → a single "skipped" record with the reason.

## Redesign Report

References used · interpretation · files changed · test suite result before/after ·
verification passes (screenshot paths) · fixes made · intentional deviations · remaining
differences.
