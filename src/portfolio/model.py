"""Validators shared by every content model. No I/O."""

import re
from collections.abc import Iterator, Mapping

PLACEHOLDER = "[X]"
# A `[...]` that is not a Markdown link `[text](url)` is an unfinished gap: `[X]`, `[TBD]`, `[n]`.
GAP = re.compile(r"\[[^\]]*\](?!\()")


def no_placeholder(value: str) -> str:
    """Refuse text that still holds a `[...]` gap: it must never reach the public site."""
    if match := GAP.search(value):
        raise ValueError(f"unresolved placeholder {match[0]!r} in {value!r}")
    return value


def find_placeholders(data: object, path: str = "") -> Iterator[str]:
    """Walk parsed YAML/JSON and yield `path: text` for every string holding a gap."""
    if isinstance(data, str):
        if match := GAP.search(data):
            yield f"{path or '<root>'}: placeholder {match[0]!r} in {data!r}"
    elif isinstance(data, Mapping):
        for key, value in data.items():
            yield from find_placeholders(value, f"{path}.{key}" if path else str(key))
    elif isinstance(data, list):
        for i, value in enumerate(data):
            yield from find_placeholders(value, f"{path}[{i}]")
