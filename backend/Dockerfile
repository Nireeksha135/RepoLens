# RepoLens backend. Portable across Render, Fly.io, Railway, or any
# container platform -- nothing platform-specific baked in except reading
# $PORT, which every one of them sets.
FROM python:3.12-slim

# GitPython shells out to a real `git` binary -- python:slim doesn't ship
# one. Cloning is the very first thing /analyze does, so this is not
# optional.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Platforms inject $PORT at runtime; default to 8000 for `docker run` without one.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
