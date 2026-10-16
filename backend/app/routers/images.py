import base64
import asyncio
from contextlib import suppress
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
from app.database import get_db, SessionLocal
from app.deps import get_current_user
from app import models, schemas
from app.routers.chats import _get_owned_chat
from app.services import image_service, generation_lock
from app.config import settings

router = APIRouter(prefix="/images", tags=["images"])


@router.post("/generate", response_model=schemas.ImageGenerateResponse)
async def generate_image(payload: schemas.ImageGenerateRequest, request: Request, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    _get_owned_chat(payload.chat_id, db, user)
    owner_id = user.id
    lease_token = generation_lock.acquire(payload.chat_id)
    db.close()  # Do not hold a PostgreSQL connection while waiting for image inference.
    generation = asyncio.create_task(asyncio.wait_for(image_service.generate(payload.prompt, payload.width, payload.height, payload.model), timeout=settings.generation_timeout_seconds))
    try:
        while not generation.done():
            await asyncio.wait({generation}, timeout=0.25)
            if await request.is_disconnected():
                raise HTTPException(499, "Image generation cancelled")
        encoded, mime = await generation
        # Recheck ownership/existence after the long network request in a fresh session.
        with SessionLocal() as fresh_db:
            chat = _get_owned_chat(payload.chat_id, fresh_db, owner_id)
            user_msg = models.Message(chat_id=chat.id, role="user", content=payload.prompt, model=payload.model)
            reply = models.Message(chat_id=chat.id, role="assistant", content="Here's your generated image.", model=payload.model)
            image = models.GeneratedImage(data=encoded, mime_type=mime)
            reply.generated_image = image
            fresh_db.add_all([user_msg, reply])
            fresh_db.flush()
            reply.image_url = f"/images/{image.id}"
            if chat.title == "New chat":
                chat.title = payload.prompt[:60]
            chat.updated_at = datetime.utcnow()
            fresh_db.commit()
            return schemas.ImageGenerateResponse(url=reply.image_url, message_id=reply.id)
    except TimeoutError:
        raise HTTPException(504, "Image generation timed out. Please retry.") from None
    finally:
        if not generation.done():
            generation.cancel()
        with suppress(asyncio.CancelledError, Exception):
            await generation
        generation_lock.release(payload.chat_id, lease_token)


@router.get("/{image_id}")
def get_image(image_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    image = db.query(models.GeneratedImage).join(models.Message).join(models.Chat).filter(
        models.GeneratedImage.id == image_id, models.Chat.user_id == user.id).first()
    if not image:
        raise HTTPException(404, "Image not found")
    return Response(content=base64.b64decode(image.data), media_type=image.mime_type, headers={"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"})
