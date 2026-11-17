"""The CV model and loader: valid data loads; every kind of bad data names its path."""

from pathlib import Path

import pytest
import yaml

from portfolio.cv.load import CVError, load_cv
from portfolio.cv.model import month_label

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "cv_sample.yml"
REAL = Path(__file__).resolve().parents[2] / "data" / "cv.yml"


def write_variant(tmp_path: Path, change: str, old: str = "", new: str = "") -> Path:
    text = SAMPLE.read_text()
    if old:
        assert old in text, old
        text = text.replace(old, new, 1)
    path = tmp_path / f"{change}.yml"
    path.write_text(text)
    return path


def test_sample_and_real_cv_load() -> None:
    cv = load_cv(SAMPLE)
    assert cv.basics.name == "Ada Example"
    assert cv.work[0].period == "Mar 2020 – Present"
    assert load_cv(REAL).work[0].start  # the published data is valid


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("label: Backend Engineer", "label: Backend Engineer\n  email: a@b.c", "basics.email"),
        ("startDate: 2020-03", "startDate: 2020-13", "work[0].startDate"),
        ("startDate: 2020-03", "startDate: March 2020", "expected YYYY-MM"),
        ("endDate: 2020-02", "endDate: 2009-02", "before startDate"),
        ("highlights: [Shipped it.]", "highlights: []", "work[1].highlights"),
        ("proof: projects/demo.md", "proof: /projects/demo", "page path under docs/"),
        ("text: Something new.", "text: 'Saved [X] % of costs'", "x_recent[0].text"),
        ("Did another thing.", "'Grew users to [N] million'", "work[0].highlights[1]"),
    ],
)
def test_invalid_data_names_the_field(tmp_path: Path, old: str, new: str, message: str) -> None:
    with pytest.raises(CVError, match=message.replace("[", r"\[").replace(".", r"\.")):
        load_cv(write_variant(tmp_path, "bad", old, new))


def test_markdown_links_are_not_placeholders() -> None:
    assert "[link](https://example.org)" in load_cv(SAMPLE).basics.summary[1]


def test_all_problems_are_listed_at_once(tmp_path: Path) -> None:
    data = yaml.safe_load(SAMPLE.read_text())
    data["work"][0]["startDate"] = "bad"
    data["work"][1]["endDate"] = "worse"
    path = tmp_path / "two.yml"
    path.write_text(yaml.safe_dump(data))
    with pytest.raises(CVError, match="2 problem"):
        load_cv(path)


@pytest.mark.parametrize("text", ["", "a: [unclosed", "- just\n- a list\n"])
def test_unreadable_or_wrong_shape(tmp_path: Path, text: str) -> None:
    path = tmp_path / "x.yml"
    path.write_text(text)
    with pytest.raises(CVError, match=r"x\.yml"):
        load_cv(path)


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(CVError, match="nope"):
        load_cv(tmp_path / "nope.yml")


def test_month_label() -> None:
    assert (month_label("2006-06"), month_label(None)) == ("Jun 2006", "Present")
