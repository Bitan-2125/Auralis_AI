"""NVIDIA-hosted FLUX.2 Klein. Images are persisted by the API layer."""
import asyncio
import base64
import binascii
import httpx
from fastapi import HTTPException
from app.config import settings
from app.services.providers import error_message

IMAGE_MODEL = "nvidia::black-forest-labs/flux.2-klein-4b"


async def generate(prompt, width, height, model):
    if model != IMAGE_MODEL:
        raise HTTPException(400, "Unsupported image model")
    if not settings.nvidia_api_key:
        raise HTTPException(503, "NVIDIA_API_KEY is not configured on the server")
    headers = {"Authorization": f"Bearer {settings.nvidia_api_key}", "Accept": "application/json", "NVCF-POLL-SECONDS": "20"}
    payload = {"prompt": prompt, "width": width,
               "height": height, "cfg_scale": 1, "steps": 4, "samples": 1, "seed": 0}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(180, connect=15)) as client:
            response = await client.post(settings.nvidia_image_url, headers=headers, json=payload)
            request_id = ""
            for _ in range(24):
                if response.status_code != 202:
                    break
                request_id = response.headers.get("nvcf-reqid") or request_id
                # Only an opaque NVIDIA request ID may enter the polling path.
                if not request_id or any(c not in "0123456789abcdefABCDEF-" for c in request_id):
                    raise HTTPException(502, "NVIDIA returned a pending image without a valid request ID")
                await asyncio.sleep(2)
                response = await client.get(f"https://api.nvcf.nvidia.com/v2/nvcf/pexec/status/{request_id}", headers=headers)
            if response.status_code == 202:
                raise HTTPException(504, "Image generation is still pending. Please retry later.")
            if response.status_code != 200:
                raise HTTPException(502, error_message("nvidia", response.status_code))
            data = response.json()
            artifacts = data.get("artifacts") or data.get("data") or []
            if not artifacts:
                raise ValueError("No image")
            artifact = artifacts[0]
            if str(artifact.get("finishReason", "SUCCESS")).upper() in {"CONTENT_FILTERED", "ERROR"}:
                raise HTTPException(422, "The image provider could not generate this prompt. Try a different description.")
            encoded = artifact.get("base64") or artifact.get("b64_json") or ""
            if len(encoded) > 24 * 1024 * 1024:
                raise ValueError("Image too large")
            raw = base64.b64decode(encoded, validate=True)
            if len(raw) > 4 * 1024 * 1024:
                raise ValueError("Image exceeds the response size limit")
            if raw.startswith(b"\x89PNG\r\n\x1a\n"):
                mime = "image/png"
            elif raw.startswith(b"\xff\xd8\xff"):
                mime = "image/jpeg"
            else:
                raise ValueError("Invalid image")
            return encoded, mime
    except httpx.TimeoutException:
        raise HTTPException(504, "Image generation timed out. Please retry.") from None
    except httpx.HTTPError:
        raise HTTPException(502, "Could not connect to NVIDIA image generation") from None
    except (ValueError, KeyError, TypeError, AttributeError, binascii.Error):
        raise HTTPException(502, "NVIDIA returned no valid image. Try another prompt.") from None
