"""Explicit provider routing and a shared OpenAI-compatible streaming transport."""
import json
import time
import httpx
from fastapi import HTTPException
from app.config import settings, GROQ_FALLBACK_MODELS, NVIDIA_MODELS, VISION_CAPABLE_MODELS, NON_CHAT_MODEL_PREFIXES

_cache = {}


def provider_config(provider):
    configs = {
        "groq": (settings.groq_api_base, settings.groq_api_key, "GROQ_API_KEY"),
        "nvidia": (settings.nvidia_api_base, settings.nvidia_api_key, "NVIDIA_API_KEY"),
        "agentrouter": (settings.agentrouter_base_url, settings.agentrouter_api_key, "AGENTROUTER_API_KEY"),
    }
    if provider not in configs:
        raise HTTPException(400, "Unknown model provider")
    return configs[provider]


def resolve_model(model):
    if "::" in model:
        provider, model_id = model.split("::", 1)
    else:
        # Existing Groq conversations keep working; never guess NVIDIA by slash.
        provider, model_id = "groq", model
    base, key, env_name = provider_config(provider)
    if not model_id or len(model_id) > 200:
        raise HTTPException(400, "Invalid model ID")
    if not key:
        raise HTTPException(503, f"{env_name} is not configured on the server")
    return provider, model_id, base, key


def error_message(provider, status):
    name = {"groq": "Groq", "nvidia": "NVIDIA NIM", "agentrouter": "AgentRouter"}.get(provider, provider)
    reason = {
        400: "rejected this request; check the model and its supported inputs",
        401: "rejected the API key; update the server configuration",
        403: "denied access to this model; check your account permissions",
        404: "could not find this model or endpoint; choose another model",
        410: "has retired this model or endpoint; choose another model",
        402: "requires available credits",
        422: "rejected the request parameters",
        429: "is rate limited or out of quota; try again later",
    }.get(status, "is temporarily unavailable; try again later")
    return f"{name} {reason} (HTTP {status})."


async def list_models():
    result = []
    for provider, label, fallback in [
        ("groq", "Groq", [(mid, mid) for mid in GROQ_FALLBACK_MODELS]),
        ("nvidia", "NVIDIA NIM", NVIDIA_MODELS),
        ("agentrouter", "AgentRouter", [(mid.strip(), mid.strip()) for mid in settings.agentrouter_models.split(",") if mid.strip()]),
    ]:
        base, key, _ = provider_config(provider)
        if provider == "agentrouter" and not key:
            continue
        live = False
        rows = fallback
        # NVIDIA catalog includes embeddings, rerankers and other non-chat models.
        # Keep its picker to the documented chat allowlist, intersected with live IDs.
        if key:
            cached = _cache.get(provider)
            if cached and cached[0] > time.monotonic():
                rows, live = cached[1:]
            else:
                try:
                    async with httpx.AsyncClient(timeout=10) as client:
                        resp = await client.get(f"{base.rstrip('/')}/models", headers={"Authorization": f"Bearer {key}"})
                        resp.raise_for_status()
                        ids = {m["id"] for m in resp.json()["data"]}
                    if provider == "groq":
                        rows = [(mid, mid) for mid in sorted(ids) if not mid.startswith(NON_CHAT_MODEL_PREFIXES)]
                        rows.sort(key=lambda item: (GROQ_FALLBACK_MODELS.index(item[0]) if item[0] in GROQ_FALLBACK_MODELS else 999, item[0]))
                    else:
                        rows = [(mid, name) for mid, name in fallback if mid in ids]
                    live = True
                except (httpx.HTTPError, ValueError, KeyError, TypeError):
                    pass
                _cache[provider] = (time.monotonic() + (300 if live else 30), rows, live)
        for mid, name in rows:
            result.append({
                "id": f"{provider}::{mid}", "name": name, "provider": label,
                "supports_vision": provider == "groq" and mid in VISION_CAPABLE_MODELS,
                "available": bool(key), "catalog_live": live,
            })
    return result


async def complete_chat(model, messages, *, tools=None):
    """Small non-streamed tool-selection request, separate from answer generation."""
    provider, model_id, base, key = resolve_model(model)
    payload = {"model": model_id, "messages": messages, "stream": False,
               "max_tokens": 1024, "temperature": 0}
    if tools:
        payload.update({"tools": tools, "tool_choice": "auto"})
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(40, connect=10)) as client:
            response = await client.post(f"{base.rstrip('/')}/chat/completions",
                                         headers={"Authorization": f"Bearer {key}"}, json=payload)
            if response.status_code != 200:
                raise RuntimeError(error_message(provider, response.status_code))
            result = response.json()["choices"][0]
            if result.get("finish_reason") == "length":
                raise RuntimeError("The search decision was interrupted before completion.")
            message = result["message"]
            if not isinstance(message, dict):
                raise ValueError()
            return message
    except httpx.TimeoutException:
        raise RuntimeError("The search decision timed out.") from None
    except httpx.HTTPError:
        raise RuntimeError("Could not connect to the search decision model.") from None
    except (ValueError, KeyError, IndexError, TypeError):
        raise RuntimeError("The search decision model returned an invalid response.") from None


async def stream_chat(model, messages):
    provider, model_id, base, key = resolve_model(model)
    payload = {"model": model_id, "messages": messages, "stream": True,
               "max_tokens": settings.max_completion_tokens, "temperature": 0.7}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=15)) as client:
            async with client.stream("POST", f"{base.rstrip('/')}/chat/completions",
                                     headers={"Authorization": f"Bearer {key}"}, json=payload) as response:
                if response.status_code != 200:
                    raise RuntimeError(error_message(provider, response.status_code))
                completed = False
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        completed = True
                        break
                    try:
                        event = json.loads(data)
                    except ValueError:
                        raise RuntimeError("The provider returned an invalid streaming response.") from None
                    if event.get("error"):
                        raise RuntimeError("The provider reported an error during generation. Please retry.")
                    for choice in event.get("choices") or []:
                        text = (choice.get("delta") or {}).get("content")
                        if isinstance(text, str) and text:
                            yield text
                        if choice.get("finish_reason"):
                            completed = True
                if not completed:
                    raise RuntimeError("The response stream ended unexpectedly. Please retry.")
    except httpx.TimeoutException:
        raise RuntimeError("The model timed out. Please try again or select a faster model.") from None
    except httpx.HTTPError:
        raise RuntimeError("Could not connect to the model provider. Please try again.") from None
