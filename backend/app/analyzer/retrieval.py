"""
Feature 3 -- Ask RepoLens (retrieval half of the RAG pipeline).

Turns each analyzed file into a compact text "chunk" (path + imports +
functions + classes + API routes) and scores those chunks against a
question using plain term-frequency overlap -- no embeddings API, no
vector DB, runs offline in milliseconds. This is a deliberate v1 stand-in
for the embeddings -> vector DB step in the original product spec:

    Chunk important code -> Embeddings -> Vector DB -> retrieve -> LLM

Swap-in point: replace this module's internals with real embeddings (e.g.
sentence-transformers, or an embeddings API) + a vector store (Chroma,
pgvector, ...) later without touching callers -- it only exposes
`retrieve_relevant_files(files, question, k) -> list[FileChunk]`.

Also worth noting: chunks are built from *structural* analysis (imports,
functions, classes, routes), not raw source text, since source isn't kept
in memory after a repo is cloned, analyzed, and cleaned up (see
git_source.cleanup_repo). That's enough for architecture-level questions
("how does auth work", "where is X used") but not line-level code
questions -- persisting source snippets alongside FileAnalysis is the
natural next step if that's needed.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from .models import FileAnalysis

TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# Common English + code-question stopwords that would otherwise dominate
# scoring without adding any signal about *which* file is relevant.
STOPWORDS = {
    "the", "a", "an", "is", "are", "does", "how", "what", "where", "when",
    "why", "and", "or", "of", "to", "in", "for", "this", "that", "it",
    "with", "on", "do", "did", "work", "works", "implemented", "used",
}


@dataclass
class FileChunk:
    path: str
    text: str
    file: FileAnalysis


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text) if t.lower() not in STOPWORDS and len(t) > 1]


def _split_camel_snake(name: str) -> list[str]:
    """'AuthService' -> ['auth', 'service']; 'auth_service' -> ['auth', 'service']."""
    spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", name)
    return _tokenize(spaced.replace("_", " "))


def build_chunk(file: FileAnalysis) -> FileChunk:
    parts: list[str] = [file.path, file.language]
    for imp in file.imports:
        parts.append(imp.module)
        parts.extend(imp.names)
    for fn in file.functions:
        parts.append(fn.name)
    for cls in file.classes:
        parts.append(cls.name)
    for route in file.api_routes:
        parts.append(f"{route.method} {route.path}")
        parts.append(route.handler)

    tokens: list[str] = []
    for p in parts:
        tokens.extend(_split_camel_snake(p))
        tokens.extend(_tokenize(p))

    # Also index the actual source text (identifiers, string literals,
    # comments) when available -- this is what lets a question match on
    # something only present in code, not captured by any structural field
    # above (e.g. a variable name, a log message, a comment explaining why).
    if file.source_snippet:
        tokens.extend(_tokenize(file.source_snippet))

    return FileChunk(path=file.path, text=" ".join(tokens), file=file)


def _fuzzy_match(a: str, b: str, min_len: int = 4) -> bool:
    """True if a==b, or one is a prefix of the other and the shorter is at
    least min_len chars. Code abbreviates ("auth") while questions spell
    things out ("authentication") -- exact-only matching misses that
    entirely, so this is the difference between the retriever actually
    working on real code and only working on the toy fixture."""
    if a == b:
        return True
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    if len(shorter) < min_len:
        return False
    return longer.startswith(shorter)


def score_chunks(chunks: list[FileChunk], question: str) -> list[tuple[FileChunk, float]]:
    q_tokens: set[str] = set()
    for word in question.replace("?", " ").split():
        q_tokens.update(_split_camel_snake(word))
        q_tokens.update(_tokenize(word))
    if not q_tokens:
        return []

    scored: list[tuple[FileChunk, float]] = []
    for chunk in chunks:
        counts = Counter(chunk.text.split())
        overlap = 0
        for ctok, cnt in counts.items():
            if any(_fuzzy_match(ctok, qtok) for qtok in q_tokens):
                overlap += cnt
        if overlap == 0:
            continue
        # Light length-normalization so a huge file doesn't win purely on
        # having more tokens, without fully punishing genuinely relevant
        # large files.
        score = overlap / (len(chunk.text.split()) ** 0.3 + 1)
        scored.append((chunk, score))

    scored.sort(key=lambda pair: -pair[1])
    return scored


def retrieve_relevant_files(files: list[FileAnalysis], question: str, k: int = 6) -> list[FileChunk]:
    chunks = [build_chunk(f) for f in files]
    scored = score_chunks(chunks, question)
    return [chunk for chunk, _score in scored[:k]]
