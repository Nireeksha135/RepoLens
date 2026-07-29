"""
Turns the list of per-file FileAnalysis results into a connected graph:

    - Resolves relative imports ("./authApi", "../services/user") and
      absolute-style Python imports ("backend.services.auth_service") to
      actual repo-relative file paths so edges point at real nodes, not raw
      strings.
    - Classifies files heuristically (service / component / db model) so the
      architecture map can pick node shapes.
    - Emits GraphNode / GraphEdge lists, and also returns a networkx.DiGraph
      for anything that needs real graph algorithms later (change-impact
      analysis is just BFS/DFS over this).
"""
from __future__ import annotations

import posixpath

import networkx as nx

from .models import EdgeType, FileAnalysis, GraphEdge, GraphNode, NodeType

JS_EXTENSIONS = [".ts", ".tsx", ".js", ".jsx"]
PY_EXTENSIONS = [".py"]

SERVICE_PATH_HINTS = ("service", "services")
MODEL_PATH_HINTS = ("model", "models")
ROUTE_PATH_HINTS = ("route", "routes", "controller", "controllers", "api")


def _js_relative_candidates(from_file: str, module: str) -> list[str]:
    """JS/TS relative imports use real path syntax: './x', '../x'."""
    base_dir = posixpath.dirname(from_file)
    joined = posixpath.normpath(posixpath.join(base_dir, module))
    candidates = [joined]
    for ext in JS_EXTENSIONS:
        candidates.append(joined + ext)
        candidates.append(posixpath.join(joined, "index" + ext))
    return candidates


def _python_relative_candidates(from_file: str, module: str) -> list[str]:
    """Python relative imports use *level* semantics, not path syntax:
    'from .ctx import X' (level=1) means "ctx.py in the current package",
    i.e. the same directory as from_file -- not a literal ".ctx" path.
    'from ..pkg.sub import X' (level=2) goes up one additional package dir.
    ImportRef.module stores this as e.g. ".ctx" or "..pkg.sub" (dots-as-level
    prefix, then a dotted module path) -- level = count of leading dots.
    """
    level = len(module) - len(module.lstrip("."))
    name = module[level:]  # remaining dotted module path, e.g. "sansio.app"

    target_dir = posixpath.dirname(from_file)
    for _ in range(level - 1):  # level=1 means "current package" (no extra step up)
        target_dir = posixpath.dirname(target_dir)

    if not name:
        # "from . import X" -- importing the package itself
        return [posixpath.join(target_dir, "__init__.py")]

    as_path = posixpath.normpath(posixpath.join(target_dir, name.replace(".", "/")))
    return [as_path + ".py", posixpath.join(as_path, "__init__.py")]


def _absolute_python_candidates(module: str) -> list[str]:
    """Python absolute imports like `from backend.services.auth import X` are
    written as dotted paths *from the repo/package root*, not relative to the
    importing file. Convert dots to slashes and try that from root."""
    as_path = module.replace(".", "/")
    return [as_path + ".py", posixpath.join(as_path, "__init__.py")]


def _classify(file: FileAnalysis) -> NodeType:
    lower_path = file.path.lower()
    if file.is_react_component_file:
        return NodeType.COMPONENT
    if file.is_db_model_file or any(h in lower_path for h in MODEL_PATH_HINTS):
        return NodeType.DB_MODEL
    if any(h in lower_path for h in SERVICE_PATH_HINTS):
        return NodeType.SERVICE
    if any(h in lower_path for h in ROUTE_PATH_HINTS) and file.api_routes:
        return NodeType.API_ENDPOINT
    return NodeType.FILE


def build_graph(files: list[FileAnalysis]) -> tuple[list[GraphNode], list[GraphEdge], nx.DiGraph]:
    by_path = {f.path: f for f in files}
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    dg = nx.DiGraph()

    # 1. one node per file
    for f in files:
        node_type = _classify(f)
        nodes.append(GraphNode(id=f.path, type=node_type, label=posixpath.basename(f.path), file=f.path))
        dg.add_node(f.path, type=node_type.value)

    # 2. one node per individual API route, wired to its defining file
    for f in files:
        for route in f.api_routes:
            if route.handler == "(client call)":
                continue  # this is a call site, not a definition; handled as an edge below
            route_id = f"route::{route.method}:{route.path}"
            if route_id not in dg:
                nodes.append(GraphNode(id=route_id, type=NodeType.API_ENDPOINT, label=f"{route.method} {route.path}"))
                dg.add_node(route_id, type=NodeType.API_ENDPOINT.value)
            edges.append(GraphEdge(source=f.path, target=route_id, type=EdgeType.DEFINES))
            dg.add_edge(f.path, route_id, type=EdgeType.DEFINES.value)

    # 3. import edges, resolved to real files where possible
    for f in files:
        is_python = f.path.endswith(".py")
        for imp in f.imports:
            resolved = None
            if imp.is_relative and is_python:
                for cand in _python_relative_candidates(f.path, imp.module):
                    if cand in by_path:
                        resolved = cand
                        break
            elif imp.is_relative:
                for cand in _js_relative_candidates(f.path, imp.module):
                    if cand in by_path:
                        resolved = cand
                        break
            elif is_python:
                # Absolute-style python import (e.g. "backend.services.auth_service").
                # Only meaningful if it actually resolves to a file in *this* repo --
                # otherwise it's a third-party package (fastapi, sqlalchemy, ...) and
                # we deliberately leave it unresolved rather than guess.
                for cand in _absolute_python_candidates(imp.module):
                    if cand in by_path:
                        resolved = cand
                        break
            else:
                continue  # non-relative JS/TS import -> external npm package, skip

            if resolved and resolved != f.path:
                edges.append(GraphEdge(source=f.path, target=resolved, type=EdgeType.IMPORTS))
                dg.add_edge(f.path, resolved, type=EdgeType.IMPORTS.value)

    # 4. call edges: a frontend file hitting a known API route by path+method
    route_lookup = {}
    for f in files:
        for route in f.api_routes:
            if route.handler != "(client call)":
                route_lookup[(route.method, route.path)] = f"route::{route.method}:{route.path}"

    for f in files:
        for route in f.api_routes:
            if route.handler != "(client call)":
                continue
            target = route_lookup.get((route.method, route.path))
            if target:
                edges.append(GraphEdge(source=f.path, target=target, type=EdgeType.CALLS))
                dg.add_edge(f.path, target, type=EdgeType.CALLS.value)

    return nodes, edges, dg
