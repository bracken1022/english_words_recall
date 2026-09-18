"""Shared parser for the "---"-delimited YAML blocks used by vocabulary and
progress-log Markdown files (see contracts/vocabulary-markdown-format.md and
contracts/progress-log-format.md).
"""

import re

import yaml

_BLOCK_RE = re.compile(r"^---\s*\n(.*?)\n---\s*$", re.DOTALL | re.MULTILINE)


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
            parsed = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            warnings.append(f"could not parse block as YAML: {exc}")
            continue

        if not isinstance(parsed, dict):
            warnings.append(f"block did not parse to a mapping: {raw.strip()!r}")
            continue

        blocks.append(parsed)

    return blocks, warnings
