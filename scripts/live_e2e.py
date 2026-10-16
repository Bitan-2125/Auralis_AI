"""Opt-in end-to-end smoke suite. Uses real providers and an isolated database.

Run: backend/.venv/Scripts/python.exe scripts/live_e2e.py
For a deployed app: add --base-url https://your-app.vercel.app
Only synthetic test accounts and records are created. No credentials are logged.
"""
import argparse
import base64
import io
import json
import os
from pathlib import Path
import secrets
import struct
import sys
import tempfile
import time
from uuid import uuid4
import zlib

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--base-url")
args = parser.parse_args()
temporary = tempfile.TemporaryDirectory()
if not args.base_url:
    os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(temporary.name) / "e2e.db").replace("\\", "/")
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]
import httpx

report = {"target": args.base_url or "local ASGI app with temporary SQLite", "checks": []}


def record(name, action):
    started = time.monotonic()
    try:
        action()
        report["checks"].append({"name": name, "passed": True, "seconds": round(time.monotonic() - started, 2)})
        print("PASS " + name, flush=True)
    except Exception as exc:
        report["checks"].append({"name": name, "passed": False, "error": str(exc)[:300]})
        print("FAIL " + name + ": " + str(exc)[:300], flush=True)


def expect(response, status=200):
    assert response.status_code == status, f"Expected HTTP {status}, received {response.status_code}"
    return response


def red_png():
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
    raw = b"".join(b"\0" + b"\xff\x00\x00" * 128 for _ in range(128))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 128, 128, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def simple_pdf(text):
    stream = f"BT /F1 12 Tf 40 750 Td ({text}) Tj ET".encode()
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>", b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"]
    data = b"%PDF-1.4\n"
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(data)
    data += f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode()
    data += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    return data + f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()


