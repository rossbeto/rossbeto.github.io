"""Projects index and home cards: order, badges, private repos, empty state, exact output."""

from typing import Any

from portfolio.projects.index import EMPTY, ordered, render_featured, render_project_index
from portfolio.projects.model import Project, ProjectMeta


def project(slug: str, **over: Any) -> Project:
    data: dict[str, Any] = {
        "title": slug,
        "summary": f"About {slug}.",
        "stage": "active",
        "kind": "lab",
        "repo": f"https://github.com/example/{slug}",
        "tags": ["python", "django"],
    } | over
    return Project(src=f"projects/{slug}.md", meta=ProjectMeta.model_validate(data))


def test_featured_then_order_then_title() -> None:
    ps = [project("c", order=1), project("b"), project("a"), project("z", featured=True, order=9)]
    assert [p.meta.title for p in ordered(ps)] == ["z", "c", "a", "b"]


def test_private_repo_is_never_linked() -> None:
    out = render_project_index([project("secret")])
    assert "github.com/example/secret" not in out
    assert "Repository: publishing soon" in out


def test_public_repo_is_linked() -> None:
    out = render_project_index([project("open", repo_public=True)])
    assert "[Repository](https://github.com/example/open)" in out


def test_kind_badge_labels_labs() -> None:
    assert "Personal lab · active" in render_project_index([project("x")])
    assert "Open source · done" in render_project_index([project("y", kind="oss", stage="done")])


def test_links_are_relative_to_each_page() -> None:
    p = project("demo", featured=True, image="assets/p/demo.png", image_alt="Demo")
    assert "](demo.md)" in render_project_index([p])
    assert "(../assets/p/demo.png)" in render_project_index([p])
    assert "](projects/demo.md)" in render_featured([p])
    assert "(assets/p/demo.png)" in render_featured([p])


def test_featured_only_and_limit() -> None:
    ps = [project(f"p{i}", featured=True, order=i) for i in range(5)] + [project("plain")]
    out = render_featured(ps)
    assert out.count("Case study") == 3
    assert "plain" not in out


def test_empty_states() -> None:
    assert render_featured([project("plain")]) == EMPTY + "\n"
    assert render_project_index([]).endswith(EMPTY + "\n")


def test_golden_card() -> None:
    out = render_featured([project("demo", featured=True)])
    assert out == (
        '<div class="grid cards" markdown>\n'
        "\n"
        "-   **[demo](projects/demo.md)**\n"
        "\n"
        "    Personal lab · active\n"
        "\n"
        "    About demo.\n"
        "\n"
        "    `python` `django`\n"
        "\n"
        "    [:octicons-arrow-right-24: Case study](projects/demo.md)"
        " · Repository: publishing soon\n"
        "\n"
        "</div>\n"
    )
