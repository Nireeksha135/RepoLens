# RepoLens

AI-powered codebase intelligence: paste a GitHub repository and get back an
interactive architecture map showing how the frontend, API, services, and
database models actually connect.

```
LoginPage.tsx  --imports-->  authApi.ts  --calls-->  POST /api/auth/login
                                                              |
                                                          defines
                                                              |
                                                        auth.py  --imports-->  auth_service.py  --imports-->  user.py
```

That chain isn't a mockup — it's real output from the analyzer in this repo.

## Status

| Feature (from the product spec)      | Status         |
|---------------------------------------|----------------|
| 1. Repository Analyzer                | ✅ built (`backend/`) |
| 2. Interactive Architecture Map       | ✅ built (`frontend/`) |
| 3. Ask RepoLens (AI Q&A / RAG)        | 🔲 not started — UI is wired up, needs a `/chat` backend endpoint |
| 4. Change Impact Analysis             | 🔲 not started — the `networkx.DiGraph` built in `graph_builder.py` already has everything needed (BFS from a node) |
| 5. API Explorer                       | 🔲 not started — data already exists in `/analyze` response (`api_routes` per file) |
| 6. Database Relationship Viewer       | 🔲 not started |
| 7. Repository Explorer (file tree)    | 🔲 not started |

v1 scope, per the spec: React + FastAPI projects only. Python parsing uses
the standard library `ast` module; JS/TS parsing is a lightweight regex-based
parser (see the note in `js_parser.py` about swapping in Tree-sitter later).

## Architecture

```
repolens/
├── backend/                  FastAPI service — Feature 1
│   ├── app/
│   │   ├── analyzer/
│   │   │   ├── scanner.py        walks the repo, computes language breakdown
│   │   │   ├── python_parser.py  ast-based: imports, functions, classes, FastAPI routes
│   │   │   ├── js_parser.py      regex-based: imports, components, axios/fetch calls
│   │   │   ├── graph_builder.py  resolves imports to files, builds the dependency graph (networkx)
│   │   │   ├── git_source.py     clones a GitHub repo into a temp dir
│   │   │   ├── models.py         shared dataclasses (FileAnalysis, GraphNode, GraphEdge, ...)
│   │   │   └── analyzer.py       orchestrates the above into analyze_github_repo()
│   │   └── main.py               POST /analyze
│   ├── tests/test_analyzer.py    10 tests, incl. an end-to-end fixture repo
│   └── requirements.txt
│
└── frontend/                 React + TypeScript + React Flow — Feature 2
    └── src/
        ├── api/               types + client matching the backend's JSON contract
        ├── layout/autoLayout.ts   dagre auto-layout (backend graph has no x/y)
        └── components/
            ├── GraphView.tsx      React Flow canvas, legend
            ├── nodes/ArchitectureNode.tsx   shape+color per node category
            ├── SignalEdge.tsx     animated "signal trace" edges (see Design below)
            ├── Sidebar.tsx        left rail nav
            ├── OverviewStats.tsx  floating stat chips + language bar
            ├── DetailPanel.tsx    right-side panel on node click
            └── AskBar.tsx         bottom-docked input (UI only — see Feature 3)
```

**How analysis becomes a graph:** the backend never asks an LLM to guess
relationships. `python_parser.py` walks a real Python AST; `js_parser.py`
pattern-matches real import/call syntax. `graph_builder.py` then resolves
each import string to an actual file in the repo (handling both `./relative`
and Python's `backend.services.auth` absolute-style imports) and wires up
`imports` / `calls` / `defines` edges. The frontend does no interpretation —
it just lays out and renders exactly what the backend resolved.

## Design

The brief called for something dark and developer-tool-ish rather than
another pastel SaaS dashboard, so the frontend leans into a **schematic /
blueprint** aesthetic: a navy-black canvas with a dot-grid backdrop, node
categories color-coded like a legend (cyan components, violet services,
emerald endpoints, gold DB models), and — the one deliberate flourish —
**edges rendered as glowing signal traces with a pulse animating along the
path**, like current moving through a circuit. That's not decoration; it's
the literal thesis of the product (RepoLens visualizes how data flows
through a codebase), so the one animated element on the page is spent
reinforcing that idea. Typography is Space Grotesk for UI chrome, IBM Plex
Sans for body text, and JetBrains Mono for anything that's actually code
(file paths, function names, stats).

## Running it locally

**Backend**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
# -> http://localhost:8000, POST /analyze { "repo_url": "..." }
```

**Backend tests**
```bash
cd backend
pip install pytest
pytest tests/ -v
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
# -> http://localhost:5173, proxies /api/* to the backend on :8000
```

Then open the app and paste a GitHub URL (small repos work best while
cloning is synchronous — see Known limitations).

## Known limitations / next steps

- **Cloning is synchronous and unbounded.** A large repo will block the
  request. Next step: background job + polling, and a repo size cap.
- **JS/TS parsing is regex-based, not a real parser.** It covers the
  patterns that show up in typical React/Express code but will miss
  unusual syntax. `js_parser.py` is written as a drop-in seam for a real
  Tree-sitter grammar later.
- **No caching.** Every analysis re-clones and re-parses from scratch.
  Worth caching by commit SHA once this is more than a demo.
- **Feature 3 (Ask RepoLens)** needs: chunk important files → embeddings →
  vector DB → retrieve on question → LLM with retrieved context, per the
  RAG pipeline in the original spec. The `AskBar` component already exists
  and calls an `onAsk` handler — it just doesn't hit a real endpoint yet.
- **Feature 4 (Change Impact Analysis)** is mostly free: `graph_builder.py`
  already returns a `networkx.DiGraph`. Impact = BFS/DFS from the selected
  node, bucketed by hop distance into HIGH/MEDIUM/LOW.
