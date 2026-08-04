"""
Vercel serverless entrypoint.

Vercel's Python runtime auto-detects a module-level ASGI app named `app`
under api/ and wraps it as a serverless function -- no Mangum or other
adapter needed for FastAPI specifically. This file exists only to satisfy
that convention; all real code lives in app/main.py and is unchanged
whether it's running here, under `uvicorn` locally, or in a Docker
container on Render/Fly.
"""
from app.main import app  # noqa: F401  (re-exported for Vercel's runtime)
