"""ProjectMeta: the card's rules are enforced at generate time."""

from typing import Any

import pytest
from pydantic import ValidationError

from portfolio.projects.model import Kind, ProjectMeta


def meta(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "title": "demo: a thing",
        "summary": "Short summary.",
        "stage": "active",
        "kind": "lab",
        "repo": "https://github.com/example/demo",
        "tags": ["python"],
    }
    return base | over


def test_valid_meta_and_defaults() -> None:
    m = ProjectMeta.model_validate(meta())
    assert (m.kind, m.repo_public, m.featured, m.order) == (Kind.LAB, False, False, 100)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("summary", "x" * 161),
        ("title", "x" * 61),
        ("stage", "paused"),
        ("kind", "hobby"),
        ("repo", "https://gitlab.com/a/b"),
        ("tags", []),
        ("tags", [str(i) for i in range(9)]),
        ("image", "../secret.png"),
        ("image", "img/x.png"),
    ],
)
def test_rejects_bad_values(field: str, value: object) -> None:
    with pytest.raises(ValidationError, match=field):
        ProjectMeta.model_validate(meta(**{field: value}))


def test_unknown_key() -> None:
    with pytest.raises(ValidationError, match="feature"):
        ProjectMeta.model_validate(meta(feature=True))


def test_placeholder() -> None:
    with pytest.raises(ValidationError, match="placeholder"):
        ProjectMeta.model_validate(meta(summary="Serves [N] users"))


def test_image_needs_alt_text() -> None:
    with pytest.raises(ValidationError, match="image_alt"):
        ProjectMeta.model_validate(meta(image="assets/x.png"))


def test_status_key_is_refused() -> None:
    # Material reads `status` as a page-status badge (an icon in the nav): use `stage`.
    with pytest.raises(ValidationError, match="status"):
        ProjectMeta.model_validate(meta(status="active"))
