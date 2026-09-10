"""
Thin wrapper around the Groq SDK.

- list_models(): live list pulled from Groq's /models endpoint (falls back to a
  small hardcoded list if the API call fails, e.g. no key set yet).
- stream_chat(): streams a chat completion as an async generator of text chunks.
"""
from typing import AsyncGenerator, List, Optional

from groq import Groq, AsyncGroq

from app.config import settings, VISION_CAPABLE_MODELS, NON_CHAT_MODEL_PREFIXES, RECOMMENDED_CHAT_MODELS

_client: Optional[Groq] = None
_async_client: Optional[AsyncGroq] = None


def get_client() -> Groq:
    global _client
    if _client is None:
        if not settings.groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to backend/.env - get a free key at "
                "https://console.groq.com/keys"
            )
        _client = Groq(api_key=settings.groq_api_key)
    return _client


def get_async_client() -> AsyncGroq:
    global _async_client
    if _async_client is None:
        if not settings.groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to backend/.env - get a free key at "
                "https://console.groq.com/keys"
            )
        _async_client = AsyncGroq(api_key=settings.groq_api_key)
    return _async_client


def list_models() -> List[dict]:
    """Returns chat-capable models currently live on Groq, newest/most relevant first."""
    try:
        client = get_client()
        resp = client.models.list()
        models = []
        for m in resp.data:
            if any(m.id.startswith(p) for p in NON_CHAT_MODEL_PREFIXES):
                continue
            models.append({
                "id": m.id,
                "name": m.id,
                "provider": "Groq",
                "owned_by": getattr(m, "owned_by", "groq"),
                "context_window": getattr(m, "context_window", None),
                "supports_vision": m.id in VISION_CAPABLE_MODELS,
            })
        # Put well-known/recommended models first for a friendlier picker.
        models.sort(key=lambda x: (x["id"] not in RECOMMENDED_CHAT_MODELS, x["id"]))
        return models
    except Exception:
        # Offline / no key yet: fall back to a static list so the UI still renders.
        return [
            {
                "id": mid,
                "name": mid,
                "provider": "Groq",
                "owned_by": "groq",
                "context_window": None,
                "supports_vision": mid in VISION_CAPABLE_MODELS,
            }
            for mid in ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.6-27b", "moonshotai/kimi-k2"]
        ]


def _build_user_content(text: str, image_url: Optional[str]):
    if not image_url:
        return text
    return [
        {"type": "text", "text": text},
        {"type": "image_url", "image_url": {"url": image_url}},
    ]


async def stream_chat(
    model: str,
    history: List[dict],
    user_message: str,
    image_url: Optional[str] = None,
    rag_context: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    history: list of {"role": "user"|"assistant", "content": str}, oldest first.
    Yields text chunks as they stream in from Groq.
    """
    client = get_async_client()

    messages = []
    if rag_context:
        messages.append({
            "role": "system",
            "content": (
                "You are a helpful assistant. Use the following retrieved context "
                "from the user's documents to answer if it's relevant. If the "
                "context doesn't help, answer from your own knowledge and say so.\n\n"
                f"--- Retrieved context ---\n{rag_context}\n--- end context ---"
            ),
        })

    messages.extend(history)
    messages.append({"role": "user", "content": _build_user_content(user_message, image_url)})

    stream = await client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        temperature=0.7,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
