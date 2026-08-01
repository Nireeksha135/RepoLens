import { useMemo, useState } from "react";
import { analyzeRepo } from "./api/client";
import { askRepoLens } from "./api/chat";
import type { AnalyzeResponse } from "./api/types";
import ApiExplorerView from "./components/ApiExplorerView";
import AskBar from "./components/AskBar";
import ChatAnswerPanel from "./components/ChatAnswerPanel";
import DetailPanel from "./components/DetailPanel";
import GraphView from "./components/GraphView";
import ImpactView from "./components/ImpactView";
import OverviewStats from "./components/OverviewStats";
import Sidebar, { type View } from "./components/Sidebar";

interface ChatState {
  question: string;
  answer: string | null;
  sources: string[];
  loading: boolean;
  error: string | null;
}

export default function App() {
  const [repoUrl, setRepoUrl] = useState("");
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<View>("architecture");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [chat, setChat] = useState<ChatState | null>(null);

  const nodesById = useMemo(
    () => new Map((data?.graph.nodes ?? []).map((n) => [n.id, n])),
    [data]
  );
  const selectedNode = selectedId ? nodesById.get(selectedId) ?? null : null;
  const selectedFile = data?.files.find((f) => f.path === selectedNode?.file);

  const highlightedIds = useMemo(
    () => (chat?.sources.length ? new Set(chat.sources) : undefined),
    [chat?.sources]
  );

  async function handleAnalyze() {
    if (!repoUrl.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeRepo(repoUrl.trim());
      setData(result);
      setSelectedId(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not analyze that repository.");
    } finally {
      setLoading(false);
    }
  }

  async function handleAsk(question: string) {
    if (!data) return;
    setChat({ question, answer: null, sources: [], loading: true, error: null });
    try {
      const res = await askRepoLens(data.files, question);
      setChat({ question, answer: res.answer, sources: res.sources, loading: false, error: null });
    } catch (e) {
      const message = e instanceof Error ? e.message : "Could not get an answer.";
      setChat({ question, answer: null, sources: [], loading: false, error: message });
    }
  }

  function goToNode(nodeId: string) {
    setSelectedId(nodeId);
    setView("architecture");
  }

  if (!data) {
    return (
      <div className="h-full flex items-center justify-center blueprint-grid">
        <div
          className="w-full max-w-md flex flex-col gap-4 p-6 rounded-xl border"
          style={{ background: "var(--bg-panel)", borderColor: "var(--border)" }}
        >
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full" style={{ background: "var(--signal)", boxShadow: "0 0 8px var(--signal)" }} />
            <h1 className="font-display font-semibold text-[15px]">RepoLens</h1>
          </div>
          <p className="text-[13px]" style={{ color: "var(--text-muted)" }}>
            Paste a GitHub repository URL to trace how it's wired together.
          </p>
          <input
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAnalyze()}
            placeholder="github.com/user/project"
            className="px-3 py-2.5 rounded-md text-[13px] font-mono outline-none"
            style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
          />
          <button
            onClick={handleAnalyze}
            disabled={loading}
            className="px-3 py-2.5 rounded-md text-[13px] font-medium transition-opacity hover:opacity-90 disabled:opacity-50"
            style={{ background: "var(--signal)", color: "var(--bg-base)" }}
          >
            {loading ? "Analyzing repository…" : "Analyze Repository"}
          </button>
          {error && (
            <p className="text-[12px]" style={{ color: "var(--node-external)" }}>
              {error}
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex" style={{ background: "var(--bg-base)" }}>
      <Sidebar active={view} onSelect={setView} />

      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex-1 flex min-h-0">
          {view === "impact" && <ImpactView data={data} onViewInArchitecture={goToNode} />}

          {view === "apis" && <ApiExplorerView data={data} onNavigate={goToNode} />}

          {view !== "impact" && view !== "apis" && (
            <div className="relative flex-1 flex flex-col min-w-0">
              <OverviewStats overview={data.overview} repoName={data.repo_name} />
              <GraphView
                data={data}
                selectedId={selectedId}
                onSelect={setSelectedId}
                highlightedIds={highlightedIds}
              />
            </div>
          )}

          {view !== "impact" && view !== "apis" && selectedNode && (
            <DetailPanel
              node={selectedNode}
              file={selectedFile}
              edges={data.graph.edges}
              nodesById={nodesById}
              onClose={() => setSelectedId(null)}
              onSelect={setSelectedId}
            />
          )}
        </div>

        {chat && (
          <ChatAnswerPanel
            question={chat.question}
            answer={chat.answer}
            sources={chat.sources}
            loading={chat.loading}
            error={chat.error}
            onClose={() => setChat(null)}
            onSelectSource={goToNode}
          />
        )}

        <AskBar onAsk={handleAsk} />
      </div>
    </div>
  );
}
