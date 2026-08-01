"""
Feature 5 -- API Explorer.

Builds a per-route summary (defined-in file, controller function, the
service(s) it uses, the DB model(s) it touches, and everything that
transitively calls it) purely from the graph Feature 1 already built.

The "Called by" field is the interesting reuse: a route's callers, including
transitive ones (LoginPage.tsx -> authApi.ts -> the route), is exactly what
Feature 4's analyze_impact() already computes when you ask "what depends on
this node" -- a route's impact *is* its caller chain. So this module adds no
new graph-traversal logic for that part, it just filters impact results down
to frontend-facing node types.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from .impact import analyze_impact
from .models import GraphEdge, GraphNode


@dataclass
class ApiRouteSummary:
    method: str
    path: str
    route_id: str
    defined_in: str | None = None
    controller: str | None = None
    uses: list[str] = field(default_factory=list)
    database_models: list[str] = field(default_factory=list)
    called_by: list[str] = field(default_factory=list)


def _etype(e: GraphEdge) -> str:
    return e.type.value if hasattr(e.type, "value") else str(e.type)


def _ntype(n: GraphNode) -> str:
    return n.type.value if hasattr(n.type, "value") else str(n.type)


def _forward_imports_bfs(edges: list[GraphEdge], start: str, max_hops: int = 3) -> list[str]:
    """Node ids reachable from `start` via 'imports' edges, nearest first."""
    adjacency: dict[str, list[str]] = {}
    for e in edges:
        if _etype(e) == "imports":
            adjacency.setdefault(e.source, []).append(e.target)

    visited = {start: 0}
    order: list[str] = []
    queue: deque[str] = deque([start])
    while queue:
        current = queue.popleft()
        hop = visited[current]
        if hop >= max_hops:
            continue
        for nxt in adjacency.get(current, []):
            if nxt in visited:
                continue
            visited[nxt] = hop + 1
            order.append(nxt)
            queue.append(nxt)
    return order


def build_api_routes(
    nodes: list[GraphNode],
    edges: list[GraphEdge],
    handlers: dict[str, str] | None = None,
) -> list[ApiRouteSummary]:
    """`handlers` maps route_id ("route::METHOD:/path") -> handler function
    name. It's passed in rather than re-derived from full FileAnalysis
    objects to keep this endpoint's request payload small -- the caller
    (frontend, which already has the full /analyze response) builds it with
    a one-line reduce over files[].api_routes."""
    handlers = handlers or {}
    nodes_by_id = {n.id: n for n in nodes}
    # Filter by the literal "route::" id prefix, not NodeType.API_ENDPOINT --
    # a *file* like backend/routes/auth.py can also get classified as
    # api_endpoint type by graph_builder's path-hint heuristic (it lives in
    # a "routes" dir and defines routes), which would otherwise collide with
    # the actual synthetic per-route nodes here.
    route_nodes = [n for n in nodes if n.id.startswith("route::")]

    definer_by_route: dict[str, str] = {}
    for e in edges:
        if _etype(e) == "defines":
            definer_by_route[e.target] = e.source

    summaries: list[ApiRouteSummary] = []
    for route in route_nodes:
        method, _, path = route.label.partition(" ")
        definer = definer_by_route.get(route.id)
        controller = handlers.get(route.id)

        uses: list[str] = []
        database_models: list[str] = []
        if definer:
            for node_id in _forward_imports_bfs(edges, definer):
                n = nodes_by_id.get(node_id)
                if not n:
                    continue
                if _ntype(n) == "service" and n.id not in uses:
                    uses.append(n.id)
                if _ntype(n) == "db_model" and n.id not in database_models:
                    database_models.append(n.id)

        impact_result = analyze_impact(nodes, edges, route.id)
        # Anything that transitively calls this route is a "caller" for
        # this purpose, regardless of how graph_builder classified it --
        # excluding db models (nothing calls a route *because* of a model)
        # and other route nodes (not meaningful as a "caller").
        called_by = [
            n.id for n in impact_result.impacted if n.node_type not in ("db_model", "api_endpoint")
        ]

        summaries.append(
            ApiRouteSummary(
                method=method,
                path=path,
                route_id=route.id,
                defined_in=definer,
                controller=controller,
                uses=uses,
                database_models=database_models,
                called_by=called_by,
            )
        )

    summaries.sort(key=lambda s: (s.path, s.method))
    return summaries
