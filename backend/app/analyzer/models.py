"""
Shared data structures for the RepoLens analyzer.

These are deliberately plain dataclasses (not pydantic) so the core analysis
engine has zero web-framework dependency -- it can be unit tested or reused
from a CLI without spinning up FastAPI.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class NodeType(str, Enum):
    FILE = "file"
    COMPONENT = "component"       # React component
    FUNCTION = "function"
    CLASS = "class"
    API_ENDPOINT = "api_endpoint"
    DB_MODEL = "db_model"
    SERVICE = "service"           # heuristically-classified "service" file


class EdgeType(str, Enum):
    IMPORTS = "imports"
    CALLS = "calls"
    DEFINES = "defines"           # file -> function/class/component it defines


@dataclass
class ImportRef:
    """A single import statement found in a source file."""
    module: str                # raw module string as written, e.g. "./authApi" or "services.auth"
    names: list[str] = field(default_factory=list)   # imported symbols, if named import
    is_relative: bool = False
    line: int = 0


@dataclass
class FunctionInfo:
    name: str
    line: int
    is_async: bool = False
    decorators: list[str] = field(default_factory=list)


@dataclass
class ClassInfo:
    name: str
    line: int
    bases: list[str] = field(default_factory=list)
    is_react_component: bool = False


@dataclass
class ApiRouteInfo:
    method: str                 # GET / POST / PUT / DELETE / PATCH
    path: str
    handler: str                # function name that handles it
    line: int = 0


@dataclass
class FileAnalysis:
    """Everything the analyzer extracted from one source file."""
    path: str                   # repo-relative path, forward slashes
    language: str                # "Python" | "TypeScript" | "JavaScript" | "CSS" | ...
    loc: int = 0
    imports: list[ImportRef] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    api_routes: list[ApiRouteInfo] = field(default_factory=list)
    is_react_component_file: bool = False
    is_db_model_file: bool = False
    parse_error: str | None = None
    # Truncated raw source, captured before the cloned repo is deleted
    # (see git_source.cleanup_repo). Only populated for parseable languages
    # (Python/TS/JS) and capped at MAX_SOURCE_CHARS -- see analyzer.py.
    # Exists so Ask RepoLens can answer from real code, not just the
    # structural summary (imports/functions/routes) it used to be limited to.
    source_snippet: str | None = None


@dataclass
class GraphNode:
    id: str
    type: NodeType
    label: str
    file: str | None = None


@dataclass
class GraphEdge:
    source: str
    target: str
    type: EdgeType


@dataclass
class RepoAnalysis:
    repo_name: str
    files: list[FileAnalysis] = field(default_factory=list)
    language_breakdown: dict[str, float] = field(default_factory=dict)  # language -> percent
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)

    @property
    def total_files(self) -> int:
        return len(self.files)

    @property
    def total_api_endpoints(self) -> int:
        return sum(
            1 for f in self.files for r in f.api_routes if r.handler != "(client call)"
        )

    @property
    def total_components(self) -> int:
        return sum(1 for f in self.files if f.is_react_component_file)

    @property
    def total_db_models(self) -> int:
        return sum(1 for f in self.files if f.is_db_model_file)
