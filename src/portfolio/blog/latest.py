"""Render the home page's "Latest posts" list. Pure: posts in, Markdown out."""

from collections.abc import Iterable

from portfolio.blog.model import Post

EMPTY = "The first posts are on their way."


def latest(posts: Iterable[Post], limit: int = 3) -> list[Post]:
    """Published posts, newest first; same day → by title, so the order is stable."""
    published = [p for p in posts if not p.meta.draft]
    by_title = sorted(published, key=lambda p: p.meta.title)
    return sorted(by_title, key=lambda p: p.meta.date, reverse=True)[:limit]


def render_latest(posts: Iterable[Post], limit: int = 3) -> str:
    """Markdown included by docs/index.md. Links point at the post sources, so
    `mkdocs build --strict` checks them."""
    chosen = latest(posts, limit)
    if not chosen:
        return EMPTY + "\n"
    lines = []
    for post in chosen:
        d = post.meta.date
        lines.append(
            f"- **[{post.meta.title}]({post.src})** · {d.day} {d:%b %Y}  \n"
            f"  {post.meta.description}"
        )
    return "\n".join(lines) + "\n"
