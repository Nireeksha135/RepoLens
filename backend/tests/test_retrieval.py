"""
Tests for Feature 3's retrieval layer.

Only tests retrieval.py -- chat.py's ask_repolens() makes a real network
call to the Anthropic API and needs ANTHROPIC_API_KEY, so it's out of scope
for a fast, offline unit test suite. What matters most to get right without
a live LLM call is: does asking about "authentication" actually surface the
auth-related files over unrelated ones?
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.analyzer.analyzer import analyze_local_repo
from app.analyzer.retrieval import retrieve_relevant_files


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    (tmp_path / "backend/routes").mkdir(parents=True)
    (tmp_path / "backend/services").mkdir(parents=True)
    (tmp_path / "backend/models").mkdir(parents=True)

    (tmp_path / "backend/routes/auth.py").write_text(
        "from fastapi import APIRouter\n"
        "from backend.services.auth_service import AuthService\n"
        "router = APIRouter()\n"
        "@router.post('/api/auth/login')\n"
        "def login(email: str, password: str):\n"
        "    pass\n"
    )
    (tmp_path / "backend/services/auth_service.py").write_text(
        "class AuthService:\n"
        "    def authenticate(self, email, password):\n"
        "        pass\n"
    )
    (tmp_path / "backend/models/user.py").write_text(
        "from backend.database import Base\n"
        "class User(Base):\n"
        "    __tablename__ = 'users'\n"
    )
    # An unrelated file that should NOT surface for an auth question.
    (tmp_path / "backend/routes/weather.py").write_text(
        "from fastapi import APIRouter\n"
        "router = APIRouter()\n"
        "@router.get('/api/weather/forecast')\n"
        "def get_forecast(city: str):\n"
        "    pass\n"
    )
    return tmp_path


class TestRetrieval:
    def test_auth_question_surfaces_auth_files_first(self, sample_repo: Path):
        analysis = analyze_local_repo(str(sample_repo))
        results = retrieve_relevant_files(analysis.files, "How does authentication work?", k=3)

        top_paths = [r.path for r in results]
        assert "backend/routes/auth.py" in top_paths
        assert "backend/services/auth_service.py" in top_paths
        assert "backend/routes/weather.py" not in top_paths

    def test_unrelated_question_does_not_surface_auth_files(self, sample_repo: Path):
        analysis = analyze_local_repo(str(sample_repo))
        results = retrieve_relevant_files(analysis.files, "How does the weather forecast endpoint work?", k=2)

        top_paths = [r.path for r in results]
        assert "backend/routes/weather.py" in top_paths

    def test_chunk_text_includes_class_and_function_names(self, sample_repo: Path):
        analysis = analyze_local_repo(str(sample_repo))
        from app.analyzer.retrieval import build_chunk

        auth_file = next(f for f in analysis.files if f.path == "backend/services/auth_service.py")
        chunk = build_chunk(auth_file)
        assert "auth" in chunk.text
        assert "service" in chunk.text
        assert "authenticate" in chunk.text

    def test_no_overlap_returns_empty(self, sample_repo: Path):
        analysis = analyze_local_repo(str(sample_repo))
        results = retrieve_relevant_files(analysis.files, "xyzzyqwerty12345nonsense", k=5)
        assert results == []
