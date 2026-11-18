"""`portfolio sync-projects`: pages and media from pinned cards (fake network), drift, bump."""

import io
import subprocess
import urllib.error
from pathlib import Path
from typing import Any

import pytest

from portfolio import cli, github
from portfolio.cli import main
from portfolio.github import FetchError, fetch_raw, latest_commit

HERE = Path(__file__).resolve().parent
OLD, NEW = "a" * 40, "b" * 40
SOURCES = f"""# comment kept
sources:
  - slug: lab
    repo: me/lab
    ref: {OLD}
    media: [docs/media/demo.gif]
    meta: {{summary: One line., stage: active, kind: lab, tags: [django]}}
"""
CARD = (
    (HERE / "data" / "portfolio-card.md")
    .read_text()
    .replace("- ![tlbuilder: the deploy plan and a dry-run deploy](media/tlb.gif)\n", "")
)


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "projects.yml").write_text(SOURCES)
    files = {"docs/portfolio-card.md": CARD.encode(), "docs/media/demo.gif": b"GIF89a-fake"}
    calls: list[tuple[str, str, str]] = []

    def fetch(repo: str, ref: str, path: str) -> bytes:
        calls.append((repo, ref, path))
        return files[path]

    monkeypatch.setattr(cli, "fetch_raw", fetch)
    monkeypatch.setattr(cli, "latest_commit", lambda repo: NEW)
    monkeypatch.setattr(cli, "_calls", calls, raising=False)
    return tmp_path


def test_sync_writes_the_page_and_media(root: Path) -> None:
    assert main(["sync-projects", "--root", str(root)]) == 0
    page = (root / "docs" / "projects" / "lab.md").read_text()
    assert page.startswith('---\ntitle: "tenantlab: a multi-tenant Django reference app"')
    assert f"me/lab@{OLD[:12]}" in page
    assert (root / "docs/assets/projects/lab/demo.gif").read_bytes() == b"GIF89a-fake"
    assert {c[1] for c in cli._calls} == {OLD}  # type: ignore[attr-defined]  # pinned ref only


def test_check_passes_after_a_sync_and_fails_on_drift(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["sync-projects", "--root", str(root), "--check"]) == 1  # nothing synced yet
    assert main(["sync-projects", "--root", str(root)]) == 0
    assert main(["sync-projects", "--root", str(root), "--check"]) == 0
    page = root / "docs" / "projects" / "lab.md"
    page.write_text(page.read_text() + "hand edit\n")
    capsys.readouterr()
    assert main(["sync-projects", "--root", str(root), "--check"]) == 1
    assert "drift: docs/projects/lab.md" in capsys.readouterr().err


def test_bump_moves_the_ref_and_syncs_the_new_commit(root: Path) -> None:
    assert main(["sync-projects", "--root", str(root), "--bump"]) == 0
    text = (root / "data" / "projects.yml").read_text()
    assert f"ref: {NEW}" in text and "# comment kept" in text
    assert f"me/lab@{NEW[:12]}" in (root / "docs" / "projects" / "lab.md").read_text()


def test_bump_with_nothing_new_changes_nothing(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "latest_commit", lambda repo: OLD)
    assert main(["sync-projects", "--root", str(root), "--bump"]) == 0
    assert (root / "data" / "projects.yml").read_text() == SOURCES


def test_errors_exit_cleanly(
    root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def offline(repo: str, ref: str, path: str) -> bytes:
        raise FetchError(f"{repo}: {path}: offline")

    monkeypatch.setattr(cli, "fetch_raw", offline)
    assert main(["sync-projects", "--root", str(root)]) == 1
    assert "me/lab: docs/portfolio-card.md: offline" in capsys.readouterr().err


def test_no_sources(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["sync-projects", "--root", str(tmp_path)]) == 0
    assert "nothing to sync" in capsys.readouterr().out
    assert main(["sync-projects", "--root", str(tmp_path), "--check"]) == 0


# The GitHub adapter, with urllib and git replaced.


class _Response(io.BytesIO):
    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def test_fetch_raw_reads_the_pinned_raw_url(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def urlopen(request: Any, timeout: int) -> _Response:
        seen.append(request.full_url)
        return _Response(b"card")

    monkeypatch.setattr(github.urllib.request, "urlopen", urlopen)
    assert fetch_raw("me/lab", OLD, "docs/c.md") == b"card"
    assert seen == [f"https://raw.githubusercontent.com/me/lab/{OLD}/docs/c.md"]


def test_fetch_raw_limits_size_and_wraps_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(github, "MAX_BYTES", 3)
    monkeypatch.setattr(github.urllib.request, "urlopen", lambda r, timeout: _Response(b"1234"))
    with pytest.raises(FetchError, match="larger than 3 bytes"):
        fetch_raw("me/lab", OLD, "x")

    def fail(request: Any, timeout: int) -> _Response:
        raise urllib.error.HTTPError(request.full_url, 404, "Not Found", {}, None)  # type: ignore[arg-type]

    monkeypatch.setattr(github.urllib.request, "urlopen", fail)
    with pytest.raises(FetchError, match="404"):
        fetch_raw("me/lab", OLD, "x")


def test_latest_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    def run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert cmd == ["git", "ls-remote", "https://github.com/me/lab.git", "HEAD"]
        assert kwargs["env"]["GIT_TERMINAL_PROMPT"] == "0"
        return subprocess.CompletedProcess(cmd, 0, stdout=f"{NEW}\tHEAD\n")

    monkeypatch.setattr(github.subprocess, "run", run)
    assert latest_commit("me/lab") == NEW

    monkeypatch.setattr(
        github.subprocess, "run", lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, stdout="")
    )
    with pytest.raises(FetchError, match="unexpected"):
        latest_commit("me/lab")

    def denied(cmd: list[str], **kwargs: Any) -> None:
        raise subprocess.CalledProcessError(128, cmd)

    monkeypatch.setattr(github.subprocess, "run", denied)
    with pytest.raises(FetchError, match="cannot read HEAD"):
        latest_commit("me/lab")
