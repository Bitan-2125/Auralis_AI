from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: Optional[str] = Field(default=None, max_length=100)

    @field_validator("password")
    @classmethod
    def password_bytes(cls, value):
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes")
        return value


class UserOut(ORMModel):
    id: str
    email: str
    full_name: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ChatCreate(BaseModel):
    title: str = Field(default="New chat", min_length=1, max_length=120)
    default_model: str = "groq::openai/gpt-oss-20b"


class ChatUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=120)
    default_model: Optional[str] = None
    use_rag: Optional[bool] = None


class ChatOut(ORMModel):
    id: str
    title: str
    default_model: str
    use_rag: bool
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=16000)
    model: Optional[str] = None
    image_url: Optional[str] = Field(default=None, max_length=4000000)
    use_rag: Optional[bool] = None
    use_memory: bool = True
    web_search: Literal["auto", "off"] = "auto"

    @field_validator("content")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Message cannot be blank")
        return value.strip()

    @field_validator("image_url")
    @classmethod
    def image_source(cls, value):
        if value and not (value.startswith("https://") or value.startswith(("data:image/png;base64,", "data:image/jpeg;base64,", "data:image/webp;base64,"))):
            raise ValueError("Use an HTTPS image URL or PNG, JPEG, WebP data URL")
        return value


class Source(BaseModel):
    number: int
    kind: Literal["document", "web"] = "document"
    document_id: Optional[str] = None
    filename: Optional[str] = None
    chunk_index: Optional[int] = None
    title: Optional[str] = None
    url: Optional[str] = None
    published_date: Optional[str] = None
    excerpt: str


class MessageOut(ORMModel):
    id: str
    role: str
    content: str
    model: Optional[str] = None
    image_url: Optional[str] = None
    sources: list[Source] = Field(default_factory=list)
    created_at: datetime


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    context_window: Optional[int] = None
    supports_vision: bool = False
    available: bool = True
    catalog_live: bool = False


class DocumentOut(ORMModel):
    id: str
    filename: str
    chunk_count: int
    created_at: datetime


class MemoryCreate(BaseModel):
    content: str = Field(min_length=1, max_length=1000)

    @field_validator("content")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Memory cannot be blank")
        return value.strip()


class MemoryOut(ORMModel):
    id: str
    content: str
    created_at: datetime


class ImageGenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    chat_id: str
    width: int = Field(default=1024, ge=1024, le=1024)
    height: int = Field(default=1024, ge=1024, le=1024)
    model: str = "nvidia::black-forest-labs/flux.2-klein-4b"

    @field_validator("prompt")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Prompt cannot be blank")
        return value.strip()


class ImageGenerateResponse(BaseModel):
    url: str
    message_id: str
