import dagre from "dagre";
import { Position, type Edge, type Node } from "reactflow";

const NODE_WIDTH = 190;
const NODE_HEIGHT = 56;

/**
 * The backend graph (GraphNode/GraphEdge) only encodes structure, not
 * screen position -- that's a rendering concern, so it belongs here, not
 * in the analyzer. Dagre gives us a readable top-to-bottom layered layout
 * that roughly matches the "LoginPage -> AuthService -> route -> ..." chains
 * the product spec shows.
 */
export function layoutGraph(
  nodes: Node[],
  edges: Edge[],
  direction: "TB" | "LR" = "LR"
): Node[] {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: direction, nodesep: 48, ranksep: 96 });

  nodes.forEach((n) => g.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT }));
  edges.forEach((e) => g.setEdge(e.source, e.target));

  dagre.layout(g);

  return nodes.map((n) => {
    const pos = g.node(n.id);
    return {
      ...n,
      targetPosition: direction === "LR" ? Position.Left : Position.Top,
      sourcePosition: direction === "LR" ? Position.Right : Position.Bottom,
      position: { x: pos.x - NODE_WIDTH / 2, y: pos.y - NODE_HEIGHT / 2 },
    };
  });
}
