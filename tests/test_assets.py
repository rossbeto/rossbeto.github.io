"""Image budget: pages stay light (GIFs ≤ 1 MB, other images ≤ 300 KB), alt text on images."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GIF_MAX = 1_000_000
IMAGE_MAX = 300_000
IMAGES = {".gif", ".png", ".jpg", ".jpeg", ".webp", ".svg"}


def test_image_budget() -> None:
    too_big = [
        f"{p.relative_to(ROOT)}: {p.stat().st_size} bytes"
        for p in (ROOT / "docs" / "assets").rglob("*")
        if p.suffix.lower() in IMAGES
        and p.stat().st_size > (GIF_MAX if p.suffix.lower() == ".gif" else IMAGE_MAX)
    ]
    assert too_big == []


def test_every_markdown_image_has_alt_text() -> None:
    no_alt = re.compile(r"!\[\s*\]\(")
    hits = [
        str(p.relative_to(ROOT))
        for p in (ROOT / "docs").rglob("*.md")
        if no_alt.search(p.read_text())
    ]
    assert hits == []
