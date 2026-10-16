import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, Text, Integer
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    chats = relationship("Chat", back_populates="owner", cascade="all, delete-orphan")


class Chat(Base):
    __tablename__ = "chats"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, default="New chat")
    default_model = Column(String, default="groq::openai/gpt-oss-20b")
    use_rag = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="chat", cascade="all, delete-orphan")
    generation = relationship("GenerationLease", uselist=False, cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=gen_uuid)
    chat_id = Column(String, ForeignKey("chats.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" | "assistant" | "system"
    content = Column(Text, nullable=False)
    model = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    chat = relationship("Chat", back_populates="messages")
    details = relationship("MessageDetails", uselist=False, cascade="all, delete-orphan")
    generated_image = relationship("GeneratedImage", uselist=False, cascade="all, delete-orphan")

    @property
    def sources(self):
        import json
        return json.loads(self.details.sources_json) if self.details else []


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=gen_uuid)
    chat_id = Column(String, ForeignKey("chats.id"), nullable=False)
    filename = Column(String, nullable=False)
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    chat = relationship("Chat", back_populates="documents")
    chunks = relationship("DocumentChunk", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id = Column(String, primary_key=True, default=gen_uuid)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)


class Memory(Base):
    __tablename__ = "memories"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class MessageDetails(Base):
    __tablename__ = "message_details"
    message_id = Column(String, ForeignKey("messages.id"), primary_key=True)
    sources_json = Column(Text, nullable=False, default="[]")


class GeneratedImage(Base):
    __tablename__ = "generated_images"
    id = Column(String, primary_key=True, default=gen_uuid)
    message_id = Column(String, ForeignKey("messages.id"), nullable=False, unique=True)
    # Store image bytes outside the conversation context and message-list response.
    data = Column(Text, nullable=False)
    mime_type = Column(String, default="image/png", nullable=False)


class GenerationLease(Base):
    __tablename__ = "generation_leases"
    chat_id = Column(String, ForeignKey("chats.id"), primary_key=True)
    token = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
