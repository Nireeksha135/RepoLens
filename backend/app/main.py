"""
RepoLens backend -- Feature 1 (Repository Analyzer) as a REST API.

Run locally:
    pip install -r requirements.txt
    uvicorn app.main:app --reload

Then:
    POST /analyze  { "repo_url": "https://github.com/user/project" }
"""
from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .analyzer.analyzer import analyze_github_repo
from .analyzer.git_source import RepoFetchError

app = FastAPI(title="RepoLens API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten before deploying beyond local dev
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    repo_url: str


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
