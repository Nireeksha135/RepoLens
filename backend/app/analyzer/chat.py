"""
Feature 3 -- Ask RepoLens (generation half of the RAG pipeline).

Takes the files retrieval.py judged relevant, builds a compact structural
context block, and asks Claude to answer using only that context -- same
"retrieve then generate" shape as any RAG system, just scoped to a
repository's structure instead of documents.

Requires ANTHROPIC_API_KEY in the environment. This never falls back to
guessing without a key -- callers get a clear, typed error instead of a
silently wrong answer.
"""
from __future__ import annotations

import os

from anthropic import Anthropic

from .models import FileAnalysis
from .retrieval import FileChunk, retrieve_relevant_files

# Update this if/when a newer model should be used -- kept as one constant
# rather than scattered through the module.
MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = """You are RepoLens, a codebase intelligence assistant. Answer \
questions about a specific repository using ONLY the structural context \
provided below (each file's imports, functions, classes, and API routes -- \
not full source code). If the context doesn't contain enough to answer \
confidently, say so plainly instead of guessing.

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
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def ask_repolens(files: list[FileAnalysis], question: str) -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ChatConfigError(
            "ANTHROPIC_API_KEY is not set. Ask RepoLens needs an Anthropic API "
            "key in the backend environment to generate answers."
        )

    relevant = retrieve_relevant_files(files, question, k=6)
    context = _format_context(relevant)

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"Repository context:\n\n{context}\n\nQuestion: {question}"}
        ],
    )

    answer_text = "".join(block.text for block in response.content if block.type == "text")

    return {"answer": answer_text, "sources": [c.path for c in relevant]}
