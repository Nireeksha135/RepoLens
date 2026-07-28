"""
Walks a repository on disk and figures out which files are worth analyzing,
plus computes the language breakdown (by lines of code) shown on the
Repository Overview screen.
"""
from __future__ import annotations

import os
from pathlib import Path

# Directories we never want to walk into.
IGNORED_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    "dist", "build", ".next", ".pytest_cache", ".mypy_cache",
    "coverage", ".turbo", "target", ".idea", ".vscode", "vendor",
    "egg-info",
}

# Extension -> language label, and whether we have a real parser for it.
EXTENSION_LANGUAGE = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".css": "CSS",
    ".scss": "CSS",
    ".html": "HTML",
    ".json": "JSON",
    ".sql": "SQL",
    ".md": "Markdown",
    ".yml": "YAML",
    ".yaml": "YAML",
}

# Languages we actually run structural parsing on (imports/functions/classes).
PARSEABLE_LANGUAGES = {"Python", "TypeScript", "JavaScript"}


def _is_ignored(dirname: str) -> bool:
    return dirname in IGNORED_DIRS or dirname.startswith(".") and dirname not in {".", ".."}


def discover_files(repo_root: str) -> list[Path]:
    """Return every source file under repo_root worth analyzing, skipping junk dirs."""
    root = Path(repo_root)
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not _is_ignored(d)]
        for fname in filenames:
            ext = Path(fname).suffix.lower()
            if ext in EXTENSION_LANGUAGE:
                found.append(Path(dirpath) / fname)
    return found


def relative_path(repo_root: str, file_path: Path) -> str:
    return str(Path(file_path).relative_to(repo_root)).replace(os.sep, "/")


def count_loc(file_path: Path) -> int:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for line in f if line.strip())
    except OSError:
        return 0


def language_breakdown(files_with_loc: list[tuple[str, int]]) -> dict[str, float]:
    """files_with_loc: list of (language, loc). Returns language -> rounded percent."""
    totals: dict[str, int] = {}
    for lang, loc in files_with_loc:
        totals[lang] = totals.get(lang, 0) + loc
    grand_total = sum(totals.values()) or 1
    return {
        lang: round(loc / grand_total * 100, 1)
        for lang, loc in sorted(totals.items(), key=lambda kv: -kv[1])
    }
