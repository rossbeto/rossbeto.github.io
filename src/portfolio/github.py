"""Adapter: read public GitHub repositories. The only module that touches the network.

No token: the sync reads public repositories only (private ones never reach the site).
"""

import os
import re
import subprocess
import urllib.error
import urllib.request

RAW = "https://raw.githubusercontent.com/{repo}/{ref}/{path}"
MAX_BYTES = 5_000_000  # a card or a media file; the image budget test is stricter
TIMEOUT = 20


class FetchError(RuntimeError):
    """A file or commit could not be read; the message names the repo and path."""


def fetch_raw(repo: str, ref: str, path: str) -> bytes:
    url = RAW.format(repo=repo, ref=ref, path=path)
    request = urllib.request.Request(url, headers={"User-Agent": "portfolio-sync"})  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310  (https only)
            data: bytes = response.read(MAX_BYTES + 1)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise FetchError(f"{repo}@{ref[:12]}: {path}: {exc}") from exc
    if len(data) > MAX_BYTES:
        raise FetchError(f"{repo}@{ref[:12]}: {path}: larger than {MAX_BYTES} bytes")
    return data


def latest_commit(repo: str) -> str:
    """The default branch's head commit (`git ls-remote`: no API, no rate limit, no token)."""
    url = f"https://github.com/{repo}.git"
    try:
        out = subprocess.run(  # noqa: S603
            ["git", "ls-remote", url, "HEAD"],  # noqa: S607
            capture_output=True,
            text=True,
            check=True,
            timeout=TIMEOUT,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},  # a private repo fails, never prompts
        ).stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise FetchError(f"{repo}: cannot read HEAD ({exc})") from exc
    match = re.match(r"^([0-9a-f]{40})\tHEAD$", out.strip())
    if not match:
        raise FetchError(f"{repo}: unexpected ls-remote output {out!r}")
    return match.group(1)
