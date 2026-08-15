from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app import models, schemas
from app.services import rag_service

router = APIRouter(prefix="/chats/{chat_id}/documents", tags=["rag"])


def _get_owned_chat(chat_id: str, db: Session, user: models.User) -> models.Chat:
    chat = db.query(models.Chat).filter(models.Chat.id == chat_id, models.Chat.user_id == user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@router.get("", response_model=List[schemas.DocumentOut])
def list_documents(chat_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    _get_owned_chat(chat_id, db, user)
    return db.query(models.Document).filter(models.Document.chat_id == chat_id).all()


@router.post("", response_model=schemas.DocumentOut)
async def upload_document(
    chat_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    chat = _get_owned_chat(chat_id, db, user)
    raw = await file.read()
    if len(raw) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (20MB limit)")

    chunk_count = rag_service.add_document(chat_id, file.filename, raw)
    if chunk_count == 0:
        raise HTTPException(status_code=400, detail="Could not extract any text from this file")

    doc = models.Document(chat_id=chat_id, filename=file.filename, chunk_count=chunk_count)
    db.add(doc)
    chat.use_rag = True  # auto-enable RAG once a doc is attached
    db.commit()
    db.refresh(doc)
    return doc


@router.delete("/{document_id}")
def delete_document(
    chat_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    _get_owned_chat(chat_id, db, user)
    doc = db.query(models.Document).filter(models.Document.id == document_id, models.Document.chat_id == chat_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(doc)
    db.commit()
    # Note: for simplicity we don't selectively remove this doc's vectors from
    # the shared chat collection here - see README "Known simplifications".
    return {"ok": True}
