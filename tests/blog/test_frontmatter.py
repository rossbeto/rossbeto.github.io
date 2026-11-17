"""Adapter: reading posts from disk, with errors that name the file."""

from pathlib import Path

import pytest

from portfolio.blog.frontmatter import FrontMatterError, read_posts, split_front_matter

GOOD = """---
date: 2026-11-17
slug: hello
title: Hello
description: First post.
authors: [lam]
categories: [Django]
tags: [a, b]
---

# Hello
"""


def write(docs: Path, name: str, text: str) -> None:
    (docs / "blog" / "posts").mkdir(parents=True, exist_ok=True)
    (docs / "blog" / "posts" / name).write_text(text)


def test_reads_posts_and_skips_templates(tmp_path: Path) -> None:
    write(tmp_path, "hello.md", GOOD)
    write(tmp_path, "_template.md.example", "not front matter")
    [only] = read_posts(tmp_path)
    assert (only.src, only.meta.slug) == ("blog/posts/hello.md", "hello")


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("# no front matter\n", "first line"),
        ("---\ntitle: x\n", "not closed"),
        ("---\n- a list\n---\n", "not a mapping"),
    ],
)
def test_broken_front_matter(text: str, message: str) -> None:
    with pytest.raises(FrontMatterError, match=message):
        split_front_matter(text, "x.md")


def test_invalid_meta_names_the_file(tmp_path: Path) -> None:
    write(tmp_path, "bad.md", GOOD.replace("title: Hello", "title: '[X] wins'"))
    with pytest.raises(FrontMatterError, match=r"(?s)blog/posts/bad\.md.*placeholder"):
        read_posts(tmp_path)
