"""
Tests for Feature 4 -- Change Impact Analysis.

Reuses the same sample_repo fixture shape as test_analyzer.py (a File
mirroring PetPal's login flow) so the impact chain has a known, checkable
shape:

    LoginPage.tsx --imports--> authApi.ts --calls--> route
    auth.py --defines--> route
    auth.py --imports--> auth_service.py --imports--> user.py

If user.py changes, impact should flow UP through auth_service.py to
auth.py, then across to the route, then to authApi.ts and LoginPage.tsx --
i.e. everything in that chain, at increasing severity as hop count grows.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.analyzer.analyzer import analyze_local_repo
from app.analyzer.impact import analyze_impact


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


class TestImpactAnalysis:
    def test_changing_user_model_impacts_the_whole_chain(self, sample_repo: Path):
        analysis = analyze_local_repo(str(sample_repo))
        result = analyze_impact(analysis.nodes, analysis.edges, "backend/models/user.py")

        impacted_ids = {n.id for n in result.impacted}
        assert "backend/services/auth_service.py" in impacted_ids
        assert "backend/routes/auth.py" in impacted_ids
        assert "route::POST:/api/auth/login" in impacted_ids
        assert "frontend/src/services/authApi.ts" in impacted_ids
        assert "frontend/src/components/LoginPage.tsx" in impacted_ids

    def test_severity_increases_with_distance(self, sample_repo: Path):
        analysis = analyze_local_repo(str(sample_repo))
        result = analyze_impact(analysis.nodes, analysis.edges, "backend/models/user.py")

        by_id = {n.id: n for n in result.impacted}
        # 1 hop away -> HIGH
        assert by_id["backend/services/auth_service.py"].severity == "HIGH"
        assert by_id["backend/services/auth_service.py"].hops == 1
        # further away -> lower severity, never higher than something closer
        auth_py_hops = by_id["backend/routes/auth.py"].hops
        login_page_hops = by_id["frontend/src/components/LoginPage.tsx"].hops
        assert login_page_hops > auth_py_hops

    def test_leaf_node_with_no_dependents_has_empty_impact(self, sample_repo: Path):
        analysis = analyze_local_repo(str(sample_repo))
        # Nothing depends on LoginPage.tsx -- it's the top of the chain.
        result = analyze_impact(analysis.nodes, analysis.edges, "frontend/src/components/LoginPage.tsx")
        assert result.impacted == []

    def test_unknown_target_returns_empty_not_error(self, sample_repo: Path):
        analysis = analyze_local_repo(str(sample_repo))
        result = analyze_impact(analysis.nodes, analysis.edges, "does/not/exist.py")
        assert result.impacted == []

    def test_high_medium_low_buckets_partition_impacted(self, sample_repo: Path):
        analysis = analyze_local_repo(str(sample_repo))
        result = analyze_impact(analysis.nodes, analysis.edges, "backend/models/user.py")
        assert len(result.high) + len(result.medium) + len(result.low) == len(result.impacted)
        assert all(n.severity == "HIGH" for n in result.high)
        assert all(n.severity == "MEDIUM" for n in result.medium)
        assert all(n.severity == "LOW" for n in result.low)
