"""Adapter: read `data/projects.yml`, the list of synced project repos."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from portfolio.projects.model import ProjectSource


class SourceError(ValueError):
    """`data/projects.yml` is unreadable or invalid; the message names the entry."""


def load_sources(path: Path) -> list[ProjectSource]:
    """No file, or `sources: []`, means nothing to sync."""
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict) or set(data) - {"sources"}:
        raise SourceError(f"{path.name}: expected a mapping with one key, `sources`")
    sources = []
    for i, entry in enumerate(data.get("sources") or []):
        try:
            sources.append(ProjectSource.model_validate(entry))
        except ValidationError as exc:
            raise SourceError(f"{path.name}: sources[{i}]: {exc}") from exc
    slugs = [s.slug for s in sources]
    if len(set(slugs)) != len(slugs):
        raise SourceError(f"{path.name}: duplicate slugs in {slugs}")
    return sources


def bump_ref(path: Path, old: str, new: str) -> None:
    """Replace one pinned SHA in place, keeping the file's comments and layout."""
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SourceError(f"{path.name}: ref {old} must appear exactly once")
    path.write_text(text.replace(old, new), encoding="utf-8")
