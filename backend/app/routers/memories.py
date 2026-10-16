from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.deps import get_current_user

router = APIRouter(prefix="/memories", tags=["memory"])


@router.get("", response_model=list[schemas.MemoryOut])
def list_memories(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return db.query(models.Memory).filter_by(user_id=user.id).order_by(models.Memory.created_at.desc()).all()


def save_memory(db, user_id, content):
    existing = db.query(models.Memory).filter_by(user_id=user_id, content=content).first()
    if existing:
        return existing
    if db.query(models.Memory).filter_by(user_id=user_id).count() >= 100:
        raise HTTPException(400, "Memory is full (100 entries). Delete an entry first.")
    memory = models.Memory(user_id=user_id, content=content)
    db.add(memory)
    db.flush()
    return memory


@router.post("", response_model=schemas.MemoryOut)
def add_memory(payload: schemas.MemoryCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    memory = save_memory(db, user.id, payload.content)
    db.commit()
    db.refresh(memory)
    return memory


@router.delete("/{memory_id}")
def delete_memory(memory_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    memory = db.query(models.Memory).filter_by(id=memory_id, user_id=user.id).first()
    if not memory:
        raise HTTPException(404, "Memory not found")
    db.delete(memory)
    db.commit()
    return {"ok": True}
