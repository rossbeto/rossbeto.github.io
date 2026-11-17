"""PostMeta enforces the review checklist's mechanical rules."""

import datetime as dt
from typing import Any

import pytest
from pydantic import ValidationError

from portfolio.blog.model import PostMeta


def meta(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "date": "2026-11-17",
        "slug": "a-post",
        "title": "A post",
        "description": "One sentence.",
        "authors": ["lam"],
        "categories": ["Django"],
        "tags": ["testing", "django"],
    }
    return base | over


def test_valid_front_matter() -> None:
    m = PostMeta.model_validate(meta())
    assert m.date == dt.date(2026, 11, 17)
    assert m.draft is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", "x" * 61),
        ("description", "x" * 156),
        ("tags", ["one"]),
        ("tags", ["a", "b", "c", "d", "e", "f"]),
        ("categories", []),
        ("authors", []),
        ("slug", "Not A Slug"),
        ("date", "someday"),
    ],
)
def test_rejects_values_outside_the_checklist(field: str, value: object) -> None:
    with pytest.raises(ValidationError, match=field):
        PostMeta.model_validate(meta(**{field: value}))


def test_rejects_unknown_keys() -> None:
    with pytest.raises(ValidationError, match="subtitle"):
        PostMeta.model_validate(meta(subtitle="typo"))


@pytest.mark.parametrize("field", ["title", "description"])
def test_rejects_placeholders(field: str) -> None:
    with pytest.raises(ValidationError, match="placeholder"):
        PostMeta.model_validate(meta(**{field: "Cut costs by [X] %"}))
