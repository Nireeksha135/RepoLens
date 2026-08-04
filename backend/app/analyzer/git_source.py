"""
Fetch a repository's source onto local disk so the analyzer can walk it --
via GitHub's tarball download, not `git clone`.

This deliberately avoids GitPython / a system `git` binary: the original
clone-based approach needed `apt-get install git` in whatever container ran
it, which doesn't work at all on Vercel's Python serverless runtime (no
shell, no system package installs, no persistent filesystem to install
into). Downloading + extracting a tarball only needs the standard library
(`urllib`, `tarfile`), so this runs anywhere Python does -- container or
serverless.
"""
from __future__ import annotations

import io
import os
import re
import shutil
import tarfile
import tempfile
import urllib.error
import urllib.request

TIMEOUT_SECONDS = 20
USER_AGENT = "RepoLens-Analyzer"  # GitHub rejects requests with no User-Agent
MAX_TARBALL_BYTES = 50 * 1024 * 1024  # 50 MB -- keeps analysis time bounded,
# which matters more now than it did on Render: serverless platforms like
# Vercel enforce a hard function execution time limit, so failing fast with
# a clear error beats a slow timeout on a huge repo.


class RepoFetchError(Exception):
    pass


def _parse_owner_repo(url: str) -> tuple[str, str]:
    # Accepts "https://github.com/owner/repo", "github.com/owner/repo",
    # and "https://github.com/owner/repo.git", trailing slash optional.
    match = re.search(r"github\.com[/:]([^/\s]+)/([^/\s]+?)(?:\.git)?/?$", url.strip())
    if not match:
        raise RepoFetchError(f"Not a recognizable GitHub URL: {url}")
    return match.group(1), match.group(2)


def _download(url: str) -> bytes | None:
    """Returns the response body, or None on a 404 (branch/repo not found
    at this URL -- a normal case here, not exceptional, since we probe
    'main' then 'master'). Any other failure raises."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            body = resp.read(MAX_TARBALL_BYTES + 1)
            if len(body) > MAX_TARBALL_BYTES:
                raise RepoFetchError(
                    f"Repository archive exceeds the {MAX_TARBALL_BYTES // (1024*1024)}MB limit for this deployment."
                )
            return body
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise RepoFetchError(f"GitHub returned {e.code} fetching {url}") from e
    except urllib.error.URLError as e:
        raise RepoFetchError(f"Could not reach GitHub: {e.reason}") from e


def _default_branch(owner: str, repo: str) -> str:
    """Only called as a fallback when neither 'main' nor 'master' exist --
    keeps normal-case requests off GitHub's rate-limited REST API (60
    unauthenticated requests/hour/IP); codeload's tarball endpoint used for
    the common case isn't subject to that same limit."""
    import json

    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    req = urllib.request.Request(
        api_url, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read())
            return data["default_branch"]
    except urllib.error.HTTPError as e:
        raise RepoFetchError(f"Could not find repository {owner}/{repo} (GitHub returned {e.code})") from e
    except urllib.error.URLError as e:
        raise RepoFetchError(f"Could not reach GitHub: {e.reason}") from e


def _extract_stripping_root(tar: tarfile.TarFile, dest: str) -> None:
    """GitHub tarballs wrap everything in one top-level dir (e.g.
    'flask-3.0.0/'). Strip that first path segment during extraction so
    `dest` itself becomes the repo root -- keeps fetch_repo/cleanup_repo
    symmetric with the old clone-based API (the returned path is exactly
    what cleanup_repo deletes). Also guards against path traversal from a
    malicious or corrupted tarball (CVE-2007-4559-style)."""
    dest_real = os.path.realpath(dest)
    for member in tar.getmembers():
        parts = member.name.split("/", 1)
        if len(parts) < 2 or not parts[1]:
            continue  # the wrapper directory entry itself
        member.name = parts[1]
        member_path = os.path.realpath(os.path.join(dest, member.name))
        if not (member_path == dest_real or member_path.startswith(dest_real + os.sep)):
            raise tarfile.TarError(f"Unsafe path in archive: {member.name}")
        # filter="data" is tarfile's safe-extraction mode (strips device
        # files, absolute paths, etc.) -- pinned explicitly rather than
        # relying on tarfile's default, which is changing in Python 3.14.
        # Our own path-traversal check above still runs first regardless.
        tar.extract(member, dest, filter="data")


def fetch_repo(url: str) -> str:
    """Downloads and extracts `url`'s default branch as a tarball into a
    fresh temp directory, returning the path to the extracted repo root.
    Caller is responsible for cleanup (see cleanup_repo)."""
    owner, repo = _parse_owner_repo(url)

    tarball = None
    branch_used = None
    for branch in ("main", "master"):
        tarball = _download(f"https://codeload.github.com/{owner}/{repo}/tar.gz/refs/heads/{branch}")
        if tarball is not None:
            branch_used = branch
            break

    if tarball is None:
        branch_used = _default_branch(owner, repo)
        tarball = _download(f"https://codeload.github.com/{owner}/{repo}/tar.gz/refs/heads/{branch_used}")
        if tarball is None:
            raise RepoFetchError(f"Could not download {owner}/{repo} (tried branch: {branch_used})")

    tmp_dir = tempfile.mkdtemp(prefix="repolens_")
    try:
        with tarfile.open(fileobj=io.BytesIO(tarball), mode="r:gz") as tar:
            _extract_stripping_root(tar, tmp_dir)
    except tarfile.TarError as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise RepoFetchError(f"Could not extract archive for {owner}/{repo}: {e}") from e

    return tmp_dir


def cleanup_repo(path: str) -> None:
    shutil.rmtree(path, ignore_errors=True)
