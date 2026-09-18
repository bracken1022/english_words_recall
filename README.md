# English Tutor

A local, single-learner CLI tool that drills English vocabulary for Chinese
speakers: it shows a Chinese meaning, has you recall the English expression,
has you write an original sentence with it, and sends that sentence to a
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

The web UI and the command-line tool can be run at the same time and are
just two ways to reach the same tutor — running one doesn't require
stopping the other (though see the caution above about keeping
`--progress-file` outside `--vocab-dir` for either).

## Development

```bash
.venv/bin/pytest         # run the test suite
.venv/bin/ruff check .   # lint
```

See `specs/001-vocab-recall-tutor/`, `specs/002-sentence-review-indicator/`,
and `specs/003-web-ui/` for the full specs, plans, and design artifacts this
project was built from.
