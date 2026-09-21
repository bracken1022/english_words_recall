# English Tutor

A local, single-learner CLI and web tool that drills English vocabulary for
Chinese speakers: it shows a Chinese meaning, has you recall the English
expression, has you write an original sentence with it (typed, or — in the
web UI — spoken and transcribed locally), and sends that sentence to a
locally running [Ollama](https://ollama.com) model (default `qwen3:14b`) for
grammar/naturalness correction via Ollama's HTTP API — the app never spawns
the `ollama` CLI. All vocabulary content and practice history are plain
Markdown files on disk — there is no database. Ollama only ever evaluates
language quality; it never controls grading or lesson progression, which are
fully deterministic regardless of what (or whether) Ollama returns.

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

> **Caution**: keep `--progress-file` *outside* `--vocab-dir`. The loader reads
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

Your practice history is appended to the progress file as plain,
human-readable Markdown — see
`specs/001-vocab-recall-tutor/contracts/progress-log-format.md`.

## Running (web UI)

A browser-based version of the same tutor is also available, so you can
practice from a phone, tablet, or another computer on the same local
network — it reads/writes the exact same vocabulary and progress files, and
reuses the exact same Ollama review pipeline, as the command line tool
above. It does not require authentication and is not exposed to the public
Internet by default.

```bash
.venv/bin/python -m src.web --vocab-dir path/to/vocabulary --progress-file progress.md
```

This prints the address to open (default `http://0.0.0.0:8420`, which is
reachable at your machine's own LAN IP address, e.g.
`http://192.168.1.23:8420`, from any other device on the same network — find
your machine's LAN IP with `ipconfig getifaddr en0` on macOS or `ip addr` on
Linux). It accepts the same `--vocab-dir`, `--progress-file`, `--group`,
`--ollama-url`, and `--model` flags as the CLI, plus `--host` and `--port`
to change what it binds to.

If you don't pass `--group`, opening the web UI first shows a screen
listing the collections found in your vocabulary folder (grouped by each
item's `group` tag, plus "Practice everything" and, if any items have no
tag, "Ungrouped words") — pick one to limit the session to just those
words. Finishing a session shows how many you recalled correctly and
offers a "Practice again" button that returns to that same screen
(re-reading the vocabulary folder, so files you've added or changed in the
meantime show up), all without restarting the server. Passing `--group`
skips this screen entirely and behaves as before: it goes straight into
practicing just that group, with no way to switch collections without
restarting.

While writing a sentence, submitting it empty asks you to confirm skipping
that word rather than sending nothing off for review.

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
