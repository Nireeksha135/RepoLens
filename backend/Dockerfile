# RepoLens backend. Only relevant if deploying to Render, Fly.io, Railway,
# or another container platform -- the primary/documented path is now
# Vercel (see api/index.py + vercel.json), which doesn't use this at all.
#
# No apt-get / system git needed anymore: repos are fetched via GitHub's
# tarball download (see analyzer/git_source.py), not `git clone`, so this
# image only needs Python + pip dependencies.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Platforms inject $PORT at runtime; default to 8000 for `docker run` without one.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
