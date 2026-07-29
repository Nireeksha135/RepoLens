import {
  LayoutGrid,
  FolderTree,
  Waypoints,
  Radio,
  Database,
  Zap,
  MessageSquare,
} from "lucide-react";

export type View = "overview" | "explorer" | "architecture" | "apis" | "database" | "impact" | "chat";

const ITEMS: { id: View; label: string; icon: React.ComponentType<{ size?: number }> }[] = [
  { id: "overview", label: "Overview", icon: LayoutGrid },
  { id: "explorer", label: "Explorer", icon: FolderTree },
  { id: "architecture", label: "Architecture", icon: Waypoints },
  { id: "apis", label: "APIs", icon: Radio },
  { id: "database", label: "Database", icon: Database },
  { id: "impact", label: "Impact", icon: Zap },
  { id: "chat", label: "AI Chat", icon: MessageSquare },
];

export default function Sidebar({
  active,
  onSelect,
}: {
  active: View;
  onSelect: (v: View) => void;
}) {
  return (
    <nav
      className="w-[168px] shrink-0 flex flex-col py-4 px-2 gap-1 border-r"
      style={{ background: "var(--bg-panel)", borderColor: "var(--border)" }}
      aria-label="Primary"
    >
      <div className="flex items-center gap-2 px-2 mb-5">
        <span
          className="w-2 h-2 rounded-full"
          style={{ background: "var(--signal)", boxShadow: "0 0 8px var(--signal)" }}
        />
        <span className="font-display font-semibold text-[13px] tracking-wide" style={{ color: "var(--text-primary)" }}>
          RepoLens
        </span>
      </div>

      {ITEMS.map(({ id, label, icon: Icon }) => {
        const isActive = active === id;
        return (
          <button
            key={id}
            onClick={() => onSelect(id)}
            className="flex items-center gap-2.5 px-2.5 py-2 rounded-md text-[13px] font-medium transition-colors text-left"
            style={{
              background: isActive ? "var(--bg-elevated)" : "transparent",
              color: isActive ? "var(--text-primary)" : "var(--text-muted)",
              borderLeft: isActive ? "2px solid var(--signal)" : "2px solid transparent",
            }}
          >
            <Icon size={15} />
            {label}
          </button>
        );
      })}
    </nav>
  );
}
