"""
Tests for Feature 5 -- API Explorer.

Same sample_repo shape as the other test files: a login route defined in
auth.py, using auth_service.py (a "service"), touching user.py (a "db
model"), called by authApi.ts and transitively by LoginPage.tsx.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.analyzer.analyzer import analyze_local_repo
from app.analyzer.api_explorer import build_api_routes


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    (tmp_path / "frontend/src/components").mkdir(parents=True)
    (tmp_path / "frontend/src/services").mkdir(parents=True)
    (tmp_path / "backend/routes").mkdir(parents=True)
    (tmp_path / "backend/services").mkdir(parents=True)
    (tmp_path / "backend/models").mkdir(parents=True)

    (tmp_path / "frontend/src/services/authApi.ts").write_text(
        "import axios from 'axios';\n"
        "export async function login(email, password) {\n"
        "  return axios.post('/api/auth/login', { email, password });\n"
        "}\n"
    )
    (tmp_path / "frontend/src/components/LoginPage.tsx").write_text(
        "import React from 'react';\n"
        "import { login } from '../services/authApi';\n"
        "export const LoginPage = () => {\n"
        "  return (<form onSubmit={login}><button>Go</button></form>);\n"
        "};\n"
    )
    (tmp_path / "backend/routes/auth.py").write_text(
        "from fastapi import APIRouter\n"
        "from backend.services.auth_service import AuthService\n"
        "router = APIRouter()\n"
        "service = AuthService()\n"
        "@router.post('/api/auth/login')\n"
        "def login(email: str, password: str):\n"
        "    return service.authenticate(email, password)\n"
    )
    (tmp_path / "backend/services/auth_service.py").write_text(
        "from backend.models.user import User\n"
        "class AuthService:\n"
        "    def authenticate(self, email, password):\n"
        "        return User.find_by_email(email)\n"
    )
    (tmp_path / "backend/models/user.py").write_text(
        "from backend.database import Base\n"
        "class User(Base):\n"
        "    __tablename__ = 'users'\n"
    )
    return tmp_path


def _handlers_from_files(files) -> dict[str, str]:
    handlers = {}
    for f in files:
        for r in f.api_routes:
            if r.handler != "(client call)":
                handlers[f"route::{r.method}:{r.path}"] = r.handler
    return handlers


class TestApiExplorer:
    def test_finds_the_login_route(self, sample_repo: Path):
        analysis = analyze_local_repo(str(sample_repo))
        handlers = _handlers_from_files(analysis.files)
        routes = build_api_routes(analysis.nodes, analysis.edges, handlers)

        assert len(routes) == 1
        route = routes[0]
        assert route.method == "POST"
        assert route.path == "/api/auth/login"

    def test_defined_in_and_controller(self, sample_repo: Path):
        analysis = analyze_local_repo(str(sample_repo))
        handlers = _handlers_from_files(analysis.files)
        route = build_api_routes(analysis.nodes, analysis.edges, handlers)[0]

        assert route.defined_in == "backend/routes/auth.py"
        assert route.controller == "login"

    def test_uses_and_database_model(self, sample_repo: Path):
        analysis = analyze_local_repo(str(sample_repo))
        handlers = _handlers_from_files(analysis.files)
        route = build_api_routes(analysis.nodes, analysis.edges, handlers)[0]

        assert "backend/services/auth_service.py" in route.uses
        assert "backend/models/user.py" in route.database_models

    def test_called_by_includes_transitive_caller(self, sample_repo: Path):
        analysis = analyze_local_repo(str(sample_repo))
        handlers = _handlers_from_files(analysis.files)
        route = build_api_routes(analysis.nodes, analysis.edges, handlers)[0]

        # authApi.ts calls it directly; LoginPage.tsx calls it transitively
        # (imports authApi.ts) -- both should show up, matching the spec's
        # "Used by AddPetModal.tsx" example (two hops from the route).
        assert "frontend/src/services/authApi.ts" in route.called_by
        assert "frontend/src/components/LoginPage.tsx" in route.called_by

    def test_missing_handler_map_degrades_gracefully(self, sample_repo: Path):
        analysis = analyze_local_repo(str(sample_repo))
        route = build_api_routes(analysis.nodes, analysis.edges, handlers=None)[0]
        assert route.controller is None
        # everything else should still resolve without the handler map
        assert route.defined_in == "backend/routes/auth.py"
