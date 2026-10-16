"""Vercel entrypoint: same-origin API plus the built React application."""
from contextlib import asynccontextmanager
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from app.main import app as api_app


@asynccontextmanager
async def lifespan(app):
    async with api_app.router.lifespan_context(api_app):
        yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/api", api_app)
app.mount("/assets", StaticFiles(directory=str(ROOT / "frontend" / "dist" / "assets"), check_dir=False))


@app.get("/{path:path}", include_in_schema=False)
def frontend(path: str):
    index = ROOT / "frontend" / "dist" / "index.html"
    if not index.is_file():
        return JSONResponse({"detail": "Build the frontend first: npm --prefix frontend run build"}, status_code=503)
    return FileResponse(index)
