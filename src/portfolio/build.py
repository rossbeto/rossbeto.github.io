"""Use cases: orchestrate the adapters and the pure renderers, return text. No writing."""

from pathlib import Path

from portfolio.blog.frontmatter import read_posts
from portfolio.blog.latest import render_latest


def build_latest_posts(docs_dir: Path, limit: int = 3) -> str:
    return render_latest(read_posts(docs_dir), limit)
