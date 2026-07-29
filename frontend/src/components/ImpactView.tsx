import { useState } from "react";
import { Zap, ArrowRight } from "lucide-react";
import { analyzeImpact, type ImpactResponse, type ImpactedNode } from "../api/impact";
import type { AnalyzeResponse } from "../api/types";

const SEVERITY_COLOR: Record<string, string> = {
  HIGH: "var(--node-external)",
  MEDIUM: "var(--node-model)",
  LOW: "var(--node-file)",
};

export default function ImpactView({
  data,
  onViewInArchitecture,
}: {
  data: AnalyzeResponse;
  onViewInArchitecture: (nodeId: string) => void;
}) {
  // Only files make sense as "things you'd change" -- route/endpoint nodes
  // are derived, not editable source.
  const fileNodes = data.graph.nodes.filter((n) => n.file);

  const [target, setTarget] = useState<string>(fileNodes[0]?.id ?? "");
  const [result, setResult] = useState<ImpactResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runAnalysis() {
    if (!target) return;
    setLoading(true);
    setError(null);
    try {
      const res = await analyzeImpact(data.graph.nodes, data.graph.edges, target);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not analyze impact.");
    } finally {
      setLoading(false);
    }
  }

  const totalImpacted = result ? result.high.length + result.medium.length + result.low.length : 0;

  return (
    <div className="flex-1 flex flex-col min-w-0 overflow-y-auto blueprint-grid">
      <div className="max-w-3xl w-full mx-auto p-8 flex flex-col gap-6">
        <div>
          <h1 className="font-display font-semibold text-[18px] flex items-center gap-2" style={{ color: "var(--text-primary)" }}>
            <Zap size={17} color="var(--signal)" />
            Change Impact Analysis
          </h1>
          <p className="text-[13px] mt-1" style={{ color: "var(--text-muted)" }}>
            Pick a file to see what breaks if you change it.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={target}
            onChange={(e) => {
              setTarget(e.target.value);
              setResult(null);
            }}
            className="flex-1 px-3 py-2.5 rounded-md text-[13px] font-mono outline-none"
            style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
          >
            {fileNodes.map((n) => (
              <option key={n.id} value={n.id}>
                {n.file}
              </option>
            ))}
          </select>
          <button
            onClick={runAnalysis}
            disabled={loading}
            className="px-4 py-2.5 rounded-md text-[13px] font-medium shrink-0 transition-opacity hover:opacity-90 disabled:opacity-50"
            style={{ background: "var(--signal)", color: "var(--bg-base)" }}
          >
            {loading ? "Analyzing…" : "Analyze Impact"}
          </button>
        </div>

        {error && (
          <p className="text-[12px]" style={{ color: "var(--node-external)" }}>
            {error}
          </p>
        )}

        {result && (
          <div className="flex flex-col gap-6">
            <p className="text-[12px] font-mono" style={{ color: "var(--text-muted)" }}>
              Changing <span style={{ color: "var(--text-secondary)" }}>{result.target}</span> may affect{" "}
              <span style={{ color: "var(--text-primary)" }}>{totalImpacted}</span> other node
              {totalImpacted === 1 ? "" : "s"}.
            </p>

            {totalImpacted === 0 ? (
              <p className="text-[13px]" style={{ color: "var(--text-muted)" }}>
                Nothing in the analyzed graph depends on this file — it looks safe to change in isolation.
              </p>
            ) : (
              (["HIGH", "MEDIUM", "LOW"] as const).map((severity) => {
                const bucket = severity === "HIGH" ? result.high : severity === "MEDIUM" ? result.medium : result.low;
                if (bucket.length === 0) return null;
                return (
                  <SeverityGroup
                    key={severity}
                    severity={severity}
                    nodes={bucket}
                    onViewInArchitecture={onViewInArchitecture}
                  />
                );
              })
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function SeverityGroup({
  severity,
  nodes,
  onViewInArchitecture,
}: {
  severity: "HIGH" | "MEDIUM" | "LOW";
  nodes: ImpactedNode[];
  onViewInArchitecture: (nodeId: string) => void;
}) {
  const color = SEVERITY_COLOR[severity];
  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <span className="w-2 h-2 rounded-full" style={{ background: color }} />
        <span className="text-[11px] font-medium uppercase tracking-wider" style={{ color }}>
          {severity} impact
        </span>
        <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
          ({nodes.length})
        </span>
      </div>
      <div className="flex flex-col gap-1.5">
        {nodes.map((n) => (
          <button
            key={n.id}
            onClick={() => onViewInArchitecture(n.id)}
            className="text-left p-3 rounded-md border transition-colors hover:border-[var(--border-bright)]"
            style={{ background: "var(--bg-elevated)", borderColor: "var(--border)" }}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono text-[13px]" style={{ color: "var(--text-primary)" }}>
                {n.label}
              </span>
              <span className="text-[11px] font-mono shrink-0" style={{ color: "var(--text-muted)" }}>
                {n.hops} hop{n.hops === 1 ? "" : "s"}
              </span>
            </div>
            <div className="flex items-center gap-1 mt-1.5 flex-wrap text-[11px] font-mono" style={{ color: "var(--text-muted)" }}>
              {n.path.map((step, i) => (
                <span key={step} className="flex items-center gap-1">
                  {i > 0 && <ArrowRight size={10} />}
                  {step.split("/").pop()?.replace(/^route::/, "")}
                </span>
              ))}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
