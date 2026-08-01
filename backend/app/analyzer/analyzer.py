"""
Top-level entry point for Feature 1 (Repository Analyzer).

    analyze_local_repo(path)   -> RepoAnalysis     # for a repo already on disk
    analyze_github_repo(url)   -> RepoAnalysis      # clones, analyzes, cleans up

This module doesn't know about FastAPI, HTTP, or the web layer at all --
it's pure analysis, which keeps it easy to unit test and reusable from a CLI.
"""
from __future__ import annotations

from pathlib import Path

from . import git_source
from .graph_builder import build_graph
from .js_parser import parse_js_file
from .models import FileAnalysis, RepoAnalysis
from .python_parser import parse_python_file
from .scanner import (
    EXTENSION_LANGUAGE,
    count_loc,
    discover_files,
    language_breakdown,
    relative_path,
)

# Caps how much raw source is retained per file (see FileAnalysis.source_snippet).
# This is what makes Ask RepoLens answer from real code instead of only
# structural summary -- but keeping it capped matters because /analyze's
# response size (and every /chat request's payload) scales with it across
# every file in the repo, not just the ones a given question retrieves.
MAX_SOURCE_CHARS = 4000
TRUNCATION_MARKER = "\n... (truncated)"


def _snippet(source: str) -> str:
    if len(source) <= MAX_SOURCE_CHARS:
        return source
    return source[:MAX_SOURCE_CHARS] + TRUNCATION_MARKER


def _analyze_one_file(abs_path: Path, rel_path: str) -> FileAnalysis:
    ext = abs_path.suffix.lower()
    language = EXTENSION_LANGUAGE.get(ext, "Other")
    loc = count_loc(abs_path)

    if language == "Python":
        try:
            source = abs_path.read_text(encoding="utf-8", errors="ignore")
        except OSError as e:
            fa = FileAnalysis(path=rel_path, language=language, loc=loc)
            fa.parse_error = str(e)
            return fa
        result = parse_python_file(source, rel_path, loc)
        result.source_snippet = _snippet(source)
        return result

    if language in ("TypeScript", "JavaScript"):
        try:
            source = abs_path.read_text(encoding="utf-8", errors="ignore")
        except OSError as e:
            fa = FileAnalysis(path=rel_path, language=language, loc=loc)
            fa.parse_error = str(e)
            return fa
        result = parse_js_file(source, rel_path, loc)
        result.source_snippet = _snippet(source)
        return result

    # Non-parsed languages (CSS, JSON, Markdown, ...) still count toward
    # the language breakdown / file count, just without structural detail
    # or a source snippet.
    return FileAnalysis(path=rel_path, language=language, loc=loc)


def analyze_local_repo(repo_root: str, repo_name: str | None = None) -> RepoAnalysis:
    repo_root = str(Path(repo_root).resolve())
    name = repo_name or Path(repo_root).name

    analysis = RepoAnalysis(repo_name=name)

    all_files = discover_files(repo_root)
    for abs_path in all_files:
        rel = relative_path(repo_root, abs_path)
        analysis.files.append(_analyze_one_file(abs_path, rel))

    analysis.language_breakdown = language_breakdown(
        [(f.language, f.loc) for f in analysis.files]
    )

    nodes, edges, _graph = build_graph(analysis.files)
    analysis.nodes = nodes
    analysis.edges = edges

    return analysis


def analyze_github_repo(url: str) -> RepoAnalysis:
    local_path = git_source.clone_repo(url)
    try:
        repo_name = url.rstrip("/").split("/")[-1].removesuffix(".git")
        return analyze_local_repo(local_path, repo_name=repo_name)
    finally:
        git_source.cleanup_repo(local_path)
