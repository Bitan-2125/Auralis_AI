import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.deps import get_current_user
from app import models, schemas
from app.services import groq_client, rag_service

router = APIRouter(prefix="/chats/{chat_id}/messages", tags=["messages"])


def _get_owned_chat(chat_id: str, db: Session, user: models.User) -> models.Chat:
    chat = db.query(models.Chat).filter(models.Chat.id == chat_id, models.Chat.user_id == user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@router.post("")
async def send_message(
    chat_id: str,
    payload: schemas.MessageCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """
    Streams the assistant's reply as Server-Sent Events.
    Each event is a JSON blob: {"delta": "..."} while streaming, then a final
    {"done": true, "message_id": "..."} once the full reply has been saved.
    """
    chat = _get_owned_chat(chat_id, db, user)
    model = payload.model or chat.default_model
    use_rag = chat.use_rag if payload.use_rag is None else payload.use_rag

    # Persist the user's message immediately.
    user_msg = models.Message(
        chat_id=chat.id, role="user", content=payload.content,
        model=model, image_url=payload.image_url,
    )
    db.add(user_msg)

    # Auto-title new chats from the first message.
    if chat.title in (None, "New chat"):
        chat.title = payload.content[:60]

    db.commit()

    # Build conversation history for context.
    history_rows = (
        db.query(models.Message)
        .filter(models.Message.chat_id == chat.id)
        .order_by(models.Message.created_at.asc())
        .all()
    )
    history = [{"role": m.role, "content": m.content} for m in history_rows[:-1]]  # exclude the just-added user msg

    rag_context = None
    if use_rag:
        rag_context = rag_service.query(chat.id, payload.content) or None

    async def event_stream():
        full_text = ""
        try:
            async for delta in groq_client.stream_chat(
                model=model,
                history=history,
                user_message=payload.content,
                image_url=payload.image_url,
                rag_context=rag_context,
            ):
                full_text += delta
                yield f"data: {json.dumps({'delta': delta})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        # Save the assistant's full reply in a fresh session (the request-scoped
        # session may already be closed by the time streaming finishes).
        with SessionLocal() as fresh_db:
            assistant_msg = models.Message(
                chat_id=chat.id, role="assistant", content=full_text, model=model,
            )
            fresh_db.add(assistant_msg)
            fresh_db.query(models.Chat).filter(models.Chat.id == chat.id).update(
                {"title": chat.title}
            )
            fresh_db.commit()
            fresh_db.refresh(assistant_msg)
            yield f"data: {json.dumps({'done': True, 'message_id': assistant_msg.id})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
