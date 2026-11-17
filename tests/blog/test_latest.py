"""The home page's latest-posts list: order, drafts, limit, empty state, exact output."""

import datetime as dt

from portfolio.blog.latest import EMPTY, latest, render_latest
from portfolio.blog.model import Post, PostMeta


def post(title: str, day: int, *, draft: bool = False) -> Post:
    slug = title.lower().replace(" ", "-")
    meta = PostMeta(
        date=dt.date(2026, 11, day),
        slug=slug,
        title=title,
        description=f"About {title}.",
        authors=["lam"],
        categories=["Django"],
        tags=["a", "b"],
        draft=draft,
    )
    return Post(src=f"blog/posts/{slug}.md", meta=meta)


def titles(posts: list[Post]) -> list[str]:
    return [p.meta.title for p in posts]


def test_newest_first_then_title_on_the_same_day() -> None:
    posts = [post("Old", 1), post("Beta", 9), post("Alpha", 9)]
    assert titles(latest(posts)) == ["Alpha", "Beta", "Old"]


def test_drafts_are_never_listed() -> None:
    assert titles(latest([post("Draft", 20, draft=True), post("Live", 1)])) == ["Live"]


def test_limit() -> None:
    posts = [post(f"P{d}", d) for d in range(1, 6)]
    assert titles(latest(posts, limit=3)) == ["P5", "P4", "P3"]


def test_empty_list_renders_a_friendly_line() -> None:
    assert render_latest([post("Draft", 2, draft=True)]) == EMPTY + "\n"


def test_golden_output() -> None:
    out = render_latest([post("First", 3), post("Second", 17)])
    assert out == (
        "- **[Second](blog/posts/second.md)** · 17 Nov 2026  \n"
        "  About Second.\n"
        "- **[First](blog/posts/first.md)** · 3 Nov 2026  \n"
        "  About First.\n"
    )
