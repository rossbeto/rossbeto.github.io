"""Composition root: `portfolio generate` and `portfolio sync-projects`. Paths and file writes
only; no logic.

Outputs (all gitignored): `docs/cv/index.md` and `docs/projects/index.md` (pages),
`docs/cv/<Name>-CV.pdf` (copied into the site by the build, so its links are checked),
`overrides/partials/profile_data.html` (the profile column's values), and snippets in
`generated/`, outside docs/, pulled into pages with `pymdownx.snippets` so they are never built
as pages of their own.
"""

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from portfolio.build import (
    PDFError,
    PdfMode,
    build_cv,
    build_latest_posts,
    build_projects,
    build_synced_projects,
    drift,
)
from portfolio.cv.load import CVError
from portfolio.frontmatter import FrontMatterError
from portfolio.github import FetchError, fetch_raw, latest_commit
from portfolio.projects.card import CardError
from portfolio.projects.sources import SourceError, bump_ref, load_sources


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"wrote {path}")


def generate(root: Path, *, pdf: PdfMode = PdfMode.AUTO) -> None:
    """Every output is gitignored; all of them are written only after all inputs validate."""
    docs = root / "docs"
    latest = build_latest_posts(docs)
    projects = build_projects(docs)
    cv = build_cv(root / "data" / "cv.yml", docs, pdf=pdf)
    pdf_file = docs / "cv" / cv.pdf_name
    if cv.pdf is None:
        pdf_file.unlink(missing_ok=True)  # never publish a stale PDF next to a page without it
        if cv.notice:
            print(f"warning: {cv.notice}", file=sys.stderr)
    else:
        pdf_file.parent.mkdir(parents=True, exist_ok=True)
        pdf_file.write_bytes(cv.pdf)
        print(f"wrote {pdf_file} ({cv.pdf_pages} pages)")
    _write(docs / "cv" / "index.md", cv.page)
    _write(root / "overrides" / "partials" / "profile_data.html", cv.profile)
    _write(root / "generated" / "home-profile.md", cv.home_header)
    _write(root / "generated" / "latest-posts.md", latest)
    _write(root / "docs" / "projects" / "index.md", projects.index)
    _write(root / "generated" / "featured-projects.md", projects.featured)


def sync_projects(root: Path, *, check: bool = False, bump: bool = False) -> int:
    """Pages and media from the repos in data/projects.yml, at their pinned commits.

    `--bump` first moves each `ref` to the repo's latest commit (the update workflow);
    `--check` writes nothing and returns 1 when the committed files differ (CI drift check).
    """
    sources_file = root / "data" / "projects.yml"
    sources = load_sources(sources_file)
    if bump:
        for source in sources:
            latest = latest_commit(source.repo)
            if latest != source.ref:
                bump_ref(sources_file, source.ref, latest)
                print(f"{source.slug}: {source.ref[:12]} -> {latest[:12]}")
        sources = load_sources(sources_file)
    files = build_synced_projects(sources, fetch_raw)
    docs = root / "docs"
    if check:
        stale = drift(files, docs)
        for path in stale:
            print(f"drift: docs/{path} differs from its pinned source", file=sys.stderr)
        if stale:
            print("run `make projects-sync` and commit the result", file=sys.stderr)
        return 1 if stale else 0
    for f in files:
        (docs / f.path).parent.mkdir(parents=True, exist_ok=True)
        (docs / f.path).write_bytes(f.data)
        print(f"wrote docs/{f.path}")
    if not sources:
        print("no sources in data/projects.yml: nothing to sync")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="portfolio", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="write the generated content files")
    gen.add_argument("--root", type=Path, default=Path.cwd(), help="project root (mkdocs.yml)")
    gen.add_argument(
        "--pdf",
        type=PdfMode,
        choices=list(PdfMode),
        default=os.environ.get("PORTFOLIO_PDF", PdfMode.AUTO),
        help="the CV PDF: auto (skip if WeasyPrint can't run), required (CI), off. "
        "Default: $PORTFOLIO_PDF or auto",
    )
    sync = sub.add_parser("sync-projects", help="project pages from their repos' portfolio cards")
    sync.add_argument("--root", type=Path, default=Path.cwd(), help="project root (mkdocs.yml)")
    mode = sync.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="exit 1 if the files have drifted")
    mode.add_argument("--bump", action="store_true", help="move each ref to the latest commit")
    args = parser.parse_args(argv)
    try:
        if args.command == "sync-projects":
            return sync_projects(args.root, check=args.check, bump=args.bump)
        generate(args.root, pdf=PdfMode(args.pdf))
    except (CVError, FrontMatterError, PDFError, SourceError, CardError, FetchError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0
