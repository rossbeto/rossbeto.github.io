"""Accessibility check (axe-core, WCAG 2.1 AA + best practices) of the built site, light and dark.

    make a11y      # builds, serves site/ on 127.0.0.1:8002, runs this in the Playwright container

Runs inside mcr.microsoft.com/playwright/python with axe.min.js from .cache/ (fetched by make).
Fails on any violation except the known ones in Material's own markup, listed in KNOWN.
"""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8002/"
PAGES = ["", "cv/", "projects/", "projects/tenantlab/", "blog/", "blog/tags/"]
RULES = ["wcag2a", "wcag2aa", "wcag21aa", "best-practice"]
KNOWN = {
    "aria-dialog-name": "Material's search dialog has no accessible name (partials/search.html)",
    "landmark-unique": "Material's nested section navs share a landmark name",
}


def main() -> int:
    axe = Path(".cache/axe.min.js").read_text()
    failures = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for scheme in ("light", "dark"):
            page = browser.new_context(color_scheme=scheme).new_page()
            for path in PAGES:
                page.goto(BASE + path, wait_until="networkidle")
                page.add_script_tag(content=axe)
                found = page.evaluate(
                    "async (rules) => (await axe.run(document, {runOnly: rules})).violations"
                    ".map(v => [v.id, v.nodes.length, v.nodes[0].target.join(' ')])",
                    RULES,
                )
                for rule, count, sample in found:
                    if rule in KNOWN:
                        continue
                    failures += 1
                    print(f"FAIL {scheme} /{path}: {rule} ({count}x, e.g. {sample})")
        browser.close()
    print(f"a11y: {failures} violations (known theme issues ignored: {', '.join(KNOWN)})")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
