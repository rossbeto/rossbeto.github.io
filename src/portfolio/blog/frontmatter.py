"""Adapter: read posts from disk."""

from pathlib import Path

from portfolio.blog.model import Post, PostMeta
from portfolio.frontmatter import FrontMatterError, split_front_matter

__all__ = ["FrontMatterError", "read_posts", "split_front_matter"]


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
