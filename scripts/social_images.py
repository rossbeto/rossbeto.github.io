"""Render the share-preview card and the touch icon (PNG) from data/cv.yml.

    make social-images     # HTML here, screenshots in the Playwright container

Step 1 (`html`, on the host): writes .cache/social/{card,icon}.html from the CV data.
Step 2 (`shoot`, in mcr.microsoft.com/playwright/python): screenshots them into
docs/assets/img/social-card.png (1200x630, what LinkedIn and others show) and
docs/assets/img/apple-touch-icon.png (180x180). The PNGs are committed; re-run after changing
the name, label or tagline. Fonts come from docs/assets/fonts (no network).
"""

import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".cache" / "social"
IMG = ROOT / "docs" / "assets" / "img"
SIZES = {"card": (1200, 630), "icon": (180, 180)}

FONTS = """
@font-face { font-family: Inter; font-weight: 400; src: url("../../docs/assets/fonts/inter-latin-400-normal.woff2"); }
@font-face { font-family: Inter; font-weight: 700; src: url("../../docs/assets/fonts/inter-latin-700-normal.woff2"); }
@font-face { font-family: Mono; src: url("../../docs/assets/fonts/jetbrains-mono-latin-400-normal.woff2"); }
html, body { margin: 0; }
"""


def _page(body: str, css: str, size: tuple[int, int]) -> str:
    w, h = size
    return (
        f'<!doctype html><meta charset="utf-8"><style>{FONTS}'
        f"body {{ width: {w}px; height: {h}px; overflow: hidden; }} {css}</style>{body}"
    )


def write_html() -> None:
    import yaml  # noqa: PLC0415  (host step only)

    basics = yaml.safe_load((ROOT / "data" / "cv.yml").read_text())["basics"]
    name, label, site = (html.escape(basics[k]) for k in ("name", "label", "url"))
    tagline = html.escape(basics.get("x_tagline", ""))
    avatar = (IMG / "avatar.svg").read_text()
    card = f"""
<main>
  <div class="avatar">{avatar}</div>
  <div class="text">
    <p class="site">A Coder's CV</p>
    <h1>{name}</h1>
    <p class="label">{label}</p>
    <p class="tagline">{tagline}</p>
    <p class="url">{site.removeprefix("https://").rstrip("/")}</p>
  </div>
</main>"""
    card_css = """
body { background: #111; color: #f2f2f2; font-family: Inter, sans-serif; }
main { display: flex; align-items: center; gap: 72px; height: 100%; padding: 0 88px; box-sizing: border-box; }
.avatar svg { width: 300px; height: 300px; display: block; border-radius: 50%; box-shadow: 0 0 0 6px #f2f2f2; }
.site { font-family: Mono, monospace; font-size: 30px; margin: 0 0 18px; color: #9fa8ff; }
h1 { font-size: 72px; font-weight: 700; margin: 0; letter-spacing: -1px; line-height: 1.05; }
.label { font-size: 38px; margin: 18px 0 0; }
.tagline { font-size: 28px; margin: 10px 0 0; color: #bdbdbd; }
.url { font-family: Mono, monospace; font-size: 26px; margin: 36px 0 0; color: #bdbdbd; }
"""
    icon_css = "body { background: #111; } svg { width: 180px; height: 180px; display: block; }"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "card.html").write_text(_page(card, card_css, SIZES["card"]))
    (OUT / "icon.html").write_text(_page(avatar, icon_css, SIZES["icon"]))
    print(f"wrote {OUT}/card.html, icon.html")


def shoot() -> None:
    from playwright.sync_api import sync_playwright  # noqa: PLC0415  (container step only)

    targets = {"card": "social-card.png", "icon": "apple-touch-icon.png"}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, png in targets.items():
            w, h = SIZES[name]
            page = browser.new_page(viewport={"width": w, "height": h})
            page.goto((OUT / f"{name}.html").as_uri())
            page.wait_for_load_state("networkidle")
            page.evaluate("document.fonts.ready")
            page.screenshot(path=str(IMG / png))
            print(f"wrote {IMG / png}")
        browser.close()


if __name__ == "__main__":
    {"html": write_html, "shoot": shoot}[sys.argv[1]]()
