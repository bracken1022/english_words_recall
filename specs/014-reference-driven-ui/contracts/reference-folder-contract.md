# Contract: `design/` folder and runtime boundary

Enforced by `tests/unit/test_design_reference_layout.py`.

## Layout

```text
design/
├── README.md
├── references/
│   ├── vocabulary-practice/   (.gitkeep)
│   ├── sentence-practice/     (.gitkeep)
│   ├── progress/              (.gitkeep)
│   └── shared/                (.gitkeep)
├── fixtures/vocabulary/sample.md
└── verification/              (git-ignored, created on demand)
```

- New page folders are added by creating `design/references/<page-key>/`. No other change
  is needed.
- `design/README.md` MUST state: what goes in each folder; the accepted image types; the
  optional `notes.md`; that references are inspiration only (no logos, brand assets or
  copied text get into the product); that nothing here is used at runtime; and the
  one-line request that starts the workflow.

## Fixture vocabulary

- Uses the existing vocabulary format (YAML front-matter blocks: `english`, `alternates`,
  `chinese`, `group`) with group `design-fixture`.
- 3–5 words, at least one with alternates. It MUST load through the existing loader
  without warnings.

## Runtime boundary

- No file under `src/` contains the substring `design/`.
- `create_app(...)` with a temporary vocab dir serves `GET /` and `GET /static/style.css`
  → 200 while the working directory has no `design/` folder.
- `.gitignore` contains `/design/verification/`.
