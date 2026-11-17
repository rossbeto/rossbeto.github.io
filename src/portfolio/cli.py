"""Composition root: `portfolio generate`. Paths and file writes only; no logic.

Output goes to `generated/` (gitignored), outside docs/, and is pulled into pages with
`pymdownx.snippets`, so it is never built as a page of its own.
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from portfolio.blog.frontmatter import FrontMatterError
from portfolio.build import build_latest_posts


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"wrote {path}")


def generate(root: Path) -> None:
    _write(root / "generated" / "latest-posts.md", build_latest_posts(root / "docs"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="portfolio", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="write the generated content files")
    gen.add_argument("--root", type=Path, default=Path.cwd(), help="project root (mkdocs.yml)")
    args = parser.parse_args(argv)
    try:
        generate(args.root)
    except FrontMatterError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0
