"""Adapter: project pages are read from docs/projects/, the generated index is skipped."""

from pathlib import Path

import pytest

from portfolio.frontmatter import FrontMatterError
from portfolio.projects.frontmatter import read_projects

PAGE = """---
title: demo
summary: A demo.
stage: done
kind: oss
repo: https://github.com/example/demo
tags: [python]
---

# demo
"""


def test_reads_pages_and_skips_the_index(tmp_path: Path) -> None:
    (tmp_path / "projects").mkdir()
    (tmp_path / "projects" / "demo.md").write_text(PAGE)
    (tmp_path / "projects" / "index.md").write_text("# generated")
    [only] = read_projects(tmp_path)
    assert (only.src, only.meta.title) == ("projects/demo.md", "demo")


def test_invalid_page_names_the_file(tmp_path: Path) -> None:
    (tmp_path / "projects").mkdir()
    (tmp_path / "projects" / "bad.md").write_text(PAGE.replace("stage: done", "stage: maybe"))
    with pytest.raises(FrontMatterError, match=r"(?s)projects/bad\.md.*stage"):
        read_projects(tmp_path)
