"""
AgentRouter client for multi-model inference via https://agentrouter.org.
Supports streaming responses with required client headers for AgentRouter's API gateway.
"""
import json
import logging
from typing import AsyncGenerator, List, Optional
import httpx

from app.config import settings

logger = logging.getLogger(__name__)

AGENTROUTER_HEADERS = {
    "Authorization": f"Bearer {settings.agentrouter_api_key}",
    "x-api-key": settings.agentrouter_api_key,
    "anthropic-version": "2023-06-01",
    "User-Agent": "claude-cli/1.0.108 (external, cli)",
    "anthropic-beta": "claude-code-20250219,interleaved-thinking-2025-05-14",
    "x-app": "cli",
    "Content-Type": "application/json",
}


def _build_messages(
    history: List[dict],
    user_message: str,
    image_url: Optional[str] = None,
    rag_context: Optional[str] = None,
) -> List[dict]:
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

    for m in history:
        messages.append({"role": m["role"], "content": m["content"]})

    if image_url:
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": user_message},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        })
    else:
        messages.append({"role": "user", "content": user_message})

    return messages


async def stream_chat(
    model: str,
    history: List[dict],
    user_message: str,
    image_url: Optional[str] = None,
    rag_context: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    Streams response deltas from AgentRouter (https://agentrouter.org/v1/chat/completions
    with fallback to /v1/messages if needed).
    """
    messages = _build_messages(history, user_message, image_url, rag_context)

    # First attempt: OpenAI-compatible /v1/chat/completions endpoint
    openai_url = f"{settings.agentrouter_base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "temperature": 0.7,
    }

    headers = dict(AGENTROUTER_HEADERS)
    if settings.agentrouter_api_key:
        headers["Authorization"] = f"Bearer {settings.agentrouter_api_key}"
        headers["x-api-key"] = settings.agentrouter_api_key

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            async with client.stream("POST", openai_url, json=payload, headers=headers) as response:
                if response.status_code == 200:
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        line_str = line.strip()
                        if line_str.startswith("data: "):
                            data_content = line_str[6:].strip()
                            if data_content == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_content)
                                choices = chunk.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content")
                                    if content:
                                        yield content
                            except json.JSONDecodeError:
                                continue
                    return
                else:
                    error_text = await response.aread()
                    logger.warning(
                        f"AgentRouter /v1/chat/completions returned {response.status_code}: {error_text.decode('utf-8', errors='ignore')}"
                    )
        except Exception as e:
            logger.error(f"Error streaming from AgentRouter chat/completions: {e}")

        # Fallback to Anthropic-compatible /v1/messages endpoint
        anthropic_url = f"{settings.agentrouter_base_url.rstrip('/')}/messages"
        # Filter system message for Anthropic format
        anthropic_system = None
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                anthropic_system = msg["content"]
            else:
                anthropic_messages.append({"role": msg["role"], "content": msg["content"]})

        anth_payload = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": 4096,
            "stream": True,
        }
        if anthropic_system:
            anth_payload["system"] = anthropic_system

        async with client.stream("POST", anthropic_url, json=anth_payload, headers=headers) as response:
            if response.status_code != 200:
                err_body = await response.aread()
                raise RuntimeError(
                    f"AgentRouter error ({response.status_code}): {err_body.decode('utf-8', errors='ignore')}"
                )

            async for line in response.aiter_lines():
                if not line:
                    continue
                line_str = line.strip()
                if line_str.startswith("data: "):
                    data_content = line_str[6:].strip()
                    try:
                        chunk = json.loads(data_content)
                        chunk_type = chunk.get("type")
                        if chunk_type == "content_block_delta":
                            delta = chunk.get("delta", {})
                            if "text" in delta:
                                yield delta["text"]
                        elif chunk_type == "message_stop":
                            break
                    except json.JSONDecodeError:
                        continue
