"""CV rendering: golden page, hidden entries, lab links, the profile and home header."""

import os
from pathlib import Path

import pytest
from jinja2 import Environment

from portfolio.cv.load import load_cv
from portfolio.cv.model import CV
from portfolio.cv.render import (
    profile_context,
    render_cv_markdown,
    render_home_header,
    render_profile_data,
)

HERE = Path(__file__).resolve().parents[1]
GOLDEN = HERE / "golden" / "cv.md"


@pytest.fixture
def cv() -> CV:
    return load_cv(HERE / "data" / "cv_sample.yml")


def test_golden_page(cv: CV) -> None:
    out = render_cv_markdown(cv)
    if os.environ.get("UPDATE_GOLDEN"):
        GOLDEN.write_text(out)
    assert out == GOLDEN.read_text(), "run UPDATE_GOLDEN=1 pytest to refresh after a review"


def test_hidden_entries_are_not_rendered(cv: CV) -> None:
    out = render_cv_markdown(cv)
    assert "Draft skill" not in out
    assert "Secret Co" not in out


def test_lab_badge_links_relative_to_the_cv_page(cv: CV) -> None:
    out = render_cv_markdown(cv)
    assert "**Lab skill** [lab](../projects/demo.md)" in out
    assert "**Work skill**:" in out  # no badge on paid work


def test_pdf_button_only_when_there_is_a_pdf(cv: CV) -> None:
    assert "Download PDF" not in render_cv_markdown(cv)
    assert "[Download PDF](cv.pdf)" in render_cv_markdown(cv, pdf_url="cv.pdf")


def test_table_cells_are_escaped(cv: CV) -> None:
    assert "Python, C\\|D" in render_cv_markdown(cv)


def test_profile_data_is_a_jinja_set_the_theme_can_import(cv: CV) -> None:
    env = Environment(autoescape=True)
    module = env.from_string(render_profile_data(cv)).module
    assert module.profile == profile_context(cv)  # type: ignore[attr-defined]
    assert module.profile["links"][0]["icon"] == "fontawesome/brands/github"  # type: ignore[attr-defined]


def test_profile_data_refuses_jinja_delimiters(cv: CV) -> None:
    bad = cv.model_copy(update={"basics": cv.basics.model_copy(update={"name": "{{ evil }}"})})
    with pytest.raises(ValueError, match="Jinja"):
        render_profile_data(bad)


def test_home_header_escapes_html(cv: CV) -> None:
    odd = cv.model_copy(update={"basics": cv.basics.model_copy(update={"label": "A <b> & C"})})
    assert "A &lt;b&gt; &amp; C · Penang" in render_home_header(odd)
