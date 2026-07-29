import { X } from "lucide-react";
import type { FileAnalysis, GraphEdge, GraphNode } from "../api/types";

const TYPE_LABEL: Record<string, string> = {
  component: "React Component",
  service: "Backend Service",
  api_endpoint: "API Endpoint",
  db_model: "Database Model",
  file: "File",
};

export default function DetailPanel({
  node,
  file,
  edges,
  nodesById,
  onClose,
  onSelect,
}: {
  node: GraphNode;
  file: FileAnalysis | undefined;
  edges: GraphEdge[];
  nodesById: Map<string, GraphNode>;
  onClose: () => void;
  onSelect: (id: string) => void;
}) {
  const usedBy = edges.filter((e) => e.target === node.id && e.type === "imports");
  const calls = edges.filter((e) => e.source === node.id && (e.type === "calls" || e.type === "imports"));
  const externalDeps = (file?.imports ?? []).filter((i) => !i.is_relative).map((i) => i.module);

  return (
    <aside
      className="w-[300px] shrink-0 border-l flex flex-col overflow-y-auto"
      style={{ background: "var(--bg-panel)", borderColor: "var(--border)" }}
    >
      <div className="flex items-start justify-between p-4 border-b" style={{ borderColor: "var(--border)" }}>
        <div>
          <p className="font-mono text-[13px] font-medium break-all" style={{ color: "var(--text-primary)" }}>
            {node.label}
          </p>
          <p className="text-[11px] mt-1" style={{ color: "var(--text-muted)" }}>
            {TYPE_LABEL[node.type] ?? node.type}
          </p>
        </div>
        <button onClick={onClose} aria-label="Close panel" className="p-1 rounded hover:opacity-70">
          <X size={16} color="var(--text-muted)" />
        </button>
      </div>

      <div className="p-4 flex flex-col gap-5 text-[12px]">
        {node.file && (
          <Section title="Path">
            <p className="font-mono break-all" style={{ color: "var(--text-secondary)" }}>{node.file}</p>
          </Section>
        )}

        {usedBy.length > 0 && (
          <Section title="Used by">
            <ChipList items={usedBy.map((e) => e.source)} nodesById={nodesById} onSelect={onSelect} />
          </Section>
        )}

        {calls.length > 0 && (
          <Section title="Calls">
            <ChipList items={calls.map((e) => e.target)} nodesById={nodesById} onSelect={onSelect} />
          </Section>
        )}

        {file && file.functions.length > 0 && (
          <Section title={`Functions (${file.functions.length})`}>
            <ul className="flex flex-col gap-1">
              {file.functions.slice(0, 8).map((fn) => (
                <li key={fn.name} className="font-mono" style={{ color: "var(--text-secondary)" }}>
                  {fn.is_async && <span style={{ color: "var(--node-service)" }}>async </span>}
                  {fn.name}()
                </li>
              ))}
            </ul>
          </Section>
        )}

        {externalDeps.length > 0 && (
          <Section title="Dependencies">
            <div className="flex flex-wrap gap-1.5">
              {externalDeps.slice(0, 10).map((dep) => (
                <span
                  key={dep}
                  className="font-mono text-[11px] px-1.5 py-0.5 rounded border"
                  style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
                >
                  {dep}
                </span>
              ))}
            </div>
          </Section>
        )}
      </div>
    </aside>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider mb-2" style={{ color: "var(--text-muted)" }}>
        {title}
      </p>
      {children}
    </div>
  );
}

function ChipList({
  items,
  nodesById,
  onSelect,
}: {
  items: string[];
  nodesById: Map<string, GraphNode>;
  onSelect: (id: string) => void;
}) {
  return (
    <ul className="flex flex-col gap-1.5">
      {items.map((id) => {
        const n = nodesById.get(id);
        return (
          <li key={id}>
            <button
              onClick={() => onSelect(id)}
              className="font-mono text-left hover:underline"
              style={{ color: "var(--node-component)" }}
            >
              {n?.label ?? id}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
