"""Use cases: orchestrate the adapters and the pure renderers, return text. No writing."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from urllib.parse import urljoin

from portfolio.blog.frontmatter import read_posts
from portfolio.blog.latest import render_latest
from portfolio.cv.load import load_cv
from portfolio.cv.model import CV
from portfolio.cv.render import (
    PrintLab,
    render_cv_markdown,
    render_cv_print_html,
    render_home_header,
    render_profile_data,
)
from portfolio.pdf import PDFUnavailable, render_pdf
from portfolio.projects.card import parse_card, render_synced_page
from portfolio.projects.frontmatter import read_projects
from portfolio.projects.index import render_featured, render_project_index
from portfolio.projects.model import Kind, Project, ProjectSource

MAX_PDF_PAGES = 3  # a CV that grew longer is a bug, not a layout detail


class PdfMode(StrEnum):
    AUTO = "auto"  # make the PDF when WeasyPrint works here; skip it with a warning otherwise
    REQUIRED = "required"  # CI: no PDF is an error
    OFF = "off"


class PDFError(Exception):
    """The PDF is required but can't be made, or it is too long."""


@dataclass(frozen=True)
class CVOutputs:
    page: str  # docs/cv/index.md
    profile: str  # overrides/partials/profile_data.html
    home_header: str  # generated/home-profile.md
    pdf_name: str  # e.g. NguyenHienLam-CV.pdf, written next to the page (docs/cv/)
    pdf: bytes | None  # None: skipped (see `notice`)
    pdf_pages: int = 0
    notice: str | None = None


def build_latest_posts(docs_dir: Path, limit: int = 3) -> str:
    return render_latest(read_posts(docs_dir), limit)


def pdf_name(cv: CV) -> str:
    return f"{''.join(cv.basics.name.split())}-CV.pdf"


def _page_url(site_url: str | None, src: str) -> str | None:
    """`projects/tenantlab.md` → `https://site/projects/tenantlab/` (directory URLs)."""
    return urljoin(site_url, src.removesuffix(".md") + "/") if site_url else None


def lab_lines(cv: CV, projects: list[Project]) -> list[PrintLab]:
    return [
        PrintLab(p.meta.title, p.meta.summary, _page_url(cv.basics.url, p.src))
        for p in projects
        if p.meta.kind is Kind.LAB
    ]


def build_cv(cv_file: Path, docs_dir: Path, *, pdf: PdfMode = PdfMode.AUTO) -> CVOutputs:
    """The CV page, the profile values, the home header and the PDF, from one load of the data.

    The PDF is made first, so the page's "Download PDF" button and the profile's "CV (PDF)"
    link appear exactly when the file exists.
    """
    cv = load_cv(cv_file)
    name = pdf_name(cv)
    data, pages, notice = None, 0, None
    if pdf is not PdfMode.OFF:
        html = render_cv_print_html(cv, labs=lab_lines(cv, read_projects(docs_dir)))
        try:
            rendered = render_pdf(html)
        except PDFUnavailable as exc:
            if pdf is PdfMode.REQUIRED:
                raise PDFError(f"{exc}; PORTFOLIO_PDF=required") from exc
            notice = f"PDF skipped: {exc}"
        else:
            if rendered.pages > MAX_PDF_PAGES:
                raise PDFError(f"{name} has {rendered.pages} pages, the limit is {MAX_PDF_PAGES}")
            data, pages = rendered.data, rendered.pages
    return CVOutputs(
        page=render_cv_markdown(cv, pdf_url=name if data else None),
        profile=render_profile_data(cv, pdf_path=f"cv/{name}" if data else None),
        home_header=render_home_header(cv),
        pdf_name=name,
        pdf=data,
        pdf_pages=pages,
        notice=notice,
    )


@dataclass(frozen=True)
class ProjectOutputs:
    index: str  # docs/projects/index.md
    featured: str  # generated/featured-projects.md


def build_projects(docs_dir: Path) -> ProjectOutputs:
    projects = read_projects(docs_dir)
    return ProjectOutputs(index=render_project_index(projects), featured=render_featured(projects))


# Project sync (Phase 006). `fetch(repo, ref, path) -> bytes` is the GitHub adapter in
# production and a dict lookup in tests.
Fetch = Callable[[str, str, str], bytes]


@dataclass(frozen=True)
class SyncedFile:
    path: str  # relative to docs/
    data: bytes


def build_synced_projects(sources: list[ProjectSource], fetch: Fetch) -> list[SyncedFile]:
    """Every file the pinned sources produce: the page, then its media."""
    files = []
    for source in sources:
        card = parse_card(
            fetch(source.repo, source.ref, source.card).decode("utf-8"),
            f"{source.repo}/{source.card}",
        )
        page = render_synced_page(card, source)
        files.append(SyncedFile(source.page, page.encode("utf-8")))
        files += [
            SyncedFile(source.asset(m), fetch(source.repo, source.ref, m)) for m in source.media
        ]
    return files


def drift(files: list[SyncedFile], docs_dir: Path) -> list[str]:
    """Files on disk that differ from what the pinned sources produce."""
    return [
        f.path
        for f in files
        if not (docs_dir / f.path).is_file() or (docs_dir / f.path).read_bytes() != f.data
    ]
