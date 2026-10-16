from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from app.database import get_db
from app.deps import get_current_user
from app import models, schemas
from app.routers.chats import _get_owned_chat
from app.services import rag_service

router = APIRouter(prefix="/chats/{chat_id}/documents", tags=["rag"])


@router.get("", response_model=list[schemas.DocumentOut])
def list_documents(chat_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    _get_owned_chat(chat_id, db, user)
    return db.query(models.Document).filter_by(chat_id=chat_id).order_by(models.Document.created_at.asc()).all()


@router.post("", response_model=schemas.DocumentOut)
async def upload_document(chat_id: str, file: UploadFile = File(...), db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    chat = _get_owned_chat(chat_id, db, user)
    if db.query(models.Document).filter_by(chat_id=chat_id).count() >= 20:
        raise HTTPException(400, "Maximum 20 documents per chat")
    raw = await file.read(rag_service.MAX_FILE_BYTES + 1)
    await file.close()
    if len(raw) > rag_service.MAX_FILE_BYTES:
        raise HTTPException(413, f"File too large ({rag_service.MAX_FILE_BYTES // (1024 * 1024)} MB limit)")
    filename = Path((file.filename or "document.txt").replace("\\", "/")).name[:200]
    text = await run_in_threadpool(rag_service.extract_text, filename, raw)
    chunks = rag_service.chunk_text(text)
    if not chunks:
        raise HTTPException(400, "No readable text found. Scanned PDFs need OCR first.")
    if len(chunks) > 1000:
        raise HTTPException(413, "Document has too many chunks")
    doc = models.Document(chat_id=chat_id, filename=filename, chunk_count=len(chunks))
    doc.chunks = [models.DocumentChunk(chunk_index=i, content=text) for i, text in enumerate(chunks)]
    db.add(doc)
    chat.use_rag = True
    db.commit()
    db.refresh(doc)
    return doc


@router.delete("/{document_id}")
def delete_document(chat_id: str, document_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    _get_owned_chat(chat_id, db, user)
    doc = db.query(models.Document).filter_by(id=document_id, chat_id=chat_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    db.delete(doc)
    db.commit()
    return {"ok": True}
