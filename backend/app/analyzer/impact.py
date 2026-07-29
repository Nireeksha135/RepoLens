"""
Feature 4 -- Change Impact Analysis.

Given a graph (the same nodes/edges build_graph() already produces) and a
target node, find everything that would be affected by changing it, and how
severely.

The subtlety is edge *direction*. build_graph() edges mean "depends on":

    LoginPage.tsx --imports--> authApi.ts     (LoginPage depends on authApi)
    authApi.ts    --calls-->   route          (authApi depends on the route)
    auth.py       --defines--> route          (the route depends on auth.py,
                                                 NOT the other way around --
                                                 "defines" points from the
                                                 file to what it produces)

Impact flows in the *opposite* direction of "depends on" for imports/calls
(if B changes, everything that depends on B is impacted), but in the *same*
direction as "defines" (if a file changes, the route it defines is impacted,
and impact continues flowing from there). So we build a dedicated impact
graph rather than just reversing every edge.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import networkx as nx

from .models import GraphEdge, GraphNode

HIGH_HOPS = 1
MEDIUM_HOPS = 2


@dataclass
class ImpactedNode:
    id: str
    label: str
    node_type: str
    hops: int
    severity: str          # "HIGH" | "MEDIUM" | "LOW"
    path: list[str] = field(default_factory=list)   # target -> ... -> this node


@dataclass
class ImpactResult:
    target: str
    impacted: list[ImpactedNode] = field(default_factory=list)

    @property
    def high(self) -> list[ImpactedNode]:
        return [n for n in self.impacted if n.severity == "HIGH"]

    @property
    def medium(self) -> list[ImpactedNode]:
        return [n for n in self.impacted if n.severity == "MEDIUM"]

    @property
    def low(self) -> list[ImpactedNode]:
        return [n for n in self.impacted if n.severity == "LOW"]


def _severity(hops: int) -> str:
    if hops <= HIGH_HOPS:
        return "HIGH"
    if hops <= MEDIUM_HOPS:
        return "MEDIUM"
    return "LOW"


def _node_type_str(node_type) -> str:
    return node_type.value if hasattr(node_type, "value") else str(node_type)


def build_impact_graph(nodes: list[GraphNode], edges: list[GraphEdge]) -> nx.DiGraph:
    """Direction here means 'impact flows this way', not 'depends on'."""
    g = nx.DiGraph()
    for n in nodes:
        g.add_node(n.id, type=_node_type_str(n.type), label=n.label)

    for e in edges:
        etype = e.type.value if hasattr(e.type, "value") else str(e.type)
        if etype in ("imports", "calls"):
            # e.source depends on e.target -> impact flows target -> source
            g.add_edge(e.target, e.source, via=etype)
        elif etype == "defines":
            # e.target (the route) depends on e.source (the file) ->
            # impact flows source -> target, same as the edge is already stored
            g.add_edge(e.source, e.target, via=etype)

    return g


def analyze_impact(
    nodes: list[GraphNode],
    edges: list[GraphEdge],
    target_id: str,
    max_hops: int = 10,
) -> ImpactResult:
    g = build_impact_graph(nodes, edges)
    if target_id not in g:
        return ImpactResult(target=target_id, impacted=[])

    node_lookup = {n.id: n for n in nodes}

    hops: dict[str, int] = {target_id: 0}
    parent: dict[str, str] = {}
    queue: deque[str] = deque([target_id])

    while queue:
        current = queue.popleft()
        current_hop = hops[current]
        if current_hop >= max_hops:
            continue
        for nxt in g.successors(current):
            if nxt in hops:
                continue
            hops[nxt] = current_hop + 1
            parent[nxt] = current
            queue.append(nxt)

    impacted: list[ImpactedNode] = []
    for node_id, hop in hops.items():
        if node_id == target_id:
            continue
        path = [node_id]
        cur = node_id
        while cur != target_id:
            cur = parent[cur]
            path.append(cur)
        path.reverse()

        n = node_lookup.get(node_id)
        impacted.append(
            ImpactedNode(
                id=node_id,
                label=n.label if n else node_id,
                node_type=_node_type_str(n.type) if n else "unknown",
                hops=hop,
                severity=_severity(hop),
                path=path,
            )
        )

    impacted.sort(key=lambda n: (n.hops, n.label))
    return ImpactResult(target=target_id, impacted=impacted)
