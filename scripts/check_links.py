#!/usr/bin/env python3
"""Offline check of relative links in Markdown: every ``[text](path)`` and ``[text](path#anchor)``
must point at an existing file, and the anchor at an existing heading. External ``http(s)://``
links are not fetched (CI stays hermetic).

    scripts/check_links.py README.md docs/ CHANGELOG.md
"""

from __future__ import annotations

import re
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path

LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
IMAGE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")
HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")


def slug(heading: str) -> str:
    """GitHub's anchor for a heading: lowercase, punctuation dropped, spaces to hyphens."""
    text = re.sub(r"`|\*", "", heading.strip().lower())
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # [text](url) -> text
    return re.sub(r"[^\w\- ]", "", text).replace(" ", "-")


def prose(text: str) -> Iterator[tuple[int, str]]:
    """Lines outside fenced code blocks."""
    fenced = False
    for no, line in enumerate(text.splitlines(), 1):
        if FENCE.match(line):
            fenced = not fenced
            continue
        if not fenced:
            yield no, line


def anchors(text: str) -> set[str]:
    seen: dict[str, int] = {}
    out = set()
    for _, line in prose(text):
        if m := HEADING.match(line):
            base = slug(m[1])
            n = seen.get(base, 0)
            seen[base] = n + 1
            out.add(base if n == 0 else f"{base}-{n}")
    return out


def problems(md: Path) -> list[str]:
    text = md.read_text(encoding="utf-8")
    out = []
    for no, line in prose(text):
        for target in [*LINK.findall(line), *IMAGE.findall(line)]:
            if re.match(r"^[a-z][a-z0-9+.-]*:", target):  # http:, https:, mailto:
                continue
            path, _, anchor = target.partition("#")
            dest = (md.parent / path).resolve() if path else md
            if not dest.exists():
                out.append(f"{md}:{no}: missing {path}")
            elif anchor and dest.suffix == ".md" and anchor not in anchors(dest.read_text()):
                out.append(f"{md}:{no}: no heading #{anchor} in {dest.name}")
    return out


def files(args: Sequence[str]) -> Iterator[Path]:
    for arg in args:
        p = Path(arg)
        yield from sorted(p.rglob("*.md")) if p.is_dir() else [p]


def main(argv: Sequence[str] | None = None) -> int:
    paths = argv if argv is not None else sys.argv[1:]
    found = [msg for md in files(paths) for msg in problems(md)]
    for msg in found:
        print(f"BROKEN {msg}")
    print(f"links: {len(found)} broken")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
