import type { RepoOverview } from "../api/types";

const LANG_COLORS: Record<string, string> = {
  Python: "var(--node-service)",
  TypeScript: "var(--node-component)",
  JavaScript: "#f2c94c",
  CSS: "var(--node-model)",
  HTML: "var(--node-external)",
  Markdown: "var(--text-muted)",
  JSON: "var(--text-muted)",
  YAML: "var(--text-muted)",
  SQL: "var(--node-api)",
  Other: "var(--text-muted)",
};

function StatChip({ label, value }: { label: string; value: number }) {
  return (
    <div
      className="flex items-baseline gap-1.5 px-3 py-1.5 rounded-md border"
      style={{ background: "var(--bg-elevated)", borderColor: "var(--border)" }}
    >
      <span className="font-mono text-[15px] font-medium" style={{ color: "var(--text-primary)" }}>
        {value}
      </span>
      <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
        {label}
      </span>
    </div>
  );
}

export default function OverviewStats({ overview, repoName }: { overview: RepoOverview; repoName: string }) {
  const entries = Object.entries(overview.language_breakdown);

  return (
    <div
      className="absolute top-4 left-4 right-4 z-10 flex flex-wrap items-center gap-3 px-3 py-3 rounded-lg border backdrop-blur-sm"
      style={{ background: "color-mix(in srgb, var(--bg-panel) 88%, transparent)", borderColor: "var(--border)" }}
    >
      <span className="font-mono text-[12px] px-2" style={{ color: "var(--text-secondary)" }}>
        {repoName}
      </span>
      <div className="w-px h-5" style={{ background: "var(--border)" }} />
      <StatChip label="files" value={overview.total_files} />
      <StatChip label="components" value={overview.total_components} />
      <StatChip label="endpoints" value={overview.total_api_endpoints} />
      <StatChip label="models" value={overview.total_db_models} />
      <div className="w-px h-5" style={{ background: "var(--border)" }} />

      <div className="flex items-center gap-1 flex-1 min-w-[160px]">
        <div className="flex h-2 flex-1 rounded-full overflow-hidden" style={{ background: "var(--bg-elevated)" }}>
          {entries.map(([lang, pct]) => (
            <div
              key={lang}
              style={{ width: `${pct}%`, background: LANG_COLORS[lang] ?? "var(--text-muted)" }}
              title={`${lang} ${pct}%`}
            />
          ))}
        </div>
      </div>
      {entries.slice(0, 3).map(([lang, pct]) => (
        <span key={lang} className="text-[11px] font-mono flex items-center gap-1.5" style={{ color: "var(--text-muted)" }}>
          <span className="w-2 h-2 rounded-full inline-block" style={{ background: LANG_COLORS[lang] ?? "var(--text-muted)" }} />
          {lang} {pct}%
        </span>
      ))}
    </div>
  );
}
