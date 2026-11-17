"""Composition root: `portfolio generate`. Paths and file writes only; no logic.

Outputs (all gitignored): `docs/cv/index.md` (a page), `overrides/partials/profile_data.html`
(the profile column's values), and snippets in `generated/`, outside docs/, pulled into pages
with `pymdownx.snippets` so they are never built as pages of their own.
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from portfolio.blog.frontmatter import FrontMatterError
from portfolio.build import build_cv, build_latest_posts
from portfolio.cv.load import CVError


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"wrote {path}")


def generate(root: Path) -> None:
    """Every output is gitignored; all of them are written only after all inputs validate."""
    cv = build_cv(root / "data" / "cv.yml")
    latest = build_latest_posts(root / "docs")
    _write(root / "docs" / "cv" / "index.md", cv.page)
    _write(root / "overrides" / "partials" / "profile_data.html", cv.profile)
    _write(root / "generated" / "home-profile.md", cv.home_header)
    _write(root / "generated" / "latest-posts.md", latest)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="portfolio", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="write the generated content files")
    gen.add_argument("--root", type=Path, default=Path.cwd(), help="project root (mkdocs.yml)")
    args = parser.parse_args(argv)
    try:
        generate(args.root)
    except (CVError, FrontMatterError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0
