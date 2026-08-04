"""
Feature 3 -- Ask RepoLens (generation half of the RAG pipeline).

Takes the files retrieval.py judged relevant, builds a compact context
block (structure + real source snippets), and asks Gemini to answer using
only that context -- same "retrieve then generate" shape as any RAG
system, just scoped to a repository's structure instead of documents.

Uses Gemini (via the `google-genai` SDK -- not the older, now-deprecated
`google-generativeai` package) specifically because its free tier is
actually free for a solo/demo project, unlike pay-per-token APIs.

Requires GEMINI_API_KEY in the environment. This never falls back to
guessing without a key -- callers get a clear, typed error instead of a
silently wrong answer.
"""
from __future__ import annotations

import os

from google import genai
from google.genai import types

from .models import FileAnalysis
from .retrieval import FileChunk, retrieve_relevant_files

# Update this if/when a newer/better free-tier model should be used -- kept
# as one constant rather than scattered through the module. Check
# https://ai.google.dev/gemini-api/docs/models for current free-tier limits
# and model names before relying on this in production; both can change.
MODEL = "gemini-2.0-flash"

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


def ask_repolens(files: list[FileAnalysis], question: str) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ChatConfigError(
            "GEMINI_API_KEY is not set. Ask RepoLens needs a Gemini API key "
            "in the backend environment to generate answers."
        )

    relevant = retrieve_relevant_files(files, question, k=6)
    context = _format_context(relevant)

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=MODEL,
        contents=f"Repository context:\n\n{context}\n\nQuestion: {question}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=1000,
        ),
    )

    answer_text = response.text or ""

    return {"answer": answer_text, "sources": [c.path for c in relevant]}
