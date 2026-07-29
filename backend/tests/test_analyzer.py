"""
Tests for Feature 1 -- the Repository Analyzer.

Uses a small synthetic repo (built in a pytest tmp_path fixture) that mirrors
the PetPal-style structure from the product spec: a React login page calling
an API, which hits a FastAPI route, which calls a service, which touches a
DB model. The point is to prove the *whole pipeline* -- scan, parse, resolve,
graph -- reproduces that exact chain, not just that each piece works alone.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.analyzer.analyzer import analyze_local_repo
from app.analyzer.js_parser import parse_js_file
from app.analyzer.python_parser import parse_python_file


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


class TestPythonParser:
    def test_extracts_imports(self):
        src = "import os\nfrom foo.bar import Baz, Qux\nfrom . import sibling\n"
        result = parse_python_file(src, "x.py", loc=3)
        modules = [i.module for i in result.imports]
        assert "os" in modules
        assert "foo.bar" in modules
        assert any(i.is_relative for i in result.imports)

    def test_extracts_fastapi_route(self):
        src = (
            "from fastapi import APIRouter\n"
            "router = APIRouter()\n"
            "@router.get('/api/pets')\n"
            "def list_pets():\n"
            "    pass\n"
        )
        result = parse_python_file(src, "routes/pets.py", loc=5)
        assert len(result.api_routes) == 1
        assert result.api_routes[0].method == "GET"
        assert result.api_routes[0].path == "/api/pets"
        assert result.api_routes[0].handler == "list_pets"

    def test_detects_db_model(self):
        src = "from backend.database import Base\nclass Pet(Base):\n    pass\n"
        result = parse_python_file(src, "models/pet.py", loc=3)
        assert result.is_db_model_file is True

    def test_syntax_error_is_captured_not_raised(self):
        result = parse_python_file("def broken(:\n", "bad.py", loc=1)
        assert result.parse_error is not None
        assert result.functions == []


class TestJsParser:
    def test_extracts_named_and_default_imports(self):
        src = "import React from 'react';\nimport { useState, useEffect } from 'react';\n"
        result = parse_js_file(src, "x.tsx", loc=2)
        modules = [i.module for i in result.imports]
        assert modules.count("react") == 2

    def test_detects_react_component(self):
        src = (
            "import React from 'react';\n"
            "export const Widget = () => {\n"
            "  return (<div>hi</div>);\n"
            "};\n"
        )
        result = parse_js_file(src, "Widget.tsx", loc=4)
        assert result.is_react_component_file is True

    def test_detects_axios_call(self):
        src = "import axios from 'axios';\naxios.get('/api/pets').then(r => r.data);\n"
        result = parse_js_file(src, "petApi.ts", loc=2)
        assert len(result.api_routes) == 1
        assert result.api_routes[0].method == "GET"
        assert result.api_routes[0].path == "/api/pets"


class TestEndToEndGraph:
    def test_full_login_chain_resolves(self, sample_repo: Path):
        analysis = analyze_local_repo(str(sample_repo), repo_name="sample")

        assert analysis.total_files == 5
        assert analysis.total_components == 1
        assert analysis.total_db_models == 1
        assert analysis.total_api_endpoints == 1  # one real route (client call doesn't double count as a def)

        edge_pairs = {(e.source, e.target, e.type.value) for e in analysis.edges}

        assert ("frontend/src/components/LoginPage.tsx", "frontend/src/services/authApi.ts", "imports") in edge_pairs
        assert ("backend/routes/auth.py", "backend/services/auth_service.py", "imports") in edge_pairs
        assert ("backend/services/auth_service.py", "backend/models/user.py", "imports") in edge_pairs
        assert ("frontend/src/services/authApi.ts", "route::POST:/api/auth/login", "calls") in edge_pairs
        assert ("backend/routes/auth.py", "route::POST:/api/auth/login", "defines") in edge_pairs

    def test_language_breakdown_sums_to_100(self, sample_repo: Path):
        analysis = analyze_local_repo(str(sample_repo))
        assert pytest.approx(sum(analysis.language_breakdown.values()), abs=0.5) == 100.0

    def test_ignores_node_modules_and_git(self, tmp_path: Path):
        (tmp_path / "node_modules/pkg").mkdir(parents=True)
        (tmp_path / "node_modules/pkg/index.js").write_text("module.exports = {};\n")
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git/config").write_text("junk")
        (tmp_path / "real.py").write_text("x = 1\n")

        analysis = analyze_local_repo(str(tmp_path))
        paths = [f.path for f in analysis.files]
        assert paths == ["real.py"]
        
    def test_python_dot_prefixed_relative_import_resolves(self, tmp_path: Path):
        # Regression test: `from .ctx import X` inside pkg/app.py must resolve
        # to pkg/ctx.py -- the leading dot is a package-level marker, not a
        # literal path character. (This was broken until the level-aware
        # resolver was added; a naive path-join treats ".ctx" as a filename.)
        (tmp_path / "pkg").mkdir()
        (tmp_path / "pkg/app.py").write_text("from .ctx import Context\n")
        (tmp_path / "pkg/ctx.py").write_text("class Context:\n    pass\n")
        (tmp_path / "pkg/sub").mkdir()
        (tmp_path / "pkg/sub/deep.py").write_text("from ..ctx import Context\n")  # level=2

        analysis = analyze_local_repo(str(tmp_path))
        edge_pairs = {(e.source, e.target) for e in analysis.edges}
        assert ("pkg/app.py", "pkg/ctx.py") in edge_pairs
        assert ("pkg/sub/deep.py", "pkg/ctx.py") in edge_pairs
