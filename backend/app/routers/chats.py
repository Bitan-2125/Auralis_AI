from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app import models, schemas
from app.services import rag_service

router = APIRouter(prefix="/chats", tags=["chats"])


@router.get("", response_model=List[schemas.ChatOut])
def list_chats(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return (
        db.query(models.Chat)
        .filter(models.Chat.user_id == user.id)
        .order_by(models.Chat.updated_at.desc())
        .all()
    )


@router.post("", response_model=schemas.ChatOut)
def create_chat(
    payload: schemas.ChatCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    chat = models.Chat(user_id=user.id, title=payload.title, default_model=payload.default_model)
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat


def _get_owned_chat(chat_id: str, db: Session, user: models.User) -> models.Chat:
    chat = db.query(models.Chat).filter(models.Chat.id == chat_id, models.Chat.user_id == user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@router.get("/{chat_id}", response_model=schemas.ChatOut)
def get_chat(chat_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return _get_owned_chat(chat_id, db, user)


@router.patch("/{chat_id}", response_model=schemas.ChatOut)
def update_chat(
    chat_id: str,
    payload: schemas.ChatUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    chat = _get_owned_chat(chat_id, db, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(chat, field, value)
    db.commit()
    db.refresh(chat)
    return chat


@router.delete("/{chat_id}")
def delete_chat(chat_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    chat = _get_owned_chat(chat_id, db, user)
    db.delete(chat)
    db.commit()
    rag_service.delete_collection(chat_id)
    return {"ok": True}


@router.get("/{chat_id}/messages", response_model=List[schemas.MessageOut])
def get_messages(chat_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    _get_owned_chat(chat_id, db, user)
    return (
        db.query(models.Message)
        .filter(models.Message.chat_id == chat_id)
        .order_by(models.Message.created_at.asc())
        .all()
    )
