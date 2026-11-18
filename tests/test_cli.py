"""`portfolio generate`: writes every output from a valid project; fails cleanly otherwise."""

import shutil
from pathlib import Path

import pytest

from portfolio import build
from portfolio.cli import main
from portfolio.pdf import PDFUnavailable, RenderedPDF

HERE = Path(__file__).resolve().parent
POST = """---
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


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "data").mkdir()
    shutil.copy(HERE / "data" / "cv_sample.yml", tmp_path / "data" / "cv.yml")
    posts = tmp_path / "docs" / "blog" / "posts"
    posts.mkdir(parents=True)
    (posts / "hello.md").write_text(POST)
    return tmp_path


def test_generate_writes_every_output(root: Path) -> None:
    assert main(["generate", "--root", str(root), "--pdf", "off"]) == 0
    assert "# Ada Example" in (root / "docs" / "cv" / "index.md").read_text()
    assert '"name": "Ada Example"' in (root / "overrides/partials/profile_data.html").read_text()
    assert "Backend Engineer · Penang" in (root / "generated" / "home-profile.md").read_text()
    assert "[Hello](blog/posts/hello.md)" in (root / "generated" / "latest-posts.md").read_text()


def test_bad_post_fails_cleanly_and_writes_nothing(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (root / "docs" / "blog" / "posts" / "bad.md").write_text("no front matter")
    assert main(["generate", "--root", str(root)]) == 1
    assert "bad.md" in capsys.readouterr().err
    assert not (root / "docs" / "cv" / "index.md").exists()


def test_bad_cv_fails_with_the_field_path(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cv = root / "data" / "cv.yml"
    cv.write_text(cv.read_text().replace("Did a thing.", "'Saved [X] %'"))
    assert main(["generate", "--root", str(root)]) == 1
    assert "work[0].highlights[0]" in capsys.readouterr().err


def test_pdf_is_written_next_to_the_cv_page(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(build, "render_pdf", lambda html: RenderedPDF(b"%PDF-fake", 2))
    assert main(["generate", "--root", str(root)]) == 0
    assert (root / "docs" / "cv" / "AdaExample-CV.pdf").read_bytes() == b"%PDF-fake"
    assert "[Download PDF](AdaExample-CV.pdf)" in (root / "docs" / "cv" / "index.md").read_text()


def test_skipped_pdf_removes_a_stale_one_and_warns(
    root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    stale = root / "docs" / "cv" / "AdaExample-CV.pdf"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"old")

    def unavailable(html: str) -> RenderedPDF:
        raise PDFUnavailable("no Pango")

    monkeypatch.setattr(build, "render_pdf", unavailable)
    assert main(["generate", "--root", str(root)]) == 0
    assert not stale.exists()
    assert "warning: PDF skipped: no Pango" in capsys.readouterr().err
    assert "Download PDF" not in (root / "docs" / "cv" / "index.md").read_text()


def test_required_pdf_fails_cleanly(
    root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def unavailable(html: str) -> RenderedPDF:
        raise PDFUnavailable("no Pango")

    monkeypatch.setattr(build, "render_pdf", unavailable)
    monkeypatch.setenv("PORTFOLIO_PDF", "required")
    assert main(["generate", "--root", str(root)]) == 1
    assert "PORTFOLIO_PDF=required" in capsys.readouterr().err
    assert not (root / "docs" / "cv" / "index.md").exists()


def test_pdf_off_skips_quietly(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["generate", "--root", str(root), "--pdf", "off"]) == 0
    assert not (root / "docs" / "cv" / "AdaExample-CV.pdf").exists()
    assert "warning" not in capsys.readouterr().err
