"""Adapter: reading posts from disk, with errors that name the file."""

from pathlib import Path

import pytest

from portfolio.blog.frontmatter import FrontMatterError, read_posts, split_front_matter
from portfolio.cli import main

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


def test_cli_generate_writes_the_list(tmp_path: Path) -> None:
    write(tmp_path / "docs", "hello.md", GOOD)
    assert main(["generate", "--root", str(tmp_path)]) == 0
    out = (tmp_path / "generated" / "latest-posts.md").read_text()
    assert "[Hello](blog/posts/hello.md)" in out


def test_cli_generate_fails_cleanly(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path / "docs", "bad.md", "no front matter")
    assert main(["generate", "--root", str(tmp_path)]) == 1
    assert "bad.md" in capsys.readouterr().err
