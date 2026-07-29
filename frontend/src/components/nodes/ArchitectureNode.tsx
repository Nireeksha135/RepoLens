import { Handle, Position, type NodeProps } from "reactflow";
import type { NodeType } from "../../api/types";

export interface ArchNodeData {
  label: string;
  nodeType: NodeType;
  file: string | null;
  onSelect: (id: string) => void;
  isSelected: boolean;
}

// Mirrors the shape legend from the product spec:
//   o React Component | diamond API Endpoint | square Backend Service
//   hexagon DB Model | triangle External Service
const SHAPE_BY_TYPE: Record<NodeType, string> = {
  component: "rounded-full",
  api_endpoint: "rotate-45 rounded-sm",
  service: "rounded-md",
  db_model: "hexagon",
  file: "rounded-sm",
  function: "rounded-sm",
  class: "rounded-sm",
};

const COLOR_VAR_BY_TYPE: Record<NodeType, string> = {
  component: "--node-component",
  api_endpoint: "--node-api",
  service: "--node-service",
  db_model: "--node-model",
  file: "--node-file",
  function: "--node-file",
  class: "--node-file",
};

export default function ArchitectureNode({ data, id }: NodeProps<ArchNodeData>) {
  const colorVar = COLOR_VAR_BY_TYPE[data.nodeType];
  const shapeClass = SHAPE_BY_TYPE[data.nodeType];
  const color = `var(${colorVar})`;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => data.onSelect(id)}
      onKeyDown={(e) => e.key === "Enter" && data.onSelect(id)}
      className="group flex items-center gap-2.5 px-3 py-2.5 rounded-lg border transition-all cursor-pointer"
      style={{
        background: "var(--bg-elevated)",
        borderColor: data.isSelected ? color : "var(--border)",
        boxShadow: data.isSelected
          ? `0 0 0 1px ${color}, 0 0 16px -2px ${color}`
          : "none",
        minWidth: 176,
      }}
    >
      <Handle type="target" position={Position.Left} style={{ background: "var(--border-bright)", border: "none" }} />
      <span
        className={`shrink-0 w-3 h-3 border-2 ${shapeClass}`}
        style={{ borderColor: color, background: `${color}33` }}
        aria-hidden
      />
      <span className="font-mono text-[12px] leading-tight truncate" style={{ color: "var(--text-primary)" }}>
        {data.label}
      </span>
      <Handle type="source" position={Position.Right} style={{ background: "var(--border-bright)", border: "none" }} />
    </div>
  );
}
