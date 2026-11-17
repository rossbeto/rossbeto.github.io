"""Use cases: orchestrate the adapters and the pure renderers, return text. No writing."""

from dataclasses import dataclass
from pathlib import Path

from portfolio.blog.frontmatter import read_posts
from portfolio.blog.latest import render_latest
from portfolio.cv.load import load_cv
from portfolio.cv.render import render_cv_markdown, render_home_header, render_profile_data
from portfolio.projects.frontmatter import read_projects
from portfolio.projects.index import render_featured, render_project_index


@dataclass(frozen=True)
class CVOutputs:
    page: str  # docs/cv/index.md
    profile: str  # overrides/partials/profile_data.html
    home_header: str  # generated/home-profile.md


def build_latest_posts(docs_dir: Path, limit: int = 3) -> str:
    return render_latest(read_posts(docs_dir), limit)


def build_cv(cv_file: Path, *, pdf_url: str | None = None) -> CVOutputs:
    cv = load_cv(cv_file)
    return CVOutputs(
        page=render_cv_markdown(cv, pdf_url=pdf_url),
        profile=render_profile_data(cv),
        home_header=render_home_header(cv),
    )


@dataclass(frozen=True)
class ProjectOutputs:
    index: str  # docs/projects/index.md
    featured: str  # generated/featured-projects.md


def build_projects(docs_dir: Path) -> ProjectOutputs:
    projects = read_projects(docs_dir)
    return ProjectOutputs(index=render_project_index(projects), featured=render_featured(projects))