def suite(client):
    created_chats, created_memories = [], []
    email = f"e2e-{uuid4().hex[:12]}@example.com"
    password = secrets.token_urlsafe(24)
    auth = expect(client.post("/api/auth/register", json={"email": email, "password": password, "full_name": "E2E Test"})).json()
    headers = {"Authorization": "Bearer " + auth["access_token"]}
    other = expect(client.post("/api/auth/register", json={"email": f"e2e-{uuid4().hex[:12]}@example.com", "password": password})).json()
    other_headers = {"Authorization": "Bearer " + other["access_token"]}

    def api(method, path, **kwargs):
        return client.request(method, "/api" + path, headers=headers, **kwargs)

    def chat(model="groq::openai/gpt-oss-20b"):
        data = expect(api("POST", "/chats", json={"default_model": model})).json()
        created_chats.append(data["id"])
        return data["id"]

    def send(chat_id, text, **options):
        response = expect(api("POST", f"/chats/{chat_id}/messages", json={"content": text, "web_search": "off", **options}))
        events = [json.loads(frame[6:]) for frame in response.text.split("\n\n") if frame.startswith("data: ")]
        errors = [event["error"] for event in events if event.get("error")]
        assert not errors, "; ".join(errors)
        assert events[-1].get("done"), "Response did not finish with a saved message"
        return "".join(event.get("delta", "") for event in events), events

    def health_auth():
        expect(client.get("/api/health"))
        expect(client.get("/api/chats"), 401)
        expect(client.get("/api/chats", headers={"Authorization": "Bearer invalid"}), 401)
        expect(client.post("/api/auth/login", data={"username": email, "password": password}))
        expect(client.post("/api/auth/login", data={"username": email, "password": "wrong"}), 401)
        assert "text/html" in expect(client.get("/chat/deep-link")).headers["content-type"]
    record("login, expired tokens, same-origin API and SPA deep links", health_auth)

    first = chat()
    def groq_history():
        text, _ = send(first, "For this conversation, the test project code is CEDAR-94731. Reply briefly.")
        assert text.strip()
        text, _ = send(first, "What test project code did I just give you? Reply only with the code.")
        assert "CEDAR-94731" in text
        expect(api("PATCH", f"/chats/{first}", json={"title": "E2E history check"}))
        assert expect(api("GET", f"/chats/{first}")).json()["title"] == "E2E history check"
        assert len(expect(api("GET", f"/chats/{first}/messages")).json()) == 4
        expect(client.get(f"/api/chats/{first}/messages", headers=other_headers), 404)
    record("Groq streaming, follow-up context, history and rename", groq_history)

    second = chat("nvidia::openai/gpt-oss-20b")
    def nvidia_memory():
        send(first, "Remember: My demo workspace nickname is Violet Harbor.")
        memories = expect(api("GET", "/memories")).json()
        created_memories.extend(m["id"] for m in memories)
        text, events = send(second, "What is my saved demo workspace nickname? Answer briefly.")
        assert "violet harbor" in text.casefold(), "Saved memory was not reflected in a new NVIDIA chat"
        assert [event for event in events if event.get("meta")][-1]["memory_count"] > 0
        _, events = send(chat(), "Say hello in one word.", use_memory=False)
        assert [event for event in events if event.get("meta")][-1]["memory_count"] == 0
        for memory_id in created_memories:
            expect(client.delete("/api/memories/" + memory_id, headers=other_headers), 404)
            expect(api("DELETE", "/memories/" + memory_id))
        created_memories.clear()
        assert expect(api("GET", "/memories")).json() == []
    record("NVIDIA streaming, cross-chat memory, disable and deletion", nvidia_memory)

    doc_chat = chat()
    def rag_documents():
        from docx import Document
        document = Document()
        document.add_paragraph("Project Cedar owner is Mira. The retrieval verification token is ORCHID-58291.")
        docx_bytes = io.BytesIO()
        document.save(docx_bytes)
        doc_ids = []
        for filename, data, mime in [
            ("brief.txt", b"Project Cedar approved budget is 41414 rupees.", "text/plain"),
            ("brief.pdf", simple_pdf("Project Cedar deadline is 23 November 2026."), "application/pdf"),
            ("brief.docx", docx_bytes.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ]:
            data = expect(api("POST", f"/chats/{doc_chat}/documents", files={"file": (filename, data, mime)})).json()
            assert data["chunk_count"] > 0
            doc_ids.append(data["id"])
        text, events = send(doc_chat, "According to the Cedar documents, what is the approved budget and who is its owner? Answer briefly.", web_search="auto")
        assert "41414" in text.replace(",", "") and "mira" in text.casefold()
        assert not any(event.get("status") == "searching" for event in events), "Document-only question triggered public web search"
        assert events[-1]["sources"]
        history = expect(api("GET", f"/chats/{doc_chat}/messages")).json()
        assert history[-1]["sources"], "Citations were not persisted"
        _, disabled = send(doc_chat, "Say hello.", use_rag=False)
        assert disabled[-1]["sources"] == []
        for doc_id in doc_ids:
            expect(api("DELETE", f"/chats/{doc_chat}/documents/{doc_id}"))
        assert expect(api("GET", f"/chats/{doc_chat}/documents")).json() == []
        _, events = send(doc_chat, "Which Cedar document passages are available now?")
        assert events[-1]["sources"] == []
    record("TXT, PDF and DOCX ingestion, RAG answers, source persistence, disable and deletion", rag_documents)

    def vision():
        vision_models = [model for model in expect(api("GET", "/models/chat")).json() if model["supports_vision"] and model["available"]]
        assert vision_models, "No configured vision model"
        vision_chat = chat(vision_models[0]["id"])
        url = "data:image/png;base64," + base64.b64encode(red_png()).decode()
        text, _ = send(vision_chat, "What single color fills this image? Answer with the color only.", image_url=url)
        assert "red" in text.casefold()
        history = expect(api("GET", f"/chats/{vision_chat}/messages")).json()
        assert history[0]["image_url"].startswith("/images/")
        assert len(json.dumps(history)) < 10000, "History contains embedded image bytes"
        expect(api("GET", history[0]["image_url"]))
        expect(client.get("/api" + history[0]["image_url"], headers=other_headers), 404)
    record("vision attachment, compact history and private image access", vision)

    def automatic_search():
        web_chat = chat()
        _, events = send(web_chat, "What is 2 + 2? Reply only with the answer.", web_search="auto")
        assert not any(event.get("status") == "searching" for event in events)
        _, events = send(web_chat, "Find recent official NVIDIA NIM product announcements and cite your sources. Answer in under 100 words.", web_search="auto")
        assert any(event.get("status") == "searching" for event in events), "No automatic search was selected"
        sources = [source for source in events[-1]["sources"] if source.get("kind") == "web"]
        assert sources and all(source["url"].startswith(("https://", "http://")) for source in sources)
        history = expect(api("GET", f"/chats/{web_chat}/messages")).json()
        assert any(source["kind"] == "web" for source in history[-1]["sources"])
        nvidia_chat = chat("nvidia::openai/gpt-oss-20b")
        _, nvidia_events = send(nvidia_chat, "Find recent official NVIDIA NIM announcements and cite your sources. Answer in under 80 words.", web_search="auto")
        assert any(event.get("status") == "searching" for event in nvidia_events), "NVIDIA-selected chat did not search"
        assert any(source.get("kind") == "web" for source in nvidia_events[-1]["sources"])
    record("automatic search selects fresh lookups, skips arithmetic and saves web sources", automatic_search)

    def image_generation():
        image_chat = chat()
        data = expect(api("POST", "/images/generate", json={"chat_id": image_chat, "prompt": "A blue ceramic teacup on a white table, natural light, product photograph."})).json()
        image = expect(api("GET", data["url"]))
        assert image.headers["content-type"] in {"image/png", "image/jpeg"}
        assert len(image.content) > 1000
        expect(client.get("/api" + data["url"], headers=other_headers), 404)
        history = expect(api("GET", f"/chats/{image_chat}/messages")).json()
        assert len(history) == 2 and history[-1]["image_url"] == data["url"]
        expect(api("DELETE", f"/chats/{image_chat}"))
        created_chats.remove(image_chat)
        expect(api("GET", data["url"]), 404)
    record("live image generation, persistent history, ownership and cascading deletion", image_generation)

    def cleanup():
        for chat_id in created_chats:
            expect(api("DELETE", f"/chats/{chat_id}"))
        for memory_id in created_memories:
            expect(api("DELETE", "/memories/" + memory_id))
        assert expect(api("GET", "/chats")).json() == []
    record("test-data cleanup and chat deletion", cleanup)


try:
    if args.base_url:
        with httpx.Client(base_url=args.base_url.rstrip("/"), timeout=290, follow_redirects=True) as client:
            suite(client)
    else:
        from fastapi.testclient import TestClient
        from index import app
        with TestClient(app) as client:
            suite(client)
finally:
    if not args.base_url:
        from app.database import engine
        engine.dispose()
    temporary.cleanup()
    (ROOT / ".local").mkdir(exist_ok=True)
    destination = ROOT / ".local" / ("deployed-e2e-report.json" if args.base_url else "live-e2e-report.json")
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Report: " + str(destination), flush=True)

if not report["checks"] or not all(check["passed"] for check in report["checks"]):
    raise SystemExit(1)
