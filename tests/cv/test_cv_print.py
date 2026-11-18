"""The printable CV (HTML for the PDF): golden file, web-only entries, escaping, links as text."""

import os
import re
from pathlib import Path

import pytest

from portfolio.cv.load import load_cv
from portfolio.cv.model import CV
from portfolio.cv.render import PrintLab, display_url, md_links, render_cv_print_html

HERE = Path(__file__).resolve().parents[1]
GOLDEN = HERE / "golden" / "cv_print.html"
LABS = [PrintLab("demo: a lab", "It shows things.", "https://example.org/projects/demo/")]


@pytest.fixture
def cv() -> CV:
    return load_cv(HERE / "data" / "cv_sample.yml")


def test_golden_print_html(cv: CV) -> None:
    # The stylesheet is left out: layout is checked by looking at the PDF, not by a diff.
    out = re.sub(r"(?s)<style>.*</style>", "<style>…</style>", render_cv_print_html(cv, labs=LABS))
    if os.environ.get("UPDATE_GOLDEN"):
        GOLDEN.write_text(out)
    assert out == GOLDEN.read_text(), "run UPDATE_GOLDEN=1 pytest to refresh after a review"


def test_web_only_and_hidden_entries_are_not_printed(cv: CV) -> None:
    out = render_cv_print_html(cv)
    for absent in ("Web only skill", "Web only tools", "Nope", "contact?x=1", "Draft skill"):
        assert absent not in out
    assert "Secret Co" not in out
    assert "Work skill" in out  # the rest is there


def test_values_are_escaped(cv: CV) -> None:
    risky = cv.model_copy(
        update={"basics": cv.basics.model_copy(update={"name": "Ada <script> & Co"})}
    )
    out = render_cv_print_html(risky)
    assert "<title>Ada &lt;script&gt; &amp; Co</title>" in out
    assert "<script>" not in out


def test_links_are_printed_as_readable_text(cv: CV) -> None:
    out = render_cv_print_html(cv, labs=LABS)
    assert '<a href="https://example.org/">example.org</a>' in out  # basics.url first
    assert '<a href="https://github.com/example">github.com/example</a>' in out
    assert ">example.org/projects/demo</a>" in out


def test_metadata_comes_from_the_data(cv: CV) -> None:
    out = render_cv_print_html(cv)
    assert '<meta name="author" content="Ada Example">' in out
    assert '<meta name="keywords" content="Python, C|D, AWS">' in out  # printed skills only


def test_lab_note_only_when_a_printed_capability_is_from_a_lab(cv: CV) -> None:
    assert "shown in a personal lab" in render_cv_print_html(cv)
    no_labs = cv.model_copy(update={"capabilities": cv.capabilities[:1]})
    assert "shown in a personal lab" not in render_cv_print_html(no_labs)


@pytest.mark.parametrize(
    ("url", "shown"),
    [
        ("https://www.linkedin.com/in/someone/", "linkedin.com/in/someone"),
        ("http://example.org", "example.org"),
        ("https://github.com/a/b", "github.com/a/b"),
    ],
)
def test_display_url(url: str, shown: str) -> None:
    assert display_url(url) == shown


def test_md_links_escape_text_and_keep_links() -> None:
    out = md_links("A <b> & [site](https://example.org/a?b=1&c=2) [not a link](javascript:x)")
    assert out == (
        'A &lt;b&gt; &amp; <a href="https://example.org/a?b=1&amp;c=2">site</a>'
        " [not a link](javascript:x)"
    )
