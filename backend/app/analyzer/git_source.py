"""Fetch a repository onto local disk so the analyzer can walk it."""
from __future__ import annotations

import shutil
import tempfile

from git import Repo


class RepoFetchError(Exception):
    pass


def clone_repo(url: str) -> str:
    """Shallow-clones `url` into a fresh temp directory and returns its path.
    Caller is responsible for cleanup (see cleanup_repo)."""
    tmp_dir = tempfile.mkdtemp(prefix="repolens_")
    try:
        Repo.clone_from(url, tmp_dir, depth=1, single_branch=True)
    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise RepoFetchError(f"Could not clone {url}: {e}") from e
    return tmp_dir


def cleanup_repo(path: str) -> None:
    shutil.rmtree(path, ignore_errors=True)
