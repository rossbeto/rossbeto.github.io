"""`data/projects.yml`: the synced sources."""

from pathlib import Path

import pytest

from portfolio.projects.sources import SourceError, bump_ref, load_sources

SHA = "0123456789abcdef0123456789abcdef01234567"
ENTRY = f"""sources:
  - slug: lab
    repo: me/lab
    ref: {SHA}  # pinned
    media: [docs/media/demo.gif]
    meta: {{summary: One line., stage: active, kind: lab, tags: [django]}}
"""


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "projects.yml"
    path.write_text(text)
    return path


def test_loads_a_source(tmp_path: Path) -> None:
    [source] = load_sources(_write(tmp_path, ENTRY))
    assert source.page == "projects/lab.md"
    assert source.asset("docs/media/demo.gif") == "assets/projects/lab/demo.gif"
    assert source.card == "docs/portfolio-card.md"


@pytest.mark.parametrize("text", ["sources: []\n", "", "# nothing yet\n"])
def test_empty_is_nothing_to_sync(tmp_path: Path, text: str) -> None:
    assert load_sources(_write(tmp_path, text)) == []


def test_no_file_is_nothing_to_sync(tmp_path: Path) -> None:
    assert load_sources(tmp_path / "missing.yml") == []


@pytest.mark.parametrize(
    ("text", "error"),
    [
        ("projects: []\n", "one key, `sources`"),
        ("- a\n", "one key"),
        (ENTRY.replace(SHA, "main"), r"(?s)sources\[0\].*ref"),
        (ENTRY.replace("docs/media/demo.gif", "../secret.gif"), "inside the repository"),
        (ENTRY.replace("docs/media/demo.gif", "/etc/x"), "inside the repository"),
        (ENTRY.replace("[docs/media/demo.gif]", "[a/demo.gif, b/demo.gif]"), "share a file name"),
        (ENTRY.replace("repo: me/lab", "repo: https://github.com/me/lab"), "repo"),
        (ENTRY + ENTRY.replace("sources:\n", ""), "duplicate slugs"),
    ],
)
def test_invalid_sources_are_refused(tmp_path: Path, text: str, error: str) -> None:
    with pytest.raises(SourceError, match=error):
        load_sources(_write(tmp_path, text))


def test_bump_keeps_comments(tmp_path: Path) -> None:
    path = _write(tmp_path, ENTRY)
    new = "f" * 40
    bump_ref(path, SHA, new)
    assert f"ref: {new}  # pinned" in path.read_text()
    with pytest.raises(SourceError, match="exactly once"):
        bump_ref(path, SHA, new)
