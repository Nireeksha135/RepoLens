import { X } from "lucide-react";

export default function ChatAnswerPanel({
  question,
  answer,
  sources,
  loading,
  error,
  onClose,
  onSelectSource,
}: {
  question: string;
  answer: string | null;
  sources: string[];
  loading: boolean;
  error: string | null;
  onClose: () => void;
  onSelectSource: (path: string) => void;
}) {
  return (
    <div
      className="shrink-0 border-t px-4 py-3 flex flex-col gap-2 max-h-[240px] overflow-y-auto"
      style={{ background: "var(--bg-panel)", borderColor: "var(--border)" }}
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-[12px] font-mono" style={{ color: "var(--text-muted)" }}>
          {question}
        </p>
        <button onClick={onClose} aria-label="Close answer" className="p-1 rounded hover:opacity-70 shrink-0">
          <X size={14} color="var(--text-muted)" />
        </button>
      </div>

      {loading && (
        <p className="text-[13px]" style={{ color: "var(--text-muted)" }}>
          Retrieving relevant files and asking Claude…
        </p>
      )}

      {error && (
        <p className="text-[13px]" style={{ color: "var(--node-external)" }}>
          {error}
        </p>
      )}

      {answer && (
        <>
          <p className="text-[13px] whitespace-pre-wrap leading-relaxed" style={{ color: "var(--text-primary)" }}>
            {answer}
          </p>
          {sources.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5 mt-1">
              <span className="text-[10px] uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                Sources
              </span>
              {sources.map((path) => (
                <button
                  key={path}
                  onClick={() => onSelectSource(path)}
                  className="font-mono text-[11px] px-1.5 py-0.5 rounded border hover:opacity-80"
                  style={{ borderColor: "var(--signal)", color: "var(--signal)" }}
                >
                  {path.split("/").pop()}
                </button>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
