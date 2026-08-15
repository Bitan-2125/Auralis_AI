# Groq Chat — Multi-user AI Chat with History, Model Picker, RAG & Image Gen

A full-stack chat application:

- **Backend:** FastAPI (Python) + PostgreSQL (users, chats, messages) + ChromaDB (RAG vectors)
- **Frontend:** React (Vite) + Tailwind CSS
- **LLMs:** Groq (live model list, user picks per-chat or per-message) + free image generation (Pollinations.ai, no key needed)
- **Auth:** Email/password with JWT, multi-user, each user only sees their own chats
- **RAG:** Upload PDF/DOCX/TXT/MD/CSV per chat → chunked, embedded locally (sentence-transformers), stored in Chroma, retrieved automatically when RAG is on

## 1. Get a free Groq API key

Sign up at https://console.groq.com/keys — Groq's free developer tier covers everything here.

## 2. Configure environment

```bash
cp backend/.env.example backend/.env
# then edit backend/.env and paste your GROQ_API_KEY, and set a real SECRET_KEY
```

## 3. Run everything with Docker

```bash
docker compose up --build
```

This starts:
- Postgres on `localhost:5432`
- ChromaDB on `localhost:8001`
- FastAPI backend on `localhost:8000` (docs at `/docs`)
- React frontend on `localhost:5173`

Open **http://localhost:5173**, register an account, and start chatting.

## 4. Running without Docker (local dev)

**Backend**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# run local Postgres + Chroma separately, or point DATABASE_URL/CHROMA_HOST at hosted instances
uvicorn app.main:app --reload
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

## How the pieces fit together

- **Model picker** (`GET /models/chat`) calls Groq's live `/models` endpoint on every request, so the dropdown always reflects whatever Groq currently hosts — no hardcoded, stale model list to maintain. A small curated map in `backend/app/config.py` (`VISION_CAPABLE_MODELS`) flags which of those models accept image input, since Groq's API doesn't expose that itself; update that set when Groq ships/retires vision models.
- **Chat streaming** — `POST /chats/{id}/messages` streams the assistant's reply token-by-token over Server-Sent Events, and only writes the full assistant message to Postgres once the stream completes.
- **RAG** — each chat gets its own Chroma collection (`chat_<id>`). Uploaded documents are chunked (~800 words, 120-word overlap), embedded locally with `all-MiniLM-L6-v2` (no external embedding API needed), and the top-k chunks are injected as system context on each turn when "Use RAG" is checked.
- **Image generation** — the "Generate image" tab calls Pollinations.ai (free, keyless) with the chosen style (`flux`/`turbo`). To add a paid provider (e.g. Stability AI) later, extend `backend/app/services/image_service.py`.
- **Vision Q&A** — pick a model flagged `supports_vision` and attach an image URL with your message; it's passed straight through as multimodal content to Groq.

## Known simplifications (worth hardening for a real production deploy)

- Deleting a single uploaded document doesn't currently remove just its vectors from the shared per-chat Chroma collection (deleting the whole chat does clean up the collection). For per-document deletion, track chunk IDs per document and call `collection.delete(ids=...)`.
- No refresh-token rotation — JWTs are long-lived (7 days) for simplicity; add refresh tokens for a stricter session model.
- No rate limiting / per-user quotas on Groq calls — add `slowapi` or a gateway if exposing this publicly.
- Alembic migrations aren't set up; tables are created via `Base.metadata.create_all` on startup. Add Alembic before you need real schema migrations.
- No file storage for uploaded documents themselves (only their extracted text goes into Chroma) — add S3/blob storage if you need the originals kept.
