"""Integration: the whole site builds in strict mode, and the profile column is on every page."""

import html
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'class="profile"'
HIDDEN_NAV = 'data-md-type="navigation" hidden'
SECTIONS = [
    "index.html",
    "cv/index.html",
    "projects/index.html",
    "blog/index.html",
    "blog/tags/index.html",
    "404.html",
]
POSTS = {  # slug -> date folder (post_url_format "{date}/{slug}")
    "the-301-that-leaked-a-tenant": "2026/11/17",
    "what-my-first-real-deploy-taught-my-tests": "2026/11/17",
}
ENV = {"NO_MKDOCS_2_WARNING": "1", "PATH": "/usr/bin:/bin"}


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("site")
    # Same order as `make build`: generated files first (D-05), then the strict build.
    subprocess.run([sys.executable, "-m", "portfolio", "generate"], cwd=ROOT, check=True, env=ENV)
    subprocess.run(
        [sys.executable, "-m", "mkdocs", "build", "--strict", "--quiet", "--site-dir", str(out)],
        cwd=ROOT,
        check=True,
        env=ENV,
    )
    return out


def _pages(site: Path) -> list[Path]:
    return sorted(p for p in site.rglob("*.html") if "search" not in p.parts)


@pytest.mark.parametrize("page", SECTIONS)
def test_section_pages_exist(site: Path, page: str) -> None:
    assert (site / page).is_file()


def _is_post(site: Path, page: Path) -> bool:
    return any(page.relative_to(site).as_posix().startswith(f"blog/{d}/") for d in POSTS.values())


def test_profile_is_visible_on_every_page_except_posts(site: Path) -> None:
    # Guards the Material template override (overrides/main.html) across theme upgrades.
    # Post pages use Material's post sidebar (author card, date, read time) instead: it hides
    # the navigation sidebar, profile included (deviation 0002 #1).
    missing = [
        str(p.relative_to(site))
        for p in _pages(site)
        if not _is_post(site, p) and (PROFILE not in p.read_text() or HIDDEN_NAV in p.read_text())
    ]
    assert missing == []


@pytest.mark.parametrize(("slug", "day"), POSTS.items())
def test_posts_show_the_author_card_linking_home(site: Path, slug: str, day: str) -> None:
    html = (site / "blog" / day / slug / "index.html").read_text()
    assert 'class="md-profile md-post__profile"' in html
    assert '<a href="/">Nguyen Hien Lam</a>' in html


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


@pytest.mark.parametrize(("slug", "day"), POSTS.items())
def test_posts_are_published_and_listed(site: Path, slug: str, day: str) -> None:
    assert (site / "blog" / day / slug / "index.html").is_file()
    assert f"{day}/{slug}/" in (site / "blog" / "index.html").read_text()
    assert f"blog/{day}/{slug}/" in (site / "index.html").read_text()  # home: latest posts


def test_author_notes_and_templates_are_not_published(site: Path) -> None:
    assert not list(site.rglob("README*"))
    assert not list(site.rglob("*.example"))


def test_cv_page_and_profile_come_from_the_data_file(site: Path) -> None:
    data = yaml.safe_load((ROOT / "data" / "cv.yml").read_text())
    cv = (site / "cv" / "index.html").read_text()
    first = data["work"][0]
    assert first["name"] in cv
    assert html.escape(first["highlights"][0].split(" used by")[0], quote=False) in cv
    label = f'<p class="profile__label">{data["basics"]["label"]}</p>'
    assert label in (site / "blog" / "index.html").read_text()  # the profile column, any page
    assert data["basics"]["name"] in (site / "index.html").read_text()  # home header (phones)


def test_cv_lab_items_are_labelled_and_link_to_projects(site: Path) -> None:
    cv = (site / "cv" / "index.html").read_text()
    assert cv.count('class="cv-lab"') == sum(
        1
        for c in yaml.safe_load((ROOT / "data" / "cv.yml").read_text())["x_capabilities"]
        if c.get("proof")
    )
    assert 'href="../projects/"' in cv
