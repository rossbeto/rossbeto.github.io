"""Media budget: pages stay light (GIFs and videos ≤ 1 MB, other images ≤ 300 KB, fonts
≤ 50 KB each); alt text on images, a label and a caption on videos."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GIF_MAX = 1_000_000
IMAGE_MAX = 300_000
IMAGES = {".gif", ".png", ".jpg", ".jpeg", ".webp", ".svg"}
VIDEOS = {".mp4", ".webm"}
FONT_MAX = 50_000


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


def test_video_and_font_budget() -> None:
    assets = list((ROOT / "docs" / "assets").rglob("*"))
    too_big = [
        f"{p.relative_to(ROOT)}: {p.stat().st_size} bytes"
        for p in assets
        if (p.suffix.lower() in VIDEOS and p.stat().st_size > GIF_MAX)
        or (p.suffix.lower() == ".woff2" and p.stat().st_size > FONT_MAX)
    ]
    assert too_big == []


def test_every_video_has_a_label_and_a_caption() -> None:
    for page in (ROOT / "docs").rglob("*.md"):
        text = page.read_text()
        for video in re.findall(r"<video\b[^>]*>", text):
            assert "aria-label=" in video, page
            assert "muted" in video and "controls" in video, page  # autoplay only when muted
        assert text.count("<video") == text.count("<figcaption>"), page
