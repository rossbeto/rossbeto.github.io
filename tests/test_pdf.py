"""The CV PDF: the WeasyPrint adapter, and the build's choices around it (modes, page limit)."""

import builtins
import ctypes
import re
from pathlib import Path
from typing import Any

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
import pytest

from portfolio import build
from portfolio.build import MAX_PDF_PAGES, PDFError, PdfMode, build_cv, lab_lines, pdf_name
from portfolio.cv.load import load_cv
from portfolio.cv.render import render_cv_print_html
from portfolio.pdf import PDFUnavailable, RenderedPDF, render_pdf
from portfolio.projects.model import Project, ProjectMeta

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "tests" / "data" / "cv_sample.yml"


def _text(data: bytes) -> str:
    pdf = pdfium.PdfDocument(data)
    return "\n".join(page.get_textpage().get_text_range() for page in pdf)


@pytest.mark.usefixtures("pdf_ready")
def test_the_real_cv_renders_within_the_page_limit() -> None:
    cv = load_cv(ROOT / "data" / "cv.yml")
    out = render_pdf(render_cv_print_html(cv))
    assert 1 <= out.pages <= MAX_PDF_PAGES
    meta = pdfium.PdfDocument(out.data).get_metadata_dict()
    assert meta["Title"] == cv.basics.name
    assert meta["Author"] == cv.basics.name
    text = _text(out.data)
    assert cv.work[0].name in text  # a real text layer, not an image
    assert not re.search(r"[\w.+-]+@[\w-]+\.\w+", text)  # no email on paper either (D-12)
    assert "[X]" not in text


@pytest.mark.usefixtures("pdf_ready")
def test_text_uses_the_bundled_font() -> None:
    out = render_pdf(render_cv_print_html(load_cv(SAMPLE)))
    text_page = pdfium.PdfDocument(out.data)[0].get_textpage()
    name, flags = ctypes.create_string_buffer(128), ctypes.c_int()
    pdfium_c.FPDFText_GetFontInfo(text_page.raw, 0, name, 128, ctypes.byref(flags))
    assert name.value.endswith(b"+Inter")  # a subset of the packaged font, not a system one


def test_missing_system_libraries_become_pdf_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "weasyprint":
            raise OSError("cannot load library 'libpango-1.0-0'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(PDFUnavailable, match="libpango"):
        render_pdf("<p>x</p>")


# The build's decisions, with the renderer replaced (fast, no WeasyPrint needed).


def _fake(pages: int = 2, *, unavailable: bool = False) -> Any:
    def render(html: str) -> RenderedPDF:
        if unavailable:
            raise PDFUnavailable("no Pango")
        assert "<html" in html
        return RenderedPDF(data=b"%PDF-fake", pages=pages)

    return render


def test_pdf_made_adds_the_button_and_the_profile_link(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(build, "render_pdf", _fake())
    out = build_cv(SAMPLE, tmp_path)
    assert out.pdf == b"%PDF-fake"
    assert out.pdf_name == "AdaExample-CV.pdf"
    assert "[Download PDF](AdaExample-CV.pdf)" in out.page
    assert '"pdf": "cv/AdaExample-CV.pdf"' in out.profile


@pytest.mark.parametrize("mode", [PdfMode.AUTO, PdfMode.OFF])
def test_no_pdf_means_no_button_and_no_link(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mode: PdfMode
) -> None:
    monkeypatch.setattr(build, "render_pdf", _fake(unavailable=True))
    out = build_cv(SAMPLE, tmp_path, pdf=mode)
    assert out.pdf is None
    assert "Download PDF" not in out.page
    assert '"pdf"' not in out.profile
    assert (out.notice is not None) is (mode is PdfMode.AUTO)


def test_required_pdf_that_cannot_be_made_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(build, "render_pdf", _fake(unavailable=True))
    with pytest.raises(PDFError, match="required"):
        build_cv(SAMPLE, tmp_path, pdf=PdfMode.REQUIRED)


def test_a_cv_longer_than_the_limit_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(build, "render_pdf", _fake(pages=MAX_PDF_PAGES + 1))
    with pytest.raises(PDFError, match="4 pages"):
        build_cv(SAMPLE, tmp_path)


def _project(src: str, kind: str) -> Project:
    meta = ProjectMeta.model_validate(
        {
            "title": src,
            "summary": "S.",
            "stage": "active",
            "kind": kind,
            "repo": "https://github.com/a/b",
            "tags": ["a"],
        }
    )
    return Project(src=src, meta=meta)


def test_labs_are_the_lab_projects_with_their_site_url() -> None:
    cv = load_cv(SAMPLE)
    labs = lab_lines(cv, [_project("projects/demo.md", "lab"), _project("projects/x.md", "oss")])
    assert [(lab.title, lab.url) for lab in labs] == [
        ("projects/demo.md", "https://example.org/projects/demo/")
    ]
    no_site = cv.model_copy(update={"basics": cv.basics.model_copy(update={"url": None})})
    assert lab_lines(no_site, [_project("projects/demo.md", "lab")])[0].url is None


def test_pdf_name_has_no_spaces() -> None:
    assert pdf_name(load_cv(SAMPLE)) == "AdaExample-CV.pdf"


@pytest.mark.usefixtures("pdf_ready")
def test_markdown_links_print_as_links() -> None:
    out = render_pdf(render_cv_print_html(load_cv(SAMPLE)))
    text = _text(out.data)
    assert "Second paragraph with a link." in text
    assert "](" not in text
