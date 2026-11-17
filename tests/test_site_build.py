"""Integration: the whole site builds in strict mode, and the profile column is on every page."""

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'class="profile"'
SECTIONS = ["index.html", "cv/index.html", "projects/index.html", "blog/index.html", "404.html"]


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("site")
    subprocess.run(
        [sys.executable, "-m", "mkdocs", "build", "--strict", "--quiet", "--site-dir", str(out)],
        cwd=ROOT,
        check=True,
        env={"NO_MKDOCS_2_WARNING": "1", "PATH": "/usr/bin:/bin"},
    )
    return out


def _pages(site: Path) -> list[Path]:
    return sorted(p for p in site.rglob("*.html") if "search" not in p.parts)


@pytest.mark.parametrize("page", SECTIONS)
def test_section_pages_exist(site: Path, page: str) -> None:
    assert (site / page).is_file()


def test_profile_is_on_every_page(site: Path) -> None:
    # Guards the Material template override (overrides/main.html) across theme upgrades.
    missing = [str(p.relative_to(site)) for p in _pages(site) if PROFILE not in p.read_text()]
    assert missing == []


def test_contact_is_a_github_issue_and_no_email_is_published(site: Path) -> None:
    home = (site / "index.html").read_text()
    assert "rossbeto.github.io/issues/new?template=contact.yml" in home
    email = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
    emails = {m for p in _pages(site) for m in email.findall(p.read_text())}
    assert {e for e in emails if not e.endswith((".svg", ".png", ".js", ".css"))} == set()


def test_site_title_is_not_the_name(site: Path) -> None:
    titles = {p: re.search(r"<title>([^<]*)</title>", p.read_text()) for p in _pages(site)}
    assert titles[site / "index.html"][1] in {"A Coder's CV", "A Coder&#39;s CV"}  # type: ignore[index]
    assert not [p for p, t in titles.items() if t and "Nguyen" in t[1]]


def test_no_placeholders_online(site: Path) -> None:
    hits = [str(p.relative_to(site)) for p in _pages(site) if "[X]" in p.read_text()]
    assert hits == []
