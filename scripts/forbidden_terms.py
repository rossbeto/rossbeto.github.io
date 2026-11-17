#!/usr/bin/env python3
"""Fail if a forbidden term (employer names, internal product names) appears in the repository.

The term list itself must not leak, and this repository is public. So
``scripts/forbidden-terms.sha256`` holds only SHA-256 hashes of the normalised terms. Every word
of every tracked file, and every adjacent pair or triple of words, is hashed and compared. A
pair or triple catches ``foo-bar``, ``foo bar`` and ``FooBar`` alike, because all three
normalise to ``foobar``.

    scripts/forbidden_terms.py check [--history] [--all-revisions]
        files in the working tree; --history adds commit messages, --all-revisions every file
        version ever committed (what publishing the history would publish)
    scripts/forbidden_terms.py hash 'Foo Bar'      # the line to add to the list

Stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

HASHES = Path(__file__).with_name("forbidden-terms.sha256")
WORD = re.compile(r"[a-z0-9]+")
MAX_WORDS = 3  # "foo bar baz" is the longest term shape


def normalise(term: str) -> str:
    return "".join(WORD.findall(term.lower()))


def digest(term: str) -> str:
    return hashlib.sha256(normalise(term).encode()).hexdigest()


def load(text: str) -> frozenset[str]:
    return frozenset(
        ln.split()[0] for ln in text.splitlines() if ln.strip() and not ln.startswith("#")
    )


@dataclass(frozen=True)
class Hit:
    where: str  # "path:line" or "commit <sha>"
    text: str  # the matching words, as written

    def __str__(self) -> str:
        return f"{self.where}: {self.text!r}"


def scan_line(line: str, hashes: frozenset[str]) -> Iterator[str]:
    """Each forbidden word, pair or triple in ``line``, in its original spelling."""
    words = list(WORD.finditer(line.lower()))
    for i in range(len(words)):
        for n in range(1, MAX_WORDS + 1):
            group = words[i : i + n]
            if len(group) < n:
                break
            joined = "".join(m[0] for m in group)
            if hashlib.sha256(joined.encode()).hexdigest() in hashes:
                yield line[group[0].start() : group[-1].end()]


def scan(sources: Iterable[tuple[str, str]], hashes: frozenset[str]) -> list[Hit]:
    """``sources``: (where, text) pairs; ``where`` gets ``:<line>`` appended."""
    hits = []
    for where, text in sources:
        for no, line in enumerate(text.splitlines(), 1):
            hits += [Hit(f"{where}:{no}", t) for t in scan_line(line, hashes)]
    return hits


def _git(*args: str) -> str:
    # git from PATH, fixed arguments: a developer/CI tool, not a service handling input
    return subprocess.run(("git", *args), check=True, capture_output=True, text=True).stdout  # noqa: S603, S607


def repo_files() -> Iterator[tuple[str, str]]:
    """Tracked + untracked-but-not-ignored text files (a new file is checked before its commit)."""
    for name in _git("ls-files", "--cached", "--others", "--exclude-standard", "-z").split("\0"):
        path = Path(name)
        if not name or not path.is_file():
            continue
        data = path.read_bytes()
        if b"\0" in data[:8192]:
            continue  # binary
        yield name, data.decode("utf-8", errors="replace")


def all_revisions() -> Iterator[tuple[str, str]]:
    """Every file version ever committed (each blob once): what a public push of the history
    would publish, including text deleted or reworded since."""
    paths: dict[str, str] = {}
    for line in _git("rev-list", "--objects", "--all").splitlines():
        sha, _, path = line.partition(" ")
        if path:
            paths.setdefault(sha, path)
    batch = subprocess.run(
        ("git", "cat-file", "--batch"),  # noqa: S607
        input="\n".join(paths).encode(),
        check=True,
        capture_output=True,
    ).stdout
    pos = 0
    while pos < len(batch):
        header_end = batch.index(b"\n", pos)
        sha, kind, size = batch[pos:header_end].decode().split()
        body = batch[header_end + 1 : header_end + 1 + int(size)]
        pos = header_end + 1 + int(size) + 1
        if kind == "blob" and b"\0" not in body[:8192]:
            yield f"{paths[sha]}@{sha[:10]}", body.decode("utf-8", errors="replace")


def _has_commits() -> bool:
    probe = subprocess.run(
        ("git", "rev-parse", "--verify", "-q", "HEAD"),  # noqa: S607
        capture_output=True,
        check=False,  # a non-zero exit is the answer, not an error
    )
    return probe.returncode == 0


def commit_messages() -> Iterator[tuple[str, str]]:
    if not _has_commits():  # a fresh repository: no history to scan yet
        return
    for record in _git("log", "--format=%H%x00%an <%ae>%n%B%x01").split("\x01"):
        sha, _, body = record.strip().partition("\0")
        if sha:
            yield f"commit {sha[:10]}", body


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    chk = sub.add_parser("check", help="scan the repository")
    chk.add_argument("--history", action="store_true", help="also scan every commit message")
    chk.add_argument(
        "--all-revisions",
        action="store_true",
        help="also scan every file version in the history (before publishing it)",
    )
    chk.add_argument("--hashes", type=Path, default=HASHES)
    hsh = sub.add_parser("hash", help="print the list line for a term")
    hsh.add_argument("term")
    args = p.parse_args(argv)
    if args.cmd == "hash":
        print(digest(args.term))
        return 0
    hashes = load(args.hashes.read_text(encoding="utf-8"))
    sources: list[Iterable[tuple[str, str]]] = [repo_files()]
    if args.history:
        sources.append(commit_messages())
    if args.all_revisions:
        sources.append(all_revisions())
    hits = [h for src in sources for h in scan(src, hashes)]
    for hit in hits:
        print(f"FORBIDDEN {hit}")
    print(f"forbidden terms: {len(hashes)} terms, {len(hits)} hits")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
