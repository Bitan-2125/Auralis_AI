from typing import Optional
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.security import decode_access_token
from app import models

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

GUEST_USER_ID = "00000000-0000-0000-0000-000000000001"
GUEST_USER_EMAIL = "guest@auralis.ai"


def _get_or_create_guest_user(db: Session) -> models.User:
    user = db.query(models.User).filter(
        (models.User.id == GUEST_USER_ID) | (models.User.email == GUEST_USER_EMAIL)
    ).first()
    if user is None:
        user = models.User(
            id=GUEST_USER_ID,
            email=GUEST_USER_EMAIL,
            full_name="Guest User",
            hashed_password="guest_no_auth_required",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """
    Returns the authenticated user if a valid token is provided;
    otherwise returns a default persistent guest user so no sign-in is required.
    """
    if token:
        user_id = decode_access_token(token)
        if user_id:
            user = db.query(models.User).filter(models.User.id == user_id).first()
            if user and user.is_active:
                return user

    return _get_or_create_guest_user(db)
