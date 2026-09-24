"""Shared parser for the "---"-delimited YAML blocks used by vocabulary and
progress-log Markdown files (see contracts/vocabulary-markdown-format.md and
contracts/progress-log-format.md).
"""

import re

import yaml

_BLOCK_RE = re.compile(r"^---\s*\n(.*?)\n---\s*$", re.DOTALL | re.MULTILINE)


class _BlockLoader(yaml.SafeLoader):
    """yaml.SafeLoader narrowed to YAML 1.2's boolean spellings.

    PyYAML's default (YAML 1.1) resolver also treats unquoted "on"/"off"/
    "yes"/"no"/"y"/"n" (any case) as booleans — a real hazard for this
    format, where short, ordinary English words like "on" and "off" are
    exactly the kind of thing a learner adds as vocabulary content, and
    silently corrupting them into Python bools eventually crashes grading
    (src/services/matcher.py) instead of failing where the mistake is.
    The progress log's "correct" field is a genuine boolean, but it's
    always written as the canonical true/false spelling
    (src/services/progress_log.py), which this narrowed resolver still
    recognizes.
    """


_BlockLoader.yaml_implicit_resolvers = {
    first_char: [
        (tag, regexp) for tag, regexp in resolvers if tag != "tag:yaml.org,2002:bool"
    ]
    for first_char, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_BlockLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool",
    re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
    list("tTfF"),
)


def parse_blocks(text: str) -> tuple[list[dict], list[str]]:
    """Parse every "---"-delimited YAML block in *text*.

    Returns (blocks, warnings). A block that fails to parse as YAML, or that
    parses to something other than a mapping, is skipped and produces one
    warning string; it never raises.
    """
    blocks: list[dict] = []
    warnings: list[str] = []

    for match in _BLOCK_RE.finditer(text):
        raw = match.group(1)
        try:
            parsed = yaml.load(raw, Loader=_BlockLoader)
        except yaml.YAMLError as exc:
            warnings.append(f"could not parse block as YAML: {exc}")
            continue

        if not isinstance(parsed, dict):
            warnings.append(f"block did not parse to a mapping: {raw.strip()!r}")
            continue

        blocks.append(parsed)

    return blocks, warnings
