"""
RepoLens backend -- Feature 1 (Repository Analyzer) + Feature 4 (Change
Impact Analysis) as a REST API.

Run locally:
    pip install -r requirements.txt
    uvicorn app.main:app --reload

Then:
    POST /analyze  { "repo_url": "https://github.com/user/project" }
    POST /impact   { "nodes": [...], "edges": [...], "target": "path/to/file.py" }
"""
from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .analyzer.analyzer import analyze_github_repo
from .analyzer.git_source import RepoFetchError
from .analyzer.impact import analyze_impact
from .analyzer.models import EdgeType, GraphEdge, GraphNode, NodeType

app = FastAPI(title="RepoLens API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten before deploying beyond local dev
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
