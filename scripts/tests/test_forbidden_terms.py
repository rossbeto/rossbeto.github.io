"""The checker, with a planted term that is not a real name (``zorblax``/``quux corp``)."""

import os
import subprocess
from pathlib import Path

import pytest
from forbidden_terms import HASHES, digest, load, main, normalise, scan, scan_line

PLANTED = load(f"# comment\n{digest('zorblax')}\n{digest('Quux Corp')}\n\n")


@pytest.mark.parametrize(
    ("term", "normal"), [("Foo-Bar", "foobar"), ("foo bar", "foobar"), ("FooBar2", "foobar2")]
)
def test_normalise(term: str, normal: str) -> None:
    assert normalise(term) == normal


@pytest.mark.parametrize(
    ("line", "found"),
    [
        ("built with Zorblax tools", ["Zorblax"]),
        ("see zorblax_443 and ZORBLAX.conf", ["zorblax", "ZORBLAX"]),  # `_` and `.` split words
        ("quux-corp, Quux Corp and quuxcorp", ["quux-corp", "Quux Corp", "quuxcorp"]),
        ("a zorblaxian word is not the term", []),
        ("quux alone, corp alone", []),
    ],
)
def test_scan_line_finds_every_spelling(line: str, found: list[str]) -> None:
    assert list(scan_line(line, PLANTED)) == found


def test_scan_reports_where() -> None:
    hits = scan([("docs/a.md", "fine\nby Quux  Corp\n")], PLANTED)
    assert [str(h) for h in hits] == ["docs/a.md:2: 'Quux  Corp'"]


def test_the_shipped_list_holds_hashes_only() -> None:
    hashes = load(HASHES.read_text())
    assert hashes and all(len(h) == 64 and int(h, 16) >= 0 for h in hashes)


def _git(repo: Path, *args: str) -> None:
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}  # fmt: skip
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=env)


def test_check_end_to_end_in_a_git_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    hashes = tmp_path / "terms.sha256"
    hashes.write_text(digest("zorblax") + "\n")
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "ok.txt").write_text("nothing here\n")
    (repo / "blob.bin").write_bytes(b"\0zorblax")  # binary: skipped
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "init")
    monkeypatch.chdir(repo)
    assert main(["check", "--history", "--all-revisions", "--hashes", str(hashes)]) == 0

    (repo / "new.md").write_text("by zorblax\n")  # untracked files are checked too
    assert main(["check", "--hashes", str(hashes)]) == 1
    assert "FORBIDDEN new.md:1: 'zorblax'" in capsys.readouterr().out

    # Reworded in the tree, but still in an old revision and in a commit message:
    _git(repo, "add", "new.md")
    _git(repo, "commit", "-qm", "add zorblax notes")
    (repo / "new.md").write_text("by an in-house tool\n")
    _git(repo, "commit", "-qam", "reword")
    capsys.readouterr()
    assert main(["check", "--hashes", str(hashes)]) == 0
    assert main(["check", "--history", "--all-revisions", "--hashes", str(hashes)]) == 1
    out = capsys.readouterr().out
    assert "FORBIDDEN new.md@" in out and "FORBIDDEN commit " in out


def test_check_works_before_the_first_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    hashes = tmp_path / "terms.sha256"
    hashes.write_text(digest("zorblax") + "\n")
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "new.md").write_text("fine\n")
    monkeypatch.chdir(repo)
    assert main(["check", "--history", "--hashes", str(hashes)]) == 0
