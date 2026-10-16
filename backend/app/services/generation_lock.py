"""Database-backed leases serialize one chat across serverless instances."""
from datetime import datetime, timedelta
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from app.config import settings
from app.database import SessionLocal
from app.models import GenerationLease


def acquire(chat_id):
    token = str(uuid4())
    now = datetime.utcnow()
    with SessionLocal() as db:
        db.query(GenerationLease).filter(GenerationLease.chat_id == chat_id, GenerationLease.expires_at < now).delete()
        db.add(GenerationLease(chat_id=chat_id, token=token,
                               expires_at=now + timedelta(seconds=settings.generation_timeout_seconds + 20)))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "A response is already being generated for this chat") from None
    return token


def release(chat_id, token):
    with SessionLocal() as db:
        db.query(GenerationLease).filter_by(chat_id=chat_id, token=token).delete()
        db.commit()
