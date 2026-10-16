import asyncio
import json
import re
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db, SessionLocal
from app.deps import get_current_user
from app.config import settings, VISION_CAPABLE_MODELS
from app import models, schemas
from app.routers.chats import _get_owned_chat
from app.routers.memories import save_memory
from app.services import providers, rag_service, context_service, web_search, generation_lock, image_storage

router = APIRouter(prefix="/chats/{chat_id}/messages", tags=["messages"])


def event(data):
    return "data: " + json.dumps(data, ensure_ascii=False) + "\n\n"


@router.post("")
async def send_message(chat_id: str, payload: schemas.MessageCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    chat = _get_owned_chat(chat_id, db, user)
    model = payload.model or chat.default_model
    memory_match = re.fullmatch(r"remember(?: that)?\s*:\s*(.+)", payload.content, re.I | re.S) if payload.use_memory else None
    if not memory_match:
        provider, mid, _, _ = providers.resolve_model(model)
        if payload.image_url and not (provider == "groq" and mid in VISION_CAPABLE_MODELS):
            raise HTTPException(400, "Choose a vision-capable Groq model to attach an image")
    lease_token = generation_lock.acquire(chat_id)
    try:
        memory_saved = None
        if memory_match:
            fact = memory_match.group(1).strip()
            if len(fact) > 1000:
                raise HTTPException(400, "A saved memory must be 1000 characters or fewer")
            memory_saved = save_memory(db, user.id, fact).id
        history = db.query(models.Message).filter_by(chat_id=chat_id).order_by(models.Message.created_at.asc(), models.Message.id.asc()).all()
        sources = rag_service.query(db, chat_id, payload.content) if (chat.use_rag if payload.use_rag is None else payload.use_rag) else []
        memories = db.query(models.Memory).filter_by(user_id=user.id).order_by(models.Memory.created_at.desc()).all() if payload.use_memory else []
        # Copy needed ORM attributes before the request session closes for streaming.
        history = [models.Message(role=row.role, content=row.content) for row in history]
        memories = [models.Memory(content=row.content) for row in memories]
        has_documents = bool(sources)
        document_sources = sources
        api_messages, history_count, sources, memory_count = context_service.build_messages(history, payload.content, memories, document_sources, payload.image_url)
        safe_sources = [{k: v for k, v in source.items() if k != "text"} for source in sources]
        user_msg = models.Message(chat_id=chat_id, role="user", content=payload.content, model=model, image_url=payload.image_url)
        db.add(user_msg)
        image_storage.attach_user_image(user_msg, payload.image_url, db)
        if chat.title == "New chat":
            chat.title = payload.content[:60]
        chat.default_model = model
        chat.updated_at = datetime.utcnow()
        db.commit()
        user_message_id = user_msg.id

    except BaseException:
        db.rollback()
        generation_lock.release(chat_id, lease_token)
        raise

    async def generate_events():
        text = ""
        answer_sources = safe_sources
        try:
            yield event({"meta": True, "sources": safe_sources, "history_messages": history_count,
                         "memory_count": memory_count, "memory_saved": memory_saved, "user_message_id": user_message_id})
            if memory_saved:
                text = "Saved to memory. You can review or delete it in the Memory panel."
                yield event({"delta": text})
            else:
                web_sources = []
                web_status = "off"
                if payload.web_search == "auto":
                    if not settings.tavily_api_key:
                        web_status = "not configured"
                        yield event({"warning": "Automatic web search is unavailable: TAVILY_API_KEY is not configured."})
                    else:
                        web_status = "not needed"
                        yield event({"status": "deciding", "message": "Checking whether web search is needed..."})
                        try:
                            requests = await web_search.plan_search(model, payload.content, history, has_documents)
                            for request in requests:
                                yield event({"status": "searching", "query": request.query, "message": "Searching the web..."})
                                try:
                                    web_sources.extend(await web_search.search(request))
                                except RuntimeError as exc:
                                    web_status = "failed"
                                    yield event({"warning": str(exc)})
                            if requests:
                                web_status = "completed" if web_sources else ("failed" if web_status == "failed" else "no results")
                                if web_status == "no results":
                                    yield event({"warning": "Web search found no usable sources for this question."})
                        except (RuntimeError, HTTPException):
                            web_status = "decision failed"
                            yield event({"warning": "Automatic web search could not be planned. Current facts have not been verified."})
                seen_urls = set()
                combined = []
                for source in [*web_sources, *document_sources]:
                    if source.get("url"):
                        if source["url"] in seen_urls:
                            continue
                        seen_urls.add(source["url"])
                    combined.append({**source, "number": len(combined) + 1})
                answer_messages, used_history, used_sources, used_memories = context_service.build_messages(
                    history, payload.content, memories, combined, payload.image_url, web_status=web_status)
                answer_sources = [{k: v for k, v in source.items() if k != "text"} for source in used_sources]
                yield event({"meta": True, "sources": answer_sources, "history_messages": used_history,
                             "memory_count": used_memories, "web_status": web_status})
                yield event({"status": "answering", "message": "Writing your answer..."})
                async for delta in providers.stream_chat(model, answer_messages):
                    text += delta
                    yield event({"delta": delta})
            if not text.strip():
                raise RuntimeError("The model returned no answer. Please choose another model or retry.")
            with SessionLocal() as fresh_db:
                existing_chat = fresh_db.get(models.Chat, chat_id)
                if not existing_chat:
                    yield event({"error": "This chat was deleted during generation."})
                    return
                reply = models.Message(chat_id=chat_id, role="assistant", content=text, model=model)
                reply.details = models.MessageDetails(sources_json=json.dumps(answer_sources))
                fresh_db.add(reply)
                existing_chat.updated_at = datetime.utcnow()
                fresh_db.commit()
                yield event({"done": True, "message_id": reply.id, "sources": answer_sources})
        except asyncio.CancelledError:
            raise
        except RuntimeError as exc:
            yield event({"error": str(exc)})
        except Exception:
            yield event({"error": "Could not finish or save the response. Please retry."})
        finally:
            generation_lock.release(chat_id, lease_token)

    async def event_stream():
        stream = generate_events()
        try:
            async with asyncio.timeout(settings.generation_timeout_seconds):
                async for frame in stream:
                    yield frame
        except TimeoutError:
            yield event({"error": "Generation timed out. Try a shorter request or another model."})
        finally:
            await stream.aclose()

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
