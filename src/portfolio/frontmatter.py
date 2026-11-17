"""Adapter: the YAML front-matter block of a Markdown file (shared by posts and projects)."""

import yaml

FENCE = "---"


class FrontMatterError(ValueError):
    """A content file with unreadable or invalid front matter; the message names the file."""


def split_front_matter(text: str, name: str) -> dict[str, object]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != FENCE:
        raise FrontMatterError(f"{name}: no front matter (the first line must be '---')")
    try:
        end = next(i for i, line in enumerate(lines[1:], 1) if line.strip() == FENCE)
    except StopIteration:
        raise FrontMatterError(f"{name}: front matter is not closed with '---'") from None
    data = yaml.safe_load("\n".join(lines[1:end])) or {}
    if not isinstance(data, dict):
        raise FrontMatterError(f"{name}: front matter is not a mapping")
    return data
