from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.security import decode_access_token
from app import models

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    user_id = decode_access_token(token)
    user = db.get(models.User, user_id) if user_id else None
    if not user or not user.is_active:
        raise HTTPException(401, "Please sign in again", headers={"WWW-Authenticate": "Bearer"})
    return user
