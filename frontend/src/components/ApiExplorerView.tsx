import { useEffect, useState } from "react";
import { Radio } from "lucide-react";
import { fetchApiRoutes, type ApiRouteSummary } from "../api/apiExplorer";
import type { AnalyzeResponse } from "../api/types";

const METHOD_COLOR: Record<string, string> = {
  GET: "var(--node-component)",
  POST: "var(--node-api)",
  PUT: "var(--node-model)",
  DELETE: "var(--node-external)",
  PATCH: "var(--node-service)",
};

function buildHandlerMap(data: AnalyzeResponse): Record<string, string> {
  const map: Record<string, string> = {};
  for (const f of data.files) {
    for (const r of f.api_routes) {
      if (r.handler === "(client call)") continue;
      map[`route::${r.method}:${r.path}`] = r.handler;
    }
  }
  return map;
}

export default function ApiExplorerView({
  data,
  onNavigate,
}: {
  data: AnalyzeResponse;
  onNavigate: (nodeId: string) => void;
}) {
  const [routes, setRoutes] = useState<ApiRouteSummary[] | null>(null);
  const [selected, setSelected] = useState<ApiRouteSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchApiRoutes(data.graph.nodes, data.graph.edges, buildHandlerMap(data))
      .then((res) => {
        if (cancelled) return;
        setRoutes(res);
        setSelected(res[0] ?? null);
      })
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : "Could not load API routes."))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [data]);

  return (
    <div className="flex-1 flex min-w-0">
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        <div className="px-6 py-5 border-b" style={{ borderColor: "var(--border)" }}>
          <h1
            className="font-display font-semibold text-[18px] flex items-center gap-2"
            style={{ color: "var(--text-primary)" }}
          >
            <Radio size={17} color="var(--signal)" />
            API Explorer
          </h1>
          <p className="text-[13px] mt-1" style={{ color: "var(--text-muted)" }}>
            {routes ? `${routes.length} route${routes.length === 1 ? "" : "s"} discovered` : "Discovering routes…"}
          </p>
        </div>

        {error && (
          <p className="p-6 text-[12px]" style={{ color: "var(--node-external)" }}>
            {error}
          </p>
        )}

        <div className="flex flex-col">
          {loading && !routes && (
            <p className="p-6 text-[13px]" style={{ color: "var(--text-muted)" }}>
              Loading…
            </p>
          )}
          {routes?.length === 0 && !loading && (
            <p className="p-6 text-[13px]" style={{ color: "var(--text-muted)" }}>
              No API routes were detected in this repository.
            </p>
          )}
          {routes?.map((r) => (
            <button
              key={r.route_id}
              onClick={() => setSelected(r)}
              className="flex items-center gap-3 px-6 py-3 border-b text-left transition-colors"
              style={{
                borderColor: "var(--border)",
                background: selected?.route_id === r.route_id ? "var(--bg-elevated)" : "transparent",
              }}
            >
              <span
                className="font-mono text-[11px] font-medium px-1.5 py-0.5 rounded shrink-0 w-14 text-center"
                style={{
                  color: METHOD_COLOR[r.method] ?? "var(--text-muted)",
                  border: `1px solid ${METHOD_COLOR[r.method] ?? "var(--border)"}`,
                }}
              >
                {r.method}
              </span>
              <span className="font-mono text-[13px]" style={{ color: "var(--text-primary)" }}>
                {r.path}
              </span>
            </button>
          ))}
        </div>
      </div>

      {selected && (
        <aside
          className="w-[300px] shrink-0 border-l p-5 flex flex-col gap-5 overflow-y-auto"
          style={{ background: "var(--bg-panel)", borderColor: "var(--border)" }}
        >
          <div>
            <span
              className="font-mono text-[11px] font-medium px-1.5 py-0.5 rounded"
              style={{
                color: METHOD_COLOR[selected.method] ?? "var(--text-muted)",
                border: `1px solid ${METHOD_COLOR[selected.method] ?? "var(--border)"}`,
              }}
            >
              {selected.method}
            </span>
            <p className="font-mono text-[14px] mt-2 break-all" style={{ color: "var(--text-primary)" }}>
              {selected.path}
            </p>
          </div>

          <Field label="Defined in" value={selected.defined_in} onClick={onNavigate} />
          <Field label="Controller" value={selected.controller ? `${selected.controller}()` : null} />
          <ListField label="Uses" items={selected.uses} onNavigate={onNavigate} />
          <ListField label="Database Model" items={selected.database_models} onNavigate={onNavigate} />
          <ListField label="Called by" items={selected.called_by} onNavigate={onNavigate} />
        </aside>
      )}
    </div>
  );
}

function Field({ label, value, onClick }: { label: string; value: string | null; onClick?: (id: string) => void }) {
  if (!value) return null;
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider mb-1.5" style={{ color: "var(--text-muted)" }}>
        {label}
      </p>
      {onClick ? (
        <button
          onClick={() => onClick(value)}
          className="font-mono text-[12px] hover:underline text-left break-all"
          style={{ color: "var(--node-component)" }}
        >
          {value}
        </button>
      ) : (
        <p className="font-mono text-[12px]" style={{ color: "var(--text-secondary)" }}>
          {value}
        </p>
      )}
    </div>
  );
}

function ListField({
  label,
  items,
  onNavigate,
}: {
  label: string;
  items: string[];
  onNavigate: (id: string) => void;
}) {
  if (items.length === 0) return null;
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider mb-1.5" style={{ color: "var(--text-muted)" }}>
        {label}
      </p>
      <div className="flex flex-col gap-1">
        {items.map((id) => (
          <button
            key={id}
            onClick={() => onNavigate(id)}
            className="font-mono text-[12px] text-left hover:underline break-all"
            style={{ color: "var(--node-component)" }}
          >
            {id.split("/").pop()}
          </button>
        ))}
      </div>
    </div>
  );
}
