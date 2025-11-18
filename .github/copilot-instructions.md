## Healthcare-RAG — Copilot Instructions

This file gives concise, actionable guidance for AI coding agents working on this repository. Focus on concrete, discoverable patterns and files.

- Project layout (quick):
  - `backend/` — FastAPI backend. Key files: `backend/app/main.py` (API endpoints), `backend/app/rag_impl.py` (RAG implementation), `backend/requirements.txt`.
  - `frontend/` — React + Vite frontend. Key files: `frontend/src/*`, `frontend/package.json`.
  - `docker-compose.yml` and `start.sh` — primary developer start paths (Docker or local dev).

- Big-picture architecture / data flow (be concrete):
  - User requests hit the FastAPI app in `backend/app/main.py` (endpoints: `/api/query`, `/api/documents`, `/api/health`, `/api/stats`).
  - `main.py` instantiates `HealthcareRAG` (from `rag_impl.py`) either on startup or lazily on first request.
  - `HealthcareRAG` stores vector embeddings in ChromaDB (persist directory: `./backend/data/chroma` as used in the code) and generates embeddings with `sentence-transformers` (`all-MiniLM-L6-v2` by default).
  - Frontend (`frontend/src/components` + `services/api.js`) calls backend endpoints. See `frontend/package.json` scripts (`dev`, `build`, `preview`).

- Quick developer workflows (use these exact commands):
  - Docker (recommended):
    - `docker-compose up -d` (uses `docker-compose.yml`). Backend data is persisted at `./backend/data`.
    - Logs: `docker-compose logs -f`.
  - Local backend (dev):
  - Centralized project environment: at repo root create `.venv`: `python3 -m venv ./.venv && source ./.venv/bin/activate` then `pip install -r requirements.txt`.
    - Run server from repo root: `uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000`.
  - Local frontend: in `frontend/` run `npm install` then `npm run dev` (Vite serves at :3000).
  - Convenience script: `./start.sh` automates Docker or local setup (inspect script for its exact behavior).

- Key integration points and runtime notes:
  - ChromaDB persistence: The backend reads `CHROMA_PERSIST_DIR` (default `./backend/data/chroma`) and will persist vectors there. For production, we recommend hosting this directory on an AWS EBS/EFS volume mounted to the host and referenced by `CHROMA_PERSIST_DIR` in the container.
  - Embedding model: The code reads `EMBEDDING_MODEL` from the environment if present; update `docker-compose.yml` or the env files to change models.

  - AWS deployment: A sample `docker-compose.aws.yml` and `deploy/aws/README.md` are included. The recommended pattern is:
    1. Provision EC2 and attach an EBS or EFS volume.
    2. Mount it at `/data` on the host and set `CHROMA_PERSIST_DIR=/data/chroma`.
    3. Run `docker-compose -f docker-compose.aws.yml up -d --build` on the EC2 host.
  - Sample documents are added automatically when a new collection is created (`_add_sample_data()` in `rag_impl.py`). These are inserted via `add_document()` which creates an id `doc_{hash(content) % 10**8}`.

- API contracts (concise):
  - POST `/api/query` accepts JSON {"question": str, "max_results": int?} and returns {"answer": str, "sources": [{content, metadata, relevance_score}], "confidence": float} — see `main.py` models `QueryRequest`/`QueryResponse`.
  - POST `/api/documents` accepts {"content": str, "metadata": obj?} and returns `{message, document_id}`.

- Observable conventions and gotchas (do not assume otherwise):
  - The backend logs errors with `print()` rather than structured logging. Tests and debug flows should inspect stdout/stderr when reproducing issues.
  - `rag_impl.py` uses synchronous blocking calls (sentence-transformers model loading and encoding). Expect startup delays and memory usage. The embedding model is loaded at `HealthcareRAG` init.
  - The code converts distances to a naive relevance score via `1/(1+distance)` (see `query()` in `rag_impl.py`). If you change retrieval, update any downstream confidence assumptions.
  - README and QUICKSTART are authoritative for dev commands; `start.sh` reflects real behavior—prefer using the script when reproducing developer setup steps.

- Concrete examples to reference in edits or tests:
  - Add document payload: `{ "content": "Example text", "metadata": {"category":"cardiovascular","condition":"hypertension"} }` (see `main.py` `add_document`).
  - Query payload: `{ "question": "What is hypertension?", "max_results": 3 }` and the expected shape in `QueryResponse`.

- Where to look first for common tasks:
  - Change embedding model or add env-driven model selection: `backend/app/rag_impl.py` (and update Docker env in `docker-compose.yml`).
  - Persist path issues: `backend/app/rag_impl.py` persist_directory vs `docker-compose.yml` volume mapping `./backend/data:/app/data`.
  - Frontend → backend API wiring: `frontend/src/services/api.js` and `frontend/package.json` scripts.

- When adding code, prefer minimal, low-risk changes and include a short manual test (curl or example request) in the PR description. Example curl commands are in `README.md` and `QUICKSTART.md`.

If anything above is unclear or you want more detail about a particular area (example: changing model loading, adding CI, or tuning Chroma settings), tell me which area and I will expand the instructions or propose a small patch.
