import { useMemo } from "react";
import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  type Edge,
  type Node,
} from "reactflow";
import "reactflow/dist/style.css";

import type { AnalyzeResponse, NodeType } from "../api/types";
import { layoutGraph } from "../layout/autoLayout";
import ArchitectureNode, { type ArchNodeData } from "./nodes/ArchitectureNode";
import SignalEdge from "./SignalEdge";

const nodeTypes = { architecture: ArchitectureNode };
const edgeTypes = { signal: SignalEdge };

const LEGEND: { type: NodeType; label: string }[] = [
  { type: "component", label: "React Component" },
  { type: "api_endpoint", label: "API Endpoint" },
  { type: "service", label: "Backend Service" },
  { type: "db_model", label: "Database Model" },
];

export default function GraphView({
  data,
  selectedId,
  onSelect,
}: {
  data: AnalyzeResponse;
  selectedId: string | null;
  onSelect: (id: string | null) => void;
}) {
  const { nodes, edges } = useMemo(() => {
    const rawNodes: Node<ArchNodeData>[] = data.graph.nodes.map((n) => ({
      id: n.id,
      type: "architecture",
      position: { x: 0, y: 0 },
      data: { label: n.label, nodeType: n.type, file: n.file, onSelect: (id: string) => onSelect(id), isSelected: n.id === selectedId },
    }));

    const laidOut = layoutGraph(rawNodes, data.graph.edges as unknown as Edge[]);

    const rawEdges: Edge[] = data.graph.edges.map((e, i) => {
      const highlighted = selectedId != null && (e.source === selectedId || e.target === selectedId);
      return {
        id: `${e.source}->${e.target}-${i}`,
        source: e.source,
        target: e.target,
        type: "signal",
        data: { edgeType: e.type, highlighted },
      };
    });

    return { nodes: laidOut, edges: rawEdges };
  }, [data, selectedId, onSelect]);

  return (
    <div className="relative flex-1 blueprint-grid">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onPaneClick={() => onSelect(null)}
        fitView
        proOptions={{ hideAttribution: true }}
        defaultEdgeOptions={{ type: "signal" }}
      >
        <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="var(--border)" />
        <Controls
          showInteractive={false}
          className="!bg-[var(--bg-elevated)] !border !border-[var(--border)] !rounded-lg !shadow-none [&>button]:!bg-transparent [&>button]:!border-[var(--border)] [&>button]:!fill-[var(--text-secondary)]"
        />
        <MiniMap
          pannable
          zoomable
          maskColor="rgba(11,14,20,0.75)"
          className="!bg-[var(--bg-elevated)] !border !border-[var(--border)] !rounded-lg"
          nodeColor={() => "var(--border-bright)"}
        />
      </ReactFlow>

      <div
        className="absolute bottom-4 left-4 z-10 flex flex-col gap-1.5 px-3 py-2.5 rounded-lg border"
        style={{ background: "color-mix(in srgb, var(--bg-panel) 88%, transparent)", borderColor: "var(--border)" }}
      >
        {LEGEND.map(({ type, label }) => (
          <div key={type} className="flex items-center gap-2 text-[11px]" style={{ color: "var(--text-muted)" }}>
            <span className="w-2.5 h-2.5 rounded-full border-2" style={{ borderColor: `var(--node-${type === "api_endpoint" ? "api" : type === "db_model" ? "model" : type})`, background: "transparent" }} />
            {label}
          </div>
        ))}
      </div>
    </div>
  );
}
