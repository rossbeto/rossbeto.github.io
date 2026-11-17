"""Adapter: read posts from disk (the only module here that touches files or YAML)."""

from pathlib import Path

import yaml

from portfolio.blog.model import Post, PostMeta

FENCE = "---"


class FrontMatterError(ValueError):
    """A post without a readable front-matter block; the message names the file."""


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


def read_posts(docs_dir: Path, posts_dir: str = "blog/posts") -> list[Post]:
    """Every `*.md` under docs/blog/posts (templates end in `.example` and are skipped)."""
    posts = []
    for path in sorted((docs_dir / posts_dir).glob("*.md")):
        src = path.relative_to(docs_dir).as_posix()
        data = split_front_matter(path.read_text(encoding="utf-8"), src)
        try:
            meta = PostMeta.model_validate(data)
        except ValueError as exc:
            raise FrontMatterError(f"{src}: {exc}") from exc
        posts.append(Post(src=src, meta=meta))
    return posts
