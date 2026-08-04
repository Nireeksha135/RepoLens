"""
Tests for git_source.py's URL parsing and archive-extraction safety logic --
the parts of the tarball-based fetcher that don't require a live network
call to GitHub. (fetch_repo() itself is validated separately by manually
running it against real repos like pallets/flask and git/git -- see the
module's docstring notes; that's not automated here since CI shouldn't
depend on GitHub's availability or rate limits.)
"""
from __future__ import annotations

import io
import tarfile

import pytest

from app.analyzer.git_source import RepoFetchError, _extract_stripping_root, _parse_owner_repo


class TestParseOwnerRepo:
    def test_https_url(self):
        assert _parse_owner_repo("https://github.com/pallets/flask") == ("pallets", "flask")

    def test_https_url_with_git_suffix(self):
        assert _parse_owner_repo("https://github.com/pallets/flask.git") == ("pallets", "flask")

    def test_https_url_with_trailing_slash(self):
        assert _parse_owner_repo("https://github.com/pallets/flask/") == ("pallets", "flask")

    def test_bare_domain_no_scheme(self):
        assert _parse_owner_repo("github.com/pallets/flask") == ("pallets", "flask")

    def test_not_a_github_url_raises(self):
        with pytest.raises(RepoFetchError):
            _parse_owner_repo("https://gitlab.com/pallets/flask")

    def test_garbage_input_raises(self):
        with pytest.raises(RepoFetchError):
            _parse_owner_repo("not a url at all")


def _make_tarball(entries: dict[str, str]) -> tarfile.TarFile:
    """Builds an in-memory tar matching entries {path: content}, already
    positioned to read from -- mimics GitHub's wrapper-dir convention."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path, content in entries.items():
            data = content.encode()
            info = tarfile.TarInfo(name=path)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    buf.seek(0)
    return tarfile.open(fileobj=buf, mode="r:gz")


class TestExtractStrippingRoot:
    def test_strips_github_wrapper_directory(self, tmp_path):
        tar = _make_tarball({
            "flask-3.0.0/setup.py": "# setup",
            "flask-3.0.0/src/flask/app.py": "# app",
        })
        _extract_stripping_root(tar, str(tmp_path))

        assert (tmp_path / "setup.py").exists()
        assert (tmp_path / "src/flask/app.py").exists()
        assert not (tmp_path / "flask-3.0.0").exists()

    def test_rejects_path_traversal(self, tmp_path):
        # A malicious/corrupted tarball with a member trying to escape dest
        # via "../" after the wrapper dir is stripped.
        tar = _make_tarball({"wrapper/../../etc/passwd": "pwned"})
        with pytest.raises(tarfile.TarError):
            _extract_stripping_root(tar, str(tmp_path))
