"""The portfolio card contract, link rewriting and the synced page."""

from pathlib import Path

import pytest

from portfolio.frontmatter import split_front_matter
from portfolio.projects.card import CardError, parse_card, render_synced_page, rewrite_links
from portfolio.projects.model import ProjectMeta, ProjectSource

CARD = (Path(__file__).resolve().parents[1] / "data" / "portfolio-card.md").read_text()
SHA = "0123456789abcdef0123456789abcdef01234567"
BLOB = f"https://github.com/me/lab/blob/{SHA}"


def _source(kind: str = "lab", **extra: object) -> ProjectSource:
    meta = {"summary": "One line.", "stage": "active", "kind": kind, "tags": ["django"]}
    return ProjectSource.model_validate(
        {
            "slug": "lab",
            "repo": "me/lab",
            "ref": SHA,
            "media": ["docs/media/demo.gif", "docs/media/tlb.gif"],
            "meta": meta,
            **extra,
        }
    )


def test_the_real_tenantlab_card_follows_the_contract() -> None:
    card = parse_card(CARD, "portfolio-card.md")
    assert card.title == "tenantlab: a multi-tenant Django reference app"
    assert card.pitch.startswith("A Django 5.2 app")
    assert "**Hermetic deploys:**" in card.highlights
    assert "Repository:" in card.links


def _without(section: str) -> str:
    start = CARD.index(f"## {section}")
    end = CARD.find("\n## ", start + 1)
    return CARD[:start] + (CARD[end + 1 :] if end != -1 else "")


@pytest.mark.parametrize(
    "section", ["Title", "Pitch", "Media", "Highlights", "Tech stack", "Links"]
)
def test_a_missing_section_is_named(section: str) -> None:
    with pytest.raises(CardError, match=f"missing section\\(s\\): ## {section}"):
        parse_card(_without(section), "card.md")


@pytest.mark.parametrize(
    ("text", "error"),
    [
        (CARD + "\n## Extras\nmore\n", "unknown section '## Extras'"),
        (CARD + "\n## Pitch\nagain\n", "'## Pitch' appears twice"),
        (CARD.replace("## Links\n", "## Links\n<!-- nothing -->\n## Ignored-not\n"), "unknown"),
        (CARD.replace("## Title\n", "## Title\n\n"), None),  # blank lines are fine
    ],
)
def test_contract_errors(text: str, error: str | None) -> None:
    if error is None:
        parse_card(text, "card.md")
        return
    with pytest.raises(CardError, match=error):
        parse_card(text, "card.md")


def test_empty_section_and_multiline_title() -> None:
    empty = CARD.replace(
        CARD[CARD.index("## Tech stack") : CARD.index("## Links")], "## Tech stack\n\n"
    )
    with pytest.raises(CardError, match="empty section\\(s\\): ## Tech stack"):
        parse_card(empty, "card.md")
    with pytest.raises(CardError, match="one line"):
        parse_card(CARD.replace("## Title\n", "## Title\nline one\n"), "card.md")


@pytest.mark.parametrize(
    ("markdown", "expected"),
    [
        ("[a](architecture.md)", f"[a]({BLOB}/docs/architecture.md)"),
        ("[r](../README.md)", f"[r]({BLOB}/README.md)"),
        ("[s](notes.md#2-the-301)", f"[s]({BLOB}/docs/notes.md#2-the-301)"),
        ("[`x.py`](../e2e/x.py)", f"[`x.py`]({BLOB}/e2e/x.py)"),
        ("![Demo](media/demo.gif)", "![Demo](../assets/projects/lab/demo.gif)"),
        ("[ext](https://example.org/a)", "[ext](https://example.org/a)"),
        ("[top](#links)", "[top](#links)"),
        ("plain text", "plain text"),
    ],
)
def test_links_are_rewritten_for_the_site(markdown: str, expected: str) -> None:
    assert rewrite_links(markdown, _source()) == expected


@pytest.mark.parametrize(
    ("markdown", "error"),
    [
        ("![x](media/other.gif)", "not listed in `media`"),
        ("![x](https://example.org/x.gif)", "no hotlinks"),
        ("[x](../../etc/passwd)", "outside the repository"),
    ],
)
def test_unsafe_links_are_refused(markdown: str, error: str) -> None:
    with pytest.raises(CardError, match=error):
        rewrite_links(markdown, _source())


def test_synced_page_front_matter_is_a_valid_project() -> None:
    page = render_synced_page(parse_card(CARD, "card.md"), _source())
    meta = ProjectMeta.model_validate(split_front_matter(page, "lab.md"))
    assert meta.title == "tenantlab: a multi-tenant Django reference app"
    assert meta.repo == "https://github.com/me/lab"
    assert meta.repo_public is True
    assert f"me/lab@{SHA[:12]}" in page  # the generated-from comment
    assert '!!! info "A personal lab"' in page
    assert "![Demo: framing allowed" in page and "{ loading=lazy }" in page
    assert "## Highlights" in page and "## Tech stack" in page and "## Links" in page


def test_only_labs_get_the_lab_note_and_images_carry_through() -> None:
    page = render_synced_page(
        parse_card(CARD, "card.md"),
        _source("oss", **{}),
    )
    assert "A personal lab" not in page
    with_image = _source()
    meta = with_image.meta.model_copy(update={"image": "assets/p.png", "image_alt": "P"})
    page = render_synced_page(
        parse_card(CARD, "card.md"), with_image.model_copy(update={"meta": meta})
    )
    assert 'image: "assets/p.png"' in page


def test_media_without_extra_bullets() -> None:
    card = parse_card(CARD, "card.md")
    only_images = card.__class__(**{**card.__dict__, "media": "- ![Demo](media/demo.gif)"})
    page = render_synced_page(only_images, _source())
    assert "![Demo](../assets/projects/lab/demo.gif){ loading=lazy }\n\n## Highlights" in page
