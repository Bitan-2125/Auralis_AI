from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr


# ---------- Auth ----------
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: Optional[str] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Chats ----------
class ChatCreate(BaseModel):
    title: Optional[str] = "New chat"
    default_model: Optional[str] = "openai/gpt-oss-120b"


class ChatUpdate(BaseModel):
    title: Optional[str] = None
    default_model: Optional[str] = None
    use_rag: Optional[bool] = None


class ChatOut(BaseModel):
    id: str
    title: str
    default_model: str
    use_rag: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------- Messages ----------
class MessageCreate(BaseModel):
    content: str
    model: Optional[str] = None       # overrides chat.default_model for this turn
    image_url: Optional[str] = None   # for vision-capable models
    use_rag: Optional[bool] = None    # overrides chat.use_rag for this turn


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    model: Optional[str] = None
    image_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Models ----------
class ModelInfo(BaseModel):
    id: str
    owned_by: Optional[str] = None
    context_window: Optional[int] = None
    supports_vision: bool = False


# ---------- RAG ----------
class DocumentOut(BaseModel):
    id: str
    filename: str
    chunk_count: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Image generation ----------
class ImageGenerateRequest(BaseModel):
    prompt: str
    width: int = 1024
    height: int = 1024
    model: str = "flux"  # free pollinations.ai model options: flux, turbo, etc.


class ImageGenerateResponse(BaseModel):
    url: str
