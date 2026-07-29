import { useState } from "react";
import { ArrowRight } from "lucide-react";

export default function AskBar({ onAsk }: { onAsk: (question: string) => void }) {
  const [value, setValue] = useState("");

  const submit = () => {
    if (!value.trim()) return;
    onAsk(value.trim());
    setValue("");
  };

  return (
    <div
      className="shrink-0 flex items-center gap-3 px-4 py-3 border-t"
      style={{ background: "var(--bg-panel)", borderColor: "var(--border)" }}
    >
      <span className="text-[11px] font-medium shrink-0" style={{ color: "var(--text-muted)" }}>
        Ask RepoLens
      </span>
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && submit()}
        placeholder="How does authentication work?"
        className="flex-1 px-3 py-2 rounded-md text-[13px] font-mono outline-none"
        style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
      />
      <button
        onClick={submit}
        className="flex items-center gap-1.5 px-3 py-2 rounded-md text-[12px] font-medium shrink-0 transition-opacity hover:opacity-90"
        style={{ background: "var(--signal)", color: "var(--bg-base)" }}
      >
        Ask <ArrowRight size={13} />
      </button>
    </div>
  );
}
