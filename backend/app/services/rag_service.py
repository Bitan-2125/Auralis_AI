"""
RAG pipeline: chunk documents, embed with a local sentence-transformers model,
store/query in ChromaDB. One Chroma collection per chat, named "chat_<chat_id>".
"""
import io
import logging
from typing import List

from app.config import settings

logger = logging.getLogger(__name__)

_chroma_client = None
_embedding_fn = None


def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        try:
            import chromadb
            # If local in-memory or http client
            if settings.chroma_host and settings.chroma_host != "chroma":
                _chroma_client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
            else:
                _chroma_client = chromadb.Client()
        except Exception as e:
            logger.warning(f"ChromaDB initialization fallback: {e}")
            import chromadb
            _chroma_client = chromadb.Client()
    return _chroma_client


def get_embedding_fn():
    global _embedding_fn
    if _embedding_fn is None:
        try:
            from chromadb.utils import embedding_functions
            _embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=settings.embedding_model
            )
        except Exception as e:
            logger.warning(f"Could not load sentence transformer: {e}")
            _embedding_fn = None
    return _embedding_fn


def _collection_name(chat_id: str) -> str:
    return f"chat_{chat_id}".replace("-", "_")


def get_or_create_collection(chat_id: str):
    client = get_chroma_client()
    fn = get_embedding_fn()
    kwargs = {"name": _collection_name(chat_id)}
    if fn:
        kwargs["embedding_function"] = fn
    return client.get_or_create_collection(**kwargs)


def extract_text(filename: str, raw: bytes) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        # Try PyMuPDF (fitz) first, then pypdf
        try:
            import fitz
            doc = fitz.open(stream=raw, filetype="pdf")
            return "\n".join(page.get_text() for page in doc)
        except Exception:
            pass
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(raw))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            pass
    if lower.endswith(".docx"):
        try:
            import docx
            d = docx.Document(io.BytesIO(raw))
            return "\n".join(p.text for p in d.paragraphs)
        except Exception:
            pass
    # Fallback: treat as plain text (.txt, .md, .csv, etc.)
    return raw.decode("utf-8", errors="ignore")


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> List[str]:
    words = text.split()
    if not words:
        return []
    chunks = []
    step = max(chunk_size - overlap, 1)
    for i in range(0, len(words), step):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
        if i + chunk_size >= len(words):
            break
    return chunks


def add_document(chat_id: str, filename: str, raw_bytes: bytes) -> int:
    text = extract_text(filename, raw_bytes)
    chunks = chunk_text(text)
    if not chunks:
        return 0
    try:
        collection = get_or_create_collection(chat_id)
        ids = [f"{filename}-{i}" for i in range(len(chunks))]
        metadatas = [{"filename": filename, "chunk_index": i} for i in range(len(chunks))]
        collection.add(documents=chunks, ids=ids, metadatas=metadatas)
        return len(chunks)
    except Exception as e:
        logger.error(f"Error adding document to RAG collection: {e}")
        return 0


def query(chat_id: str, question: str, n_results: int = 4) -> str:
    try:
        collection = get_or_create_collection(chat_id)
        if collection.count() == 0:
            return ""
        results = collection.query(query_texts=[question], n_results=min(n_results, collection.count()))
        docs = results.get("documents", [[]])[0]
        return "\n\n---\n\n".join(docs)
    except Exception as e:
        logger.error(f"Error querying RAG collection: {e}")
        return ""


def delete_collection(chat_id: str):
    try:
        client = get_chroma_client()
        client.delete_collection(_collection_name(chat_id))
    except Exception:
        pass
