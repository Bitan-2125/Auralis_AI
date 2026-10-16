from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.database import Base, engine
from app import models  # noqa: F401 - registers models on Base metadata
from app.routers import auth, chats, messages, models_router, images, rag, memories

@asynccontextmanager
async def lifespan(app):
    await run_in_threadpool(Base.metadata.create_all, bind=engine)
    yield
    engine.dispose()

app = FastAPI(title="Auralis Chat API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chats.router)
app.include_router(messages.router)
app.include_router(models_router.router)
app.include_router(images.router)
app.include_router(rag.router)
app.include_router(memories.router)


@app.get("/health")
def health():
    return {"status": "ok"}
