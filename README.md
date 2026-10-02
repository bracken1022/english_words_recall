# English Tutor

A local CLI and web tool that drills English vocabulary for
Chinese speakers: it shows a Chinese meaning, has you recall the English
expression, has you write an original sentence with it (typed, or — in the
web UI — spoken and transcribed locally), and sends that sentence to a
locally running [Ollama](https://ollama.com) model (default `qwen3:14b`) for
grammar/naturalness correction via Ollama's HTTP API — the app never spawns
the `ollama` CLI. All vocabulary content and practice history are plain
Markdown files on disk — there is no database. Ollama only ever evaluates
language quality; it never controls grading or lesson progression, which are
fully deterministic regardless of what (or whether) Ollama returns. The
command line is a single-learner tool; the web UI supports several learners
on one machine, each logging in to their own account with their own
practice history (see [Accounts](#accounts-web-ui)).

## Setup

1. Install Python 3.11+.
2. Create a virtual environment and install dependencies:

   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -e ".[dev]"
   ```

3. Install and run [Ollama](https://ollama.com) locally, and pull the
   default model:

   ```bash
   ollama pull qwen3:14b
   ```

   Ollama must be reachable at `http://localhost:11434` (the default) for
   sentence-correction feedback. The recall drill itself works without it.
   A different model can be used instead via `--model` (see below).

## Vocabulary content

Create a directory of Markdown files describing what to practice. Each
vocabulary item is a `---`-delimited YAML block (see
`specs/001-vocab-recall-tutor/contracts/vocabulary-markdown-format.md` for
the full contract):

```markdown
---
english: receive
alternates: [accept]
chinese: 收到；接受
group: unit1
---
```

- `english` and `chinese` are required; `alternates` and `group` are optional.
- Add or edit items by hand-editing these files — no rebuild step needed.

> **Caution**: keep `--progress-file` (and the web UI's per-account
> `progress-<username>.md` files, which sit next to it) and `--word-lists-dir`
> *outside* `--vocab-dir`. The loader reads
> every `.md` file in the vocabulary directory as vocabulary content, so a
> progress log placed inside it will be (harmlessly, but noisily) treated as
> a malformed vocabulary file. The defaults (`./vocabulary/` vs
> `./progress.md`) already keep them separate.

## Running (command line)

```bash
.venv/bin/python -m src.cli --vocab-dir path/to/vocabulary --progress-file progress.md
```

While a submitted sentence is being reviewed, the app shows a spinner
("Reviewing your sentence...") so you know it's still working — it
disappears the instant the review completes or fails, and never shows a
fake percentage. If output isn't an interactive terminal (e.g., redirected
to a file), it prints that same message once instead of animating.

Options:

| Flag | Default | Purpose |
|---|---|---|
| `--vocab-dir` | `./vocabulary` | Directory of vocabulary Markdown files |
| `--progress-file` | `./progress.md` | Where practice attempts are appended |
| `--group` | (all items) | Only practice items tagged with this lesson/group |
| `--ollama-url` | `http://localhost:11434` | Base URL of the local Ollama server |
| `--model` | `qwen3:14b` | Local Ollama model name to use for correction |
| `--order` | `sequential` | Present words in file order (`sequential`) or shuffled (`random`) |
| `--mode` | `sentence` | `sentence` (write a sentence for each word, as above) or `recall-only` (skip sentence-writing entirely — see below) |

Your practice history is appended to the progress file as plain,
human-readable Markdown — see
`specs/001-vocab-recall-tutor/contracts/progress-log-format.md`.

### Recall-only mode

Passing `--mode recall-only` drops the sentence-writing step entirely —
each word is just: see the Chinese meaning, type the English expression,
see whether you were right, move on. It never calls Ollama, so it works
even if the local model isn't running.

A **correct** answer moves on immediately, exactly like sentence mode
does after finishing a sentence. A **wrong** answer instead prints the
correct expression and waits — "Press Enter to continue..." — so you can
actually study the word you missed before it's replaced, rather than
losing it to a fixed timer.

## Running (web UI)

A browser-based version of the same tutor is also available, so you can
practice from a phone, tablet, or another computer on the same local
network — it reads/writes the exact same vocabulary and progress files, and
reuses the exact same Ollama review pipeline, as the command line tool
above. Each learner logs in to their own account first (see
[Accounts](#accounts-web-ui) below — the web UI won't start without an
`accounts.yml`), and it is not exposed to the public Internet by default.

```bash
.venv/bin/python -m src.web --vocab-dir path/to/vocabulary --progress-file progress.md
```

This prints the address to open (default `http://0.0.0.0:8420`, which is
reachable at your machine's own LAN IP address, e.g.
`http://192.168.1.23:8420`, from any other device on the same network — find
your machine's LAN IP with `ipconfig getifaddr en0` on macOS or `ip addr` on
Linux). It accepts the same `--vocab-dir`, `--progress-file`, `--group`,
`--ollama-url`, `--model`, `--order`, and `--mode` flags as the CLI, plus
`--host` and `--port` to change what it binds to, `--accounts-file`
(default `./accounts.yml`) to choose the accounts list, and
`--word-lists-dir` (default `./word-lists`) for learners' uploaded word
lists. `--order` and `--mode`
only take effect when `--group` is also given — otherwise the interactive
choose screen below governs both fresh, every time.

If you don't pass `--group`, opening the web UI first shows a screen
listing the collections found in your vocabulary folder (grouped by each
item's `group` tag, plus "Practice everything" and, if any items have no
tag, "Ungrouped words"), alongside toggles for **Order** (Sequential /
Random) and **Mode** (Sentence / Recall only) — pick your settings and a
collection to start. Finishing a session shows your score and offers a
"Back to word sets" button that returns to that same screen (re-reading the vocabulary folder, so files you've added or changed
in the meantime show up, and letting you pick fresh settings for the next
pass), all without restarting the server. Passing `--group` skips this
screen entirely and behaves as before: it goes straight into practicing
just that group, with no way to switch collections without restarting.

After you check a word, the web UI shows the result and waits for you
(Enter or the button) before moving on, so you can study it for as long as
you want. A wrong answer, or "Show answer", shows every accepted expression
and goes on to the next word; only a correct answer in **Sentence** mode
leads to the sentence step. There you can type or speak a sentence, review
it (Cmd/Ctrl+Enter), skip it, or after the review choose "Try another
sentence" to write a new one for the same word (each reviewed sentence is
logged). Submitting an empty sentence asks you to confirm skipping the
word. "End session" in the header returns to the word sets mid-session;
the word in progress is not logged. In **recall-only** mode (see above)
there's no sentence step at all.

### Accounts (web UI)

Several people can share one running web UI — say, you on your laptop and
your partner on their phone — each practicing under their own account, at
the same time, without seeing or affecting each other's session or history.
There is no sign-up screen: you list the accounts by hand.

```bash
cp accounts.example.yml accounts.yml   # then edit usernames/passwords
```

```yaml
accounts:
  - username: weibo
    password: change-me
    display_name: Weibo        # optional, shown in the header
  - username: lily
    password: change-me-too
```

- Usernames ignore case and may use `a–z`, `0–9`, `_`, `-` (max 32).
  Passwords are matched exactly; quote any that look like a number or
  yes/no (`"1234"`). Full format:
  `specs/015-multi-account-login/contracts/accounts-file-format.md`.
- **The first account owns the existing `progress.md`** (so the history
  you had before accounts existed stays yours); every other account writes
  `progress-<username>.md` next to it. All accounts share the same
  vocabulary folder.
- Changing `accounts.yml` takes effect on restart. The web UI refuses to
  start, with a message saying why, if the file is missing, empty, or lists
  a username twice. Passwords are never printed.
- A login lasts (even across browser restarts) until you press **Log out**
  or the server restarts. Logging out mid-word discards that word unlogged,
  like **End session**.
- `accounts.yml` is gitignored. Passwords are stored and sent as plain
  text — this keeps learners apart on a trusted home network; it is not
  security for anything exposed to the Internet.

The command line tool has no accounts or login and is unchanged.

### Your own word lists (web UI)

Each learner can upload their own word lists from the word-set screen
(**Upload word list**) — from a phone or any other device — and practice
them separately from everyone else.

- **Formats**: a `.csv`, `.txt` or `.tsv` file with one word per line —
  English, then the Chinese meaning, then any extra accepted answers —
  separated by commas (`,` or the Chinese `，`) or tabs. A spreadsheet
  saved as CSV works, and a header row is skipped. Your existing
  vocabulary `.md` files upload as they are, too.

  ```text
  English, Chinese
  receive, 收到；接受, accept
  give up，放弃
  ```

  Use `；` to separate several meanings. Lines that can't be used are
  skipped and listed after the upload (e.g. `line 12: no Chinese meaning`).
- **One file = one word set**, named after the file (`unit1.csv` →
  "unit1").
- **Once you have at least one list, you practice only your own lists**;
  until then (or after deleting all of them) you practice the shared
  vocabulary folder as before. Nobody ever sees anyone else's lists.
- Upload a file with the same name to **replace** a list (you'll be asked
  to confirm), or **Delete** it under "My word lists". Your practice
  history is always kept. A session in progress isn't interrupted — the
  change shows up the next time you pick a word set.
- Limits: 1 MB and 5,000 words per file. Lists are saved as readable
  Markdown in `word-lists/<username>/` (gitignored).

The web UI loads its fonts (Source Serif 4, Noto Serif SC) and icons
(Phosphor) from Google Fonts and unpkg. Offline, it falls back to local
serif fonts and the icons are simply omitted.

The web UI and the command-line tool can be run at the same time and are
just two ways to reach the same tutor — running one doesn't require
stopping the other (though see the caution above about keeping
`--progress-file` outside `--vocab-dir` for either). The collection screen,
skip confirmation, and voice input below are conveniences specific to the
web UI; the command-line tool intentionally keeps its original, simpler
one-word-at-a-time flow.

### Voice input (optional)

Instead of typing a sentence, you can speak it. This is entirely
local — no cloud speech service is ever used, and no audio is kept once
it's transcribed:

```bash
.venv/bin/pip install -e ".[voice]"
```

The first time you use it, a small local speech-to-text model
(`faster-whisper`) is downloaded and cached — a one-time setup step, the
same idea as pulling an Ollama model. Once installed, a "Speak instead"
button appears next to the sentence field; tap it to start recording, tap
it again to stop. The recognized text lands in that same field for you to
review and edit — nothing is ever submitted straight from speech. If the
dependency isn't installed (or fails to load), the button simply doesn't
appear and typing works exactly as it always has.

> **Note**: browsers only allow microphone access on `localhost` or over
> HTTPS. If you're reaching the web UI from another device on your LAN
> (see above), voice input generally won't be available there — typing is
> unaffected either way.

## Development

```bash
.venv/bin/pytest         # run the test suite
.venv/bin/ruff check .   # lint
```

See `specs/` (one directory per feature, each with its own spec, plan, and
design artifacts) for the full history this project was built from.

### Design workflow (reference-driven UI)

To redesign a page from visual references, drop screenshots into
`design/references/<page>/` (shared styles go in `design/references/shared/`)
and ask Claude Code:

> Redesign the vocabulary practice page using the frontend-design skill and the
> references in design/references/vocabulary-practice.

The `frontend-design` project skill (`.claude/skills/frontend-design/`) works
out a written design interpretation first. It then implements within the
existing templates and CSS without changing learning behavior, and checks the
result with screenshots at desktop and mobile widths, against a fixture
vocabulary. `design/` is development-only: the app never reads it. See
`design/README.md`.
