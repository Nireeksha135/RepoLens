"""
RepoLens backend -- Feature 1 (Repository Analyzer), Feature 3 (Ask
RepoLens), Feature 4 (Change Impact Analysis), and Feature 5 (API Explorer)
as a REST API.

Run locally:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=...   # only needed for POST /chat
    uvicorn app.main:app --reload

Then:
    POST /analyze     { "repo_url": "https://github.com/user/project" }
    POST /impact       { "nodes": [...], "edges": [...], "target": "path/to/file.py" }
    POST /api-routes   { "nodes": [...], "edges": [...], "handlers": {...} }
    POST /chat         { "files": [...], "question": "..." }
"""
import os

from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .analyzer.analyzer import analyze_github_repo
from .analyzer.api_explorer import build_api_routes
from .analyzer.chat import ChatConfigError, ask_repolens
from .analyzer.git_source import RepoFetchError
from .analyzer.impact import analyze_impact
from .analyzer.models import (
    ApiRouteInfo,
    ClassInfo,
    EdgeType,
    FileAnalysis,
    FunctionInfo,
    GraphEdge,
    GraphNode,
    ImportRef,
    NodeType,
)

app = FastAPI(title="RepoLens API", version="0.1.0")

# ALLOWED_ORIGINS is a comma-separated list, e.g.
# "https://repolens.vercel.app,https://repolens.example.com". Falls back to
# "*" only when the env var is entirely unset, so local dev keeps working
# without configuration -- but that means the wildcard is the *unconfigured*
# state, not a deliberate production choice. Set ALLOWED_ORIGINS explicitly
# before deploying anywhere public.
_allowed_origins_env = os.environ.get("ALLOWED_ORIGINS")
ALLOWED_ORIGINS = (
    [o.strip() for o in _allowed_origins_env.split(",") if o.strip()]
    if _allowed_origins_env
    else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    repo_url: str


class GraphNodeIn(BaseModel):
    id: str
    type: str
    label: str
    file: str | None = None


class GraphEdgeIn(BaseModel):
    source: str
    target: str
    type: str


class ImpactRequest(BaseModel):
    # The frontend already has the graph from a prior /analyze call --
    # impact analysis is pure graph traversal, so there's no need to
    # re-clone or re-parse the repo to answer "what depends on this file".
    nodes: list[GraphNodeIn]
    edges: list[GraphEdgeIn]
    target: str


class ApiRoutesRequest(BaseModel):
    nodes: list[GraphNodeIn]
    edges: list[GraphEdgeIn]
    handlers: dict[str, str] = {}


class ImportRefIn(BaseModel):
    module: str
    names: list[str] = []
    is_relative: bool = False
    line: int = 0


class FunctionInfoIn(BaseModel):
    name: str
    line: int
    is_async: bool = False
    decorators: list[str] = []


class ClassInfoIn(BaseModel):
    name: str
    line: int
    bases: list[str] = []
    is_react_component: bool = False


class ApiRouteInfoIn(BaseModel):
    method: str
    path: str
    handler: str
    line: int = 0


class FileAnalysisIn(BaseModel):
    path: str
    language: str
    loc: int = 0
    imports: list[ImportRefIn] = []
    functions: list[FunctionInfoIn] = []
    classes: list[ClassInfoIn] = []
    api_routes: list[ApiRouteInfoIn] = []
    is_react_component_file: bool = False
    is_db_model_file: bool = False
    parse_error: str | None = None


class ChatRequest(BaseModel):
    # The frontend already has the full file list from /analyze -- Ask
    # RepoLens doesn't re-clone or re-parse, it just retrieves + generates.
    files: list[FileAnalysisIn]
    question: str


def _to_file_analysis(f: FileAnalysisIn) -> FileAnalysis:
    return FileAnalysis(
        path=f.path,
        language=f.language,
        loc=f.loc,
        imports=[ImportRef(module=i.module, names=i.names, is_relative=i.is_relative, line=i.line) for i in f.imports],
        functions=[FunctionInfo(name=fn.name, line=fn.line, is_async=fn.is_async, decorators=fn.decorators) for fn in f.functions],
        classes=[ClassInfo(name=c.name, line=c.line, bases=c.bases, is_react_component=c.is_react_component) for c in f.classes],
        api_routes=[ApiRouteInfo(method=r.method, path=r.path, handler=r.handler, line=r.line) for r in f.api_routes],
        is_react_component_file=f.is_react_component_file,
        is_db_model_file=f.is_db_model_file,
        parse_error=f.parse_error,
    )

class FileAnalysisIn(BaseModel):
    path: str
    language: str
    loc: int = 0
    imports: list[ImportRefIn] = []
    functions: list[FunctionInfoIn] = []
    classes: list[ClassInfoIn] = []
    api_routes: list[ApiRouteInfoIn] = []
    is_react_component_file: bool = False
    is_db_model_file: bool = False
    parse_error: str | None = None
    source_snippet: str | None = None


def _to_file_analysis(f: FileAnalysisIn) -> FileAnalysis:
    return FileAnalysis(
        path=f.path,
        language=f.language,
        loc=f.loc,
        imports=[ImportRef(module=i.module, names=i.names, is_relative=i.is_relative, line=i.line) for i in f.imports],
        functions=[FunctionInfo(name=fn.name, line=fn.line, is_async=fn.is_async, decorators=fn.decorators) for fn in f.functions],
        classes=[ClassInfo(name=c.name, line=c.line, bases=c.bases, is_react_component=c.is_react_component) for c in f.classes],
        api_routes=[ApiRouteInfo(method=r.method, path=r.path, handler=r.handler, line=r.line) for r in f.api_routes],
        is_react_component_file=f.is_react_component_file,
        is_db_model_file=f.is_db_model_file,
        parse_error=f.parse_error,
        source_snippet=f.source_snippet,
    )

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    """Clone + analyze a GitHub repo, returning overview stats plus the
    architecture graph (nodes/edges) the frontend renders with React Flow."""
    try:
        result = analyze_github_repo(req.repo_url)
    except RepoFetchError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return {
        "repo_name": result.repo_name,
        "overview": {
            "total_files": result.total_files,
            "total_components": result.total_components,
            "total_api_endpoints": result.total_api_endpoints,
            "total_db_models": result.total_db_models,
            "language_breakdown": result.language_breakdown,
        },
        "graph": {
            "nodes": [asdict(n) for n in result.nodes],
            "edges": [asdict(e) for e in result.edges],
        },
        "files": [asdict(f) for f in result.files],
    }


@app.post("/impact")
def impact(req: ImpactRequest):
    """Feature 4 -- what breaks if this file changes, bucketed into
    HIGH / MEDIUM / LOW by hop distance in the dependency graph."""
    nodes = [GraphNode(id=n.id, type=NodeType(n.type), label=n.label, file=n.file) for n in req.nodes]
    edges = [GraphEdge(source=e.source, target=e.target, type=EdgeType(e.type)) for e in req.edges]

    if req.target not in {n.id for n in nodes}:
        raise HTTPException(status_code=404, detail=f"Unknown node: {req.target}")

    result = analyze_impact(nodes, edges, req.target)

    return {
        "target": result.target,
        "high": [asdict(n) for n in result.high],
        "medium": [asdict(n) for n in result.medium],
        "low": [asdict(n) for n in result.low],
    }


@app.post("/api-routes")
def api_routes(req: ApiRoutesRequest):
    """Feature 5 -- every discovered API route plus what defines it, what it
    uses, and everything that (transitively) calls it."""
    nodes = [GraphNode(id=n.id, type=NodeType(n.type), label=n.label, file=n.file) for n in req.nodes]
    edges = [GraphEdge(source=e.source, target=e.target, type=EdgeType(e.type)) for e in req.edges]

    summaries = build_api_routes(nodes, edges, req.handlers)
    return [asdict(s) for s in summaries]


@app.post("/chat")
def chat(req: ChatRequest):
    """Feature 3 -- Ask RepoLens. Retrieves the most relevant files for the
    question, then asks an LLM to answer using only that context."""
    files = [_to_file_analysis(f) for f in req.files]
    try:
        return ask_repolens(files, req.question)
    except ChatConfigError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
