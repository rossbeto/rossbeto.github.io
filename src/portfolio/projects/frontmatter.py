"""Adapter: read project pages' front matter from docs/projects/."""

from pathlib import Path

from portfolio.frontmatter import FrontMatterError, split_front_matter
from portfolio.projects.model import Project, ProjectMeta


def read_projects(docs_dir: Path, projects_dir: str = "projects") -> list[Project]:
    """Every `docs/projects/*.md` except the generated `index.md`."""
    projects = []
    for path in sorted((docs_dir / projects_dir).glob("*.md")):
        if path.name == "index.md":
            continue
        src = path.relative_to(docs_dir).as_posix()
        data = split_front_matter(path.read_text(encoding="utf-8"), src)
        try:
            meta = ProjectMeta.model_validate(data)
        except ValueError as exc:
            raise FrontMatterError(f"{src}: {exc}") from exc
        projects.append(Project(src=src, meta=meta))
    return projects
