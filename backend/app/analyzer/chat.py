SYSTEM_PROMPT = """You are RepoLens, a codebase intelligence assistant. Answer \
questions about a specific repository using ONLY the context provided below \
-- each file's imports, functions, classes, API routes, and a source code \
excerpt (which may be truncated for long files). If the context doesn't \
contain enough to answer confidently, say so plainly instead of guessing.

When you describe a flow through the code, show it as a chain, e.g.:
LoginPage.tsx -> authApi.ts -> POST /api/auth/login -> auth.py -> AuthService -> User
"""


class ChatConfigError(Exception):
    """Raised when the backend isn't configured to answer chat questions
    (missing API key) -- distinct from a normal empty/low-confidence answer."""


def _format_context(chunks: list[FileChunk]) -> str:
    blocks = []
    for chunk in chunks:
        f: FileAnalysis = chunk.file
        lines = [f"### {f.path} ({f.language})"]
        if f.imports:
            lines.append("imports: " + ", ".join(sorted({i.module for i in f.imports})))
        if f.functions:
            lines.append("functions: " + ", ".join(fn.name for fn in f.functions))
        if f.classes:
            lines.append("classes: " + ", ".join(c.name for c in f.classes))
        real_routes = [r for r in f.api_routes if r.handler != "(client call)"]
        if real_routes:
            lines.append("routes: " + ", ".join(f"{r.method} {r.path}" for r in real_routes))
        if f.source_snippet:
            lines.append(f"```{f.language.lower()}\n{f.source_snippet}\n```")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)
