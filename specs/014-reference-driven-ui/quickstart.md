# Quickstart: Validating the Reference-Driven UI Workflow

## Prerequisites

- `pip install -e '.[dev]'`
- Optional, for screenshots: Claude browser tools in the session, or Node/npx (Playwright
  CLI is fetched on demand).

## 1. Contract tests

```sh
pytest tests/unit/test_design_workflow_skill.py tests/unit/test_design_reference_layout.py
pytest   # full suite. Must be all green, same as before this feature
```

Expected: all pass. This covers the skill contract ([contracts/skill-contract.md](contracts/skill-contract.md))
and the folder/runtime boundary ([contracts/reference-folder-contract.md](contracts/reference-folder-contract.md)).

## 2. Runtime independence (SC-004)

```sh
mv design /tmp/design.bak && python -m src.web --port 8422 --host 127.0.0.1 &
curl -s -o /dev/null -w '%{http_code}\n' localhost:8422/   # → 200
kill %1; mv /tmp/design.bak design
```

## 3. Isolated verification instance

Follow [contracts/verification-recipe.md](contracts/verification-recipe.md) §1–2. Expected:
the choose screen lists `design-fixture`. After `select` the recall prompt shows a fixture
word's Chinese meaning. `progress.md` at the repo root is unchanged (`git status`).

## 4. End-to-end dry run (manual, with Claude)

1. Put 1–2 screenshots in `design/references/vocabulary-practice/`.
2. Ask: "Redesign the vocabulary practice page using the frontend-design skill and the
   references in design/references/vocabulary-practice."
3. Expected order of Claude's output:
   - Lists the references inspected, then a design interpretation with all sections from
     [data-model.md](data-model.md). No files edited yet.
   - Edits limited to `src/web/templates/index.html`, `src/web/static/style.css` and,
     if needed, presentation-only parts of `app.js`. Test suite green before and after.
   - Screenshots at 1280 and 390 under `design/verification/vocabulary-practice/pass-0/`,
     a findings list, at least one refine pass, and a final report.
4. Repeat with an empty `design/references/progress/`. Expected: Claude reports no
   references and asks before proceeding.
5. `git diff .claude/skills/frontend-design/`. Expected: no changes from either run (SC-006).
