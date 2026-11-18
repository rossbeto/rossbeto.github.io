"""The portfolio card contract and the synced project page. Pure: Markdown in, Markdown out.

A card (`docs/portfolio-card.md` in a project repo) has exactly these `##` sections, in any
order: Title, Pitch, Media, Highlights, Tech stack, Links. Links are rewritten for the site:
repo-relative links point at the file on GitHub at the pinned commit; images must be listed in
the source's `media` and point at their copy under `docs/assets/projects/<slug>/`.
"""

import json
import posixpath
import re
from dataclasses import dataclass

from portfolio.projects.model import Kind, ProjectSource

SECTIONS = ("Title", "Pitch", "Media", "Highlights", "Tech stack", "Links")
_HEADING = re.compile(r"^## +(.+?) *$", re.MULTILINE)
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_LINK = re.compile(r"(!?)\[((?:[^\[\]]|\[[^\]]*\])*)\]\(([^)\s]+)\)")
_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)
_IMAGE_ITEM = re.compile(r"^- +(!\[[^\]]*\]\([^)\s]+\)) *$")

LAB_NOTE = (
    '!!! info "A personal lab"\n'
    "    I built this on my own time to work through problems I find interesting. Numbers on\n"
    "    this page are test numbers, not production traffic.\n"
)


class CardError(ValueError):
    """The card breaks the contract; the message names the card and the problem."""


@dataclass(frozen=True)
class Card:
    title: str
    pitch: str
    media: str
    highlights: str
    tech: str
    links: str


def parse_card(text: str, name: str) -> Card:
    body = _COMMENT.sub("", text)
    parts = _HEADING.split(body)  # [before, heading, content, heading, content, ...]
    found: dict[str, str] = {}
    for heading, content in zip(parts[1::2], parts[2::2], strict=True):
        if heading not in SECTIONS:
            raise CardError(f"{name}: unknown section '## {heading}' (expected {SECTIONS})")
        if heading in found:
            raise CardError(f"{name}: section '## {heading}' appears twice")
        found[heading] = content.strip()
    missing = [s for s in SECTIONS if s not in found]
    if missing:
        raise CardError(f"{name}: missing section(s): {', '.join('## ' + s for s in missing)}")
    empty = [s for s in SECTIONS if not found[s]]
    if empty:
        raise CardError(f"{name}: empty section(s): {', '.join('## ' + s for s in empty)}")
    if "\n" in found["Title"]:
        raise CardError(f"{name}: '## Title' must be one line")
    return Card(
        title=found["Title"],
        pitch=found["Pitch"],
        media=found["Media"],
        highlights=found["Highlights"],
        tech=found["Tech stack"],
        links=found["Links"],
    )


def rewrite_links(markdown: str, source: ProjectSource) -> str:
    """Repo-relative links → GitHub at the pinned commit; images → the copied asset."""
    card_dir = posixpath.dirname(source.card)
    page_dir = posixpath.dirname(source.page)

    def replace(match: re.Match[str]) -> str:
        bang, text, target = match.groups()
        if _SCHEME.match(target) or target.startswith("#"):
            if bang:
                raise CardError(f"{source.card}: image {target!r} is not a repo file (no hotlinks)")
            return match.group(0)
        path, _, fragment = target.partition("#")
        resolved = posixpath.normpath(posixpath.join(card_dir, path))
        if resolved.startswith(".."):
            raise CardError(f"{source.card}: link {target!r} points outside the repository")
        if bang:
            if resolved not in source.media:
                raise CardError(f"{source.card}: image {resolved!r} is not listed in `media`")
            return f"![{text}]({posixpath.relpath(source.asset(resolved), page_dir)})"
        url = f"https://github.com/{source.repo}/blob/{source.ref}/{resolved}"
        return f"[{text}]({url}{'#' + fragment if fragment else ''})"

    return _LINK.sub(replace, markdown)


def _media_block(media: str) -> str:
    """Image bullets become full-width images; the other bullets stay a list under them."""
    images, rest = [], []
    for line in media.splitlines():
        m = _IMAGE_ITEM.match(line)
        if m:
            images.append(m.group(1) + "{ loading=lazy }")
        elif line.strip():
            rest.append(line)
    return "\n\n".join([*images, "\n".join(rest)] if rest else images)


def _scalar(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)  # JSON scalars and lists are valid YAML


def render_synced_page(card: Card, source: ProjectSource) -> str:
    m = source.meta
    fields: dict[str, object] = {
        "title": card.title,
        "summary": m.summary,
        "description": m.summary,
        "stage": m.stage.value,
        "kind": m.kind.value,
        "repo": f"https://github.com/{source.repo}",
        "repo_public": True,  # sync reads public repos only
        **({"image": m.image, "image_alt": m.image_alt} if m.image else {}),
        "tags": m.tags,
        "featured": m.featured,
        "order": m.order,
    }
    front = "\n".join(f"{k}: {_scalar(v)}" for k, v in fields.items())
    sections = [
        f"---\n{front}\n---",
        f"<!-- Generated by `portfolio sync-projects` from {source.repo}@{source.ref[:12]} "
        f"({source.card}): edit the card there, then sync. -->",
        f"# {card.title}",
        *([LAB_NOTE.rstrip()] if m.kind is Kind.LAB else []),
        rewrite_links(card.pitch, source),
        _media_block(rewrite_links(card.media, source)),
        "## Highlights\n\n" + rewrite_links(card.highlights, source),
        "## Tech stack\n\n" + rewrite_links(card.tech, source),
        "## Links\n\n" + rewrite_links(card.links, source),
    ]
    return "\n\n".join(sections) + "\n"
